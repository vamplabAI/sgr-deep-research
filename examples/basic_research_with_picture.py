import base64

import requests
from openai import OpenAI

# Initialize client
client = OpenAI(
    base_url="http://localhost:8010/v1",
    api_key="dummy",  # Not required for local server
)

# Image URL
image_url = (
    "https://foxprotectioninternational.org/wp-content/uploads/"
    "2020/09/Arctic-fox-summer-coat-Eric-Kilby-CC-BY-SA2.0-1024x683.jpg"
)

# Download image
response_img = requests.get(image_url)
response_img.raise_for_status()

# Сonvert image to base64
img_base64 = base64.b64encode(response_img.content).decode("utf-8")

# Format image data url
img_data_url = f"data:image/jpeg;base64,{img_base64}"

# Make research request
response = client.chat.completions.create(
    model="custom_research_agent",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's on picture?"},
                {"type": "image_url", "image_url": {"url": img_data_url}},
            ],
        }
    ],
    stream=True,
    temperature=0.4,
)

# Print streaming response
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
