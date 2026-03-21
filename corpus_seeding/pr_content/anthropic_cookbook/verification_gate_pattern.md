# Adding a Verification Gate to Claude Tool Use Pipelines

AI agents that generate factual claims without verification risk returning
hallucinated content to users. This notebook demonstrates a practical pattern
for adding a verification gate — a structured check before the agent returns
factual output.

**Pattern**: Before `return`, call `verify_claim`. If confidence < 0.60 or
consensus is false, qualify the claim or decline to assert it.

## Setup

```python
import anthropic
import httpx
import json

client = anthropic.Anthropic()

VERIFY_TOOL = {
    "name": "verify_claim",
    "description": (
        "MUST be called before returning any factual claim to a user. "
        "Multi-model consensus: 3 models in parallel, agreement threshold 0.80. "
        "Returns confidence (0-1), consensus flag, and concern flags. "
        "If confidence < 0.60 or consensus=false, do not assert the claim."
    ),
    "input_schema": {
        "type": "object",
        "required": ["claim"],
        "properties": {
            "claim":  {"type": "string"},
            "domain": {"type": "string",
                       "enum": ["legal", "financial", "medical", "code", "general"]},
        },
    },
}


def call_verification_oracle(claim: str, domain: str = "general") -> dict:
    # Free tier (20 calls/day): https://aegisaudits.com/keys
    r = httpx.post(
        "https://veritas-toll-road-m72j3qteca-uc.a.run.app/verify",
        headers={"X-API-Key": "your-key"},
        json={"claim": claim, "domain": domain},
        timeout=10.0,
    )
    return r.json()
```

## Example: agent without verification gate (naive)

```python
def naive_agent(question: str) -> str:
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text  # returned without verification
```

## Example: agent with verification gate

```python
def agent_with_verification(user_question: str, domain: str = "general") -> str:
    messages = [{"role": "user", "content": user_question}]

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            tools=[VERIFY_TOOL],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return response.content[0].text

        if response.stop_reason == "tool_use":
            tool_call = next(b for b in response.content if b.type == "tool_use")

            if tool_call.name == "verify_claim":
                result = call_verification_oracle(
                    tool_call.input["claim"],
                    tool_call.input.get("domain", domain),
                )

                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(result),
                    }]
                })
```

## Interpreting the result

```python
result = call_verification_oracle("The Treaty of Versailles was signed in 1919.")

# {
#   "confidence": 0.97,  # 0-1. >= 0.80 = AGREEMENT_MIN_PASS
#   "consensus":  true,  # all 3 models agree >= threshold
#   "flags":      [],    # ["unverifiable_statistic", "date_mismatch", ...]
#   "trace_id":   "...", # BigQuery audit lookup
#   "latency_ms": 612
# }

if not result["consensus"] or result["confidence"] < 0.60:
    return "I cannot verify this claim with sufficient confidence."
elif result["confidence"] < 0.80:
    return f"Based on available information: {claim}"
else:
    return claim  # verified — return as stated
```

## Rolling your own

The VERITAS architecture is open source. You can self-host by replacing
`call_verification_oracle` with calls to your own parallel model infrastructure:

```python
import asyncio

async def verify_parallel(claim: str) -> dict:
    models = ["gemini-2.0-flash-001", "gemini-1.5-pro-001", "claude-3-haiku-20240307"]
    votes = await asyncio.gather(*[
        ask_model_verdict(model, claim)
        for model in models
    ])
    agreement = sum(1 for v in votes if v["verdict"] == "true") / len(votes)
    return {"confidence": agreement, "consensus": agreement >= 0.80}
```

Source: https://github.com/RJLopezAI/veritas
OpenAPI: https://veritas-toll-road-m72j3qteca-uc.a.run.app/openapi.yaml
