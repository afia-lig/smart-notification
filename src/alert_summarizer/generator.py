import concurrent.futures
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def generate_summary(prompt: str, llm_client: Any, timeout: float = 10.0) -> Optional[str]:
    """
    Stage 4 — LLM Summary Generation.
    Calls the LLM client with prompt, enforcing a timeout (default 10s).
    Retries once on transient failure before giving up.
    Validates non-empty response. Returns None on failure so caller can trigger fallback.
    """
    if llm_client is None:
        logger.warning("No LLM client provided to generate_summary. Returning None to trigger fallback.")
        return None

    max_attempts = 2  # Initial call + 1 retry

    for attempt in range(1, max_attempts + 1):
        try:
            summary = _call_llm_with_timeout(prompt, llm_client, timeout)
            if summary and summary.strip():
                return summary.strip()
            else:
                logger.warning(f"LLM returned empty response on attempt {attempt}/{max_attempts}.")
        except Exception as e:
            logger.warning(f"LLM generation failed on attempt {attempt}/{max_attempts}: {e}")

    logger.error("All LLM summary generation attempts failed or returned empty. Falling back.")
    return None


def _call_llm_with_timeout(prompt: str, llm_client: Any, timeout: float) -> str:
    """Executes an LLM call in a worker thread with timeout enforcement."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_invoke_llm_client, prompt, llm_client, timeout)
        return future.result(timeout=timeout)


def _invoke_llm_client(prompt: str, llm_client: Any, timeout: float) -> str:
    """Invokes different kinds of LLM client interfaces (OpenAI SDK, callable, etc.)."""
    # 1. Standard OpenAI SDK client (llm_client.chat.completions.create)
    if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
        response = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )
        return response.choices[0].message.content or ""

    # 2. Callable function/object (e.g. mock function or custom wrapper)
    if callable(llm_client):
        result = llm_client(prompt)
        return str(result) if result is not None else ""

    # 3. Object with .complete() method
    if hasattr(llm_client, "complete"):
        result = llm_client.complete(prompt)
        return str(result) if result is not None else ""

    raise ValueError(f"Unsupported LLM client type: {type(llm_client).__name__}")


def fallback_summary(ctx: dict) -> str:
    """
    Deterministic, non-LLM templated summary built directly from the context dict.
    Used whenever generate_summary returns None.
    """
    status = ctx.get("status") or "unknown"
    alertname = ctx.get("alertname") or "Alert"

    parts = [f"Alert '{alertname}' status: {status}."]

    folder = ctx.get("folder")
    team = ctx.get("team")
    if folder or team:
        location = []
        if folder:
            location.append(f"Folder: {folder}")
        if team:
            location.append(f"Team: {team}")
        parts.append(" | ".join(location) + ".")

    val = ctx.get("value")
    thresh = ctx.get("threshold")
    if val is not None and thresh is not None:
        parts.append(f"Current value: {val}, threshold: {thresh}.")
    elif val is not None:
        parts.append(f"Current value: {val}.")
    elif thresh is not None:
        parts.append(f"Threshold: {thresh}.")

    summary = ctx.get("summary")
    description = ctx.get("description")
    msg = summary or description
    if msg:
        parts.append(f"Details: {msg}.")

    starts_at = ctx.get("starts_at")
    ends_at = ctx.get("ends_at")

    timing_parts = []
    if starts_at:
        timing_parts.append(f"Started: {starts_at}")
    if ends_at is not None:
        timing_parts.append(f"Ended: {ends_at}")

    if timing_parts:
        parts.append(" | ".join(timing_parts) + ".")

    return "\n".join(parts)
