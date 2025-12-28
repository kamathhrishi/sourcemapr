"""
SourcemapR Demo - Elaborate LangChain RAG over Tesla 10K SEC Filings

This is an expanded version with many more diverse queries covering:
- Financial metrics (revenue, costs, margins, cash flow)
- Operations (deliveries, production, factories)
- Risk factors and legal matters
- Business segments and strategy
- Management and governance
- Environmental and sustainability
- Supply chain and manufacturing

After running this, use the MCP evaluation script to run LLM-as-judge evaluations.

Usage:
    # Terminal 1: Start the server
    sourcemapr server

    # Terminal 2: Run this demo
    python examples/tesla_10k_sec_elaborate.py

    # Terminal 3: Run evaluations via MCP
    python examples/mcp_llm_judge.py

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


# Comprehensive queries covering all aspects of a 10K filing
ELABORATE_QUERIES = [
    # === FINANCIAL METRICS ===
    # Revenue & Growth
    "What was Tesla's total revenue in 2021 and how did it compare to 2020?",
    "What was the revenue breakdown by segment (automotive vs energy)?",
    "What was Tesla's automotive revenue excluding regulatory credits?",
    "How much revenue did Tesla generate from regulatory credits in 2021?",
    "What was the year-over-year revenue growth rate?",

    # Costs & Margins
    "What was Tesla's gross profit margin in 2021?",
    "What were Tesla's total operating expenses?",
    "What was the cost of automotive revenue?",
    "How did Tesla's automotive gross margin change from 2020 to 2021?",
    "What were the research and development expenses?",

    # Profitability
    "What was Tesla's net income in 2021?",
    "What was Tesla's operating income?",
    "What was Tesla's earnings per share (EPS)?",
    "Did Tesla achieve GAAP profitability in 2021?",

    # Cash Flow & Balance Sheet
    "What was Tesla's cash position at the end of 2021?",
    "What was the free cash flow for 2021?",
    "What was Tesla's total debt?",
    "What were Tesla's capital expenditures in 2021?",
    "What was Tesla's total assets value?",

    # === OPERATIONS & PRODUCTION ===
    # Deliveries & Production
    "How many vehicles did Tesla deliver in 2021?",
    "What was the production volume by model (Model S, 3, X, Y)?",
    "How did deliveries compare to 2020?",
    "What was the quarterly breakdown of deliveries?",

    # Manufacturing & Factories
    "Where are Tesla's manufacturing facilities located?",
    "What is the production capacity of the Fremont factory?",
    "What was the status of Gigafactory Berlin?",
    "What was the status of Gigafactory Texas?",
    "What is the production capacity of Gigafactory Shanghai?",

    # Products
    "What new products or vehicles did Tesla announce or launch?",
    "What is the status of the Cybertruck?",
    "What is the status of the Tesla Semi?",
    "What updates were made to existing vehicle models?",

    # === RISK FACTORS ===
    "What are the main risk factors mentioned in the filing?",
    "What supply chain risks does Tesla face?",
    "What regulatory risks does Tesla face?",
    "What competition risks does Tesla mention?",
    "What are the risks related to battery supply and raw materials?",
    "What cybersecurity risks are mentioned?",
    "What risks does Tesla face from its Autopilot/FSD technology?",
    "What are the geopolitical risks mentioned?",

    # === BUSINESS STRATEGY ===
    "What is Tesla's stated mission?",
    "What is Tesla's competitive advantage according to the filing?",
    "What is Tesla's strategy for the energy business?",
    "What is Tesla's approach to vertical integration?",
    "What is Tesla's direct sales model and how does it differ from traditional automakers?",

    # === TECHNOLOGY & INNOVATION ===
    "What is the status of Tesla's Full Self-Driving (FSD) technology?",
    "What battery technology developments are mentioned?",
    "What is 4680 battery cell and its significance?",
    "What is Tesla's approach to software updates?",
    "What AI and machine learning capabilities does Tesla have?",

    # === ENERGY BUSINESS ===
    "What were the energy storage deployments in 2021?",
    "What is the Megapack product?",
    "What is Tesla's solar business performance?",
    "How does the energy segment contribute to overall revenue?",

    # === LEGAL & REGULATORY ===
    "What legal proceedings is Tesla involved in?",
    "What regulatory approvals does Tesla need for its vehicles?",
    "What environmental regulations affect Tesla?",
    "Are there any SEC investigations mentioned?",

    # === EMPLOYEES & MANAGEMENT ===
    "How many employees does Tesla have?",
    "Who are the key executive officers?",
    "What is Elon Musk's compensation?",
    "What is the board of directors composition?",

    # === SUSTAINABILITY & ESG ===
    "What environmental initiatives does Tesla mention?",
    "What is Tesla's approach to sustainability?",
    "What is Tesla's carbon footprint?",

    # === SPECIFIC NUMBERS ===
    "What was the average selling price per vehicle?",
    "What is the warranty reserve?",
    "What were the stock-based compensation expenses?",
    "What is the depreciation and amortization?",
]


def main():
    """Run elaborate LangChain RAG over Tesla 10K SEC filings with tracing."""
    print("\n" + "=" * 70)
    print("SourcemapR Demo - ELABORATE Tesla 10K SEC Analysis")
    print("Comprehensive RAG with {} Diverse Queries".format(len(ELABORATE_QUERIES)))
    print("=" * 70)

    # =====================================================
    # THIS IS ALL YOU NEED TO ADD OBSERVABILITY!
    # =====================================================
    from sourcemapr import init_tracing, stop_tracing, get_langchain_handler
    init_tracing(endpoint="http://localhost:5000", experiment="tesla-10k-elaborate")

    # Get the callback handler for explicit use in chains
    handler = get_langchain_handler()
    # =====================================================

    # Download SEC filings
    print("\nStep 1: Downloading Tesla 10K SEC filings...")
    data_dir = download_tesla_10k_files()

    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("\nERROR: OPENAI_API_KEY not set.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Import LangChain components
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser

    # Load document
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

    # Split into chunks with position tracking
    print("\nStep 3: Splitting into chunks (with position tracking)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    # Create vector store
    print("\nStep 4: Creating vector store...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    print("Vector store created!")

    # Create RAG chain
    print("\nStep 5: Setting up RAG chain...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
You are an expert financial analyst analyzing Tesla's 2021 10K SEC filing.
Answer the question based ONLY on the following context from the filing.
Be specific and include exact numbers, dates, and figures when available.
If the information is not in the context, say "Information not found in the provided context."

Context from Tesla 2021 10K:
{context}

Question: {question}

Detailed Answer:""")

    def format_docs(docs):
        return "\n\n---\n\n".join(
            f"[Chunk from position {doc.metadata.get('start_index', 'unknown')}]\n{doc.page_content}"
            for doc in docs
        )

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # Run all queries
    print("\n" + "=" * 70)
    print(f"Running {len(ELABORATE_QUERIES)} queries on Tesla 2021 10K...")
    print("=" * 70)

    results = []
    for i, q in enumerate(ELABORATE_QUERIES, 1):
        print(f"\n[{i}/{len(ELABORATE_QUERIES)}] Q: {q}")
        try:
            response = rag_chain.invoke(q, config={"callbacks": [handler]} if handler else {})
            results.append({"query": q, "response": response, "status": "success"})
            # Print truncated response
            display_response = response[:300] + "..." if len(response) > 300 else response
            print(f"A: {display_response}")
        except Exception as e:
            results.append({"query": q, "response": str(e), "status": "error"})
            print(f"Error: {e}")

    # Stop tracing
    print("\n\nFlushing traces...")
    stop_tracing()

    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total queries: {len(ELABORATE_QUERIES)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"\nExperiment: tesla-10k-elaborate")
    print(f"Dashboard: http://localhost:5000")
    print("\n" + "=" * 70)
    print("NEXT STEP: Run LLM-as-Judge evaluations via MCP")
    print("=" * 70)
    print("\n1. Add SourcemapR MCP server to your Claude Code config:")
    print('   Edit ~/.claude/claude_desktop_config.json (or settings.json):')
    print('''
   {
     "mcpServers": {
       "sourcemapr": {
         "command": "sourcemapr",
         "args": ["mcp"]
       }
     }
   }
''')
    print("2. Restart Claude Code to load the MCP server")
    print("\n3. Ask Claude to evaluate:")
    print('   "Use the sourcemapr MCP tools to evaluate all queries from the')
    print('    tesla-10k-elaborate experiment. For each query, score relevance,')
    print('    faithfulness, and completeness. Also categorize each query."')
    print("\n4. View results in the Evaluations tab at http://localhost:5000")


if __name__ == "__main__":
    main()
