"""
SourcemapR Demo - LangChain RAG over Tesla 10K SEC Filings

This example demonstrates RAG over SEC 10K filings using LangChain:
- BSHTMLLoader or UnstructuredHTMLLoader for loading HTML files
- RecursiveCharacterTextSplitter with add_start_index=True for precise chunk positioning
- FAISS vector store for retrieval

Usage:
    # Terminal 1: Start the server
    sourcemapr server

    # Terminal 2: Run this demo
    python examples/tesla_10k_sec_langchain.py

Requirements:
    pip install langchain langchain-openai langchain-community faiss-cpu beautifulsoup4 lxml
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
    """Run LangChain RAG over Tesla 10K SEC filings with tracing."""
    print("\n" + "=" * 60)
    print("SourcemapR Demo - LangChain Tesla 10K SEC Filings")
    print("RAG with Precise Chunk Position Tracking")
    print("=" * 60)

    # =====================================================
    # THIS IS ALL YOU NEED TO ADD OBSERVABILITY!
    # =====================================================
    from sourcemapr import init_tracing, stop_tracing, get_langchain_handler
    init_tracing(endpoint="http://localhost:5000", experiment="langchain-sec-10k")

    # Get the callback handler for explicit use in chains
    handler = get_langchain_handler()
    # =====================================================

    # Download SEC filings
    print("\nStep 1: Downloading Tesla 10K SEC filings...")
    data_dir = download_tesla_10k_files()

    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("\nWARNING: OPENAI_API_KEY not set. LLM queries will fail.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")

    # Import LangChain components
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser

    # Try BSHTMLLoader first, fall back to UnstructuredHTMLLoader
    print("\nStep 2: Loading Tesla 10K SEC filing...")
    try:
        from langchain_community.document_loaders import BSHTMLLoader
        loader = BSHTMLLoader(str(data_dir / "tesla_2021_10k.htm"))
        loader_name = "BSHTMLLoader"
    except ImportError:
        from langchain_community.document_loaders import UnstructuredHTMLLoader
        loader = UnstructuredHTMLLoader(str(data_dir / "tesla_2021_10k.htm"))
        loader_name = "UnstructuredHTMLLoader"

    print(f"Using {loader_name} to load HTML...")
    documents = loader.load()
    print(f"Loaded {len(documents)} document(s)")

    # Split into chunks with add_start_index=True for precise positioning
    # This enables exact character position tracking in the UI!
    print("\nStep 3: Splitting into chunks (with position tracking)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,  # <-- IMPORTANT: Enables precise chunk positioning!
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    # Show example of chunk metadata with start_index
    if chunks:
        sample = chunks[0]
        print(f"\nSample chunk metadata:")
        print(f"  - start_index: {sample.metadata.get('start_index', 'N/A')}")
        print(f"  - source: {sample.metadata.get('source', 'N/A')}")
        print(f"  - text preview: {sample.page_content[:100]}...")

    # Create vector store
    print("\nStep 4: Creating vector store...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 50})
    print("Vector store created!")

    # Create RAG chain
    print("\nStep 5: Setting up RAG chain...")
    llm = ChatOpenAI(model="gpt-4.1-nano-2025-04-14", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
You are analyzing Tesla's 2021 10K SEC filing. Answer the question based only on the following context.
If the context contains financial data or tables, include specific numbers in your answer.

Context:
{context}

Question: {question}

Answer:""")

    def format_docs(docs):
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # Run queries about SEC filing
    print("\n" + "-" * 60)
    print("Running queries on Tesla 2021 10K...")
    print("-" * 60)

    queries = [
        "What was Tesla's total revenue in 2021?",
        "How many vehicles did Tesla deliver in 2021?",
        "What are the main risk factors mentioned in the filing?",
        "What is Tesla's cash position?",
    ]

    for q in queries:
        print(f"\nQ: {q}")
        try:
            # Pass the callback handler to trace the chain
            response = rag_chain.invoke(q, config={"callbacks": [handler]} if handler else {})
            print(f"A: {response[:500]}...")
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
    print("  - Document loading (BSHTMLLoader/UnstructuredHTMLLoader)")
    print("  - Chunk creation with start_index positions")
    print("  - Retrieval events with chunk locations")
    print("  - LLM calls with SEC filing context")
    print("\nThe UI will show PRECISE chunk positions because")
    print("we used add_start_index=True in the text splitter!")


if __name__ == "__main__":
    main()
