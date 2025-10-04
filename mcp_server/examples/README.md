# Kotaemon MCP Server Examples

This directory contains example scripts and utilities to help you get started with the kotaemon MCP server.

## Files

### `client_demo.py`
A comprehensive demonstration script showing how to interact with the kotaemon MCP server using various tools. This script provides examples of:

- Basic server operations (status, health checks)
- Document indexing and management
- Question answering with different reasoning strategies
- GraphRAG operations
- Advanced features like collection export

**Usage:**
```bash
# Note: Requires MCP client libraries
pip install mcp
python client_demo.py
```

### `test_server.py`
A comprehensive test suite that validates kotaemon MCP server functionality using mock responses. This script can be run independently without requiring MCP client libraries or full kotaemon setup.

**Features:**
- Tests all major server operations
- Validates error handling
- Performance testing with larger datasets
- No external dependencies beyond Python standard library

**Usage:**
```bash
python test_server.py
```

### `claude_config_helper.py`
A configuration helper script that automatically generates the correct Claude Desktop configuration for using kotaemon as an MCP server.

**Features:**
- Automatically detects kotaemon installation path
- Generates proper Claude Desktop configuration
- Includes environment variables from .env file
- Validates installation requirements

**Usage:**
```bash
python claude_config_helper.py
```

## Getting Started

### 1. Test the Server
Start by running the test suite to ensure everything is working:

```bash
python test_server.py
```

### 2. Configure Claude Desktop
Use the configuration helper to set up Claude Desktop:

```bash
python claude_config_helper.py
```

### 3. Run Examples
Try the client demo to see all features in action:

```bash
# Install MCP client libraries first
pip install mcp
python client_demo.py
```

## Example Configurations

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "kotaemon": {
      "command": "python",
      "args": ["/path/to/kotaemon/mcp_server/enhanced_server.py"],
      "env": {
        "KOTAEMON_DATA_DIR": "/path/to/kotaemon/ktem_app_data",
        "OPENAI_API_KEY": "your_api_key",
        "PYTHONPATH": "/path/to/kotaemon:/path/to/kotaemon/libs/kotaemon:/path/to/kotaemon/libs/ktem"
      }
    }
  }
}
```

### VS Code MCP Extension Configuration
```json
{
  "mcp.servers": {
    "kotaemon": {
      "command": "python",
      "args": ["/path/to/kotaemon/mcp_server/enhanced_server.py"],
      "env": {
        "KOTAEMON_DATA_DIR": "/path/to/kotaemon/ktem_app_data"
      }
    }
  }
}
```

## Sample Workflows

### Document Indexing Workflow
1. Create a collection
2. Index documents
3. Verify indexing success
4. Test retrieval

```python
# Create collection
{
  "tool": "create_collection",
  "arguments": {
    "collection_name": "research_papers",
    "index_type": "graphrag"
  }
}

# Index documents
{
  "tool": "index_documents", 
  "arguments": {
    "file_paths": ["/path/to/paper1.pdf", "/path/to/paper2.pdf"],
    "collection_name": "research_papers"
  }
}

# Test retrieval
{
  "tool": "retrieve_documents",
  "arguments": {
    "query": "machine learning applications",
    "collection_name": "research_papers"
  }
}
```

### Question Answering Workflow
1. Configure LLM
2. Ask questions with different reasoning types
3. Compare results

```python
# Configure LLM
{
  "tool": "configure_llm",
  "arguments": {
    "provider": "openai",
    "model": "gpt-4o-mini"
  }
}

# Simple QA
{
  "tool": "answer_question",
  "arguments": {
    "question": "What are the key findings?",
    "reasoning_type": "simple"
  }
}

# GraphRAG QA
{
  "tool": "graphrag_query",
  "arguments": {
    "query": "How do concepts relate?",
    "query_type": "global"
  }
}
```

## Troubleshooting Examples

### Common Issues and Solutions

1. **Server won't start**
   ```bash
   # Check Python path
   which python
   
   # Verify kotaemon installation
   python -c "import kotaemon; print('OK')"
   
   # Check MCP installation
   python -c "import mcp; print('OK')"
   ```

2. **Import errors**
   ```bash
   # Set Python path
   export PYTHONPATH="/path/to/kotaemon:/path/to/kotaemon/libs/kotaemon:/path/to/kotaemon/libs/ktem"
   
   # Or install kotaemon packages
   cd /path/to/kotaemon
   pip install -e libs/kotaemon
   pip install -e libs/ktem
   ```

3. **Configuration issues**
   ```bash
   # Use the configuration helper
   python claude_config_helper.py
   
   # Or manually check config file
   cat ~/.config/claude/claude_desktop_config.json
   ```

## Performance Tips

### For Better Response Times
1. Use local models (Ollama) for faster processing
2. Configure appropriate chunk sizes
3. Enable hybrid search for better relevance
4. Use reranking for improved results

### For Large Document Collections
1. Use GraphRAG for complex reasoning
2. Batch document indexing
3. Configure appropriate embedding dimensions
4. Monitor memory usage

## Security Considerations

### API Key Management
- Store API keys in environment variables
- Use .env files for local development
- Never commit API keys to version control
- Use different keys for different environments

### Data Privacy
- Configure private collections for sensitive data
- Use local models for complete privacy
- Monitor data directory permissions
- Regular backup of indexed data

## Next Steps

1. **Explore Advanced Features**: Try GraphRAG queries, multi-modal document processing, and advanced reasoning strategies
2. **Custom Integration**: Modify the server to add custom tools for your specific use case
3. **Production Deployment**: Configure the server for production use with proper logging and monitoring
4. **Contribute**: Submit improvements and new features to the main kotaemon repository

For more information, see the main README and kotaemon documentation.
