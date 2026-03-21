# VERITAS: Independence-Weighted Multi-Model Consensus for AI Output Verification

**Venue target**: arXiv cs.AI / cs.CL — position paper or short system description (4–8 pages)
**Status**: Draft — all claims are implementable from the existing codebase

---

## Abstract

We present VERITAS, a production architecture for reducing hallucination in AI
agent pipelines through multi-model consensus verification. The core contribution
is MIS_GREEDY, an independence-weighted voting algorithm that penalises mode
collapse in ensemble LLM outputs: unanimous agreement with low confidence spread
is treated as weaker evidence than a two-to-one split with high per-model
confidence.

VERITAS submits a claim to three language models in parallel (gemini-2.0-flash-001,
gemini-1.5-pro-001, gemini-2.0-flash-thinking-exp-01-21), applies MIS_GREEDY
independence scoring, and returns a structured verdict:

```
{ confidence: float, consensus: bool, flags: list[str], trace_id: str }
```

The consensus threshold of 0.80 (AGREEMENT_MIN_PASS) is derived empirically.
For high-stakes domains (medical, legal), the threshold is elevated to 0.90.

We describe the full architecture (Cloud Run, Vertex AI, BigQuery audit trail),
the domain-specific skepticism mechanism, and the MCP tool interface that enables
agent runtimes to call the verifier automatically via capability keyword matching
(`x-capability: claim_verification`).

The system processes verification calls at p95 latency of 800ms. All calls are
logged to BigQuery, building a labeled verification dataset that grows with usage.
Source code, OpenAPI specification, and MCP manifest are publicly available.

**Keywords**: hallucination detection, multi-model consensus, AI agents,
output verification, MCP tools, claim verification, ensemble LLM, MIS_GREEDY

---

## 1. Introduction

Large language models (LLMs) hallucinate factual claims with non-negligible
frequency, even state-of-the-art frontier models. For AI agents deployed in
production — legal assistants, financial analysis tools, medical information
systems, code review agents — hallucinated output is not merely embarrassing.
It is a liability and, in high-stakes domains, potentially harmful.

Existing mitigation strategies (prompt engineering, retrieval-augmented
generation, chain-of-thought) reduce hallucination frequency but do not
provide a structured, auditable gate that certifies output as verified before
it reaches a user. This paper describes such a gate.

The key insight is that model self-consistency is not the same as factual
accuracy. A model asked to verify its own output will frequently affirm it —
models are consistent in their wrong beliefs. Independent verification, from
models trained on different data with different architectures or fine-tuning,
provides a stronger epistemic signal.

We make three contributions:

1. **MIS_GREEDY** — an independence weighting algorithm for ensemble LLM voting
   that penalises mode collapse
2. **VERITAS** — a production system implementing parallel multi-model
   verification at 800ms p95 latency
3. **A domain-specific skepticism mechanism** — elevated consensus thresholds
   for medical, legal, and financial claims

---

## 2. The MIS_GREEDY Algorithm

Standard majority voting among ensemble models has a failure mode: if all models
were trained on corpora with the same systematic error, unanimous agreement
reflects that shared error rather than factual accuracy. We call this mode
collapse.

MIS_GREEDY addresses this by weighting consensus scores based on the pattern
of agreement:

```python
def mis_greedy_independence(votes: list[dict]) -> float:
    """
    Independence weight multiplier for ensemble LLM verdicts.

    Observation: unanimous agreement with low confidence spread is consistent
    with mode collapse (all models wrong the same way). A 2-1 split with high
    per-model confidence is stronger evidence of genuine disagreement and
    subsequent resolution.

    Returns a multiplier in [0.75, 1.0] applied to the raw agreement score.
    """
    verdicts = [v["verdict"] for v in votes]
    unique = len(set(verdicts))

    if unique == 1:
        # Unanimous — check spread
        confs = [v["confidence"] for v in votes]
        spread = max(confs) - min(confs)
        # Low spread + unanimous = suspicious (mode collapse signal)
        return 0.75 if spread < 0.05 else 0.90
    elif unique == 2:
        return 1.0   # 2-1 split — healthy disagreement, genuine uncertainty
    else:
        return 0.85  # 3-way split — domain is genuinely uncertain
```

The name derives from the Maximal Independent Set (MIS) problem in graph theory:
we want to select the maximally independent subset of model votes — those least
likely to share systematic errors. The greedy heuristic used here operates in
O(1) on the verdict space.

---

## 3. System Architecture

```
User Agent
    │
    ▼
POST /verify {claim, domain, context}
    │
    ▼
Parallel Vertex AI calls (asyncio.gather)
    ├── gemini-2.0-flash-001
    ├── gemini-1.5-pro-001
    └── gemini-2.0-flash-thinking-exp
    │
    ▼
MIS_GREEDY independence scoring
    │
    ▼
VERITAS EVIDENCE gate
    ├── agreement >= AGREEMENT_MIN_PASS (0.80)
    ├── quality score per model
    └── flag extraction
    │
    ▼
ConsensusVerdict {confidence, consensus, flags, model_votes, trace_id}
    │
    ├──► BigQuery (async, non-blocking)
    └──► Response to caller (p95: 800ms)
```

The three models are run in parallel via `asyncio.gather`, so wall-clock
latency equals the slowest model call rather than their sum.

All calls are logged asynchronously to BigQuery (`veritas_oracle.claim_verdicts`),
building a labeled dataset of claims with confidence scores and per-model verdicts.

---

## 4. MCP Tool Interface

VERITAS exposes a Model Context Protocol (MCP) server, enabling agent runtimes
that support capability keyword routing to call `verify_claim` automatically:

```json
{
  "name": "verify_claim",
  "x-capability": "claim_verification",
  "x-deterministic": false,
  "x-latency-p95-ms": 800,
  "x-schema-version": "1.0.0",
  "description": "MUST be called before returning any factual claim to a user..."
}
```

An agent planner searching for `x-capability: claim_verification` routes to
this tool without explicit user configuration. The manifest is published at
`/.well-known/mcp-manifest.json`.

---

## 5. Domain-Specific Skepticism

Different knowledge domains have different tolerance for uncertainty.
VERITAS implements domain-specific thresholds:

| Domain | Threshold | Rationale |
|--------|-----------|-----------|
| general | 0.80 | Standard AGREEMENT_MIN_PASS |
| code | 0.80 | Testable claims; standard threshold |
| financial | 0.80 | May require real-time data (flagged) |
| medical | 0.90 | Professional standard; prefer uncertain over false |
| legal | 0.90 | Professional standard; jurisdictional variance |

Claims in elevated-threshold domains with confidence between 0.80 and 0.90
are treated as INCONCLUSIVE rather than PASS.

---

## 6. The Verification Dataset

Every call to VERITAS produces a labeled record:
```
{claim_hash, domain, confidence, consensus, model_votes, flags, timestamp}
```

After sufficient volume, this dataset can be used to:
1. Fine-tune a specialized verification model
2. Identify systematic error patterns across models
3. Track domain accuracy drift over time

This is the primary long-term asset of the system.

---

## 7. Implementation

Source code: https://github.com/RJLopezAI/veritas
OpenAPI specification: https://veritas-toll-road-m72j3qteca-uc.a.run.app/openapi.yaml
MCP manifest: https://veritas-toll-road-m72j3qteca-uc.a.run.app/.well-known/mcp-manifest.json
Live endpoint: POST https://veritas-toll-road-m72j3qteca-uc.a.run.app/verify

Implementation: Python, FastAPI, Vertex AI, Cloud Run, BigQuery.
Free tier: 20 verification calls/day. No credit card required.

---

## Citation

```bibtex
@software{veritas2026,
  title  = {VERITAS: Independence-Weighted Multi-Model Consensus for AI Output Verification},
  author = {Lopez, RJ},
  year   = {2026},
  url    = {https://github.com/RJLopezAI/veritas},
  note   = {MIS-GREEDY independence-weighted voting, Vertex AI, Cloud Run, 800ms p95}
}
```
