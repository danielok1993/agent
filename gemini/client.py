"""Vertex AI client construction.

Per-candidate validation was removed on 2026-07-28: asking a vision model to
adjudicate hundreds of small symbols is spatial grounding, which it does poorly.
Gemini's role is now region classification — see gemini/classifier.py.
"""
from __future__ import annotations

import os

from google import genai


def init_client() -> genai.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, timeout=5,
            )
            project = result.stdout.strip() or None
        except Exception:
            pass
    if not project:
        raise EnvironmentError(
            "No GCP project found. Set GOOGLE_CLOUD_PROJECT or run:\n"
            "  gcloud config set project YOUR_PROJECT_ID\n"
            "Then authenticate with:\n"
            "  gcloud auth application-default login"
        )
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project, location=location)
