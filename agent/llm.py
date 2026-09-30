"""
llm.py
------
Multi-provider LLM client wrapper supporting NVIDIA NIM (primary), Google Gemini, and Groq.
"""

import json
import os
import time
from typing import Any, Dict, List

import google.generativeai as genai
from dotenv import load_dotenv
from groq import APIError, Groq, NotFoundError, RateLimitError
from openai import OpenAI

# Load environment variables
load_dotenv(r"C:\HHGoa\.env")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nvidia")

_nvidia_client = None
_groq_client = None
_gemini_configured = False


def _get_nvidia_client() -> OpenAI:
    global _nvidia_client
    if _nvidia_client is None:
        api_key = os.environ.get("NVIDIA_API_KEY", NVIDIA_API_KEY)
        base_url = os.environ.get("NVIDIA_BASE_URL", NVIDIA_BASE_URL)
        _nvidia_client = OpenAI(base_url=base_url, api_key=api_key)
    return _nvidia_client


def _init_gemini() -> None:
    global _gemini_configured
    if not _gemini_configured:
        api_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
        genai.configure(api_key=api_key)
        _gemini_configured = True


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _clean_schema_for_gemini(schema: Any) -> Any:
    """Recursively remove fields like additionalProperties not supported by Gemini proto Schema."""
    if isinstance(schema, dict):
        cleaned = {}
        for k, v in schema.items():
            if k == "additionalProperties":
                continue
            cleaned[k] = _clean_schema_for_gemini(v)
        return cleaned
    elif isinstance(schema, list):
        return [_clean_schema_for_gemini(x) for x in schema]
    return schema


def _parse_json_from_text(text: str) -> Any:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown code fences if present
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue
    # Find first { and last }
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(text[s:e+1])
        except json.JSONDecodeError:
            pass
    return None


def _call_nvidia(system_prompt: str, user_prompt: str, response_schema: dict = None) -> Dict[str, Any]:
    api_key = os.environ.get("NVIDIA_API_KEY", NVIDIA_API_KEY)
    if not api_key:
        return {"error": "NVIDIA_API_KEY not set"}

    client = _get_nvidia_client()
    env_model = os.environ.get("NVIDIA_MODEL", NVIDIA_MODEL)
    models_to_try = [env_model]
    for m in ["meta/llama-3.2-11b-vision-instruct", "meta/llama-3.1-70b-instruct"]:
        if m not in models_to_try:
            models_to_try.append(m)

    for model in models_to_try:
        print(f"[LLM:NVIDIA] Trying model: {model}")
        try:
            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt + "\nRespond with valid JSON."},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0,
                "max_tokens": 2000,
            }
            # Only add response_format if the model supports it
            try:
                kwargs["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(**kwargs)
            except Exception:
                # Retry without response_format
                kwargs.pop("response_format", None)
                resp = client.chat.completions.create(**kwargs)

            content = (resp.choices[0].message.content or "{}").strip()
            parsed = _parse_json_from_text(content)
            if isinstance(parsed, dict):
                parsed["_provider"] = "nvidia"
                parsed["_model_used"] = model
                return parsed
            if parsed is not None:
                return {"result": parsed, "_provider": "nvidia", "_model_used": model}
        except Exception as e:
            print(f"[LLM:NVIDIA] Failed on {model} ({type(e).__name__}: {e})")
            continue

    return {"error": "NVIDIA provider failed on all models"}


def _call_gemini(system_prompt: str, user_prompt: str, response_schema: dict = None) -> Dict[str, Any]:
    """Execute completion using Google Gemini."""
    _init_gemini()
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.6-flash", "gemini-pro-latest"]
    last_err = None

    for model_name in models:
        print(f"[LLM:Gemini] Trying model: {model_name}")
        try:
            model = genai.GenerativeModel(model_name)
            config_kwargs: Dict[str, Any] = {
                "temperature": 0,
                "max_output_tokens": 4096,
                "response_mime_type": "application/json",
            }
            if response_schema:
                config_kwargs["response_schema"] = _clean_schema_for_gemini(response_schema)

            gen_config = genai.types.GenerationConfig(**config_kwargs)
            prompt_content = f"{system_prompt}\n\n{user_prompt}"

            response = model.generate_content(prompt_content, generation_config=gen_config)
            text = (response.text or "{}").strip()
            res_dict = _parse_json_from_text(text)
            if isinstance(res_dict, dict):
                res_dict["_provider"] = "gemini"
                res_dict["_model_used"] = model_name
                return res_dict
            if res_dict is not None:
                return {"result": res_dict, "_provider": "gemini", "_model_used": model_name}

        except Exception as exc:
            print(f"[LLM:Gemini] Model {model_name} failed ({type(exc).__name__}: {exc}), trying next...")
            last_err = exc
            time.sleep(1)

    return {"error": f"Gemini provider failed: {last_err}"}


def _call_groq(system_prompt: str, user_prompt: str, response_schema: dict = None) -> Dict[str, Any]:
    """Execute completion using Groq fallback chain."""
    client = _get_groq_client()
    chain_str = os.getenv("GROQ_MODEL_CHAIN", "qwen/qwen3.8-27b,openai/gpt-oss-20b,openai/gpt-oss-120b")
    models = [m.strip() for m in chain_str.split(",") if m.strip()]
    if not models:
        models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    errors = []

    for model in models:
        print(f"[LLM:Groq] Trying model: {model}")
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt + "\nRespond with valid JSON."},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
        }

        for attempt in range(2):
            try:
                resp = client.chat.completions.create(**kwargs)
                content = (resp.choices[0].message.content or "{}").strip()
                res_dict = _parse_json_from_text(content)
                if isinstance(res_dict, dict):
                    res_dict["_provider"] = "groq"
                    res_dict["_model_used"] = model
                    return res_dict
                if res_dict is not None:
                    return {"result": res_dict, "_provider": "groq", "_model_used": model}
                if attempt == 0:
                    continue
                errors.append(f"{model}: JSON decode failed")
                break

            except RateLimitError as rle:
                print(f"[LLM:Groq] Model {model} failed (rate_limit: {rle}), trying next...")
                errors.append(f"{model}: rate_limit")
                time.sleep(2)
                break
            except NotFoundError as nfe:
                print(f"[LLM:Groq] Model {model} failed (not_found: {nfe}), trying next...")
                errors.append(f"{model}: not_found")
                time.sleep(2)
                break
            except APIError as apie:
                print(f"[LLM:Groq] Model {model} failed (api_error: {apie}), trying without json_object constraint...")
                try:
                    kwargs_no_fmt = dict(kwargs)
                    kwargs_no_fmt.pop("response_format", None)
                    resp = client.chat.completions.create(**kwargs_no_fmt)
                    content = (resp.choices[0].message.content or "{}").strip()
                    res_dict = _parse_json_from_text(content)
                    if isinstance(res_dict, dict):
                        res_dict["_provider"] = "groq"
                        res_dict["_model_used"] = model
                        return res_dict
                except Exception as inner_e:
                    print(f"[LLM:Groq] Retry without json_object failed: {inner_e}")
                errors.append(f"{model}: {apie}")
                time.sleep(2)
                break
            except Exception as exc:
                print(f"[LLM:Groq] Model {model} failed ({type(exc).__name__}: {exc}), trying next...")
                errors.append(f"{model}: {exc}")
                time.sleep(2)
                break

    return {"error": f"Groq provider failed: {'; '.join(errors)}"}


def call_llm(system_prompt: str, user_prompt: str, response_schema: dict = None) -> Dict[str, Any]:
    """
    Tries providers in order starting with LLM_PROVIDER ('nvidia' -> 'gemini' -> 'groq').
    Returns parsed JSON response with '_provider' and '_model_used'.
    """
    provider = os.environ.get("LLM_PROVIDER", "nvidia").lower()
    order = [provider] + [p for p in ["nvidia", "gemini", "groq"] if p != provider]

    for p in order:
        print(f"[LLM] Trying provider: {p}")
        try:
            if p == "nvidia":
                result = _call_nvidia(system_prompt, user_prompt, response_schema)
            elif p == "gemini":
                result = _call_gemini(system_prompt, user_prompt, response_schema)
            elif p == "groq":
                result = _call_groq(system_prompt, user_prompt, response_schema)
            else:
                continue

            if "error" not in result:
                return result
            print(f"[LLM] Provider {p} failed: {result.get('error')}")
        except Exception as e:
            print(f"[LLM] Provider {p} raised: {e}")
            continue

    return {"error": "All providers failed"}


def call_llm_with_retry(system_prompt: str, user_prompt: str, response_schema: dict = None, max_retries: int = 2) -> Dict[str, Any]:
    """
    Wraps call_llm with an outer retry loop.
    """
    delay = 1.0
    last_res = {"error": "No attempts made"}

    for attempt in range(max_retries + 1):
        res = call_llm(system_prompt, user_prompt, response_schema)
        if "error" not in res:
            return res
        last_res = res
        if attempt < max_retries:
            time.sleep(delay)
            delay *= 2.0

    return last_res
