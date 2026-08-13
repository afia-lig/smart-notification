from fastapi import FastAPI, HTTPException, Body
from typing import Any, Dict
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file automatically
load_dotenv()

from alert_summarizer import process_webhook, PayloadValidationError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Grafana Alert Summarizer API",
    description="Proactive AI Alert Summarization Pipeline endpoint with Swagger UI",
    version="1.0.0",
)

SAMPLE_SWAGGER_PAYLOAD = {
    "status": "firing",
    "alerts": [
        {
            "alertname": "HighCPUUsage",
            "infoore_folder": "Infrastructure",
            "team": "DevOps",
            "threshold": 80,
            "summary": "High CPU usage detected on web-server-01",
            "description": "CPU usage exceeded threshold over 5m average.",
            "startsAt": "2026-08-11T06:30:00Z",
            "endsAt": None,
            "values": {"A": 92.5},
            "valueString": "92.5",
            "dashboardURL": "https://grafana.example.com/d/infrastructure",
            "silenceURL": "https://grafana.example.com/alerting/silence/new",
            "title": "High CPU Usage",
        }
    ],
}


@app.get("/")
def root():
    return {
        "message": "Grafana Alert Summarizer API is running.",
        "swagger_ui": "Go to /docs to test via Swagger UI",
    }


@app.post("/summarize", summary="Summarize Grafana Alert Payload", response_model=Dict[str, Any])
def handle_summarize(payload: Dict[str, Any] = Body(..., example=SAMPLE_SWAGGER_PAYLOAD)):

    """
    Receives Grafana alert webhook payload, validates input, extracts context,
    constructs prompt, generates alert summaries (with deterministic fallback),
    and formats final output for delivery.
    """
    try:
        # Automatically initialize OpenAI client if OPENAI_API_KEY is present in environment
        llm_client = None
        if os.environ.get("OPENAI_API_KEY"):
            try:
                import openai
                llm_client = openai.OpenAI()
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}. Using fallback.")

        summaries = process_webhook(payload, llm_client=llm_client)


        return {
            "status": "success",
            "processed_alerts": len(summaries),
            "summaries": summaries,
        }
    except PayloadValidationError as e:
        logger.error(f"Payload validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal processing error: {e}")
