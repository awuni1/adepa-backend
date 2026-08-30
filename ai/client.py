"""Single wrapper around the Gemini SDK (§9, §2.2). Modules never call Gemini
directly — they go through ai.services, which uses this client. Centralising
here gives one place for model choice, prompt loading, token accounting, and
retries."""

import time
from pathlib import Path

from django.conf import settings

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


class GeminiClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def generate(self, prompt: str, model: str, feature: str, response_schema=None, files=None):
        """Runs a Gemini generation call and logs usage to AIUsageLog (§4.2's
        AIUsageLog is the one place token accounting lands, per §2.2)."""
        from .models import AIUsageLog

        start = time.monotonic()
        success, error = True, ""
        input_tokens = output_tokens = 0
        text = ""
        try:
            contents = [prompt] + (files or [])
            config = {"response_schema": response_schema} if response_schema else {}
            response = self.client.models.generate_content(model=model, contents=contents, config=config)
            text = response.text
            usage = getattr(response, "usage_metadata", None)
            if usage:
                input_tokens = getattr(usage, "prompt_token_count", 0) or 0
                output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        except Exception as exc:
            success = False
            error = str(exc)
            raise
        finally:
            AIUsageLog.objects.create(
                feature=feature,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=int((time.monotonic() - start) * 1000),
                success=success,
                error=error,
            )
        return text


gemini_client = GeminiClient()
