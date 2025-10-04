#!/usr/bin/env python3
"""
Standalone Kotaemon MCP Server
A minimal MCP server that provides kotaemon-like functionality for testing without dependencies.
This server runs independently and can be used with Claude Desktop immediately.
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StandaloneMCPServer:
    """Standalone MCP server with mock kotaemon functionality"""
    
    def __init__(self):
        self.server_info = {
            "name": "kotaemon-mcp-standalone",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {}
        }
        self.collections = {
            "research_papers": {"documents": 25, "created": "2024-10-01"},
            "technical_docs": {"documents": 12, "created": "2024-10-02"}, 
            "meeting_notes": {"documents": 8, "created": "2024-10-03"}
        }
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of available MCP tools"""
        return [
            {
                "name": "list_collections",
                "description": "List all available document collections with metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "create_collection", 
                "description": "Create a new document collection for organizing content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Unique collection name"},
                        "description": {"type": "string", "description": "Collection description"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "index_documents",
                "description": "Index documents into a collection using various strategies",
                "inputSchema": {
                    "type": "object", 
                    "properties": {
                        "file_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file paths to index"
                        },
                        "collection_name": {"type": "string", "description": "Target collection"},
                        "index_type": {
                            "type": "string",
                            "enum": ["simple", "advanced", "graphrag"],
                            "description": "Indexing strategy to use"
                        },
                        "chunk_size": {"type": "integer", "description": "Text chunk size"}
                    },
                    "required": ["file_paths", "collection_name"]
                }
            },
            {
                "name": "answer_question",
                "description": "Answer questions using RAG with multiple reasoning strategies",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Question to answer"},
                        "collection_name": {"type": "string", "description": "Collection to search"},
                        "reasoning_type": {
                            "type": "string", 
                            "enum": ["simple", "react", "decomposed", "graphrag"],
                            "description": "Reasoning strategy"
                        },
                        "include_sources": {"type": "boolean", "description": "Include source references"},
                        "language": {"type": "string", "description": "Response language"}
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "graphrag_query",
                "description": "Perform GraphRAG queries for complex knowledge graph analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "GraphRAG query"},
                        "query_type": {
                            "type": "string",
                            "enum": ["local", "global", "community"],
                            "description": "Type of GraphRAG query"
                        },
                        "collection_name": {"type": "string", "description": "Target collection"},
                        "community_level": {"type": "integer", "description": "Community analysis level"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_server_status",
                "description": "Get comprehensive server health and status information",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            logger.info(f"Handling request: {method}")
            
            if method == "initialize":
                return await self._handle_initialize(request_id, params)
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tool_call(request_id, params)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")
                
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return self._error_response(request.get("id"), -32603, f"Internal error: {str(e)}")
    
    async def _handle_initialize(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": self.server_info,
                "capabilities": self.capabilities
            }
        }
    
    async def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Handle tools listing"""
        return {
            "jsonrpc": "2.0", 
            "id": request_id,
            "result": {
                "tools": self.get_tools()
            }
        }
    
    async def _handle_tool_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "list_collections":
                content = await self._list_collections(arguments)
            elif tool_name == "create_collection":
                content = await self._create_collection(arguments)
            elif tool_name == "index_documents":
                content = await self._index_documents(arguments)
            elif tool_name == "answer_question":
                content = await self._answer_question(arguments)
            elif tool_name == "graphrag_query":
                content = await self._graphrag_query(arguments)
            elif tool_name == "get_server_status":
                content = await self._get_server_status(arguments)
            else:
                content = [{"type": "text", "text": f"❌ Unknown tool: {tool_name}"}]
                
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": content
                }
            }
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return self._error_response(request_id, -32603, f"Tool execution failed: {str(e)}")
    
    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def _list_collections(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all collections"""
        collection_list = []
        for name, info in self.collections.items():
            collection_list.append(f"📚 **{name}**: {info['documents']} documents (created: {info['created']})")
        
        response = f"🗂️  **Available Collections ({len(self.collections)})**\n\n" + "\n".join(collection_list)
        response += "\n\n✨ *Ready for document indexing and querying*"
        
        return [{"type": "text", "text": response}]
    
    async def _create_collection(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create new collection"""
        name = args.get("name")
        description = args.get("description", "")
        
        if not name:
            return [{"type": "text", "text": "❌ **Error**: Collection name is required"}]
        
        if name in self.collections:
            return [{"type": "text", "text": f"⚠️  **Warning**: Collection '{name}' already exists"}]
        
        self.collections[name] = {
            "documents": 0,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "description": description
        }
        
        response = f"✅ **Collection Created Successfully**\n\n"
        response += f"📁 **Name**: {name}\n"
        response += f"📝 **Description**: {description or 'No description provided'}\n"
        response += f"📅 **Created**: {self.collections[name]['created']}\n"
        response += f"📊 **Documents**: 0 (ready for indexing)"
        
        return [{"type": "text", "text": response}]
    
    async def _index_documents(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Index documents into collection"""
        file_paths = args.get("file_paths", [])
        collection_name = args.get("collection_name")
        index_type = args.get("index_type", "simple")
        chunk_size = args.get("chunk_size", 1000)
        
        if not file_paths:
            return [{"type": "text", "text": "❌ **Error**: No file paths provided"}]
        
        if not collection_name:
            return [{"type": "text", "text": "❌ **Error**: Collection name is required"}]
        
        # Simulate document processing
        processed_files = []
        for path in file_paths:
            file_type = path.split('.')[-1].upper() if '.' in path else "UNKNOWN"
            processed_files.append(f"📄 {path.split('/')[-1]} ({file_type})")
        
        # Update collection
        if collection_name in self.collections:
            self.collections[collection_name]["documents"] += len(file_paths)
        
        response = f"📚 **Document Indexing Complete**\n\n"
        response += f"🎯 **Collection**: {collection_name}\n"
        response += f"📊 **Files Processed**: {len(file_paths)}\n"
        response += f"⚙️  **Index Type**: {index_type.title()}\n"
        response += f"📏 **Chunk Size**: {chunk_size} characters\n\n"
        response += "**Processed Files:**\n" + "\n".join(processed_files[:5])
        if len(processed_files) > 5:
            response += f"\n... and {len(processed_files) - 5} more files"
        
        response += "\n\n✅ *Ready for question answering and retrieval*"
        
        return [{"type": "text", "text": response}]
    
    async def _answer_question(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Answer question using RAG"""
        question = args.get("question")
        collection_name = args.get("collection_name", "default")
        reasoning_type = args.get("reasoning_type", "simple")
        include_sources = args.get("include_sources", True)
        language = args.get("language", "en")
        
        if not question:
            return [{"type": "text", "text": "❌ **Error**: Question is required"}]
        
        # Generate contextual response based on question
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["graph", "relation", "connect", "network"]):
            answer_type = "Graph Analysis"
            answer = "This question involves understanding relationships and connections between entities. Based on the knowledge graph analysis, there are several interconnected concepts that form clusters around key themes."
        elif any(word in question_lower for word in ["trend", "pattern", "analysis", "insight"]):
            answer_type = "Trend Analysis"
            answer = "The analysis reveals several emerging patterns and trends in the data. Key insights include cyclical behaviors, growth trajectories, and correlation patterns across different domains."
        elif any(word in question_lower for word in ["how", "process", "step", "method"]):
            answer_type = "Process Explanation"
            answer = "This involves a multi-step process with several key phases. The methodology includes data collection, analysis, and interpretation stages, each with specific requirements and best practices."
        else:
            answer_type = "General Analysis"
            answer = "Based on the comprehensive analysis of the indexed documents, this topic encompasses multiple dimensions and perspectives that intersect in meaningful ways."
        
        response = f"🤖 **Answer** ({reasoning_type.title()} Reasoning)\n\n"
        response += f"**Question**: {question}\n\n"
        response += f"**{answer_type}**: {answer}\n\n"
        
        response += "**Key Insights:**\n"
        response += f"• Analysis performed using {reasoning_type} reasoning strategy\n"
        response += f"• Information synthesized from '{collection_name}' collection\n"
        response += "• High confidence in result accuracy (87%)\n"
        response += f"• Response optimized for {language.upper()} language\n\n"
        
        if include_sources:
            response += "**Sources Referenced:**\n"
            response += "📄 Document 1: research_analysis_2024.pdf (relevance: 92%)\n"
            response += "📄 Document 2: methodology_overview.md (relevance: 88%)\n" 
            response += "📄 Document 3: case_study_findings.docx (relevance: 85%)\n\n"
        
        response += f"⏱️  *Processing time: 1.{len(question) % 9 + 1} seconds*"
        
        return [{"type": "text", "text": response}]
    
    async def _graphrag_query(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform GraphRAG query"""
        query = args.get("query")
        query_type = args.get("query_type", "local")
        collection_name = args.get("collection_name", "default")
        community_level = args.get("community_level", 1)
        
        if not query:
            return [{"type": "text", "text": "❌ **Error**: GraphRAG query is required"}]
        
        response = f"🕸️  **GraphRAG Analysis Results**\n\n"
        response += f"**Query**: {query}\n"
        response += f"**Type**: {query_type.title()} Analysis\n"
        response += f"**Collection**: {collection_name}\n\n"
        
        if query_type == "local":
            response += "**Local Entity Analysis:**\n"
            response += "• Identified 15 primary entities related to your query\n"
            response += "• Found 28 direct relationships between entities\n"
            response += "• Detected 3 entity clusters with high connectivity\n"
            response += "• Average relationship strength: 0.74\n\n"
        elif query_type == "global":
            response += "**Global Network Analysis:**\n"
            response += "• Analyzed complete knowledge graph structure\n"
            response += "• Identified 7 major thematic communities\n"
            response += "• Cross-community connections: 42 pathways\n"
            response += "• Network density: 0.68 (highly connected)\n\n"
        else:  # community
            response += f"**Community Analysis (Level {community_level}):**\n"
            response += f"• Detected {5 + community_level * 2} communities at this level\n"
            response += "• Community coherence score: 0.82\n"
            response += "• Inter-community bridge nodes: 12\n"
            response += "• Hierarchical structure depth: 4 levels\n\n"
        
        response += "**Key Graph Insights:**\n"
        response += "🔗 Strong clustering around central concepts\n"
        response += "🌐 Multiple pathways for information flow\n"
        response += "📊 High semantic coherence within clusters\n"
        response += "🎯 Clear hierarchical organization patterns\n\n"
        
        response += "**Related Entities:**\n"
        query_words = query.lower().split()
        for i, word in enumerate(query_words[:3]):
            response += f"• {word.title()}Entity_{i+1} (confidence: {90-i*3}%)\n"
        
        response += f"\n⚡ *GraphRAG processing completed in {len(query) % 3 + 1}.{len(query) % 9}s*"
        
        return [{"type": "text", "text": response}]
    
    async def _get_server_status(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get comprehensive server status"""
        uptime_hours = 2  # Simulated uptime
        total_docs = sum(info["documents"] for info in self.collections.values())
        
        response = f"🟢 **Kotaemon MCP Server Status**\n\n"
        response += f"**Server Information:**\n"
        response += f"• Status: ✅ Healthy & Ready\n"
        response += f"• Version: {self.server_info['version']}\n"
        response += f"• Uptime: {uptime_hours} hours, 23 minutes\n"
        response += f"• Mode: Standalone (Testing)\n\n"
        
        response += f"**Collections & Documents:**\n"
        response += f"• Active Collections: {len(self.collections)}\n"
        response += f"• Total Documents: {total_docs}\n"
        response += f"• Indexing Status: Ready\n"
        response += f"• Query Processing: Enabled\n\n"
        
        response += f"**Capabilities:**\n"
        response += f"• Document Indexing: ✅ Active\n"
        response += f"• Question Answering: ✅ Active\n"
        response += f"• GraphRAG Queries: ✅ Active\n"
        response += f"• Collection Management: ✅ Active\n\n"
        
        response += f"**System Resources:**\n"
        response += f"• Memory Usage: 156.7 MB\n"
        response += f"• CPU Usage: 12%\n"
        response += f"• Active Connections: 1\n"
        response += f"• Response Time: <200ms\n\n"
        
        response += f"🎯 **Ready for**: Document processing, Q&A, GraphRAG analysis"
        
        return [{"type": "text", "text": response}]

async def main():
    """Main MCP server loop"""
    server = StandaloneMCPServer()
    logger.info("🚀 Kotaemon MCP Server starting...")
    logger.info(f"📋 Available tools: {len(server.get_tools())}")
    
    try:
        while True:
            # Read JSON-RPC request from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            try:
                request = json.loads(line.strip())
                response = await server.handle_request(request)
                
                # Send response to stdout
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        logger.info("👋 Server shutting down...")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
