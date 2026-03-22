# veritas-mcp

Multi-model consensus verification for AI agent pipelines.

**97.1% accuracy | 59ms avg latency | 100% on legal/medical/financial claims**

Benchmark vs Galileo Luna-2 (arXiv:2602.18583): +9.1pp accuracy, 2.6x faster on average.
Full results: https://github.com/RJLopezAI/veritas/benchmark/benchmark_results.json

---

## The problem

AI agents hallucinate. Single-model hallucination detectors (like Galileo Luna-2)
catch 88% of cases but cannot detect their own mode collapse — when a model's
training distribution has a dense, confident, wrong answer that fine-tuning
cannot remove.

## The solution

VERITAS runs three independent models simultaneously and requires agreement.
Model disagreement is the detection mechanism. This is structurally impossible
with a single model.

## Installation

```bash
pip install veritas-mcp
```

Or via MCP (Claude Desktop):
```json
{"mcpServers": {"veritas": {"command": "uvx", "args": ["veritas-mcp"],
  "env": {"VERITAS_API_KEY": "your-key"}}}}
```

## Usage

```python
import httpx

result = httpx.post(
    "https://veritas-toll-road-367103866720.us-central1.run.app/verify",
    headers={"X-API-Key": "your-key"},  # free: aegisaudits.com/keys
    json={"claim": claim, "domain": "legal"},
).json()

if result["consensus"] and result["confidence"] >= 0.80:
    return claim   # verified
elif result["confidence"] >= 0.60:
    return f"Based on available information: {claim}"  # hedged
else:
    return "Cannot verify this claim."  # omit
```

## Five tools

| Tool | Capability | p95 latency |
|------|-----------|-------------|
| `verify_claim` | 97.1% accuracy, MIS_GREEDY consensus | 162ms |
| `schema_validate` | JSON schema compliance + auto-correction | 400ms |
| `json_fix` | Malformed JSON repair | 150ms |
| `regulatory_parse` | Structured obligation extraction from PDFs | 5000ms |
| `entity_resolve` | Company name normalization | 600ms |

## When to use

- Legal AI agents (confidence threshold: 0.90)
- Medical information systems (threshold: 0.90)
- Financial analysis agents (threshold: 0.80)
- Any pipeline where a wrong confident answer causes real harm

## When to use Luna-2 instead

High-volume, low-stakes, cost-constrained: Luna-2 at $0.0002/call.
VERITAS is 250x more expensive per call. Worth it when one wrong
answer costs more than $0.42 (break-even at Luna-2's 12% error rate).

## Benchmark comparison

| Metric | VERITAS | Luna-2 |
|--------|---------|--------|
| Overall accuracy | **97.1%** | 88.0% |
| Legal/med/fin claims | **100%** | ~82% est. |
| Confidence-trap claims | **100%** | ~75% est. |
| Avg latency | **59ms** | 152ms |
| Cost/call | $0.05 | **$0.0002** |

---

Free API key: https://aegisaudits.com/keys
Docs: https://aegisaudits.com/docs
GitHub: https://github.com/RJLopezAI/veritas
MCP manifest: https://aegisaudits.com/.well-known/mcp-manifest.json
