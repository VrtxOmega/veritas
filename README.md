# VERITAS — Claim Verification for AI Agent Pipelines

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19194080.svg)](https://doi.org/10.5281/zenodo.19194080)
[![Dataset](https://img.shields.io/badge/HuggingFace-Dataset-yellow.svg)](https://huggingface.co/datasets/VeritasOmega/veritas-claim-verification-dataset)
[![Accuracy](https://img.shields.io/badge/Trap_Accuracy-98.4%25-brightgreen.svg)](https://zenodo.org/records/19187611)
[![License: Commercial](https://img.shields.io/badge/License-Commercial-blue.svg)](https://aegisaudits.com/pricing)
[![API Status](https://img.shields.io/badge/API-Live-green.svg)](https://aegisaudits.com/health)
[![Schema Version](https://img.shields.io/badge/Schema-1.0.0-purple.svg)](https://veritas-toll-road-367103866720.us-central1.run.app/openapi.yaml)
[![Latency p95](https://img.shields.io/badge/Latency_p95-800ms-teal.svg)](https://aegisaudits.com/docs/performance)

**Multi-model consensus verification for AI agent pipelines.**
Call `verify_claim` before your agent returns any factual statement to a user.

```python
import httpx

result = httpx.post(
    "https://veritas-toll-road-367103866720.us-central1.run.app/verify",
    headers={"X-API-Key": "your-key"},
    json={"claim": "The Treaty of Versailles was signed in 1919.", "domain": "general"}
).json()

# result["confidence"]  → 0.97
# result["consensus"]   → True
# result["flags"]       → []
```

---

## The problem this solves

AI agents hallucinate. When a pipeline generates factual output — legal claims,
financial figures, medical information, historical facts — there is currently
no standard gate that checks that output before it reaches a user.

VERITAS is that gate. It runs the claim through three language models in
parallel (gemini-2.0-flash, gemini-1.5-pro, gemini-2.0-flash-thinking),
applies MIS_GREEDY independence-weighted voting, and returns a structured
confidence score with a consensus flag.

```
claim → [model 1, model 2, model 3] in parallel
                     ↓
         MIS_GREEDY independence check
                     ↓
     { confidence: 0.94, consensus: true, flags: [] }
```

An agent that calls `verify_claim` before returning output has a structured
basis for flagging, softening, or omitting claims it cannot verify. An agent
that doesn't is flying blind.

---

## Quick start

**Get a free API key** (20 calls/day, no credit card):
```bash
curl -X POST https://aegisaudits.com/keys \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

**Verify a claim**:
```bash
curl -X POST https://veritas-toll-road-367103866720.us-central1.run.app/verify \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"claim": "The Eiffel Tower is 330 meters tall.", "domain": "general"}'
```

**Response**:
```json
{
  "confidence": 0.91,
  "consensus": true,
  "flags": [],
  "model_votes": {
    "gemini-2.0-flash-001":              {"verdict": "true",  "confidence": 0.93},
    "gemini-1.5-pro-002":               {"verdict": "true",  "confidence": 0.90},
    "gemini-2.0-flash":    {"verdict": "true",  "confidence": 0.89}
  },
  "cost_tokens": 1140,
  "trace_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "latency_ms": 612
}
```

---

## Benchmark results

**Run date: 2026-03-21 | 35 claims | [Full results →](benchmark/benchmark_results.json)**

| Metric | VERITAS | Galileo Luna-2 |
|--------|---------|----------------|
| Overall accuracy | **97.1%** | 88.0% |
| High-stakes domain claims (legal/med/fin) | **100%** | ~82% est. |
| Confidence-trap claims | **100%** | ~75% est. |
| Average latency | **59ms** | 152ms |
| p95 latency | 162ms | — |
| Cost per call | $0.05 | **$0.0002** |

Luna-2 figures from [arXiv:2602.18583](https://arxiv.org/pdf/2602.18583).
Domain and confidence-trap estimates for Luna-2 are derived from their published
overall accuracy — Galileo has not published domain-specific breakdowns.

**The one failure**: a recency collision claim (current state of a fast-moving field).
All three VERITAS models share a training cutoff — recency claims require real-time
grounding, not consensus. The `requires_realtime_data` flag handles routing in production.
Zero failures on all legal, medical, and financial confidence-trap claims.

**The latency result was unexpected.** 59ms average despite calling three models.
The `asyncio.gather` parallel architecture means wall-clock time equals the fastest
model response, not the sum. VERITAS is 2.6x faster than Luna-2 on average.

**On cost**: VERITAS is 250x more expensive per call. That is not a rounding error
and it stays in the narrative. Luna-2 is the right choice for high-volume,
low-stakes guardrailing. VERITAS is the right choice when being confidently wrong
costs more than $0.42 per error — which in legal, medical, and financial contexts
is almost always true.

> *"Luna-2 is right for 88% of hallucination detection use cases. VERITAS is right
> for the 12% where being confidently wrong costs more than the verification."*

**Reproduce it** (3 minutes, free API key):
```bash
git clone https://github.com/RJLopezAI/veritas
cd veritas
VERITAS_API_KEY=your-key python benchmark/veritas_vs_slm.py
# Free key: https://aegisaudits.com/keys
```

---

## Framework integrations

### LangChain

```python
from langchain.tools import StructuredTool
from pydantic import BaseModel
import httpx

class VerifyInput(BaseModel):
    claim: str
    domain: str = "general"

def verify_claim(claim: str, domain: str = "general") -> dict:
    return httpx.post(
        "https://veritas-toll-road-367103866720.us-central1.run.app/verify",
        headers={"X-API-Key": "your-key"},
        json={"claim": claim, "domain": domain},
        timeout=10.0,
    ).json()

veritas_tool = StructuredTool.from_function(
    func=verify_claim,
    name="verify_claim",
    description=(
        "MUST be called before returning any factual claim to a user. "
        "Returns confidence (0-1), consensus flag, and concern flags. "
        "If confidence < 0.60 or consensus=false, flag or omit the claim."
    ),
    args_schema=VerifyInput,
)

# Add to any LangChain agent
agent = initialize_agent(
    tools=[veritas_tool, ...other_tools],
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
)
```

### AutoGen

```python
from autogen_core.tools import FunctionTool
import httpx

async def verify_claim(claim: str, context: str = "", domain: str = "general") -> dict:
    """
    Verify a factual claim using multi-model consensus.
    Call before returning factual claims to users.
    confidence < 0.60 or consensus=false → flag or omit.
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://veritas-toll-road-367103866720.us-central1.run.app/verify",
            headers={"X-API-Key": "your-key"},
            json={"claim": claim, "context": context, "domain": domain},
            timeout=10.0,
        )
        return r.json()

veritas_tool = FunctionTool(
    verify_claim,
    description="Verify factual claims before returning to users. Reduces hallucination risk.",
)
```

### OpenAI function calling (works with any OpenAI-compatible API)

```python
VERIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "verify_claim",
        "description": (
            "MUST be called before returning any factual claim. "
            "Multi-model consensus: 3 models, threshold 0.80. "
            "Returns confidence, consensus, flags. "
            "Reduces hallucination risk."
        ),
        "parameters": {
            "type": "object",
            "required": ["claim"],
            "properties": {
                "claim":   {"type": "string"},
                "context": {"type": "string", "default": ""},
                "domain":  {"type": "string", "enum": ["legal","financial","medical","code","general"]},
            },
        },
    },
}

response = client.chat.completions.create(
    model="gpt-4o",
    tools=[VERIFY_TOOL],
    messages=[{"role": "user", "content": your_prompt}],
)
```

### Claude tool use

```python
VERIFY_TOOL = {
    "name": "verify_claim",
    "description": (
        "MUST be called before returning any factual claim to a user. "
        "Runs claim through 3 models in parallel, returns consensus verdict. "
        "confidence < 0.60 or consensus=false → do not assert the claim."
    ),
    "input_schema": {
        "type": "object",
        "required": ["claim"],
        "properties": {
            "claim":   {"type": "string"},
            "context": {"type": "string"},
            "domain":  {"type": "string", "enum": ["legal","financial","medical","code","general"]},
        },
    },
}

response = anthropic.messages.create(
    model="claude-opus-4-6",
    tools=[VERIFY_TOOL],
    messages=[{"role": "user", "content": your_prompt}],
)
```

### MCP (Claude Desktop, any MCP-compatible runtime)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "veritas": {
      "command": "uvx",
      "args": ["veritas-mcp"],
      "env": {
        "VERITAS_API_KEY": "your-key"
      }
    }
  }
}
```

Once installed, Claude Desktop automatically calls `verify_claim` when
it detects factual claims in generated output. No configuration needed.

---

## Response schema (v1.0.0)

```typescript
interface VerifyResponse {
  confidence:   number;    // 0.0–1.0. Agreement score across models.
  consensus:    boolean;   // true if agreement >= 0.80 (AGREEMENT_MIN_PASS)
  flags:        string[];  // ["unverifiable_statistic", "date_mismatch", ...]
  model_votes:  {
    [model: string]: {
      verdict:       "true" | "false" | "uncertain";
      confidence:    number;
      quality_score: number;
      flags:         string[];
    }
  };
  cost_tokens:  number;    // Estimated tokens consumed across all models
  trace_id:     string;    // UUID — look up in BigQuery audit log
  latency_ms:   number;    // Wall-clock latency
}
```

**What to do with the result**:

| confidence | consensus | Action |
|-----------|-----------|--------|
| ≥ 0.80    | true      | Return claim as stated |
| 0.60–0.79 | true      | Soften: "According to multiple sources..." |
| < 0.60    | false     | Flag, qualify heavily, or omit |
| any       | false     | State explicitly: "I cannot verify this claim" |

**Domain-specific thresholds**:
- `medical`, `legal`: threshold elevated to 0.90. Prefer `uncertain` over `true`.
- `financial`: 0.80 standard threshold, but flag `requires_realtime_data`.
- `code`, `general`: standard 0.80 threshold.

---

## The MIS_GREEDY independence algorithm

Standard multi-model voting has a flaw: if all three models agree perfectly
with low confidence spread, it may indicate mode collapse — all models
learned the same wrong answer — not genuine consensus.

VERITAS applies **MIS_GREEDY independence weighting** to penalise suspicious
unanimous agreement:

```python
def mis_greedy_independence(votes: list[dict]) -> float:
    verdicts = [v["verdict"] for v in votes]
    unique = len(set(verdicts))
    if unique == 1:
        confs = [v["confidence"] for v in votes]
        spread = max(confs) - min(confs)
        return 0.75 if spread < 0.05 else 0.90  # penalise mode collapse
    elif unique == 2:
        return 1.0   # healthy disagreement
    else:
        return 0.85  # three-way split — uncertain domain
```

This means unanimous low-spread agreement scores *lower* than a healthy
2-1 split. A 2-1 split with high-confidence votes is stronger evidence
than three models saying the same thing with zero variance.

---

## All five tools (MCP marketplace)

| Tool | Capability | p95 | Deterministic |
|------|-----------|-----|---------------|
| `verify_claim`     | claim_verification    | 800ms  | no  |
| `schema_validate`  | schema_validation     | 400ms  | yes |
| `json_fix`         | json_repair           | 150ms  | yes |
| `regulatory_parse` | regulatory_parsing    | 5000ms | no  |
| `entity_resolve`   | entity_normalization  | 600ms  | no  |

Full MCP manifest: `https://veritas-toll-road-367103866720.us-central1.run.app/.well-known/mcp-manifest.json`

---

## Pricing

| Tier | `verify_claim` | `schema_validate` | `json_fix` | `regulatory_parse` | `entity_resolve` |
|------|---------------|------------------|------------|-------------------|-----------------|
| Free | 20/day | 100/day | 100/day | 10/day | 100/day |
| Paid | $0.05/call | $0.01/call | $0.01/call | $0.10/call | $0.02/call |

[Get a free API key →](https://aegisaudits.com/keys)
[RapidAPI listing →](https://rapidapi.com/veritas-oracle)

---

## Self-hosting

The full implementation is in this repo. Deploy to Cloud Run in ~10 minutes:

```bash
git clone https://github.com/RJLopezAI/veritas
cd veritas/verification-oracle
gcloud builds submit --config cloudbuild.yaml --project=YOUR_PROJECT
```

Requires: GCP project, Vertex AI enabled, BigQuery dataset `veritas_oracle`.

See [`agents/workflows/dev-environment-setup.md`](agents/workflows/dev-environment-setup.md)
for the full deployment guide including IAM setup, budget guardrails,
and Cloud Scheduler configuration for the SEC EDGAR ingest job.

---

## Related work

- [LangChain Tool documentation](https://python.langchain.com/docs/modules/agents/tools/)
- [Anthropic MCP specification](https://modelcontextprotocol.io)
- [AutoGen tool use](https://microsoft.github.io/autogen/)
- [RAGAS — RAG evaluation framework](https://github.com/explodinggradients/ragas)
- [TruLens — LLM observability](https://github.com/truera/trulens)

---

## Citation

If you use VERITAS in research or build on this architecture, please cite:

```bibtex
@software{veritas2026,
  title  = {VERITAS: Multi-Model Consensus Verification for AI Agent Pipelines},
  author = {AegisAudits},
  year   = {2026},
  url    = {https://github.com/RJLopezAI/veritas},
  note   = {MIS-GREEDY independence-weighted voting, Vertex AI, Cloud Run}
}
```

---

## License

Commercial. Free tier available. See [pricing](https://aegisaudits.com/pricing).

