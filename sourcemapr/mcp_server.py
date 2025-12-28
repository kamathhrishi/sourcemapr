"""
SourcemapR MCP Server - Expose RAG observability data to AI agents.

Provides read access to documents, chunks, queries, and LLM calls.
Provides write access for evaluations (LLM-as-judge, categorization, etc).
"""

import asyncio
import json
from typing import Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from sourcemapr.server import database as db


# Initialize MCP server
server = Server("sourcemapr")


# =============================================================================
# Read Tools - Documents, Chunks, Queries, LLM Calls
# =============================================================================

@server.list_tools()
async def list_tools():
    """List all available tools."""
    return [
        # Read tools
        Tool(
            name="list_experiments",
            description="List all experiments with their document and query counts",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_documents",
            description="List documents in the workspace. Optionally filter by experiment_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_id": {
                        "type": "integer",
                        "description": "Optional experiment ID to filter by"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_document_parsed",
            description="Get the parsed text content of a document (no raw HTML/PDF).",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "The document ID"
                    }
                },
                "required": ["doc_id"]
            }
        ),
        Tool(
            name="list_chunks",
            description="List chunks in the workspace. Optionally filter by experiment_id or doc_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_id": {
                        "type": "integer",
                        "description": "Optional experiment ID to filter by"
                    },
                    "doc_id": {
                        "type": "string",
                        "description": "Optional document ID to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of chunks to return (default 100)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_chunk",
            description="Get full details of a specific chunk by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                        "description": "The chunk ID"
                    }
                },
                "required": ["chunk_id"]
            }
        ),
        Tool(
            name="list_queries",
            description="List retrieval queries/searches. Optionally filter by experiment_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_id": {
                        "type": "integer",
                        "description": "Optional experiment ID to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of queries to return (default 100)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_query",
            description="Get full details of a query including retrieval results and LLM response.",
            inputSchema={
                "type": "object",
                "properties": {
                    "retrieval_id": {
                        "type": "string",
                        "description": "The retrieval ID (UUID string from list_queries)"
                    }
                },
                "required": ["retrieval_id"]
            }
        ),
        Tool(
            name="list_llm_calls",
            description="List LLM calls. Optionally filter by experiment_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_id": {
                        "type": "integer",
                        "description": "Optional experiment ID to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of LLM calls to return (default 100)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_llm_call",
            description="Get full details of an LLM call including messages, prompt, and response.",
            inputSchema={
                "type": "object",
                "properties": {
                    "llm_call_id": {
                        "type": "integer",
                        "description": "The LLM call ID"
                    }
                },
                "required": ["llm_call_id"]
            }
        ),

        # Write tools - Evaluations
        Tool(
            name="create_evaluation",
            description="Create a new evaluation (LLM-as-judge score, category, or error classification).",
            inputSchema={
                "type": "object",
                "properties": {
                    "evaluation_type": {
                        "type": "string",
                        "enum": ["llm_judge", "category", "error_class"],
                        "description": "Type of evaluation"
                    },
                    "retrieval_id": {
                        "type": "string",
                        "description": "Optional retrieval ID this evaluation is for"
                    },
                    "experiment_id": {
                        "type": "integer",
                        "description": "Optional experiment ID this evaluation is for"
                    },
                    "metric_name": {
                        "type": "string",
                        "description": "Name of the metric (e.g., 'relevance', 'faithfulness')"
                    },
                    "score": {
                        "type": "number",
                        "description": "Score from 0.0 to 1.0"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation for the score or classification"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category label (for category type)"
                    },
                    "error_type": {
                        "type": "string",
                        "description": "Error type label (for error_class type)"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent creating this evaluation"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata as JSON object"
                    }
                },
                "required": ["evaluation_type"]
            }
        ),
        Tool(
            name="update_evaluation",
            description="Update an existing evaluation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "evaluation_id": {
                        "type": "string",
                        "description": "The evaluation ID to update"
                    },
                    "score": {
                        "type": "number",
                        "description": "Updated score"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Updated reasoning"
                    },
                    "category": {
                        "type": "string",
                        "description": "Updated category"
                    },
                    "error_type": {
                        "type": "string",
                        "description": "Updated error type"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Updated metadata"
                    }
                },
                "required": ["evaluation_id"]
            }
        ),
        Tool(
            name="delete_evaluation",
            description="Delete an evaluation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "evaluation_id": {
                        "type": "string",
                        "description": "The evaluation ID to delete"
                    }
                },
                "required": ["evaluation_id"]
            }
        ),
        Tool(
            name="list_evaluations",
            description="List evaluations. Optionally filter by experiment_id, retrieval_id, or type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_id": {
                        "type": "integer",
                        "description": "Optional experiment ID to filter by"
                    },
                    "retrieval_id": {
                        "type": "string",
                        "description": "Optional retrieval ID to filter by"
                    },
                    "evaluation_type": {
                        "type": "string",
                        "enum": ["llm_judge", "category", "error_class"],
                        "description": "Optional evaluation type to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of evaluations to return (default 500)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_evaluation",
            description="Get full details of a specific evaluation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "evaluation_id": {
                        "type": "string",
                        "description": "The evaluation ID"
                    }
                },
                "required": ["evaluation_id"]
            }
        ),

        # Query categories
        Tool(
            name="add_query_category",
            description="Add a category tag to a query/retrieval.",
            inputSchema={
                "type": "object",
                "properties": {
                    "retrieval_id": {
                        "type": "string",
                        "description": "The retrieval ID to categorize"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category label to add"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Optional confidence score (0.0 to 1.0)"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent adding this category"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata"
                    }
                },
                "required": ["retrieval_id", "category"]
            }
        ),
        Tool(
            name="remove_query_category",
            description="Remove a category tag from a query/retrieval.",
            inputSchema={
                "type": "object",
                "properties": {
                    "retrieval_id": {
                        "type": "string",
                        "description": "The retrieval ID"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category label to remove"
                    }
                },
                "required": ["retrieval_id", "category"]
            }
        ),
        Tool(
            name="list_categories",
            description="List all categories with counts.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    try:
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def handle_tool_call(name: str, arguments: dict):
    """Route tool calls to appropriate handlers."""

    # Read tools
    if name == "list_experiments":
        return handle_list_experiments()
    elif name == "list_documents":
        return handle_list_documents(arguments.get("experiment_id"))
    elif name == "get_document_parsed":
        return handle_get_document_parsed(arguments["doc_id"])
    elif name == "list_chunks":
        return handle_list_chunks(
            arguments.get("experiment_id"),
            arguments.get("doc_id"),
            arguments.get("limit", 100)
        )
    elif name == "get_chunk":
        return handle_get_chunk(arguments["chunk_id"])
    elif name == "list_queries":
        return handle_list_queries(
            arguments.get("experiment_id"),
            arguments.get("limit", 100)
        )
    elif name == "get_query":
        return handle_get_query(arguments["retrieval_id"])
    elif name == "list_llm_calls":
        return handle_list_llm_calls(
            arguments.get("experiment_id"),
            arguments.get("limit", 100)
        )
    elif name == "get_llm_call":
        return handle_get_llm_call(arguments["llm_call_id"])

    # Write tools - Evaluations
    elif name == "create_evaluation":
        return handle_create_evaluation(arguments)
    elif name == "update_evaluation":
        return handle_update_evaluation(
            arguments["evaluation_id"],
            {k: v for k, v in arguments.items() if k != "evaluation_id"}
        )
    elif name == "delete_evaluation":
        return handle_delete_evaluation(arguments["evaluation_id"])
    elif name == "list_evaluations":
        return handle_list_evaluations(
            arguments.get("experiment_id"),
            arguments.get("retrieval_id"),
            arguments.get("evaluation_type"),
            arguments.get("limit", 500)
        )
    elif name == "get_evaluation":
        return handle_get_evaluation(arguments["evaluation_id"])

    # Query categories
    elif name == "add_query_category":
        return handle_add_query_category(
            arguments["retrieval_id"],
            arguments["category"],
            arguments.get("confidence"),
            arguments.get("metadata"),
            arguments.get("agent_name")
        )
    elif name == "remove_query_category":
        return handle_remove_query_category(
            arguments["retrieval_id"],
            arguments["category"]
        )
    elif name == "list_categories":
        return handle_list_categories()

    else:
        return {"error": f"Unknown tool: {name}"}


# =============================================================================
# Read Tool Handlers
# =============================================================================

def handle_list_experiments():
    """List all experiments with counts."""
    experiments = db.get_experiments()
    return [
        {
            "id": e["id"],
            "name": e["name"],
            "description": e.get("description"),
            "framework": e.get("framework"),
            "doc_count": e.get("doc_count", 0),
            "retrieval_count": e.get("retrieval_count", 0),
            "llm_count": e.get("llm_count", 0),
            "created_at": e.get("created_at")
        }
        for e in experiments
    ]


def handle_list_documents(experiment_id: Optional[int] = None):
    """List documents with basic info (no raw content)."""
    docs = db.get_documents(experiment_id)
    return [
        {
            "doc_id": doc.get("doc_id"),
            "filename": doc.get("filename"),
            "num_pages": doc.get("num_pages"),
            "text_length": doc.get("text_length"),
            "experiment_id": doc.get("experiment_id"),
            "created_at": doc.get("created_at")
        }
        for doc in docs.values()
    ]


def handle_get_document_parsed(doc_id: str):
    """Get parsed text content of a document."""
    parsed = db.get_parsed_doc(doc_id)
    if not parsed:
        return {"error": f"Document not found: {doc_id}"}

    # Get basic doc info
    docs = db.get_documents()
    doc = docs.get(doc_id, {})

    return {
        "doc_id": doc_id,
        "filename": doc.get("filename") or parsed.get("filename"),
        "text": parsed.get("text", ""),
        "text_length": len(parsed.get("text", "")),
        "num_pages": doc.get("num_pages")
    }


def handle_list_chunks(
    experiment_id: Optional[int] = None,
    doc_id: Optional[str] = None,
    limit: int = 100
):
    """List chunks with preview text."""
    chunks = db.get_chunks(doc_id=doc_id, experiment_id=experiment_id, include_text=False, limit=limit)
    return [
        {
            "chunk_id": c.get("chunk_id"),
            "doc_id": c.get("doc_id"),
            "index": c.get("index"),
            "text_preview": (c.get("text", "")[:200] + "...") if len(c.get("text", "")) > 200 else c.get("text", ""),
            "text_length": c.get("text_length"),
            "page_number": c.get("page_number"),
            "experiment_id": c.get("experiment_id")
        }
        for c in chunks.values()
    ]


def handle_get_chunk(chunk_id: str):
    """Get full chunk details."""
    chunks = db.get_chunks()
    chunk = chunks.get(chunk_id)
    if not chunk:
        return {"error": f"Chunk not found: {chunk_id}"}

    return {
        "chunk_id": chunk.get("chunk_id"),
        "doc_id": chunk.get("doc_id"),
        "index": chunk.get("index"),
        "text": chunk.get("text"),
        "text_length": chunk.get("text_length"),
        "page_number": chunk.get("page_number"),
        "start_char_idx": chunk.get("start_char_idx"),
        "end_char_idx": chunk.get("end_char_idx"),
        "metadata": chunk.get("metadata", {}),
        "experiment_id": chunk.get("experiment_id")
    }


def handle_list_queries(experiment_id: Optional[int] = None, limit: int = 100):
    """List retrieval queries."""
    retrievals = db.get_retrievals(experiment_id, limit)
    return [
        {
            "id": r.get("id"),
            "retrieval_id": r.get("retrieval_id"),
            "query": r.get("query"),
            "num_results": r.get("num_results", 0),
            "duration_ms": r.get("duration_ms"),
            "experiment_id": r.get("experiment_id"),
            "timestamp": r.get("timestamp")
        }
        for r in retrievals
    ]


def handle_get_query(retrieval_id: str):
    """Get full query details including results and LLM response."""
    retrievals = db.get_retrievals()
    # Match on retrieval_id (UUID string), not integer id
    retrieval = next((r for r in retrievals if r.get("retrieval_id") == retrieval_id), None)
    if not retrieval:
        return {"error": f"Retrieval not found: {retrieval_id}"}

    # Get associated LLM call by retrieval_id
    llm_calls = db.get_llm_calls()
    llm_call = next((l for l in llm_calls if l.get("retrieval_id") == retrieval_id), None)

    result = {
        "id": retrieval.get("id"),
        "retrieval_id": retrieval.get("retrieval_id"),
        "query": retrieval.get("query"),
        "num_results": retrieval.get("num_results", 0),
        "duration_ms": retrieval.get("duration_ms"),
        "results": [
            {
                "chunk_id": r.get("chunk_id"),
                "text": r.get("text"),
                "score": r.get("score"),
                "page_number": r.get("page_number")
            }
            for r in (retrieval.get("results") or [])
        ],
        "experiment_id": retrieval.get("experiment_id"),
        "timestamp": retrieval.get("timestamp")
    }

    if llm_call:
        result["llm_call"] = {
            "id": llm_call.get("id"),
            "model": llm_call.get("model"),
            "prompt": llm_call.get("prompt"),
            "response": llm_call.get("response"),
            "prompt_tokens": llm_call.get("prompt_tokens"),
            "completion_tokens": llm_call.get("completion_tokens"),
            "total_tokens": llm_call.get("total_tokens"),
            "duration_ms": llm_call.get("duration_ms")
        }

    return result


def handle_list_llm_calls(experiment_id: Optional[int] = None, limit: int = 100):
    """List LLM calls with preview."""
    llm_calls = db.get_llm_calls(experiment_id, limit)
    return [
        {
            "id": l.get("id"),
            "model": l.get("model"),
            "prompt_preview": (l.get("prompt", "") or "")[:200] + "..." if len(l.get("prompt", "") or "") > 200 else l.get("prompt"),
            "prompt_tokens": l.get("prompt_tokens"),
            "completion_tokens": l.get("completion_tokens"),
            "total_tokens": l.get("total_tokens"),
            "duration_ms": l.get("duration_ms"),
            "status": l.get("status"),
            "experiment_id": l.get("experiment_id"),
            "timestamp": l.get("timestamp")
        }
        for l in llm_calls
    ]


def handle_get_llm_call(llm_call_id: int):
    """Get full LLM call details."""
    llm_calls = db.get_llm_calls()
    llm_call = next((l for l in llm_calls if l.get("id") == llm_call_id), None)
    if not llm_call:
        return {"error": f"LLM call not found: {llm_call_id}"}

    return {
        "id": llm_call.get("id"),
        "model": llm_call.get("model"),
        "input_type": llm_call.get("input_type"),
        "messages": llm_call.get("messages"),
        "prompt": llm_call.get("prompt"),
        "response": llm_call.get("response"),
        "prompt_tokens": llm_call.get("prompt_tokens"),
        "completion_tokens": llm_call.get("completion_tokens"),
        "total_tokens": llm_call.get("total_tokens"),
        "temperature": llm_call.get("temperature"),
        "duration_ms": llm_call.get("duration_ms"),
        "status": llm_call.get("status"),
        "error": llm_call.get("error"),
        "experiment_id": llm_call.get("experiment_id"),
        "timestamp": llm_call.get("timestamp")
    }


# =============================================================================
# Write Tool Handlers - Evaluations
# =============================================================================

def handle_create_evaluation(data: dict):
    """Create a new evaluation."""
    evaluation_id = db.store_evaluation(data)
    return {
        "success": True,
        "evaluation_id": evaluation_id
    }


def handle_update_evaluation(evaluation_id: str, updates: dict):
    """Update an existing evaluation."""
    success = db.update_evaluation(evaluation_id, updates)
    return {
        "success": success,
        "evaluation_id": evaluation_id
    }


def handle_delete_evaluation(evaluation_id: str):
    """Delete an evaluation."""
    success = db.delete_evaluation(evaluation_id)
    return {
        "success": success,
        "evaluation_id": evaluation_id
    }


def handle_list_evaluations(
    experiment_id: Optional[int] = None,
    retrieval_id: Optional[str] = None,
    evaluation_type: Optional[str] = None,
    limit: int = 500
):
    """List evaluations with optional filters."""
    return db.get_evaluations(experiment_id, retrieval_id, evaluation_type, limit)


def handle_get_evaluation(evaluation_id: str):
    """Get a specific evaluation."""
    evaluation = db.get_evaluation(evaluation_id)
    if not evaluation:
        return {"error": f"Evaluation not found: {evaluation_id}"}
    return evaluation


# =============================================================================
# Query Categories Handlers
# =============================================================================

def handle_add_query_category(
    retrieval_id: str,
    category: str,
    confidence: Optional[float] = None,
    metadata: Optional[dict] = None,
    agent_name: Optional[str] = None
):
    """Add a category to a query."""
    success = db.add_query_category(retrieval_id, category, confidence, metadata, agent_name)
    return {
        "success": success,
        "retrieval_id": retrieval_id,
        "category": category
    }


def handle_remove_query_category(retrieval_id: str, category: str):
    """Remove a category from a query."""
    success = db.remove_query_category(retrieval_id, category)
    return {
        "success": success,
        "retrieval_id": retrieval_id,
        "category": category
    }


def handle_list_categories():
    """List all categories with counts."""
    return db.get_category_summary()


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run the MCP server."""
    # Ensure database is initialized
    db.init_db()

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def run():
    """Entry point for CLI."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
