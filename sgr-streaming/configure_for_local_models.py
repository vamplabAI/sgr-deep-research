#!/usr/bin/env python3
"""
SGR Local Model Configuration Helper
Automatically configures SGR for optimal local model performance
"""

import os
import yaml
import shutil
import requests
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

def backup_config(config_path):
    """Create backup of existing config"""
    if os.path.exists(config_path):
        backup_path = f"{config_path}.backup"
        shutil.copy2(config_path, backup_path)
        return backup_path
    return None

def get_recommended_models():
    """Return recommended model configurations"""
    return {
        "gemma2:27b": {
            "litellm_name": "sgr-gemma27b",
            "temperature": 0.1,
            "max_tokens": 16000,
            "quality": "Best",
            "description": "Excellent structured output, recommended for production",
            "pull_cmd": "ollama pull gemma2:27b"
        },
        "llama3.1:70b": {
            "litellm_name": "sgr-llama70b", 
            "temperature": 0.1,
            "max_tokens": 16000,
            "quality": "Best",
            "description": "Excellent structured output, very capable",
            "pull_cmd": "ollama pull llama3.1:70b"
        },
        "gemma2:9b": {
            "litellm_name": "sgr-gemma9b",
            "temperature": 0.2,
            "max_tokens": 12000,
            "quality": "Good",
            "description": "Good balance of speed and accuracy",
            "pull_cmd": "ollama pull gemma2:9b"
        },
        "llama3.1:8b": {
            "litellm_name": "sgr-llama8b",
            "temperature": 0.2,
            "max_tokens": 12000,
            "quality": "Good", 
            "description": "Decent structured output, faster inference",
            "pull_cmd": "ollama pull llama3.1:8b"
        },
        "qwen2.5:7b": {
            "litellm_name": "sgr-qwen7b",
            "temperature": 0.2,
            "max_tokens": 12000,
            "quality": "Good",
            "description": "Good structured output, efficient",
            "pull_cmd": "ollama pull qwen2.5:7b"
        }
    }

def check_ollama_running():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_ollama_models():
    """Get list of models from Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get('models', []):
                name = model.get('name', '').replace(':latest', '')
                if name:
                    models.append(name)
            return sorted(models)
        return []
    except Exception as e:
        return []

def pull_ollama_model(model_name: str, console: Console) -> bool:
    """Pull a model using ollama pull"""
    try:
        console.print(f"[yellow]📥 Pulling {model_name}...[/yellow]")
        console.print("[dim]This may take several minutes depending on model size[/dim]")
        
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        if result.returncode == 0:
            console.print(f"✅ [green]Successfully pulled {model_name}[/green]")
            return True
        else:
            console.print(f"❌ [red]Failed to pull {model_name}: {result.stderr}[/red]")
            return False
            
    except subprocess.TimeoutExpired:
        console.print(f"❌ [red]Timeout pulling {model_name}[/red]")
        return False
    except FileNotFoundError:
        console.print("❌ [red]Ollama command not found. Please install Ollama first.[/red]")
        return False
    except Exception as e:
        console.print(f"❌ [red]Error pulling {model_name}: {e}[/red]")
        return False

def show_available_models(console, available_models, recommended_models):
    """Display available and recommended models"""
    
    # Show available models
    if available_models:
        console.print(f"\n[bold green]✅ Available Models in Ollama ({len(available_models)})[/bold green]")
        available_table = Table()
        available_table.add_column("Model", style="cyan")
        available_table.add_column("Status", style="green")
        available_table.add_column("Recommendation", style="dim")
        
        for model in available_models:
            if model in recommended_models:
                quality = recommended_models[model]["quality"]
                desc = recommended_models[model]["description"]
                available_table.add_row(model, "✅ Ready", f"{quality} - {desc}")
            else:
                available_table.add_row(model, "✅ Ready", "Available for use")
        
        console.print(available_table)
    
    # Show recommended models not yet available
    missing_recommended = [m for m in recommended_models.keys() if m not in available_models]
    if missing_recommended:
        console.print(f"\n[bold yellow]📥 Recommended Models Not Yet Downloaded[/bold yellow]")
        rec_table = Table()
        rec_table.add_column("Model", style="cyan")
        rec_table.add_column("Quality", style="bold")
        rec_table.add_column("Description", style="dim")
        rec_table.add_column("Pull Command", style="green")
        
        for model in missing_recommended:
            config = recommended_models[model]
            rec_table.add_row(
                model,
                config["quality"],
                config["description"],
                config["pull_cmd"]
            )
        
        console.print(rec_table)

def configure_sgr_config(console):
    """Configure main SGR config.yaml"""
    console.print("\n[bold cyan]📝 Configuring SGR config.yaml[/bold cyan]")
    
    config_path = "config.yaml"
    example_path = "config.yaml.example"
    
    # Check if example exists
    if not os.path.exists(example_path):
        console.print(f"❌ {example_path} not found!")
        return False
    
    # Backup existing config
    backup_path = backup_config(config_path)
    if backup_path:
        console.print(f"📋 Backed up existing config to {backup_path}")
    
    # Load example config
    with open(example_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Get user preferences
    use_local = Confirm.ask("Use local models via LiteLLM proxy?", default=True)
    
    if use_local:
        # Check Ollama status
        if not check_ollama_running():
            console.print("⚠️ [yellow]Ollama is not running or not accessible at localhost:11434[/yellow]")
            console.print("💡 Start Ollama with: [green]ollama serve[/green]")
            
            if not Confirm.ask("Continue anyway?", default=True):
                return False
        
        # Get available models
        available_models = get_ollama_models()
        recommended_models = get_recommended_models()
        
        # Show model status
        show_available_models(console, available_models, recommended_models)
        
        # Configure for local models
        config['openai']['api_key'] = 'dev-key'
        config['openai']['base_url'] = 'http://localhost:8000/v1'
        
        # Model selection
        if available_models:
            console.print(f"\n[bold]Model Selection[/bold]")
            
            # Combine available and recommended models
            all_models = list(set(available_models + list(recommended_models.keys())))
            all_models.sort()
            
            console.print(f"Available models: {', '.join(available_models)}")
            if len(available_models) != len(all_models):
                missing = [m for m in recommended_models.keys() if m not in available_models]
                console.print(f"Recommended (not downloaded): {', '.join(missing)}")
            
            # Let user choose from available models or download recommended
            selected_model = Prompt.ask(
                "Which model do you want to use?",
                choices=all_models,
                default=available_models[0] if available_models else "gemma2:9b"
            )
            
            # If model not available, offer to download it
            if selected_model not in available_models:
                if selected_model in recommended_models:
                    console.print(f"[yellow]Model {selected_model} not found locally.[/yellow]")
                    if Confirm.ask(f"Download {selected_model}?", default=True):
                        if pull_ollama_model(selected_model, console):
                            available_models.append(selected_model)
                        else:
                            console.print("❌ Failed to download model. Please try manually.")
                            return False
                    else:
                        console.print("❌ Cannot proceed without a model.")
                        return False
            
            # Configure model settings
            if selected_model in recommended_models:
                model_config = recommended_models[selected_model]
                config['openai']['model'] = model_config['litellm_name']
                config['openai']['temperature'] = model_config['temperature']
                config['openai']['max_tokens'] = model_config['max_tokens']
            else:
                # Use generic settings for non-recommended models
                config['openai']['model'] = f"sgr-{selected_model.replace(':', '-')}"
                config['openai']['temperature'] = 0.2
                config['openai']['max_tokens'] = 12000
            
            console.print(f"✅ Configured for {selected_model}")
            
        else:
            console.print("❌ No models available. Please install Ollama and pull some models first.")
            console.print("💡 Try: [green]ollama pull gemma2:9b[/green]")
            return False
        
    else:
        # Configure for OpenAI
        api_key = Prompt.ask("Enter your OpenAI API key")
        config['openai']['api_key'] = api_key
        config['openai']['base_url'] = ""
        config['openai']['model'] = "gpt-4o-mini"
        config['openai']['temperature'] = 0.2
        config['openai']['max_tokens'] = 8000
    
    # Get Tavily API key
    tavily_key = Prompt.ask("Enter your Tavily API key (for web search)")
    config['tavily']['api_key'] = tavily_key
    
    # Save config
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    console.print(f"✅ Saved configuration to {config_path}")
    return True

def update_litellm_config(available_models, recommended_models, console):
    """Update LiteLLM config with available models"""
    proxy_config_path = "proxy/litellm_config.yaml"
    
    try:
        # Load existing config
        with open(proxy_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Create model list from available models
        model_list = []
        
        for model in available_models:
            if model in recommended_models:
                rec_config = recommended_models[model]
                model_entry = {
                    "model_name": rec_config['litellm_name'],
                    "litellm_params": {
                        "model": f"ollama/{model}",
                        "api_base": "http://localhost:11434",
                        "stream": True,
                        "temperature": rec_config['temperature'],
                        "max_tokens": rec_config['max_tokens']
                    }
                }
            else:
                # Generic config for non-recommended models
                model_entry = {
                    "model_name": f"sgr-{model.replace(':', '-')}",
                    "litellm_params": {
                        "model": f"ollama/{model}",
                        "api_base": "http://localhost:11434",
                        "stream": True,
                        "temperature": 0.2,
                        "max_tokens": 12000
                    }
                }
            
            model_list.append(model_entry)
        
        # Update config
        config['model_list'] = model_list
        
        # Save updated config
        with open(proxy_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        console.print(f"✅ Updated {proxy_config_path} with {len(model_list)} models")
        return True
        
    except Exception as e:
        console.print(f"❌ Failed to update LiteLLM config: {e}")
        return False

def configure_litellm_proxy(console):
    """Configure LiteLLM proxy settings"""
    console.print("\n[bold cyan]⚙️ LiteLLM Proxy Configuration[/bold cyan]")
    
    proxy_config_path = "proxy/litellm_config.yaml"
    
    if not os.path.exists(proxy_config_path):
        console.print(f"❌ {proxy_config_path} not found!")
        return False
    
    # Get available models to update proxy config
    available_models = get_ollama_models()
    recommended_models = get_recommended_models()
    
    if available_models:
        console.print("📋 Available models for LiteLLM proxy:")
        
        for model in available_models:
            if model in recommended_models:
                litellm_name = recommended_models[model]['litellm_name']
                console.print(f"  • {litellm_name} -> {model} [recommended]")
            else:
                litellm_name = f"sgr-{model.replace(':', '-')}"
                console.print(f"  • {litellm_name} -> {model}")
        
        # Update the LiteLLM config file
        if Confirm.ask("Update LiteLLM config with these models?", default=True):
            return update_litellm_config(available_models, recommended_models, console)
        else:
            console.print("✅ Keeping existing LiteLLM configuration")
            return True
    else:
        console.print("⚠️ [yellow]No models found in Ollama. Keeping default configuration.[/yellow]")
        return True

def setup_environment(console):
    """Setup environment variables"""
    console.print("\n[bold cyan]🌍 Environment Setup[/bold cyan]")
    
    # Check if user wants debug mode
    enable_debug = Confirm.ask("Enable JSON debug mode?", default=True)
    
    if enable_debug:
        console.print("💡 Add this to your shell profile (.bashrc, .zshrc, etc.):")
        console.print("[green]export SGR_DEBUG_JSON=1[/green]")
        console.print("\nOr run before starting SGR:")
        console.print("[green]SGR_DEBUG_JSON=1 python sgr_streaming.py[/green]")
        console.print("\n💡 Additional debugging tools:")
        console.print("[green]python validate_nextstep_schema.py[/green] - Test schema validation")
        console.print("[green]python validate_nextstep_schema.py logs/debug_file.txt[/green] - Validate specific file")
    
    return True

def show_startup_commands(console):
    """Show commands to start the full stack"""
    console.print("\n[bold cyan]🚀 Startup Commands[/bold cyan]")
    
    console.print("Start the full local model stack:")
    console.print()
    console.print("[bold]1. Start Ollama:[/bold]")
    console.print("   [green]ollama serve[/green]")
    console.print()
    console.print("[bold]2. Start LiteLLM Proxy:[/bold]")
    console.print("   [green]litellm --config proxy/litellm_config.yaml --host 0.0.0.0 --port 8000[/green]")
    console.print()
    console.print("[bold]3. (Optional) Start Airsroute Gateway:[/bold]")
    console.print("   [green]python -m uvicorn proxy.airsroute_gateway.app:app --reload --port 8010[/green]")
    console.print()
    console.print("[bold]4. Test JSON parsing:[/bold]")
    console.print("   [green]python test_json_parsing.py[/green]")
    console.print()
    console.print("[bold]5. Run SGR:[/bold]")
    console.print("   [green]SGR_DEBUG_JSON=1 python sgr_streaming.py[/green]")

def show_model_installation_guide(console):
    """Show guide for installing recommended models"""
    console.print("\n[bold cyan]📥 Model Installation Guide[/bold cyan]")
    
    recommended_models = get_recommended_models()
    
    console.print("To install recommended models, run these commands:")
    console.print()
    
    for model, config in recommended_models.items():
        console.print(f"[bold]{config['quality']}:[/bold] {model}")
        console.print(f"  [green]{config['pull_cmd']}[/green]")
        console.print(f"  {config['description']}")
        console.print()
    
    console.print("💡 Start with gemma2:9b for a good balance of performance and speed")
    console.print("💡 Use gemma2:27b or llama3.1:70b for best structured output quality")

def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]SGR Local Model Configuration Helper[/bold cyan]\n"
        "Automatically configure SGR for optimal local model performance",
        title="⚙️ Setup Wizard"
    ))
    
    # Check if we're in the right directory
    if not os.path.exists("sgr_streaming.py"):
        console.print("❌ Please run this from the sgr-streaming directory")
        return
    
    # Check Ollama status first
    if not check_ollama_running():
        console.print("⚠️ [yellow]Ollama is not running or not found[/yellow]")
        console.print("Please start Ollama first: [green]ollama serve[/green]")
        
        if Confirm.ask("Show model installation guide anyway?", default=True):
            show_model_installation_guide(console)
        return
    
    # Check available models
    available_models = get_ollama_models()
    if not available_models:
        console.print("📥 [yellow]No models found in Ollama[/yellow]")
        show_model_installation_guide(console)
        
        if not Confirm.ask("Continue with configuration anyway?", default=False):
            return
    
    success = True
    
    # Configure main config
    if success:
        success = configure_sgr_config(console)
    
    # Configure LiteLLM proxy
    if success:
        success = configure_litellm_proxy(console)
    
    # Setup environment
    if success:
        success = setup_environment(console)
    
    # Show startup commands
    if success:
        show_startup_commands(console)
        
        console.print(f"\n🎉 [bold green]Configuration complete![/bold green]")
        console.print("💡 Run the startup commands above to begin using SGR with local models")
    else:
        console.print(f"\n❌ [bold red]Configuration failed![/bold red]")
        console.print("Please check the errors above and try again")

if __name__ == "__main__":
    main()