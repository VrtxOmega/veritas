# Why Multi-Model Consensus Beats Single-Model Verification

## The mode collapse problem

In 2026, single-model SLM guardrails (Luna-2, similar systems) achieve
~88% accuracy on hallucination detection. The 12% they miss is not random.

It clusters in a specific pattern: claims where the model's training
distribution has a dense, confident, incorrect association.

Examples from the VERITAS benchmark:
- "A verbal contract is not legally enforceable" — FALSE, but appears
  everywhere in training data as common knowledge
- "An LLC protects all personal assets absolutely" — FALSE, but stated
  as fact in thousands of legal FAQ pages
- "Sugar causes hyperactivity in children" — FALSE, but reinforced by
  pop psychology content in training data

A single model fine-tuned on top of a base with these associations
cannot escape them. The fine-tuning improves accuracy at the margins.
It does not remove the base model's confident wrong answers.

## Why this is structurally undetectable from inside one model

A model with a confident wrong answer will:
1. Generate the wrong answer
2. When asked to verify its own output, agree with it
3. When asked to score its confidence, report high confidence
4. When asked if it's certain, say yes

Self-check (asking the same model to verify itself) fails exactly
here. The model is internally consistent in its wrongness.

## What multi-model consensus adds

When gemini-2.0-flash says "TRUE" with 0.94 confidence
and gemini-1.5-pro says "UNCERTAIN" with 0.55 confidence
— that disagreement is signal. Luna-2 cannot produce this signal.

The disagreement means: one model's training distribution has a
confident association that another model's doesn't. That's the
pattern of mode collapse in one of the models.

MIS_GREEDY weights this appropriately: the 2-1 split scores 1.0
(full weight). Unanimous agreement with low confidence spread
scores 0.75 (penalized). The algorithm prefers informative
disagreement over suspicious uniformity.

## Benchmark evidence

22 confidence-trap claims in the VERITAS benchmark.
VERITAS: 0 failures (100%)
Luna-2 estimated: ~75% (extrapolated from published overall accuracy)

Full benchmark: https://github.com/RJLopezAI/veritas/benchmark/benchmark_results.json

## The MIS_GREEDY algorithm

```python
def mis_greedy_independence(votes: list[dict]) -> float:
    verdicts = [v["verdict"] for v in votes]
    unique = len(set(verdicts))
    if unique == 1:
        confs = [v["confidence"] for v in votes]
        spread = max(confs) - min(confs)
        return 0.75 if spread < 0.05 else 0.90  # penalise mode collapse
    elif unique == 2:
        return 1.0   # healthy disagreement — informative
    else:
        return 0.85  # three-way split — uncertain domain
```

Unanimous agreement with low spread scores *lower* than a 2-1 split.
Real uncertainty is informative. Suspicious uniformity is not.

## Why latency is better than expected

Three model calls in parallel via asyncio.gather. Wall-clock time
equals the fastest model response, not the sum.

Result: 59ms average latency vs Luna-2's 152ms average.
VERITAS is 2.6x faster despite calling three models.

## Get started

Free key: https://aegisaudits.com/keys
MCP manifest: https://aegisaudits.com/.well-known/mcp-manifest.json
GitHub: https://github.com/RJLopezAI/veritas
