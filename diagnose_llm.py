import os
from dotenv import load_dotenv
from agent.mcp_client import MCPClient
from agent.llm import call_llm_with_retry

load_dotenv()

# Test 1 — basic LLM call
print("=== TEST 1: basic LLM call ===")
result = call_llm_with_retry(
    "You are a fraud analyst. Reply with valid JSON only.",
    'Return {"status": "ok"} as JSON.'
)
print("Result:", result)
print()

# Test 2 — with real evidence
print("=== TEST 2: LLM with real evidence ===")
c = MCPClient()
txn = c.get_transaction_context('3514030')
print("Transaction context retrieved:", "error" not in txn)
similar = c.find_similar_cases('C12382', 'customer', 5)
print("Similar cases retrieved:", len(similar.get('similar_cases', [])))

system_prompt = "You are a fraud analyst. Reply with valid JSON only."
user_prompt = "Evidence: " + str(txn)[:500] + "\nPrior cases: " + str(similar)[:500] + "\nReturn JSON with a 'recommendation' field."

result2 = call_llm_with_retry(system_prompt, user_prompt)
print("Result:", result2)