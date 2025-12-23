"""
SourcemapR Demo - Joint Tabular/Semantic QA over Tesla 10K SEC Filings

This example demonstrates hierarchical RAG over SEC 10K filings using:
- FlatReader for loading HTML files
- UnstructuredElementNodeParser for parsing tables and text
- RecursiveRetriever for hierarchical retrieval

Based on LlamaIndex's "Joint Tabular/Semantic QA over Tesla 10K" tutorial.

Usage:
    # Terminal 1: Start the server
    sourcemapr server

    # Terminal 2: Run this demo
    python examples/tesla_10k_sec.py
"""

import sys
import os
from pathlib import Path

# Add parent to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_tesla_10k_files():
    """Download Tesla 10K SEC filings if not already present."""
    import urllib.request

    data_dir = Path("./sec_data")
    data_dir.mkdir(exist_ok=True)

    files = {
        "tesla_2021_10k.htm": "https://www.dropbox.com/scl/fi/mlaymdy1ni1ovyeykhhuk/tesla_2021_10k.htm?rlkey=qf9k4zn0ejrbm716j0gg7r802&dl=1",
    }

    for filename, url in files.items():
        filepath = data_dir / filename
        if not filepath.exists():
            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(url, filepath)
            print(f"Downloaded {filename}")
        else:
            print(f"{filename} already exists")

    return data_dir


def main():
    """Run hierarchical RAG over Tesla 10K SEC filings with tracing."""
    print("\n" + "=" * 60)
    print("SourcemapR Demo - Tesla 10K SEC Filings")
    print("Joint Tabular/Semantic QA with Hierarchical Retrieval")
    print("=" * 60)

    # =====================================================
    # THIS IS ALL YOU NEED TO ADD OBSERVABILITY!
    # =====================================================
    from sourcemapr import init_tracing, stop_tracing
    init_tracing(endpoint="http://localhost:5000", experiment="tesla-10k-sec")
    # =====================================================

    # Download SEC filings
    print("\nStep 1: Downloading Tesla 10K SEC filings...")
    data_dir = download_tesla_10k_files()

    # Import LlamaIndex components
    from llama_index.readers.file import FlatReader
    from llama_index.core.node_parser import UnstructuredElementNodeParser
    from llama_index.core import VectorStoreIndex, Settings
    from llama_index.core.retrievers import RecursiveRetriever
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.llms.openai import OpenAI

    # Configure embedding model (using local embeddings for this demo)
    print("\nStep 2: Configuring embedding model...")
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.llm = OpenAI(model="gpt-4.1-nano-2025-04-14")

    # Check if OpenAI API key is set for LLM
    if not os.environ.get("OPENAI_API_KEY"):
        print("\nWARNING: OPENAI_API_KEY not set. LLM queries will fail.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")

    # Load documents using FlatReader
    print("\nStep 3: Loading Tesla 10K SEC filing...")
    reader = FlatReader()
    docs_2021 = reader.load_data(data_dir / "tesla_2021_10k.htm")
    print(f"Loaded 2021 10K: {len(docs_2021)} document(s)")

    # Parse documents with UnstructuredElementNodeParser
    # This extracts both text and table elements
    print("\nStep 4: Parsing documents with UnstructuredElementNodeParser...")
    print("(This extracts tables and text elements for hierarchical retrieval)")
    node_parser = UnstructuredElementNodeParser()

    # Cache parsed nodes (parsing is slow)
    cache_dir = Path("./sec_cache")
    cache_dir.mkdir(exist_ok=True)

    import pickle
    nodes_2021_path = cache_dir / "nodes_2021.pkl"

    if nodes_2021_path.exists():
        print("Loading cached 2021 nodes...")
        raw_nodes_2021 = pickle.load(open(nodes_2021_path, "rb"))
        print(f"Loaded {len(raw_nodes_2021)} cached nodes")
    else:
        print("Parsing 2021 10K (this may take a few minutes)...")
        raw_nodes_2021 = node_parser.get_nodes_from_documents(docs_2021)
        pickle.dump(raw_nodes_2021, open(nodes_2021_path, "wb"))
        print(f"Parsed and cached 2021 nodes: {len(raw_nodes_2021)} nodes")

    # Get base nodes and mappings for recursive retrieval
    print("\nStep 5: Building hierarchical node structure...")
    base_nodes_2021, node_mappings_2021 = node_parser.get_base_nodes_and_mappings(raw_nodes_2021)
    print(f"2021: {len(base_nodes_2021)} base nodes, {len(node_mappings_2021)} table mappings")

    # Create vector index
    print("\nStep 6: Creating vector index...")
    vector_index_2021 = VectorStoreIndex(base_nodes_2021)
    print("Vector index created!")

    # Create recursive retriever for hierarchical retrieval
    print("\nStep 7: Setting up recursive retriever...")
    vector_retriever_2021 = vector_index_2021.as_retriever(similarity_top_k=50)

    recursive_retriever_2021 = RecursiveRetriever(
        "vector",
        retriever_dict={"vector": vector_retriever_2021},
        node_dict=node_mappings_2021,
        verbose=True,
    )

    # Create query engine
    print("\nStep 8: Creating query engine...")
    query_engine = RetrieverQueryEngine.from_args(recursive_retriever_2021)

    # Run queries
    print("\n" + "-" * 60)
    print("Running queries on Tesla 2021 10K...")
    print("-" * 60)

    queries = [
        "What was Tesla's total revenue in 2021?",
        "What were Tesla's vehicle deliveries?",
        "What are the main risk factors mentioned?",
    ]

    for q in queries:
        print(f"\nQ: {q}")
        try:
            response = query_engine.query(q)
            print(f"A: {str(response)[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
            print("(Make sure OPENAI_API_KEY is set)")

    # Stop tracing
    print("\nFlushing traces...")
    stop_tracing()

    print("\n" + "=" * 60)
    print("Done! Check http://localhost:5000 to see traces")
    print("=" * 60)
    print("\nYou should see:")
    print("  - Document loading (FlatReader)")
    print("  - Node parsing (UnstructuredElementNodeParser)")
    print("  - Chunk creation for tables and text")
    print("  - Hierarchical retrieval events")
    print("  - LLM calls with context from tables")


if __name__ == "__main__":
    main()
