# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI

client = OpenAI(
    api_key="sk-b144893266434ceb9ac1815e744ac902",
    base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}}
)

print(response.choices[0].message.content)

from openai import OpenAI

client = OpenAI(
    api_key="14b46e4c89644530b635349585de686e.rxvc0824HAu7VLRS",
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

response = client.chat.completions.create(
    model="glm-4.6v-flash",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://cdn.bigmodel.cn/static/logo/register.png"
                    }
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://cdn.bigmodel.cn/static/logo/api-key.png"
                    }
                },
                {
                    "type": "text",
                    "text": "这些图片讲的是什么内容？"
                }
            ]
        }
    ],
    extra_body={
            "thinking": {
                "type": "enabled",
            },
        }
)
print(response.choices[0].message)

stream = client.chat.completions.create(
    model="autoglm-phone",
    messages=[
        {"role": "user", "content": "写一首关于人工智能的诗，不超过50字"}
    ],
    stream=True,
    temperature=0.8
)
print("Streamed response: ", stream)
for chunk in stream:
    # print(chunk, end="", flush=True)
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)

print()  # 换行


import requests

url = "https://open.bigmodel.cn/api/paas/v4/rerank"

payload = {
    "model": "rerank",
    "query": "查询候选文本A",
    "documents": ["需要打分的候选文本A", "需要打分的候选文本B"],
    "top_n": 4
}
headers = {
    "Authorization": "Bearer 14b46e4c89644530b635349585de686e.rxvc0824HAu7VLRS",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)