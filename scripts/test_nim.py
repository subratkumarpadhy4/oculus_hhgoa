import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv('C:/HHGoa/.env')

model = os.environ['NVIDIA_MODEL']
print('Testing model:', model)

client = OpenAI(
    base_url=os.environ['NVIDIA_BASE_URL'],
    api_key=os.environ['NVIDIA_API_KEY']
)

try:
    resp = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': 'Return JSON with key status and value ok'}],
        max_tokens=100
    )
    print('Response:', resp.choices[0].message.content)
    print('SUCCESS')
except Exception as e:
    print('FAILED:', e)