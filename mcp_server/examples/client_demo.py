#!/usr/bin/env python3
"""
Example MCP Client for Kotaemon

This script demonstrates how to interact with the kotaemon MCP server
using various tools and operations.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the MCP client libraries (you would install these separately)
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("MCP client libraries not found. This is a demonstration script.")
    print("In a real scenario, you would install the MCP client libraries.")
    sys.exit(1)

class KotaemonMCPClient:
    """Example client for interacting with kotaemon MCP server."""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.session = None
    
    async def connect(self):
        """Connect to the kotaemon MCP server."""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_path]
        )
        
        self.session = await stdio_client(server_params)
        
    async def list_tools(self):
        """List all available tools."""
        if not self.session:
            await self.connect()
            
        tools = await self.session.list_tools()
        print("Available tools:")
        for tool in tools.tools:
            print(f"- {tool.name}: {tool.description}")
        return tools
    
    async def call_tool(self, name: str, arguments: dict):
        """Call a specific tool with arguments."""
        if not self.session:
            await self.connect()
            
        result = await self.session.call_tool(name, arguments)
        return result
    
    async def close(self):
        """Close the connection."""
        if self.session:
            await self.session.close()

async def demo_basic_operations():
    """Demonstrate basic kotaemon MCP operations."""
    
    # Initialize client
    server_path = Path(__file__).parent.parent / "enhanced_server.py"
    client = KotaemonMCPClient(str(server_path))
    
    try:
        print("🚀 Kotaemon MCP Client Demo")
        print("=" * 50)
        
        # 1. List available tools
        print("\n1. Listing available tools...")
        tools = await client.list_tools()
        
        # 2. Get server status
        print("\n2. Getting server status...")
        status = await client.call_tool("get_server_status", {
            "include_system_info": True
        })
        print("Server Status:")
        for content in status.content:
            print(content.text)
        
        # 3. List collections
        print("\n3. Listing collections...")
        collections = await client.call_tool("list_collections", {
            "include_stats": True
        })
        print("Collections:")
        for content in collections.content:
            print(content.text)
        
        # 4. Create a new collection
        print("\n4. Creating a new collection...")
        create_result = await client.call_tool("create_collection", {
            "collection_name": "demo_collection",
            "description": "Demo collection for testing",
            "index_type": "vector",
            "is_private": True
        })
        print("Collection Creation Result:")
        for content in create_result.content:
            print(content.text)
        
        # 5. Configure LLM (demo with mock data)
        print("\n5. Configuring LLM...")
        llm_config = await client.call_tool("configure_llm", {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 2000,
            "set_as_default": True
        })
        print("LLM Configuration:")
        for content in llm_config.content:
            print(content.text)
        
        # 6. List available models
        print("\n6. Listing available models...")
        models = await client.call_tool("list_available_models", {
            "model_type": "all"
        })
        print("Available Models:")
        for content in models.content:
            print(content.text)
        
        # 7. Health check
        print("\n7. Performing health check...")
        health = await client.call_tool("health_check", {
            "check_models": True,
            "check_storage": True
        })
        print("Health Check:")
        for content in health.content:
            print(content.text)
            
    except Exception as e:
        print(f"Error during demo: {e}")
    
    finally:
        await client.close()

async def demo_document_operations():
    """Demonstrate document indexing and querying operations."""
    
    server_path = Path(__file__).parent.parent / "enhanced_server.py"
    client = KotaemonMCPClient(str(server_path))
    
    try:
        print("\n📚 Document Operations Demo")
        print("=" * 50)
        
        # 1. Index documents (using mock file paths)
        print("\n1. Indexing documents...")
        index_result = await client.call_tool("index_documents", {
            "file_paths": [
                "/path/to/research_paper.pdf",
                "/path/to/technical_doc.docx"
            ],
            "collection_name": "research_docs",
            "index_type": "vector",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "reindex": False
        })
        print("Indexing Result:")
        for content in index_result.content:
            print(content.text)
        
        # 2. Answer questions
        print("\n2. Answering questions...")
        qa_result = await client.call_tool("answer_question", {
            "question": "What are the main findings in the research papers?",
            "collection_name": "research_docs",
            "reasoning_type": "simple",
            "include_sources": True,
            "language": "en"
        })
        print("Q&A Result:")
        for content in qa_result.content:
            print(content.text)
        
        # 3. Retrieve documents
        print("\n3. Retrieving relevant documents...")
        retrieval_result = await client.call_tool("retrieve_documents", {
            "query": "machine learning applications",
            "collection_name": "research_docs",
            "top_k": 3,
            "search_type": "hybrid",
            "rerank": True,
            "include_metadata": True
        })
        print("Retrieval Result:")
        for content in retrieval_result.content:
            print(content.text)
        
        # 4. List files in collection
        print("\n4. Listing files in collection...")
        files_result = await client.call_tool("list_files", {
            "collection_name": "research_docs",
            "file_type": "all"
        })
        print("Files in Collection:")
        for content in files_result.content:
            print(content.text)
            
    except Exception as e:
        print(f"Error during document demo: {e}")
    
    finally:
        await client.close()

async def demo_graphrag_operations():
    """Demonstrate GraphRAG operations."""
    
    server_path = Path(__file__).parent.parent / "enhanced_server.py"
    client = KotaemonMCPClient(str(server_path))
    
    try:
        print("\n🕸️ GraphRAG Operations Demo")
        print("=" * 50)
        
        # 1. GraphRAG query
        print("\n1. Performing GraphRAG query...")
        graphrag_result = await client.call_tool("graphrag_query", {
            "query": "How do machine learning and neural networks relate in the research?",
            "collection_name": "research_docs",
            "query_type": "local",
            "community_level": 2
        })
        print("GraphRAG Query Result:")
        for content in graphrag_result.content:
            print(content.text)
        
        # 2. Analyze document graph
        print("\n2. Analyzing document graph...")
        graph_analysis = await client.call_tool("analyze_document_graph", {
            "collection_name": "research_docs",
            "analysis_type": "summary"
        })
        print("Graph Analysis:")
        for content in graph_analysis.content:
            print(content.text)
        
        # 3. Global GraphRAG query
        print("\n3. Performing global GraphRAG query...")
        global_result = await client.call_tool("graphrag_query", {
            "query": "What are the main research trends across all documents?",
            "collection_name": "research_docs",
            "query_type": "global",
            "community_level": 1
        })
        print("Global GraphRAG Result:")
        for content in global_result.content:
            print(content.text)
            
    except Exception as e:
        print(f"Error during GraphRAG demo: {e}")
    
    finally:
        await client.close()

async def demo_advanced_features():
    """Demonstrate advanced features like export and configuration."""
    
    server_path = Path(__file__).parent.parent / "enhanced_server.py"
    client = KotaemonMCPClient(str(server_path))
    
    try:
        print("\n⚡ Advanced Features Demo")
        print("=" * 50)
        
        # 1. Export collection
        print("\n1. Exporting collection...")
        export_result = await client.call_tool("export_collection", {
            "collection_name": "research_docs",
            "format": "json",
            "include_embeddings": False,
            "output_path": "/tmp/exported_collection.json"
        })
        print("Export Result:")
        for content in export_result.content:
            print(content.text)
        
        # 2. Configure embeddings
        print("\n2. Configuring embeddings...")
        embedding_config = await client.call_tool("configure_embeddings", {
            "provider": "openai",
            "model": "text-embedding-3-large",
            "dimensions": 3072,
            "set_as_default": True
        })
        print("Embedding Configuration:")
        for content in embedding_config.content:
            print(content.text)
        
        # 3. Get collection info
        print("\n3. Getting detailed collection info...")
        collection_info = await client.call_tool("get_collection_info", {
            "collection_name": "research_docs",
            "include_documents": True
        })
        print("Collection Info:")
        for content in collection_info.content:
            print(content.text)
            
    except Exception as e:
        print(f"Error during advanced demo: {e}")
    
    finally:
        await client.close()

async def main():
    """Run all demo operations."""
    print("🎯 Kotaemon MCP Client Examples")
    print("This script demonstrates various operations with the kotaemon MCP server.")
    print("Note: This requires the MCP client libraries to be installed.")
    print()
    
    # Run different demo scenarios
    await demo_basic_operations()
    await demo_document_operations()
    await demo_graphrag_operations()
    await demo_advanced_features()
    
    print("\n✅ Demo completed successfully!")
    print("\nTo use these examples:")
    print("1. Install MCP client libraries")
    print("2. Start the kotaemon MCP server")
    print("3. Modify the file paths and configuration as needed")
    print("4. Run the specific demo functions")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)
