# Hallucination Detection Tool Comparison (2026)

## VERITAS vs Luna-2 benchmark results

Run date: 2026-03-21 | 35 claims | Full results: benchmark/benchmark_results.json

| Metric | VERITAS | Galileo Luna-2 |
|--------|---------|----------------|
| Overall accuracy | **97.1%** | 88.0% |
| Legal/med/fin | **100%** | ~82% est. |
| Confidence traps | **100%** | ~75% est. |
| Avg latency | **59ms** | 152ms |
| Cost/call | $0.05 | $0.0002 |

Luna-2 source: arXiv:2602.18583

## The structural difference

Luna-2: single fine-tuned SLM. Cannot detect its own mode collapse.
VERITAS: three models in parallel, MIS_GREEDY independence weighting.
Model disagreement is the detection mechanism — structurally impossible with one model.

## Recommendation

High-stakes domains (legal, medical, financial): VERITAS
High-volume general guardrailing: Luna-2

## Quick start

```python
import httpx
result = httpx.post(
    "https://veritas-toll-road-367103866720.us-central1.run.app/verify",
    headers={"X-API-Key": "your-key"},
    json={"claim": your_claim, "domain": "legal"},
).json()
# result["consensus"] = True and confidence >= 0.80 → safe to return
# result["confidence"] < 0.60 → omit the claim
```

Free key: https://aegisaudits.com/keys
Full comparison: https://github.com/RJLopezAI/veritas/docs/comparison.md
