from typing import Any, Dict, Optional


def extract_context(alert: dict, top_level_status: str) -> dict:
    """
    Stage 2 — Context Extraction.
    Called once per alert. Extracts relevant fields into a flat context dict.
    Explicitly excludes fingerprint, ref_id, datasource_uid, panelURL, generatorURL.
    """
    # 1. status: alert-level status if present and non-None, else fallback to top-level status
    alert_status = alert.get("status")
    status = str(alert_status) if alert_status is not None else top_level_status

    # 2. alertname: prefer title, fallback to alertname
    title = alert.get("title")
    alertname = title if title else alert.get("alertname")

    # 3. folder: infoore_folder
    folder = alert.get("infoore_folder")

    # 4. team: team
    team = alert.get("team")

    # 5. threshold: pass through unmodified (any type)
    threshold = alert.get("threshold")

    # 6. value: prefer first numeric entry from values dict; fallback to valueString
    values = alert.get("values")
    value_string = alert.get("valueString")
    value = _extract_value(values, value_string)

    # 7. summary & description
    summary = alert.get("summary")
    description = alert.get("description")

    # 8. starts_at & ends_at (keep as None if null/missing)
    starts_at = alert.get("startsAt")
    ends_at = alert.get("endsAt")

    # 9. dashboard_url & silence_url
    dashboard_url = alert.get("dashboardURL")
    panel_url = alert.get("panelURL")
    generator_url = alert.get("generatorURL")
    silence_url = alert.get("silenceURL")

    return {
        "status": status,
        "alertname": alertname,
        "folder": folder,
        "team": team,
        "threshold": threshold,
        "value": value,
        "summary": summary,
        "description": description,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "dashboard_url": dashboard_url,
        "panel_url": panel_url,
        "generator_url": generator_url,
        "silence_url": silence_url,
    }



def _extract_value(values: Any, value_string: Any) -> Any:
    """
    Extract first numeric entry (int or float) from values dict if available.
    Otherwise fall back to value_string.
    """
    if isinstance(values, dict) and values:
        for val in values.values():
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return val
    return value_string
