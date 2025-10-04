#!/usr/bin/env python3
"""
Claude Desktop Configuration Helper
Automatically configures Claude Desktop to use the Kotaemon MCP Server
"""

import json
import os
import shutil
from pathlib import Path

def get_claude_config_path():
    """Get the Claude Desktop configuration file path"""
    home = Path.home()
    config_path = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return config_path

def backup_existing_config(config_path):
    """Create backup of existing configuration"""
    if config_path.exists():
        backup_path = config_path.with_suffix('.json.backup')
        shutil.copy2(config_path, backup_path)
        print(f"✅ Existing config backed up to: {backup_path}")
        return True
    return False

def create_kotaemon_config():
    """Create MCP server configuration for kotaemon"""
    current_dir = Path(__file__).parent.absolute()
    server_path = current_dir / "standalone_server.py"
    
    config = {
        "mcpServers": {
            "kotaemon": {
                "command": "python3",
                "args": [str(server_path)],
                "env": {
                    "PYTHONPATH": str(current_dir.parent)
                }
            }
        }
    }
    return config

def merge_configs(existing_config, new_config):
    """Merge new MCP server config with existing config"""
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["kotaemon"] = new_config["mcpServers"]["kotaemon"]
    return existing_config

def main():
    """Main configuration function"""
    print("🔧 Claude Desktop Configuration Helper")
    print("=" * 50)
    print("This tool will configure Claude Desktop to use the Kotaemon MCP Server")
    print()
    
    # Get config path
    config_path = get_claude_config_path()
    print(f"📁 Claude config location: {config_path}")
    
    # Check if Claude Desktop is installed
    if not config_path.parent.exists():
        print("❌ Claude Desktop not found!")
        print("   Please install Claude Desktop first: https://claude.ai/download")
        return False
    
    # Create config directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Backup existing config
    has_existing = backup_existing_config(config_path)
    
    # Load existing config or create new
    if has_existing:
        with open(config_path, 'r') as f:
            existing_config = json.load(f)
        print("📋 Loading existing configuration...")
    else:
        existing_config = {}
        print("📋 Creating new configuration...")
    
    # Create kotaemon MCP config
    kotaemon_config = create_kotaemon_config()
    
    # Merge configurations
    final_config = merge_configs(existing_config, kotaemon_config)
    
    # Save configuration
    with open(config_path, 'w') as f:
        json.dump(final_config, f, indent=2)
    
    print("✅ Configuration saved successfully!")
    print()
    print("📋 Configuration Summary:")
    print(f"   • Server: kotaemon MCP server")
    print(f"   • Path: {kotaemon_config['mcpServers']['kotaemon']['args'][0]}")
    print(f"   • Status: Ready for use")
    print()
    print("🔄 Next Steps:")
    print("1. Restart Claude Desktop application")
    print("2. Open a new conversation in Claude")
    print("3. You should see kotaemon tools available!")
    print()
    print("🎯 Available Tools:")
    print("   • list_collections - View document collections")
    print("   • create_collection - Create new collections")
    print("   • index_documents - Add documents to collections")
    print("   • answer_question - RAG-based question answering")
    print("   • graphrag_query - Knowledge graph analysis")
    print("   • get_server_status - Check server health")
    print()
    print("🚀 Kotaemon MCP Server is now integrated with Claude Desktop!")
    
    return True

def test_config():
    """Test the configuration by loading it"""
    config_path = get_claude_config_path()
    
    if not config_path.exists():
        print("❌ No configuration file found")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if "mcpServers" in config and "kotaemon" in config["mcpServers"]:
            kotaemon_config = config["mcpServers"]["kotaemon"]
            server_path = kotaemon_config["args"][0]
            
            print("✅ Configuration test passed!")
            print(f"   Server path: {server_path}")
            print(f"   Path exists: {Path(server_path).exists()}")
            return True
        else:
            print("❌ Kotaemon configuration not found")
            return False
            
    except json.JSONDecodeError:
        print("❌ Invalid JSON in configuration file")
        return False
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def show_current_config():
    """Display current Claude Desktop configuration"""
    config_path = get_claude_config_path()
    
    if not config_path.exists():
        print("📋 No Claude Desktop configuration found")
        return
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("📋 Current Claude Desktop Configuration:")
        print(json.dumps(config, indent=2))
        
        if "mcpServers" in config:
            print(f"\n🔧 Found {len(config['mcpServers'])} MCP servers configured:")
            for name, server_config in config["mcpServers"].items():
                print(f"   • {name}: {server_config.get('command', 'unknown')} {' '.join(server_config.get('args', []))}")
        else:
            print("\n⚠️  No MCP servers configured")
            
    except Exception as e:
        print(f"❌ Failed to read configuration: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_config()
        elif sys.argv[1] == "show":
            show_current_config()
        else:
            print("Usage: python claude_config_helper.py [test|show]")
    else:
        main()
