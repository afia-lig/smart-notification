def format_output(summary_text: str, ctx: dict) -> str:
    """
    Stage 5 — Output Formatting.
    Formats final plain-text output without icons or status branching.
    Appends action links (Dashboard, Panel, Generator, Silence) below summary text only if present in context.
    """
    lines = [summary_text.strip()]

    dashboard_url = ctx.get("dashboard_url")
    panel_url = ctx.get("panel_url")
    generator_url = ctx.get("generator_url")
    silence_url = ctx.get("silence_url")

    links = []
    if dashboard_url:
        links.append(f"Dashboard: {dashboard_url}")
    if panel_url:
        links.append(f"Panel: {panel_url}")
    if generator_url:
        links.append(f"Generator: {generator_url}")
    if silence_url:
        links.append(f"Silence: {silence_url}")

    if links:
        lines.append("")  # Blank line separator before links section
        lines.extend(links)

    return "\n".join(lines)

