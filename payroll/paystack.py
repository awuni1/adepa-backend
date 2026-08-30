"""Thin REST wrapper around Paystack's Transfer Recipient and Transfer APIs
(https://paystack.com/docs/api/transfer-recipient/, /transfer/) — used to pay
out approved payroll runs straight to each employee's bank account. Money
only ever moves via `initiate_transfer`; whether it actually landed is never
assumed at request time — that confirmation comes back asynchronously
through Paystack's webhook (see PaystackWebhookView) and is what flips a
Payslip to `transfer_status=success`."""

import hashlib
import hmac
from decimal import Decimal

import requests
from django.conf import settings

BASE_URL = "https://api.paystack.co"
TIMEOUT = 15


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verifies the `x-paystack-signature` header — HMAC-SHA512 over the raw
    request body, keyed with the secret key. Docs: Paystack → Settings →
    API Keys & Webhooks."""
    if not settings.PAYSTACK_SECRET_KEY or not signature:
        return False
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def list_banks(currency: str = "GHS") -> list[dict]:
    resp = requests.get(f"{BASE_URL}/bank", params={"currency": currency}, headers=_headers(), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["data"]


def resolve_account_number(account_number: str, bank_code: str) -> dict:
    """Confirms an account number belongs to the named bank and returns the
    account holder's name, so the employee sees who they're about to be paid
    as *before* we ever register a Paystack recipient for it."""
    resp = requests.get(
        f"{BASE_URL}/bank/resolve",
        params={"account_number": account_number, "bank_code": bank_code},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise ValueError(resp.json().get("message") or "Couldn't verify that account number.")
    return resp.json()["data"]


def create_transfer_recipient(*, name: str, account_number: str, bank_code: str, currency: str = "GHS") -> dict:
    resp = requests.post(
        f"{BASE_URL}/transferrecipient",
        json={
            "type": "ghipss" if currency == "GHS" else "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency,
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise ValueError(resp.json().get("message") or "Couldn't register this bank account with Paystack.")
    return resp.json()["data"]


def initiate_transfer(*, amount: Decimal, recipient_code: str, reference: str, reason: str) -> dict:
    """`amount` is the payslip's net pay in the account's major currency unit
    (e.g. GHS); Paystack's API takes the minor unit (pesewas/kobo)."""
    resp = requests.post(
        f"{BASE_URL}/transfer",
        json={
            "source": "balance",
            "amount": int((amount * 100).to_integral_value()),
            "recipient": recipient_code,
            "reference": reference,
            "reason": reason,
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise ValueError(resp.json().get("message") or "Transfer request was rejected.")
    return resp.json()["data"]
