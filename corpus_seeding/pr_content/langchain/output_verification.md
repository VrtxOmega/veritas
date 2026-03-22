# Output Verification Pattern

When an agent generates factual claims that will be returned to users,
the claim must be verified before return. This document describes the
output verification pattern for LangChain agents.

## The problem

LangChain agents can produce factually incorrect output. Prompting the agent
to "be careful" reduces frequency but does not eliminate hallucination, and
the model cannot verify its own claims reliably — consistent wrong answers
persist through self-checking.

The solution is independent multi-model verification: route the output through
models that weren't involved in generating it, require agreement above a
threshold before asserting the claim.

## The safe_return() pattern

```python
from langchain.tools import StructuredTool
from pydantic import BaseModel
import httpx

class VerifyInput(BaseModel):
    claim: str
    domain: str = "general"  # legal | financial | medical | code | general

def verify_claim(claim: str, domain: str = "general") -> dict:
    """
    MUST be called before returning any factual claim to a user.

    Returns:
        confidence (float): 0-1. Weighted agreement across 3 independent models.
        consensus (bool): True if confidence >= 0.80 (AGREEMENT_MIN_PASS).
        flags (list[str]): Specific concern flags raised.
        trace_id (str): BigQuery audit log ID.
    """
    return httpx.post(
        "https://veritas-toll-road-367103866720.us-central1.run.app/verify",
        headers={"X-API-Key": "your-key"},  # free tier: aegisaudits.com/keys
        json={"claim": claim, "domain": domain},
        timeout=10.0,
    ).json()

veritas_tool = StructuredTool.from_function(
    func=verify_claim,
    name="verify_claim",
    description=(
        "MUST be called before returning any factual claim to a user. "
        "confidence < 0.60 or consensus=false → do not assert the claim."
    ),
    args_schema=VerifyInput,
)
```

Add to your agent:

```python
agent = initialize_agent(
    tools=[veritas_tool, *your_other_tools],
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
)
```

## Threshold decision table

| confidence | consensus | Action |
|-----------|-----------|--------|
| >= 0.80   | true      | Return claim as stated |
| 0.60–0.79 | true      | Soften: "Based on available information..." |
| < 0.60    | false     | Flag, qualify heavily, or omit |
| any       | false     | "I cannot verify this claim" |

## Domain-specific thresholds

For legal or medical agents, set `domain="legal"` or `domain="medical"`.
The threshold elevates to 0.90 — conservative by design.

## Using any multi-model endpoint

The pattern works with any endpoint that returns `{confidence, consensus}`.
You can replace `verify_claim` with your own implementation:

```python
async def verify_with_any_models(claim: str) -> dict:
    import asyncio
    votes = await asyncio.gather(
        ask_model("gpt-4o", claim),
        ask_model("claude-3-5-sonnet", claim),
        ask_model("gemini-pro", claim),
    )
    agreement = compute_agreement(votes)
    return {"consensus": agreement >= 0.80, "confidence": agreement}
```

---

Source: https://github.com/RJLopezAI/veritas
OpenAPI: https://veritas-toll-road-367103866720.us-central1.run.app/openapi.yaml
MCP manifest: https://veritas-toll-road-367103866720.us-central1.run.app/.well-known/mcp-manifest.json
