# Kotaemon MCP Server 🚀

A **Model Context Protocol (MCP) server** that exposes kotaemon's powerful RAG capabilities as standardized tools for AI assistants like Claude Desktop, VS Code extensions, and other MCP-compatible clients.

## ✨ Quick Start

### Option 1: Standalone Server (No Dependencies)
```bash
cd kotaemon/mcp_server
python3 standalone_server.py
```
Perfect for testing MCP integration without setting up the full kotaemon environment.

### Option 2: Full Integration with Kotaemon
```bash
cd kotaemon/mcp_server
pip install -r requirements.txt
python3 enhanced_server.py
```
Provides real document processing with full kotaemon capabilities.

### Option 3: Claude Desktop Integration
```bash
cd kotaemon/mcp_server/examples
python3 claude_config_helper.py
```
Automatically configures Claude Desktop to use kotaemon tools.

## 🛠️ Available Tools

### 📚 Document Management (5 tools)
- `list_collections` - View all document collections
- `create_collection` - Create new collections for organizing content  
- `index_documents` - Add documents to collections with various strategies
- `retrieve_documents` - Search documents using hybrid vector/keyword search
- `delete_file` - Remove specific files from collections

### 🤖 Question Answering (3 tools)
- `answer_question` - RAG-based Q&A with multiple reasoning strategies
- `graphrag_query` - Knowledge graph-based question answering
- `get_conversation_history` - Access previous Q&A sessions

### ⚙️ System Management (4 tools)
- `get_server_status` - Comprehensive health and status information
- `configure_llm` - Set up language models (OpenAI, Anthropic, etc.)
- `configure_embeddings` - Configure embedding models
- `export_collection` - Export data to JSON, CSV, Markdown, PDF

## 🔧 Server Options

### 1. Enhanced Server (`enhanced_server.py`)
**Full-featured server with complete kotaemon integration**
- 22 comprehensive tools
- Real document processing
- All kotaemon RAG strategies
- GraphRAG support (Microsoft, Nano, Light)
- Requires kotaemon dependencies

### 2. Basic Server (`server.py`) 
**Simplified server for basic use cases**
- Core functionality only
- Minimal dependencies
- Good for getting started

### 3. Standalone Server (`standalone_server.py`)
**Zero-dependency testing server**
- No kotaemon dependencies required
- Mock responses for all tools
- Perfect for MCP client testing
- Immediate testing capability

## 📋 Configuration

### Environment Setup
Copy the example environment file and configure:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### Claude Desktop Integration
1. Run the configuration helper:
   ```bash
   python3 examples/claude_config_helper.py
   ```

2. Restart Claude Desktop

3. You'll see kotaemon tools available in Claude!

### Manual Configuration
Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kotaemon": {
      "command": "python3",
      "args": ["/path/to/kotaemon/mcp_server/enhanced_server.py"],
      "env": {
        "KOTAEMON_DATA_DIR": "/path/to/kotaemon/ktem_app_data"
      }
    }
  }
}
```

## 🎯 Usage Examples

### Document Indexing with GraphRAG
```python
{
  "tool": "index_documents",
  "arguments": {
    "file_paths": ["/path/to/documents/"],
    "collection_name": "research_papers",
    "index_type": "graphrag",
    "chunk_size": 1000
  }
}
```

### Advanced Question Answering
```python
{
  "tool": "answer_question",
  "arguments": {
    "question": "What are the key ML trends?",
    "reasoning_type": "graphrag",
    "include_sources": true,
    "language": "en"
  }
}
```

### GraphRAG Knowledge Analysis
```python
{
  "tool": "graphrag_query",
  "arguments": {
    "query": "How do AI concepts interconnect?",
    "query_type": "global",
    "community_level": 2
  }
}
```

## 📁 Project Structure

```
kotaemon/mcp_server/
├── enhanced_server.py       # Full MCP server (22 tools)
├── server.py               # Basic MCP server
├── standalone_server.py    # Zero-dependency test server
├── README.md              # This documentation
├── requirements.txt       # Dependencies
├── pyproject.toml         # Package configuration
├── .env.example           # Environment template
└── examples/              # Examples and utilities
    ├── client_demo.py     # Usage demonstrations
    ├── claude_config_helper.py  # Configuration automation
    └── README.md          # Examples documentation
```

## 🔧 Dependencies

### Core Dependencies (for enhanced_server.py)
- `kotaemon` - Core RAG framework
- `mcp` - Model Context Protocol library
- `pydantic` - Data validation
- `asyncio` - Async runtime

### Optional Dependencies
- `openai` - OpenAI API client
- `anthropic` - Anthropic API client
- `chromadb` - Vector database
- `lancedb` - Alternative vector database

See `requirements.txt` for complete list.

## 🚀 Development

### Running Tests
The standalone server includes built-in mock responses for testing:
```bash
python3 standalone_server.py
```

### Adding New Tools
1. Define tool schema in the server class
2. Implement the tool handler method
3. Register the tool in the tools list
4. Update documentation

## 🤝 Contributing

This MCP server is part of the kotaemon project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the standalone server
5. Submit a pull request

## 📄 License

This project follows the same license as kotaemon. See the main repository for details.

## 🔗 Links

- [Kotaemon Repository](https://github.com/Cinnamon/kotaemon)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/download)
- [MCP Specification](https://spec.modelcontextprotocol.io/)

---

**Ready to supercharge your AI workflow with kotaemon's RAG capabilities!** 🎉
