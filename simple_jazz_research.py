#!/usr/bin/env python3

import yaml
from openai import OpenAI

def load_config():
    with open('sgr-streaming/config.yaml', 'r') as f:
        return yaml.safe_load(f)

def research_jazz():
    config = load_config()
    openai_config = config.get('openai', {})
    
    client = OpenAI(
        api_key=openai_config.get('api_key', 'dev-key'),
        base_url=openai_config.get('base_url', 'http://localhost:8000/v1')
    )
    
    print("🎵 Researching the Origins of Jazz Music 🎵\n")
    
    # Simple research prompt
    prompt = """Research the origins of Jazz music. Provide key facts about:
1. Where jazz originated
2. When jazz developed
3. Key influences and musical elements
4. Important early musicians
5. How jazz spread

Respond with clear, factual information in a readable format."""
    
    try:
        response = client.chat.completions.create(
            model=openai_config.get('model', 'sgr-llama2'),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        
        print("📋 Research Results:")
        print("=" * 50)
        print(response.choices[0].message.content)
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Research failed: {e}")

if __name__ == "__main__":
    research_jazz()