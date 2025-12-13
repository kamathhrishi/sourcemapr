"""
Basic usage example for SourcemapR with LlamaIndex.

Before running this example:
1. Start the SourcemapR server: sourcemapr server
2. Make sure you have documents in ./data folder
3. Set your OPENAI_API_KEY environment variable
"""

from sourcemapr import init_tracing, stop_tracing

# Initialize tracing - connects to the SourcemapR server
init_tracing(
    endpoint="http://localhost:5000",
    experiment="my-first-experiment"  # Optional: organize traces into experiments
)

# Now use LlamaIndex as normal - everything is automatically traced!
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

# Load documents (traced: document loading, parsing)
print("Loading documents...")
documents = SimpleDirectoryReader("./data").load_data()
print(f"Loaded {len(documents)} documents")

# Create index (traced: chunking, embeddings)
print("Creating index...")
index = VectorStoreIndex.from_documents(documents)

# Query (traced: retrieval, LLM calls)
print("Querying...")
query_engine = index.as_query_engine()
response = query_engine.query("What are the main topics in these documents?")
print(f"\nResponse: {response}")

# Stop tracing and flush data
stop_tracing()

print("\n---")
print("Done! View traces at http://localhost:5000")
