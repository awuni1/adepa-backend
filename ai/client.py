"""Single wrapper around the Groq SDK (§9, §2.2). Modules never call Groq
directly — they go through ai.services, which uses this client. Centralising
here gives one place for model choice, prompt loading, token accounting, and
retries."""

import json
import time
from pathlib import Path

from django.conf import settings

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


class GroqClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from groq import Groq

            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    def generate(self, prompt: str, model: str, feature: str, response_schema=None, files=None,
                 system: str = "You are a helpful assistant."):
        """Runs a Groq chat completion and logs usage to AIUsageLog (§4.2's
        AIUsageLog is the one place token accounting lands, per §2.2).

        `files` (raw audio bytes for interview summaries) isn't accepted by
        Groq's chat endpoint — callers that need audio should transcribe it
        first via `transcribe_audio` and fold the transcript into `prompt`.
        """
        from .models import AIUsageLog

        if response_schema:
            prompt = (
                f"{prompt}\n\nRespond with ONLY a single JSON object matching this schema "
                f"(no markdown fences, no commentary):\n{json.dumps(response_schema)}"
            )

        start = time.monotonic()
        success, error = True, ""
        input_tokens = output_tokens = 0
        text = ""
        try:
            kwargs = {}
            if response_schema:
                kwargs["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                **kwargs,
            )
            text = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            if usage:
                input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(usage, "completion_tokens", 0) or 0
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

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.mp4",
                          model: str = "whisper-large-v3") -> str:
        """Groq has no audio-input chat mode like Gemini did, so interview
        recordings go through this separate transcription call first; the
        resulting text is what gets folded into the summary prompt."""
        response = self.client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=model,
        )
        return response.text


groq_client = GroqClient()
