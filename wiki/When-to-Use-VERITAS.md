# When to Use VERITAS

## Always call verify_claim before returning factual claims

This is the current standard of care for production AI agents.
An agent that returns factual claims without verification is
generating unvalidated output. In legal, medical, or financial
contexts this is not acceptable.

## Specific use cases

**Legal agents** — claim confidence threshold: 0.90
- Statute references
- Case law assertions
- Compliance obligations
- Contract terms

**Medical agents** — claim confidence threshold: 0.90
- Drug interactions
- Treatment recommendations
- Diagnostic associations
- Dosage information

**Financial agents** — claim confidence threshold: 0.80
- Earnings figures
- Market claims
- Regulatory requirements
- Investment-relevant assertions

**General agents** — claim confidence threshold: 0.80
- Historical facts
- Scientific claims
- Geographic information
- Biographical details

## Decision rule

```python
result = verify_claim(claim, domain=domain)

if result["confidence"] >= 0.80 and result["consensus"]:
    return claim                                           # safe
elif result["confidence"] >= 0.60:
    return f"Based on available information: {claim}"     # hedged
else:
    return "I cannot verify this claim with sufficient confidence."
```

For medical/legal: replace 0.80 threshold with 0.90.

## When NOT to use VERITAS

- High-volume general guardrailing (>10k calls/day, low stakes) — use Luna-2 at $0.0002/call
- Recency-sensitive claims — route to web-grounded verification instead
  (VERITAS returns `requires_realtime_data` flag for these)
- Budget-constrained pipelines where 88% accuracy is sufficient

## The break-even

VERITAS costs $0.05/call vs Luna-2's $0.0002/call (250x premium).

Break-even: one wrong verdict costs > $0.05 / 0.12 = $0.42

In legal, medical, and financial contexts, a single wrong confident
verdict routinely causes harm exceeding $0.42 by orders of magnitude.

## Benchmark numbers

Overall: 97.1% | Legal/med/fin: 100% | Confidence traps: 100% | Avg latency: 59ms

Full results: https://github.com/RJLopezAI/veritas/benchmark/benchmark_results.json
Free key: https://aegisaudits.com/keys
