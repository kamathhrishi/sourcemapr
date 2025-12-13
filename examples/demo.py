"""
SourcemapR Demo - RAG with Attention Paper

Usage:
    # Terminal 1: Start the server
    sourcemapr server

    # Terminal 2: Run this demo
    python examples/demo.py
"""

import sys
from pathlib import Path

# Add parent to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Run the RAG application with tracing."""
    print("\n" + "=" * 50)
    print("SourcemapR Demo - RAG with Attention Paper")
    print("=" * 50)

    # =====================================================
    # THIS IS ALL YOU NEED TO ADD OBSERVABILITY!
    # =====================================================
    from sourcemapr import init_tracing, stop_tracing
    init_tracing(endpoint="http://localhost:5000")
    # =====================================================

    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    print("\nConfiguring LlamaIndex...")
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    print("Loading documents from ./data ...")
    documents = SimpleDirectoryReader("./data").load_data()
    print(f"Loaded {len(documents)} documents")

    print("Creating index...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)
    print("Index created!")

    print("\n" + "-" * 50)
    print("Running queries...")
    print("-" * 50)

    query_engine = index.as_query_engine(similarity_top_k=3)

    queries = [
        "What is the attention mechanism?",
        "How was Llama 2 trained?",
        "What is retrieval augmented generation?",
    ]

    for q in queries:
        print(f"\nQ: {q}")
        response = query_engine.query(q)
        print(f"A: {str(response)[:200]}...")

    # Stop tracing
    print("\nFlushing traces...")
    stop_tracing()

    print("\n" + "=" * 50)
    print("Done! Check http://localhost:5000 to see traces")
    print("=" * 50)


if __name__ == "__main__":
    main()
