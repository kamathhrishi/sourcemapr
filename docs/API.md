# REST API

The SourceMapR server exposes a REST API at `http://localhost:5000`.

## Endpoints

### Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data` | GET | All trace data (documents, chunks, queries, LLM calls) |
| `/api/stats` | GET | Summary statistics |
| `/api/documents` | GET | List all documents |
| `/api/documents/{doc_id}` | GET | Get document with chunks |
| `/api/chunks` | GET | List all chunks |
| `/api/retrievals` | GET | List all queries/retrievals |
| `/api/llm` | GET | List all LLM calls |
| `/api/traces` | GET | List all traces |
| `/api/traces/{trace_id}` | GET | Get trace with spans |

### Experiments

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/experiments` | GET | List all experiments |
| `/api/experiments` | POST | Create experiment |
| `/api/experiments/{id}` | GET | Get experiment |
| `/api/experiments/{id}` | PUT | Update experiment |
| `/api/experiments/{id}` | DELETE | Delete experiment |
| `/api/experiments/{id}/assign` | POST | Assign items to experiment |
| `/api/experiments/{id}/unassign` | POST | Remove items from experiment |

### Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/clear` | POST | Clear all data |
| `/api/traces` | POST | Receive trace data (internal) |

---

## Filtering

Add `?experiment_id=X` to filter by experiment:

```bash
curl http://localhost:5000/api/retrievals?experiment_id=1
```

---

## Examples

### Get all stats

```bash
curl http://localhost:5000/api/stats
```

```json
{
  "total_traces": 5,
  "total_spans": 12,
  "total_documents": 3,
  "total_parsed": 3,
  "total_chunks": 150,
  "total_embeddings": 150,
  "total_retrievals": 10,
  "total_llm_calls": 10
}
```

### Get all queries

```bash
curl http://localhost:5000/api/retrievals
```

```json
[
  {
    "id": 1,
    "query": "What is attention?",
    "results": [
      {"chunk_id": "abc", "score": 0.89, "text": "..."},
      {"chunk_id": "def", "score": 0.84, "text": "..."}
    ],
    "duration_ms": 234.5,
    "timestamp": "2024-12-13T15:30:00"
  }
]
```

### Create experiment

```bash
curl -X POST http://localhost:5000/api/experiments \
  -H "Content-Type: application/json" \
  -d '{"name": "chunk-size-512", "description": "Testing 512 chunk size"}'
```

### Assign queries to experiment

```bash
curl -X POST http://localhost:5000/api/experiments/1/assign \
  -H "Content-Type: application/json" \
  -d '{"retrieval_ids": [1, 2, 3]}'
```

---

## Interactive Docs

Visit `http://localhost:5000/docs` for Swagger UI.
