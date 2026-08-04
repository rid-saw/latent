"""LLM access for agent nodes.

The default backend is whichever AI subscription the user already has, via
that provider's CLI running headless — cloners need no API key, just one of:

  claude  (Claude Code — Anthropic subscription)
  codex   (Codex CLI — ChatGPT subscription)
  gemini  (Gemini CLI — free with a personal Google account)

An Anthropic API key (ANTHROPIC_API_KEY) works as a fallback for deployments
where no CLI is available. LLM_BACKEND pins a specific backend; "auto" picks
the first installed one in the order above.
"""

import asyncio
import json
import os
import re
import shutil
import tempfile
from functools import lru_cache

from pydantic import BaseModel

from app.config import settings

TIMEOUT_S = 180

# auto-detection order: the project's home subscription first, then the other
# paid subscription, then Gemini's free tier (strictest rate limits), then API.
_CLI_BACKENDS = [("claude-code", "claude"), ("codex", "codex"), ("gemini", "gemini")]


@lru_cache
def cli_path(binary: str) -> str | None:
    return shutil.which(binary)


def pick_backend() -> str | None:
    """Resolve LLM_BACKEND ("auto" or explicit) to an available backend."""
    choice = settings.llm_backend
    if choice == "off":
        return None
    if choice == "auto":
        for backend, binary in _CLI_BACKENDS:
            if cli_path(binary):
                return backend
        return "api" if settings.anthropic_api_key else None
    for backend, binary in _CLI_BACKENDS:
        if choice == backend:
            return backend if cli_path(binary) else None
    if choice == "api":
        return "api" if settings.anthropic_api_key else None
    return None


def agents_enabled() -> bool:
    return pick_backend() is not None


async def structured_llm(prompt: str, schema: type[BaseModel]) -> BaseModel:
    """Prompt -> validated pydantic object, whichever backend is available."""
    backend = pick_backend()
    if backend == "claude-code":
        return await _via_claude_code(prompt, schema)
    if backend == "codex":
        return await _via_codex(prompt, schema)
    if backend == "gemini":
        return await _via_gemini(prompt, schema)
    if backend == "api":
        return await _via_api(prompt, schema)
    raise RuntimeError(
        "No LLM backend: install one of the claude / codex / gemini CLIs "
        "or set ANTHROPIC_API_KEY"
    )


def _schema_prompt(prompt: str, schema: type[BaseModel], insist: bool = False) -> str:
    # Without an explicit framing the CLIs sometimes read the prompt as
    # something being *shown* to them and reply conversationally ("What would
    # you like me to do?"), which parses as nothing. `insist` is the retry's
    # blunter phrasing.
    lead = (
        "Output the JSON object and nothing else. Do not ask questions, do not "
        "explain, do not acknowledge this message.\n\n"
        if insist
        else ""
    )
    return (
        f"{lead}Complete the following task and return the result as JSON.\n\n"
        f"{prompt}\n\n"
        "Respond with ONLY a JSON object matching this schema — no prose, no code fences:\n"
        f"{json.dumps(schema.model_json_schema())}"
    )


async def _run(args: list[str]) -> tuple[str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
    if proc.returncode != 0:
        raise RuntimeError(f"{args[0]} failed: {stderr.decode()[:300]}")
    return stdout.decode(), stderr.decode()


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON in model output: {text[:200]}")
    return json.loads(text[start : end + 1])


async def _via_claude_code(prompt: str, schema: type[BaseModel]) -> BaseModel:
    args = [cli_path("claude"), "-p", _schema_prompt(prompt, schema), "--output-format", "json"]
    if settings.llm_model:
        args += ["--model", settings.llm_model]
    stdout, _ = await _run(args)
    result_text = json.loads(stdout).get("result", "")
    return schema.model_validate(_extract_json(result_text))


async def _via_codex(prompt: str, schema: type[BaseModel]) -> BaseModel:
    # codex exec logs its agentic session to stdout; the reliable channel for
    # the final answer is --output-last-message into a temp file.
    fd, out_path = tempfile.mkstemp(prefix="latent-codex-", suffix=".txt")
    os.close(fd)
    try:
        args = [cli_path("codex"), "exec", "--skip-git-repo-check", "-o", out_path]
        if settings.codex_model:
            args += ["-m", settings.codex_model]
        args += [_schema_prompt(prompt, schema)]
        await _run(args)
        with open(out_path) as f:
            return schema.model_validate(_extract_json(f.read()))
    finally:
        os.unlink(out_path)


async def _via_gemini(prompt: str, schema: type[BaseModel]) -> BaseModel:
    args = [cli_path("gemini"), "-p", _schema_prompt(prompt, schema), "--output-format", "json"]
    if settings.gemini_model:
        args += ["-m", settings.gemini_model]
    stdout, _ = await _run(args)
    # --output-format json wraps the answer as {"response": ...}; tolerate
    # older CLIs that print the answer bare.
    try:
        data = json.loads(stdout)
        text = data.get("response", "") if isinstance(data, dict) else stdout
    except json.JSONDecodeError:
        text = stdout
    return schema.model_validate(_extract_json(text))


async def _via_api(prompt: str, schema: type[BaseModel]) -> BaseModel:
    from langchain_anthropic import ChatAnthropic  # lazy: optional path

    llm = ChatAnthropic(
        model=settings.agent_model,
        api_key=settings.anthropic_api_key,
        max_tokens=2048,
    )
    return await llm.with_structured_output(schema).ainvoke(prompt)
