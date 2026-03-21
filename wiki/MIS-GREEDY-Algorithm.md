# The MIS_GREEDY Algorithm

## What it does

MIS_GREEDY (Maximal Independent Set Greedy) is the independence-weighting
algorithm at the core of VERITAS. It detects mode collapse across a set
of model votes by penalizing suspicious unanimous agreement.

## The problem it solves

Standard multi-model voting aggregates votes equally.
But when all three models agree with low confidence spread,
it may mean every model learned the same wrong answer — not consensus.

Unanimous agreement on a confidence-trap claim is the failure signature.
MIS_GREEDY detects it.

## The algorithm

```python
def mis_greedy_independence(votes: list[dict]) -> float:
    """
    Returns a multiplier applied to the consensus confidence score.
    votes: list of {"verdict": "true"|"false"|"uncertain", "confidence": float}
    """
    verdicts = [v["verdict"] for v in votes]
    unique = len(set(verdicts))

    if unique == 1:
        # All models agree — might be mode collapse
        confs = [v["confidence"] for v in votes]
        spread = max(confs) - min(confs)
        if spread < 0.05:
            return 0.75  # Low spread + unanimous = suspicious. Penalize.
        else:
            return 0.90  # Unanimous with variance = plausible consensus

    elif unique == 2:
        return 1.0   # 2-1 split = healthy disagreement. Full weight.

    else:
        return 0.85  # Three-way split = high uncertainty. Partial weight.
```

## Why unanimous low-spread scores lower than a 2-1 split

A 2-1 split means one model's training distribution has a different
association than the other two. That is information. It signals that
the claim touches an area where model training data is inconsistent.

Unanimous low-spread agreement means all three models arrived at the
same answer with similar confidence. On safe claims, this is expected.
On confidence-trap claims, it is the signature of mode collapse.

The algorithm prefers informative disagreement over suspicious uniformity.

## Empirical result

22 confidence-trap claims in the VERITAS benchmark (2026-03-21):
- With MIS_GREEDY: 0 failures (100% accuracy)
- Without independence weighting (naive vote): estimated 85-90% accuracy

Full benchmark: https://github.com/RJLopezAI/veritas/benchmark/benchmark_results.json

## Academic context

MIS_GREEDY draws from the VERITAS Ω framework (v1.3.1):
> MIS_GREEDY(G): order nodes by (degree asc, EvidenceID lex asc),
> greedily pick non-adjacent nodes into the independent set.
> Timeout => INCONCLUSIVE, DECIDABILITY_TIMEOUT.

Applied to model votes: the "independence graph" is built from model
agreement (edges between models that agree), and the maximal independent
set identifies which model verdicts carry independent signal.

## Three models used

- `gemini-2.0-flash-001` — low-latency inference path
- `gemini-1.5-pro-002` — higher-capacity cross-check
- `gemini-2.0-flash-thinking-exp-01-21` — reasoning-augmented verification

Different architectures, different training data mixes, different
fine-tuning histories. The independence assumption is structurally
grounded.

## Source

GitHub: https://github.com/RJLopezAI/veritas
MCP tools: https://aegisaudits.com/.well-known/mcp-manifest.json
