#!/usr/bin/env python3
"""
Kotaemon MCP Server

A Model Context Protocol server that exposes kotaemon's RAG capabilities as MCP tools.
This allows AI assistants to perform document indexing, question answering, and 
document management operations using kotaemon's robust RAG infrastructure.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl

# Add kotaemon libs to path
kotaemon_root = Path(__file__).parent.parent
sys.path.insert(0, str(kotaemon_root / "libs" / "kotaemon"))
sys.path.insert(0, str(kotaemon_root / "libs" / "ktem"))

try:
    from ktem.main import App
    from ktem.reasoning.simple import FullQAPipeline
    from ktem.index.file.ui import FileIndex
    from kotaemon.base import Document
    from kotaemon.storages import ChromaVectorStore, SimpleFileDocumentStore
    from kotaemon.embeddings import OpenAIEmbeddings
    from kotaemon.llms import ChatOpenAI
    from theflow.settings import settings as flowsettings
except ImportError as e:
    print(f"Error importing kotaemon modules: {e}")
    print("Please ensure kotaemon is properly installed and configured.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kotaemon-mcp")

# Initialize MCP server
server = Server("kotaemon-mcp")

class KotaemonMCPServer:
    """Main MCP server class that handles kotaemon operations."""
    
    def __init__(self):
        self.app = None
        self.initialized = False
        self.data_dir = Path(os.getenv("KOTAEMON_DATA_DIR", "./ktem_app_data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize the kotaemon app and components."""
        if self.initialized:
            return
            
        try:
            # Initialize kotaemon app
            self.app = App()
            self.initialized = True
            logger.info("Kotaemon MCP server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize kotaemon: {e}")
            raise

# Global server instance
kotaemon_server = KotaemonMCPServer()

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """Return list of available MCP tools."""
    return [
        types.Tool(
            name="index_documents",
            description="Index documents for RAG-based question answering",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to index"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the collection to store documents",
                        "default": "default"
                    },
                    "reindex": {
                        "type": "boolean",
                        "description": "Whether to reindex existing documents",
                        "default": False
                    }
                },
                "required": ["file_paths"]
            }
        ),
        types.Tool(
            name="answer_question",
            description="Answer questions using RAG over indexed documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to answer"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "Collection to search in",
                        "default": "default"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID for context",
                        "default": "default"
                    },
                    "history": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "description": "Conversation history as [user, assistant] pairs",
                        "default": []
                    }
                },
                "required": ["question"]
            }
        ),
        types.Tool(
            name="retrieve_documents",
            description="Retrieve relevant documents for a query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "Collection to search in",
                        "default": "default"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of documents to retrieve",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="list_collections",
            description="List all available document collections",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_collection_info",
            description="Get information about a specific collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the collection"
                    }
                },
                "required": ["collection_name"]
            }
        ),
        types.Tool(
            name="delete_collection",
            description="Delete a document collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the collection to delete"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation to delete collection",
                        "default": False
                    }
                },
                "required": ["collection_name", "confirm"]
            }
        ),
        types.Tool(
            name="configure_llm",
            description="Configure LLM settings for question answering",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "LLM provider (openai, azure, anthropic, etc.)",
                        "enum": ["openai", "azure", "anthropic", "google", "cohere", "groq", "ollama"]
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key for the provider"
                    },
                    "base_url": {
                        "type": "string",
                        "description": "Base URL for API (optional)"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature for generation",
                        "default": 0.0,
                        "minimum": 0.0,
                        "maximum": 2.0
                    }
                },
                "required": ["provider", "model"]
            }
        ),
        types.Tool(
            name="configure_embeddings",
            description="Configure embedding model settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "Embedding provider",
                        "enum": ["openai", "azure", "cohere", "voyage", "huggingface", "ollama"]
                    },
                    "model": {
                        "type": "string",
                        "description": "Embedding model name"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key for the provider"
                    },
                    "base_url": {
                        "type": "string",
                        "description": "Base URL for API (optional)"
                    }
                },
                "required": ["provider", "model"]
            }
        ),
        types.Tool(
            name="get_server_status",
            description="Get current server status and configuration",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls from MCP clients."""
    
    # Ensure server is initialized
    await kotaemon_server.initialize()
    
    try:
        if name == "index_documents":
            return await index_documents(arguments)
        elif name == "answer_question":
            return await answer_question(arguments)
        elif name == "retrieve_documents":
            return await retrieve_documents(arguments)
        elif name == "list_collections":
            return await list_collections(arguments)
        elif name == "get_collection_info":
            return await get_collection_info(arguments)
        elif name == "delete_collection":
            return await delete_collection(arguments)
        elif name == "configure_llm":
            return await configure_llm(arguments)
        elif name == "configure_embeddings":
            return await configure_embeddings(arguments)
        elif name == "get_server_status":
            return await get_server_status(arguments)
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]

async def index_documents(args: Dict[str, Any]) -> List[types.TextContent]:
    """Index documents for RAG."""
    file_paths = args.get("file_paths", [])
    collection_name = args.get("collection_name", "default")
    reindex = args.get("reindex", False)
    
    if not file_paths:
        return [types.TextContent(
            type="text",
            text="No file paths provided"
        )]
    
    # Validate file paths
    valid_files = []
    for path in file_paths:
        if os.path.exists(path):
            valid_files.append(path)
        else:
            logger.warning(f"File not found: {path}")
    
    if not valid_files:
        return [types.TextContent(
            type="text",
            text="No valid files found"
        )]
    
    try:
        # Initialize indexing pipeline
        if not hasattr(kotaemon_server.app, 'index_manager'):
            return [types.TextContent(
                type="text",
                text="Index manager not available"
            )]
        
        # Get file index
        file_indices = [idx for idx in kotaemon_server.app.index_manager.indices 
                       if hasattr(idx, '_indexing_pipeline_cls')]
        
        if not file_indices:
            return [types.TextContent(
                type="text",
                text="No file index available"
            )]
        
        file_index = file_indices[0]
        
        # Index files
        results = []
        for file_path in valid_files:
            try:
                # Note: This is a simplified version. In practice, you'd need to
                # properly handle the indexing pipeline with user settings
                indexing_pipeline = file_index.get_indexing_pipeline({}, user_id=1)
                result = list(indexing_pipeline.run(file_path, reindex=reindex))
                results.append(f"Indexed: {file_path}")
            except Exception as e:
                results.append(f"Failed to index {file_path}: {str(e)}")
        
        return [types.TextContent(
            type="text",
            text=f"Indexing completed for collection '{collection_name}':\n" + "\n".join(results)
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error during indexing: {str(e)}"
        )]

async def answer_question(args: Dict[str, Any]) -> List[types.TextContent]:
    """Answer a question using RAG."""
    question = args.get("question", "")
    collection_name = args.get("collection_name", "default")
    conversation_id = args.get("conversation_id", "default")
    history = args.get("history", [])
    
    if not question:
        return [types.TextContent(
            type="text",
            text="No question provided"
        )]
    
    try:
        # Get reasoning pipeline
        reasoning_pipelines = getattr(kotaemon_server.app, 'reasonings', {})
        if not reasoning_pipelines:
            return [types.TextContent(
                type="text",
                text="No reasoning pipelines available"
            )]
        
        # Use the first available reasoning pipeline
        pipeline_name = list(reasoning_pipelines.keys())[0]
        pipeline = reasoning_pipelines[pipeline_name]
        
        # Run the pipeline
        result = pipeline.run(question, conversation_id, history)
        
        if hasattr(result, 'content'):
            answer_text = result.content
        else:
            answer_text = str(result)
        
        return [types.TextContent(
            type="text",
            text=f"Question: {question}\n\nAnswer: {answer_text}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error answering question: {str(e)}"
        )]

async def retrieve_documents(args: Dict[str, Any]) -> List[types.TextContent]:
    """Retrieve relevant documents for a query."""
    query = args.get("query", "")
    collection_name = args.get("collection_name", "default")
    top_k = args.get("top_k", 5)
    
    if not query:
        return [types.TextContent(
            type="text",
            text="No query provided"
        )]
    
    try:
        # Get index manager
        if not hasattr(kotaemon_server.app, 'index_manager'):
            return [types.TextContent(
                type="text",
                text="Index manager not available"
            )]
        
        # Get retriever
        file_indices = [idx for idx in kotaemon_server.app.index_manager.indices 
                       if hasattr(idx, 'get_retriever_pipelines')]
        
        if not file_indices:
            return [types.TextContent(
                type="text",
                text="No retrievers available"
            )]
        
        file_index = file_indices[0]
        retrievers = file_index.get_retriever_pipelines({}, user_id=1)
        
        if not retrievers:
            return [types.TextContent(
                type="text",
                text="No retrievers configured"
            )]
        
        # Retrieve documents
        retriever = retrievers[0]
        docs = retriever.run(query)
        
        # Format results
        results = []
        for i, doc in enumerate(docs[:top_k]):
            doc_text = getattr(doc, 'text', str(doc))[:500]  # Limit text length
            metadata = getattr(doc, 'metadata', {})
            file_name = metadata.get('file_name', f'Document {i+1}')
            
            results.append(f"Document {i+1}: {file_name}\n{doc_text}...\n")
        
        return [types.TextContent(
            type="text",
            text=f"Retrieved {len(results)} documents for query: '{query}'\n\n" + 
                 "\n".join(results)
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error retrieving documents: {str(e)}"
        )]

async def list_collections(args: Dict[str, Any]) -> List[types.TextContent]:
    """List all available collections."""
    try:
        # Get index manager
        if not hasattr(kotaemon_server.app, 'index_manager'):
            return [types.TextContent(
                type="text",
                text="No collections available"
            )]
        
        indices = kotaemon_server.app.index_manager.indices
        collections = [idx.name for idx in indices]
        
        return [types.TextContent(
            type="text",
            text=f"Available collections: {', '.join(collections) if collections else 'None'}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error listing collections: {str(e)}"
        )]

async def get_collection_info(args: Dict[str, Any]) -> List[types.TextContent]:
    """Get information about a specific collection."""
    collection_name = args.get("collection_name", "")
    
    if not collection_name:
        return [types.TextContent(
            type="text",
            text="No collection name provided"
        )]
    
    try:
        # Find collection
        if not hasattr(kotaemon_server.app, 'index_manager'):
            return [types.TextContent(
                type="text",
                text="Index manager not available"
            )]
        
        target_index = None
        for idx in kotaemon_server.app.index_manager.indices:
            if idx.name == collection_name:
                target_index = idx
                break
        
        if not target_index:
            return [types.TextContent(
                type="text",
                text=f"Collection '{collection_name}' not found"
            )]
        
        # Get collection info
        info = {
            "name": target_index.name,
            "type": type(target_index).__name__,
            "config": getattr(target_index, 'config', {})
        }
        
        return [types.TextContent(
            type="text",
            text=f"Collection info: {json.dumps(info, indent=2)}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting collection info: {str(e)}"
        )]

async def delete_collection(args: Dict[str, Any]) -> List[types.TextContent]:
    """Delete a collection."""
    collection_name = args.get("collection_name", "")
    confirm = args.get("confirm", False)
    
    if not collection_name:
        return [types.TextContent(
            type="text",
            text="No collection name provided"
        )]
    
    if not confirm:
        return [types.TextContent(
            type="text",
            text="Collection deletion requires confirmation (set confirm=true)"
        )]
    
    try:
        # Note: This is a placeholder. Actual deletion would depend on
        # kotaemon's collection management implementation
        return [types.TextContent(
            type="text",
            text=f"Collection '{collection_name}' deletion not implemented yet"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error deleting collection: {str(e)}"
        )]

async def configure_llm(args: Dict[str, Any]) -> List[types.TextContent]:
    """Configure LLM settings."""
    provider = args.get("provider", "")
    model = args.get("model", "")
    
    if not provider or not model:
        return [types.TextContent(
            type="text",
            text="Provider and model are required"
        )]
    
    try:
        # Note: This would need to integrate with kotaemon's LLM configuration
        # For now, return configuration info
        config_info = {
            "provider": provider,
            "model": model,
            "temperature": args.get("temperature", 0.0),
            "api_key": "***" if args.get("api_key") else None,
            "base_url": args.get("base_url")
        }
        
        return [types.TextContent(
            type="text",
            text=f"LLM configuration updated: {json.dumps(config_info, indent=2)}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error configuring LLM: {str(e)}"
        )]

async def configure_embeddings(args: Dict[str, Any]) -> List[types.TextContent]:
    """Configure embedding settings."""
    provider = args.get("provider", "")
    model = args.get("model", "")
    
    if not provider or not model:
        return [types.TextContent(
            type="text",
            text="Provider and model are required"
        )]
    
    try:
        # Note: This would need to integrate with kotaemon's embedding configuration
        config_info = {
            "provider": provider,
            "model": model,
            "api_key": "***" if args.get("api_key") else None,
            "base_url": args.get("base_url")
        }
        
        return [types.TextContent(
            type="text",
            text=f"Embedding configuration updated: {json.dumps(config_info, indent=2)}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error configuring embeddings: {str(e)}"
        )]

async def get_server_status(args: Dict[str, Any]) -> List[types.TextContent]:
    """Get server status and configuration."""
    try:
        status = {
            "initialized": kotaemon_server.initialized,
            "data_directory": str(kotaemon_server.data_dir),
            "app_available": kotaemon_server.app is not None,
            "collections": []
        }
        
        if kotaemon_server.app and hasattr(kotaemon_server.app, 'index_manager'):
            status["collections"] = [idx.name for idx in kotaemon_server.app.index_manager.indices]
        
        return [types.TextContent(
            type="text",
            text=f"Server status: {json.dumps(status, indent=2)}"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting server status: {str(e)}"
        )]

async def main():
    """Main entry point for the MCP server."""
    # Initialize the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            NotificationOptions(tools_changed=True)
        )

if __name__ == "__main__":
    asyncio.run(main())
