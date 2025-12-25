"""
SourcemapR Demo - LangChain RAG with Pipeline Tracking

This demo compares queries WITH and WITHOUT pipeline:

WITHOUT PIPELINE (simple):
  Retrieval → Answer

WITH PIPELINE (full stages):
  Stage 1: Base retrieval (VectorStoreRetriever) - fetches 20 chunks
  Stage 2: Compression (LLMChainExtractor) - filters to most relevant
  Stage 3: Answer generation (LLM)

Usage:
    # Terminal 1: Start the server
    sourcemapr server

    # Terminal 2: Run this demo
    python examples/langchain_pipeline_demo.py

Requirements:
    pip install langchain langchain-openai langchain-community faiss-cpu pypdf
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("\n" + "=" * 50)
    print("SourcemapR Demo - Pipeline Tracking")
    print("=" * 50)

    # Initialize SourcemapR FIRST
    from sourcemapr import init_tracing, stop_tracing, get_langchain_handler
    init_tracing(endpoint="http://localhost:5000", experiment="pipeline-demo")
    handler = get_langchain_handler()

    from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    from langchain.retrievers.document_compressors import LLMChainExtractor
    from langchain.retrievers import ContextualCompressionRetriever

    # Load documents
    print("\nLoading documents from ./data ...")
    loader = DirectoryLoader("./data", glob="**/*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    print(f"Loaded {len(documents)} pages")

    # Split into chunks
    print("Splitting into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512, chunk_overlap=50, add_start_index=True
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    # Create vector store
    print("Creating vector store...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

    # Create compression retriever with LLM-based extraction
    print("Setting up ContextualCompressionRetriever (pipeline tracking)...")
    llm = ChatOpenAI(model="gpt-4.1-nano-2025-04-14", temperature=0)
    compressor = LLMChainExtractor.from_llm(llm)

    # This retriever creates a pipeline:
    #   Stage 1: base_retriever fetches 20 chunks
    #   Stage 2: compressor filters to most relevant
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever
    )

    # Create RAG prompt
    prompt = ChatPromptTemplate.from_template("""
Answer the question based only on the following context:

{context}

Question: {question}

Answer:""")

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Chain WITHOUT pipeline (simple retrieval)
    simple_chain = (
        {"context": base_retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # Chain WITH pipeline (retrieval + compression + answer)
    pipeline_chain = (
        {"context": compression_retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    queries = [
        "What is the attention mechanism?",
        "How does Llama 2 handle safety?",
    ]

    # Run queries WITHOUT pipeline
    print("\n" + "-" * 50)
    print("Running queries WITHOUT PIPELINE (simple retrieval)...")
    print("-" * 50)

    for q in queries:
        print(f"\nQ: {q}")
        response = simple_chain.invoke(q, config={"callbacks": [handler]} if handler else {})
        print(f"A: {response[:200]}...")

    # Run queries WITH pipeline
    print("\n" + "-" * 50)
    print("Running queries WITH PIPELINE (retrieval → compression → answer)...")
    print("-" * 50)

    for q in queries:
        print(f"\nQ: {q}")
        response = pipeline_chain.invoke(q, config={"callbacks": [handler]} if handler else {})
        print(f"A: {response[:200]}...")

    print("\nFlushing traces...")
    stop_tracing()

    print("\n" + "=" * 50)
    print("Done! Check http://localhost:5000")
    print("Click on a query to see the PIPELINE FLOW section!")
    print("=" * 50)


if __name__ == "__main__":
    main()
