import json


def build_prompt(ctx: dict) -> str:
    """
    Stage 3 — Prompt Construction.
    Builds a single prompt string instructing the LLM to write a 2–4 line alert summary
    for one alert according to strict formatting and context rules.
    """
    ctx_json = json.dumps(ctx, indent=2, default=str)

    return (
        "You are an alert summarization assistant. Your task is to generate a concise, "
        "human-readable summary of a Grafana monitoring alert for notification channels.\n\n"
        "Here is the context data for the alert:\n"
        f"{ctx_json}\n\n"
        "STRICT INSTRUCTIONS:\n"
        "1. You MUST explicitly state the alert status (e.g. 'Status: firing' or 'alert status is firing') near the beginning of the summary based on the 'status' field in the context. Do not assume status is only 'firing' or 'resolved'; it can be any string (e.g. 'normal').\n"
        "2. Include the alert name ('alertname'), team, and folder in the summary if present in the context data.\n"
        "3. Never say 'ongoing', 'still active', or invent any timing/duration language not directly supported by the data.\n"
        "4. If 'ends_at' is null/None, mention ONLY the start time ('starts_at') in a clean, human-readable format (e.g. 'August 11, 2026 at 06:30 UTC'). Do NOT reference an end time, duration, or resolution status at all.\n"
        "5. If 'ends_at' is present and not null/None, state both the start time and end time in a clean, human-readable format.\n"
        "6. Always state the numeric value vs. threshold together if both are present in the context.\n"
        "7. Do not mention fingerprint, ref_id, or datasource_uid — they are excluded from the context.\n"
        "8. Do not include URLs or web links in your text (such as dashboard_url, silence_url, panel_url, or generator_url) — action links are appended automatically below your summary.\n"

        "9. Keep the output to 2 to 4 lines of plain, scannable prose. Do not use markdown headers (such as # or ##) or bulleted lists (such as - or *).\n"
    )


