"""
SourcemapR Demo - LangChain RAG

Usage:
    # Terminal 1: Start the server
    sourcemapr server

    # Terminal 2: Run this demo
    python examples/langchain_demo.py

Requirements:
    pip install langchain langchain-openai langchain-community faiss-cpu pypdf
"""

import sys
from pathlib import Path

# Add parent to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("\n" + "=" * 50)
    print("SourcemapR Demo - LangChain RAG")
    print("=" * 50)

    # =====================================================
    # Initialize SourcemapR FIRST
    # =====================================================
    from sourcemapr import init_tracing, stop_tracing, get_langchain_handler
    init_tracing(endpoint="http://localhost:5000", experiment="langchain-demo")

    # Get the callback handler for explicit use in chains
    handler = get_langchain_handler()
    # =====================================================

    from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser

    # Load documents
    print("\nLoading documents from ./data ...")
    loader = DirectoryLoader(
        "./data",
        glob="**/*.pdf",
        loader_cls=PyPDFLoader
    )
    documents = loader.load()
    print(f"Loaded {len(documents)} pages")

    # Split into chunks with add_start_index=True for precise positioning
    print("Splitting into chunks (with position tracking)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        add_start_index=True  # Enables precise chunk position tracking in UI!
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    # Create vector store
    print("Creating vector store...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # Create RAG chain
    print("Setting up RAG chain...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
Answer the question based only on the following context:

{context}

Question: {question}

Answer:""")

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # Run queries
    print("\n" + "-" * 50)
    print("Running queries...")
    print("-" * 50)

    queries = [
        "What is the attention mechanism?",
        "How was Llama 2 trained?",
        "What is retrieval augmented generation?",
    ]

    for q in queries:
        print(f"\nQ: {q}")
        # Pass the callback handler to trace the chain
        response = rag_chain.invoke(q, config={"callbacks": [handler]} if handler else {})
        print(f"A: {response[:200]}...")

    # Stop tracing
    print("\nFlushing traces...")
    stop_tracing()

    print("\n" + "=" * 50)
    print("Done! Check http://localhost:5000 to see traces")
    print("=" * 50)


if __name__ == "__main__":
    main()
