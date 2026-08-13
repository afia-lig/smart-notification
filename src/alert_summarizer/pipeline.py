import logging
from typing import Any, List, Optional

from alert_summarizer.schemas import validate_payload
from alert_summarizer.extractor import extract_context
from alert_summarizer.prompt import build_prompt
from alert_summarizer.generator import generate_summary, fallback_summary
from alert_summarizer.formatter import format_output

logger = logging.getLogger(__name__)


def process_webhook(raw_payload: dict, llm_client: Any = None) -> List[str]:
    """
    Orchestrates the alert summarization pipeline:
    1. Runs Stage 1 (validation) on raw payload.
    2. Loops over every alert in payload["alerts"]:
       - Stage 2: Context Extraction
       - Stage 3: Prompt Construction
       - Stage 4: LLM Summary Generation (or Fallback if generation returns None)
       - Stage 5: Output Formatting
    3. Catches and logs per-alert unexpected errors without failing the whole batch.
    4. Returns a list of formatted summary strings.
    """
    # Stage 1 — Validation
    validated_payload = validate_payload(raw_payload)

    top_level_status = validated_payload["status"]
    alerts = validated_payload["alerts"]

    formatted_summaries = []

    for index, alert in enumerate(alerts):
        try:
            # Stage 2 — Context Extraction
            ctx = extract_context(alert, top_level_status)

            # Stage 3 — Prompt Construction
            prompt = build_prompt(ctx)

            # Stage 4 — LLM Generation (with fallback)
            summary_text = generate_summary(prompt, llm_client)
            if not summary_text:
                logger.info(f"LLM summary returned None for alert #{index} ({ctx.get('alertname')}). Using fallback.")
                summary_text = fallback_summary(ctx)

            # Stage 5 — Output Formatting
            formatted = format_output(summary_text, ctx)
            formatted_summaries.append(formatted)

        except Exception as e:
            alert_id = alert.get("alertname") or alert.get("title") or f"index #{index}"
            logger.error(f"Unexpected error processing alert '{alert_id}': {e}", exc_info=True)
            # Skip this alert and continue batch
            continue

    return formatted_summaries
