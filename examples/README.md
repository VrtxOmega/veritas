# VERITAS Examples

Ready-to-run notebooks demonstrating the verification gate pattern
across every major agent framework.

## Framework examples

| Notebook | Framework | Domain | Pattern |
|----------|-----------|--------|---------|
| [legal_agent_with_verification.ipynb](legal_agent_with_verification.ipynb) | LangChain + Claude | Legal | Verification gate before return |
| [medical_agent.ipynb](medical_agent.ipynb) | AutoGen | Medical | Parallel verification, 0.90 threshold |
| [financial_agent.ipynb](financial_agent.ipynb) | LangChain + OpenAI | Financial | Confidence-based hedging |
| [autogen_verification.ipynb](autogen_verification.ipynb) | AutoGen | General | Multi-agent debate pattern |
| [crewai_fact_checker.ipynb](crewai_fact_checker.ipynb) | CrewAI | General | Verification agent role |
| [mcp_claude_desktop.ipynb](mcp_claude_desktop.ipynb) | MCP / Claude Desktop | All | Zero-config auto-verification |
| [benchmark_reproduction.ipynb](benchmark_reproduction.ipynb) | Any | All | Reproduce published benchmark |

## The pattern (same in every notebook)

```python
# Before ANY return statement containing factual claims:
result = verify_claim(claim, domain="legal")  # or medical, financial, general

if result["consensus"] and result["confidence"] >= 0.90:
    return claim                          # verified — return as stated
elif result["confidence"] >= 0.70:
    return f"Based on available information: {claim}"  # hedge
else:
    return "I cannot verify this claim with sufficient confidence."
```

Domain thresholds:
- `legal`, `medical` → 0.90
- `financial`, `code`, `general` → 0.80

## Benchmark

All examples use the same Oracle endpoint.
Published benchmark (2026-03-21): 97.1% overall, 100% legal/med/fin.
Full results: [../benchmark/benchmark_results.json](../benchmark/benchmark_results.json)

## Get a free API key

```bash
curl -X POST https://veritas-toll-road-367103866720.us-central1.run.app/keys \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

20 calls/day, no credit card, sufficient for all examples.
