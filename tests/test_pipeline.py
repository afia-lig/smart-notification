import pytest
from unittest.mock import MagicMock

from alert_summarizer import (
    validate_payload,
    PayloadValidationError,
    extract_context,
    build_prompt,
    generate_summary,
    fallback_summary,
    format_output,
    process_webhook,
)


SAMPLE_PAYLOAD_FIRING = {
    "status": "firing",
    "alerts": [
        {
            "alertname": "HighCPUUsage",
            "infoore_folder": "Infrastructure",
            "team": "DevOps",
            "threshold": 80,
            "datasource_uid": "prometheus",
            "ref_id": "A",
            "summary": "High CPU usage detected",
            "description": "CPU usage has exceeded the configured threshold.",
            "grafana_state_reason": "Threshold breached",
            "startsAt": "2026-08-11T06:30:00Z",
            "endsAt": None,
            "values": {"A": 92.5},
            "valueString": "92.5",
            "dashboardURL": "https://grafana.example.com/d/dashboard-id/dashboard-name",
            "panelURL": "https://grafana.example.com/d/dashboard-id/dashboard-name?viewPanel=10",
            "generatorURL": "https://grafana.example.com/api/alerting/grafana/alert-id",
            "silenceURL": "https://grafana.example.com/alerting/silence/new",
            "fingerprint": "a1b2c3d4e5f6",
            "title": "High CPU Usage",
        }
    ],
}

SAMPLE_PAYLOAD_NORMAL = {
    "status": "normal",
    "alerts": [
        {
            "alertname": "LowDiskSpace",
            "infoore_folder": "Storage",
            "team": "SysAdmin",
            "threshold": 90,
            "startsAt": "2026-08-11T07:00:00Z",
            "endsAt": None,
            "values": {"A": 45.0},
            "valueString": "45.0",
            "dashboardURL": "https://grafana.example.com/d/disk",
            "silenceURL": "https://grafana.example.com/silence",
            "title": "Low Disk Space",
        }
    ],
}

SAMPLE_PAYLOAD_RESOLVED = {
    "status": "resolved",
    "alerts": [
        {
            "alertname": "HighMemoryUsage",
            "infoore_folder": "Infrastructure",
            "team": "DevOps",
            "threshold": 85,
            "startsAt": "2026-08-11T06:00:00Z",
            "endsAt": "2026-08-11T06:45:00Z",
            "values": {"A": 70.0},
            "valueString": "70.0",
            "title": "High Memory Usage",
        }
    ],
}


def test_1_firing_ends_at_null():
    """Test 1: Firing payload with endsAt: null (single alert, all fields present)."""
    payload = validate_payload(SAMPLE_PAYLOAD_FIRING)
    alert = payload["alerts"][0]
    ctx = extract_context(alert, payload["status"])

    assert ctx["status"] == "firing"
    assert ctx["alertname"] == "High CPU Usage"
    assert ctx["folder"] == "Infrastructure"
    assert ctx["team"] == "DevOps"
    assert ctx["threshold"] == 80
    assert ctx["value"] == 92.5
    assert ctx["starts_at"] == "2026-08-11T06:30:00Z"
    assert ctx["ends_at"] is None
    assert ctx["panel_url"] == "https://grafana.example.com/d/dashboard-id/dashboard-name?viewPanel=10"
    assert ctx["generator_url"] == "https://grafana.example.com/api/alerting/grafana/alert-id"

    # Excluded fields must not be present
    for excluded in ["fingerprint", "ref_id", "datasource_uid"]:
        assert excluded not in ctx

    prompt = build_prompt(ctx)
    assert "2026-08-11T06:30:00Z" in prompt

    fb_summary = fallback_summary(ctx)
    assert "firing" in fb_summary
    assert "High CPU Usage" in fb_summary
    assert "2026-08-11T06:30:00Z" in fb_summary


def test_2_status_normal():
    """Test 2: Payload with status: 'normal', endsAt: null, value below threshold."""
    payload = validate_payload(SAMPLE_PAYLOAD_NORMAL)
    alert = payload["alerts"][0]
    ctx = extract_context(alert, payload["status"])

    assert ctx["status"] == "normal"
    assert ctx["value"] == 45.0
    assert ctx["threshold"] == 90


def test_3_resolved_ends_at_populated():
    """Test 3: Payload with endsAt populated (resolved case)."""
    payload = validate_payload(SAMPLE_PAYLOAD_RESOLVED)
    alert = payload["alerts"][0]
    ctx = extract_context(alert, payload["status"])

    assert ctx["ends_at"] == "2026-08-11T06:45:00Z"


def test_4_missing_optional_fields():
    """Test 4: Payload missing optional fields."""
    minimal_payload = {
        "status": "firing",
        "alerts": [
            {
                "alertname": "SimpleAlert",
                "startsAt": "2026-08-11T08:00:00Z",
            }
        ],
    }
    payload = validate_payload(minimal_payload)
    alert = payload["alerts"][0]
    ctx = extract_context(alert, payload["status"])

    assert ctx["alertname"] == "SimpleAlert"
    assert ctx["team"] is None
    assert ctx["dashboard_url"] is None
    assert ctx["panel_url"] is None
    assert ctx["generator_url"] is None
    assert ctx["ends_at"] is None


def test_5_multiple_alerts_batch():
    """Test 5: Payload with 2+ alerts in alerts array."""
    multi_payload = {
        "status": "firing",
        "alerts": [
            {
                "alertname": "AlertOne",
                "startsAt": "2026-08-11T01:00:00Z",
                "team": "Team Alpha",
                "threshold": 10,
                "values": {"A": 15},
            },
            {
                "alertname": "AlertTwo",
                "startsAt": "2026-08-11T02:00:00Z",
                "team": "Team Beta",
                "threshold": 99,
                "values": {"A": 100},
            },
        ],
    }
    results = process_webhook(multi_payload, llm_client=None)

    assert len(results) == 2
    assert "AlertOne" in results[0]
    assert "AlertTwo" in results[1]


def test_6_batch_with_malformed_alert():
    """Test 6: Batch of 2+ alerts where one is malformed (missing alertname)."""
    multi_payload = {
        "status": "firing",
        "alerts": [
            {
                "alertname": "ValidAlert1",
                "startsAt": "2026-08-11T01:00:00Z",
            },
            {
                "startsAt": "2026-08-11T02:00:00Z",
            },
        ],
    }

    with pytest.raises(PayloadValidationError):
        validate_payload(multi_payload)


def test_7_fallback_path():
    """Test 7: Force generate_summary to return None, confirm fallback_summary works."""
    mock_llm = MagicMock()
    mock_llm.chat.completions.create.side_effect = Exception("LLM down")

    res = generate_summary("test prompt", mock_llm)
    assert res is None

    summaries = process_webhook(SAMPLE_PAYLOAD_FIRING, llm_client=mock_llm)
    assert len(summaries) == 1
    assert "Alert 'High CPU Usage' status: firing." in summaries[0]
