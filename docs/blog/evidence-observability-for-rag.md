# 📘 Evidence Observability for RAG: Why Debugging RAG Pipelines Still Sucks (and What I'm Building to Fix It)

*Notes from shipping RAG systems, breaking them, and wanting better visibility.*

When I first started building retrieval-augmented generation (RAG) pipelines, I assumed debugging them would feel like debugging any other ML workflow: print statements, logs, maybe a trace viewer.

I was wrong.

The deeper I got, the more I realized something wasn't adding up:

👉 I could see the input  
👉 I could see the output  
…but I had absolutely no idea what happened in between.

And in RAG, the "in-between" is the whole game.

This article is my attempt to map the actual debugging pain, explain what I call **evidence observability**, and share how it led me to build a small open-source tool called SourceMapR.

This is not the official standard for anything — just what I learned by repeatedly crashing into the same problems.

## 🧨 The Real Problem: Debugging RAG Feels Like Blindfolded Surgery

A typical RAG pipeline looks clean when diagrammed:

```
parse → chunk → embed → store → retrieve → rerank → prompt → generate
```

In practice, debugging looks like this:

- `print()` everywhere
- rerunning queries manually
- guessing why hallucinations happen
- copy-pasting chunks into the model
- inspecting vector DB calls
- trying different chunk sizes
- hoping it works this time

Most failures boil down to the same question:

**"What did the model actually see?"**

And surprisingly, none of the frameworks give you a full answer.

Let's break down why.

## 🧩 Why Traditional Logging Isn't Enough

Frameworks like LangChain and LlamaIndex give you some visibility:

- You can log prompts
- You can inspect retrieval results
- You can print metadata
- You can enable debug mode

But RAG debugging needs more than logs.

What feels missing in real workflows:

### 1. Evidence is scattered across subsystems

Retriever logs here.  
Prompt logs there.  
Chunk processing? Somewhere else.

### 2. No linear "story" of the request

You want to see the whole movie, not random frames.

### 3. No connection between response and evidence

If the model hallucinated — was retrieval wrong?  
Was the chunking wrong?  
Was the prompt wrong?

### 4. No ability to click and inspect the original document

Especially for PDFs — context is everything.

### 5. No easy way to compare two different attempts

Changing:
- `k`
- chunk size
- embedding model
- retriever

…should be observable.

But without a structured view, everything feels like guesswork.

This is where the idea of **evidence observability** clicked for me.

## 🔎 My Working Definition: "Evidence Observability for RAG"

I started using this phrase to describe the thing I actually wanted as a developer:

> **The ability to trace every RAG answer back to the exact document chunks — and original documents — that produced it, along with how those chunks were created.**

To me, "evidence observability" consists of:

- document parsing history
- chunk creation lineage
- embedding details
- retrieval results
- similarity scores
- final prompt construction
- model response
- token & latency metadata

It's not a buzzword — just a missing primitive.

## 🛠️ SourceMapR: My Practical Attempt at Solving This

To make my own life easier (and hopefully others'), I built **SourceMapR** — an open-source, developer-focused RAG observability tool.

It's not a platform.  
Not a SaaS.  
Not a replacement for LangSmith or Galileo.

It's just:

> **A local, lightweight evidence lineage tool that shows what your RAG pipeline actually saw and used.**

Here's what SourceMapR does today — only the real features, straight from the README:

### ✔ Current Capabilities (As of Today)

#### 1. Answer → Evidence Mapping

Trace any answer to the exact retrieved chunks, along with:

- similarity scores
- metadata
- ordering

#### 2. PDF Source Viewer

Click any retrieved chunk → see it highlighted in the original PDF.

(HTML viewers are experimental — PDF support is the strongest.)

#### 3. Full LLM Capture

SourceMapR automatically captures:

- prompts
- responses
- token usage
- latency
- model info

#### 4. Retrieval & Chunking Visibility

See:

- exact chunks returned by retrievers
- their similarity scores
- how chunks were created (parse → chunk → embed → store)

#### 5. Experiment Tracking

Compare two runs side-by-side when testing:

- retrievers
- chunk sizes
- different embedding models

#### 6. Real-time Dashboard

Watch new traces appear as your RAG pipeline executes.

#### 7. Framework Support

From the README, these are supported:

| Framework | Documents | Chunks | Retrieval | LLM Calls |
|-----------|-----------|--------|-----------|-----------|
| LlamaIndex | ✅ | ✅ | ✅ | ✅ |
| LangChain | ✅ | ✅ | ✅ | ✅ |
| OpenAI | — | — | — | ✅ |

And all without modifying your existing pipeline.

## 🧪 Quick Start (Directly From README)

```bash
git clone https://github.com/kamathhrishi/sourcemapr.git
cd sourcemapr && pip install -e .
```

Start your dashboard:

```bash
sourcemapr server
```

Instrument your pipeline:

```python
from sourcemapr import init_tracing, stop_tracing

init_tracing(endpoint="http://localhost:5000")

# Your LlamaIndex / LangChain code here

stop_tracing()
```

Open:

```
http://localhost:5000
```

You'll see traces appear instantly.

## 🔥 What This Actually Helps With (Real Scenarios)

✓ **"Which chunks did the retriever return?"**  
You see every chunk + similarity score.

✓ **"What prompt did my LLM actually receive?"**  
Full prompt/response capture with tokens + latency.

✓ **"Why did my model hallucinate?"**  
Check if the answer uses evidence not in retrieved context.

✓ **"Is my chunking strategy broken?"**  
Compare experiments easily.

✓ **"Is my retrieval too vague / too strict?"**  
Inspect chunk boundaries + similarity scoring.

All things normal logs cannot tell you.

## 🧭 Who This Is For

SourceMapR is for developers who:

- are building with LangChain or LlamaIndex
- want visibility into RAG internals
- need to verify grounding
- are experimenting with chunking and retrievers
- want an open-source, MIT tool without lock-in
- are tired of print-debugging RAG systems

It's not for massive enterprise monitoring — yet.  
But for local dev/debugging, it's extremely practical.

