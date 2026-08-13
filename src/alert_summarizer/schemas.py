import logging
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict

logger = logging.getLogger(__name__)


class PayloadValidationError(ValueError):
    """Raised when the webhook payload fails schema validation."""
    pass


class AlertItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    alertname: str
    startsAt: str

    # Optional fields with permissive / no strict type enforcement
    title: Optional[Any] = None

    infoore_folder: Optional[Any] = None
    team: Optional[Any] = None
    threshold: Optional[Any] = None  # Do not numeric-validate or cast
    datasource_uid: Optional[Any] = None
    ref_id: Optional[Any] = None
    summary: Optional[Any] = None
    description: Optional[Any] = None
    grafana_state_reason: Optional[Any] = None
    endsAt: Optional[Any] = None
    values: Optional[Any] = None
    valueString: Optional[Any] = None
    dashboardURL: Optional[Any] = None
    panelURL: Optional[Any] = None
    generatorURL: Optional[Any] = None
    silenceURL: Optional[Any] = None
    fingerprint: Optional[Any] = None
    status: Optional[Any] = None


class AlertPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    alerts: List[AlertItem]

    @field_validator("alerts")
    @classmethod
    def alerts_must_not_be_empty(cls, v: List[AlertItem]) -> List[AlertItem]:
        if not v or len(v) == 0:
            raise ValueError("Payload 'alerts' list must not be empty.")
        return v


def validate_payload(raw_payload: Any) -> dict:
    """
    Stage 1 — Light Input Validation.
    Validates top-level status and alerts list, and required fields within each alert.
    Logs raw payload on validation failure and raises PayloadValidationError.
    """
    if not isinstance(raw_payload, dict):
        logger.error(f"Payload validation failed: expected dict, got {type(raw_payload).__name__}. Raw payload: {raw_payload}")
        raise PayloadValidationError(f"Invalid payload shape: expected dict, got {type(raw_payload).__name__}")

    try:
        validated = AlertPayload.model_validate(raw_payload)
        return validated.model_dump(mode="python")
    except Exception as e:
        logger.error(f"Webhook payload validation failed: {e}. Raw payload: {raw_payload}")
        raise PayloadValidationError(f"Payload validation failed: {e}") from e
