"""Thin wrapper around Agora's token builder and Cloud Recording REST API
(§8 of the technical documentation). Django's video responsibilities are
limited to: minting short-lived RTC tokens and starting/stopping cloud
recording — media itself flows browser <-> Agora directly, never through
Django."""

import hashlib
import hmac
import time

import requests
from django.conf import settings

TOKEN_TTL_SECONDS = 60 * 60  # 1 hour, short-lived per §2.2


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verifies the Agora-Signature-V2 header (HMAC-SHA256 over the raw
    request body) on incoming Cloud Recording notification callbacks.
    Docs: Agora Console → Notifications → Add signature verification."""
    if not settings.AGORA_WEBHOOK_SECRET or not signature:
        return False
    expected = hmac.new(
        settings.AGORA_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def build_rtc_token(channel_name: str, uid: int, role: str = "publisher") -> str:
    from agora_token_builder.RtcTokenBuilder import Role_Publisher, Role_Subscriber, RtcTokenBuilder

    expire_at = int(time.time()) + TOKEN_TTL_SECONDS
    agora_role = Role_Publisher if role == "publisher" else Role_Subscriber
    return RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        agora_role,
        expire_at,
    )


class AgoraCloudRecording:
    """Thin REST client for Agora's Cloud Recording API (composite mode)."""

    BASE_URL = "https://api.agora.io/v1/apps/{app_id}/cloud_recording"

    def __init__(self):
        self.auth = (settings.AGORA_CUSTOMER_KEY, settings.AGORA_CUSTOMER_SECRET)
        self.app_id = settings.AGORA_APP_ID

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL.format(app_id=self.app_id)}{path}"

    def acquire(self, channel_name: str, uid: str) -> str:
        resp = requests.post(
            self._url("/acquire"),
            json={"cname": channel_name, "uid": uid, "clientRequest": {}},
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["resourceId"]

    def start(self, channel_name: str, uid: str, resource_id: str, storage_config: dict) -> str:
        resp = requests.post(
            self._url(f"/resourceid/{resource_id}/mode/mix/start"),
            json={
                "cname": channel_name,
                "uid": uid,
                "clientRequest": {"recordingConfig": {"channelType": 1}, "storageConfig": storage_config},
            },
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["sid"]

    def stop(self, channel_name: str, uid: str, resource_id: str, sid: str) -> dict:
        resp = requests.post(
            self._url(f"/resourceid/{resource_id}/sid/{sid}/mode/mix/stop"),
            json={"cname": channel_name, "uid": uid, "clientRequest": {}},
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
