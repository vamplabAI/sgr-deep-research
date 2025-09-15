#!/usr/bin/env python3

import yaml
import os

def debug_config():
    print("=== Config Debug ===")
    
    # Check environment variables
    print(f"OPENAI_BASE_URL env: {os.getenv('OPENAI_BASE_URL', 'NOT SET')}")
    
    # Load YAML config
    try:
        with open('sgr-streaming/config.yaml', 'r') as f:
            yaml_config = yaml.safe_load(f)
        print(f"YAML base_url: {yaml_config.get('openai', {}).get('base_url', 'NOT SET')}")
    except Exception as e:
        print(f"Error loading YAML: {e}")
    
    # Simulate the SGR config loading logic
    config = {
        'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
        'openai_base_url': os.getenv('OPENAI_BASE_URL', ''),
        'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
    }
    
    print(f"Initial config base_url: '{config['openai_base_url']}'")
    
    # Load from YAML (simulating SGR logic)
    try:
        with open('sgr-streaming/config.yaml', 'r') as f:
            yaml_config = yaml.safe_load(f)
            if 'openai' in yaml_config:
                openai_cfg = yaml_config['openai']
                config['openai_base_url'] = openai_cfg.get('base_url', config['openai_base_url'])
                print(f"After YAML merge base_url: '{config['openai_base_url']}'")
    except Exception as e:
        print(f"Error in YAML merge: {e}")
    
    print(f"Final config base_url: '{config['openai_base_url']}'")
    print(f"Bool check: {bool(config['openai_base_url'])}")

if __name__ == "__main__":
    debug_config()