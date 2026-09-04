"""
Shared MiniMax API plumbing.

One place for the base URL, the key, request/response handling and error
translation, so the image and video modules don't each reinvent it.

MiniMax returns HTTP 200 for application-level failures and puts the real
outcome in `base_resp.status_code`. Checking only the HTTP status is the
classic way to "succeed" with no output, so every call goes through here.

Docs: https://platform.minimax.io/docs/api-reference/api-overview
"""

import base64
import mimetypes
import os

import requests

# Region matters. api.minimax.io is the international platform; the mainland
# China platform is a different host AND a different account/key namespace.
# A key from one will not authenticate against the other.
DEFAULT_API_BASE = "https://api.minimax.io"


class MinimaxError(Exception):
    """Raised with a message safe to show a booth visitor."""


def api_base():
    return os.getenv("MINIMAX_API_BASE", DEFAULT_API_BASE).rstrip("/")


def resolve_api_key():
    """The one place the key is read."""
    key = os.getenv("MINIMAX_API_KEY")
    if not key:
        raise MinimaxError(
            "MINIMAX_API_KEY is not set. Copy .env.example to .env and add your "
            "key from https://platform.minimax.io/user-center/basic-information"
        )
    return key


def headers(json_body=True):
    head = {"Authorization": f"Bearer {resolve_api_key()}"}
    if json_body:
        head["Content-Type"] = "application/json"
    return head


# MiniMax application-level codes. Only the ones worth a tailored message are
# listed; anything else falls through to a generic message that still prints the
# code, so staff can look it up rather than being told "something went wrong".
_STATUS_MESSAGES = {
    1002: "MiniMax rate limit hit. Wait a few seconds and try again.",
    1004: "MiniMax rejected the API key. Check MINIMAX_API_KEY in your .env, "
          "and check you are using the right region (api.minimax.io vs the "
          "mainland China host); keys are not interchangeable.",
    1008: "The MiniMax account has run out of credit. Top up at "
          "https://platform.minimax.io/user-center/payment",
    1026: "MiniMax's content filter blocked this input. Try a different photo.",
    1027: "MiniMax's content filter blocked the generated result. Try again or "
          "use a different photo.",
    2013: "MiniMax rejected the request parameters as invalid.",
    2049: "MiniMax says this API key is invalid. Check MINIMAX_API_KEY.",
}


def check_base_resp(payload, context):
    """
    Raise MinimaxError unless base_resp says success.

    A missing base_resp is treated as success: some endpoints omit it on the
    happy path, and the callers verify the payload they actually need anyway.
    """
    base_resp = payload.get("base_resp") or {}
    code = base_resp.get("status_code", 0)
    if code in (0, None):
        return payload

    msg = base_resp.get("status_msg") or "no detail"
    if code in _STATUS_MESSAGES:
        raise MinimaxError(_STATUS_MESSAGES[code])
    raise MinimaxError(f"{context} failed (MiniMax code {code}: {msg}).")


def post_json(path, payload, timeout=120, context="MiniMax request"):
    url = f"{api_base()}{path}"
    try:
        response = requests.post(url, json=payload, headers=headers(), timeout=timeout)
    except requests.RequestException as e:
        raise MinimaxError(f"Could not reach MiniMax: {e}") from e
    return _decode(response, context)


def get_json(path, params=None, timeout=60, context="MiniMax request"):
    url = f"{api_base()}{path}"
    try:
        response = requests.get(
            url, params=params or {}, headers=headers(json_body=False), timeout=timeout
        )
    except requests.RequestException as e:
        raise MinimaxError(f"Could not reach MiniMax: {e}") from e
    return _decode(response, context)


# The v2 video API reports failures with real HTTP status codes and an
# {"type":"error","error":{...}} envelope, where v1 returns HTTP 200 plus
# base_resp. Both are handled so one client serves both API generations.
_HTTP_MESSAGES = {
    400: "MiniMax rejected the request as malformed.",
    401: _STATUS_MESSAGES[1004],
    402: _STATUS_MESSAGES[1008],
    422: "MiniMax's content filter flagged this input. Try a different photo.",
    429: _STATUS_MESSAGES[1002],
}


def _decode(response, context):
    detail = ""
    payload = None
    try:
        payload = response.json()
    except ValueError:
        payload = None

    # v2 error envelope, which can accompany any 4xx/5xx.
    if isinstance(payload, dict) and payload.get("type") == "error":
        detail = (payload.get("error") or {}).get("message") or ""

    if response.status_code in _HTTP_MESSAGES:
        message = _HTTP_MESSAGES[response.status_code]
        if detail:
            message = f"{message} ({detail[:150]})"
        raise MinimaxError(message)

    if response.status_code >= 400:
        raise MinimaxError(
            f"{context} failed: HTTP {response.status_code} "
            f"{detail[:200] or response.text[:200]}"
        )

    if payload is None:
        raise MinimaxError(
            f"{context} returned a non-JSON response: {response.text[:200]}"
        )

    if detail:
        raise MinimaxError(f"{context} failed: {detail[:200]}")

    return check_base_resp(payload, context)


def data_uri(source, mime_type=None):
    """
    Encode bytes or a file path as a data URI.

    MiniMax accepts either a public URL or a base64 data URI for input media.
    A booth laptop on venue WiFi has no public URL, so everything goes inline.
    """
    if isinstance(source, tuple):
        raw, mime_type = source
    elif isinstance(source, (bytes, bytearray)):
        raw = bytes(source)
    else:
        with open(source, "rb") as f:
            raw = f.read()
        mime_type = mime_type or mimetypes.guess_type(source)[0]

    mime_type = mime_type or "image/jpeg"
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode()}"


def ping():
    """
    Cheap readiness check: validates the key without paying for a generation.

    There is no dedicated health endpoint, so this asks the text model for a
    single token. Costs a fraction of a cent and proves key + region + credit.
    """
    payload = {
        "model": os.getenv("MINIMAX_TEXT_MODEL", "MiniMax-M3"),
        "messages": [{"role": "user", "content": "ok"}],
        "max_tokens": 1,
    }
    post_json("/v1/chat/completions", payload, timeout=30, context="MiniMax key check")
    return True
