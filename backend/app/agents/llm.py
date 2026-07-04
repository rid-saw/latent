"""LLM access for agent nodes.

Default backend is the user's own Claude subscription via the Claude Code CLI
(`claude -p`, headless) — cloners need no API key, just `claude` installed and
logged in. An Anthropic API key (ANTHROPIC_API_KEY) works as a fallback for
deployments where the CLI isn't available.
"""

import asyncio
import json
import re
import shutil
from functools import lru_cache

from pydantic import BaseModel

from app.config import settings


@lru_cache
def claude_cli() -> str | None:
    return shutil.which("claude")


def agents_enabled() -> bool:
    if settings.llm_backend == "off":
        return False
    return claude_cli() is not None or bool(settings.anthropic_api_key)


async def structured_llm(prompt: str, schema: type[BaseModel]) -> BaseModel:
    """Prompt -> validated pydantic object, whichever backend is available."""
    if claude_cli() and settings.llm_backend in ("auto", "claude-code"):
        return await _via_claude_code(prompt, schema)
    if settings.anthropic_api_key:
        return await _via_api(prompt, schema)
    raise RuntimeError("No LLM backend: install Claude Code (claude) or set ANTHROPIC_API_KEY")


async def _via_claude_code(prompt: str, schema: type[BaseModel]) -> BaseModel:
    full_prompt = (
        f"{prompt}\n\n"
        "Respond with ONLY a JSON object matching this schema — no prose, no code fences:\n"
        f"{json.dumps(schema.model_json_schema())}"
    )
    args = [claude_cli(), "-p", full_prompt, "--output-format", "json"]
    if settings.llm_model:
        args += ["--model", settings.llm_model]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {stderr.decode()[:300]}")
    result_text = json.loads(stdout.decode()).get("result", "")
    return schema.model_validate(_extract_json(result_text))


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON in model output: {text[:200]}")
    return json.loads(text[start : end + 1])


async def _via_api(prompt: str, schema: type[BaseModel]) -> BaseModel:
    from langchain_anthropic import ChatAnthropic  # lazy: optional path

    llm = ChatAnthropic(
        model=settings.agent_model,
        api_key=settings.anthropic_api_key,
        max_tokens=2048,
    )
    return await llm.with_structured_output(schema).ainvoke(prompt)
