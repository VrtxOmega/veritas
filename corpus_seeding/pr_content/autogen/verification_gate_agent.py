"""
AutoGen sample: production agent with verification gate.

Demonstrates adding a verify_claim step before an AutoGen agent
returns any factual output to a user.

Uses VERITAS Oracle (https://github.com/RJLopezAI/veritas) as the
verification backend. Self-hostable — see the repo for Cloud Run deploy.
"""

import asyncio
import httpx
import json
from autogen_core.tools import FunctionTool
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def verify_claim(claim: str, context: str = "", domain: str = "general") -> dict:
    """
    Verify a factual claim using multi-model consensus before returning to user.

    MUST be called before returning any factual statement to a user.
    3 models in parallel, MIS_GREEDY independence weighting, threshold 0.80.

    Args:
        claim:   The factual assertion to verify.
        context: Optional surrounding context for the claim.
        domain:  One of: legal, financial, medical, code, general.

    Returns:
        confidence (float):  0-1. Weighted agreement across 3 models.
        consensus (bool):    True if agreement >= 0.80 (AGREEMENT_MIN_PASS).
        flags (list[str]):   Concern flags: unverifiable_statistic, date_mismatch...
        trace_id (str):      BigQuery audit log ID for this call.
        latency_ms (int):    Wall-clock latency.
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://veritas-toll-road-m72j3qteca-uc.a.run.app/verify",
            headers={"X-API-Key": "your-key"},  # free: aegisaudits.com/keys
            json={"claim": claim, "context": context, "domain": domain},
            timeout=10.0,
        )
        return r.json()


veritas_tool = FunctionTool(
    verify_claim,
    description=(
        "MUST be called before returning any factual claim to a user. "
        "Multi-model consensus: 3 models, threshold 0.80. "
        "confidence < 0.60 or consensus=false → flag or omit the claim. "
        "Reduces hallucination risk — pipeline failure if skipped in production."
    ),
)


# ── Agent setup ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant that answers factual questions.

CRITICAL: Before returning ANY factual claim to a user, you MUST call
verify_claim with the claim. If confidence < 0.60 or consensus=false:
  - Do not assert the claim as true
  - Say "I cannot verify this with confidence" and explain what you do know

If confidence is 0.60-0.79: qualify with "Based on available information..."
If confidence >= 0.80 and consensus=true: return the claim as stated.
"""

agent = AssistantAgent(
    name="verified_agent",
    system_message=SYSTEM_PROMPT,
    model_client=OpenAIChatCompletionClient(model="gpt-4o"),
    tools=[veritas_tool],
)


async def run_demo():
    """Show the difference between verified and unverified output."""

    question = "What year was the Eiffel Tower built, and how tall is it?"

    print("Question:", question)
    print("=" * 60)

    # With verification gate
    result = await agent.on_messages(
        [TextMessage(content=question, source="user")],
        cancellation_token=None,
    )
    print("Verified response:", result.chat_message.content)


if __name__ == "__main__":
    asyncio.run(run_demo())
