"""
Gemini image generation & editing.

Powers Station 2 (person + reference photo -> edited image) and
Station 3 (person + environment photo -> composited scene). Both are the same
underlying operation: N input images + an instruction -> 1 output image.

Uses the google-genai SDK (`client.models.generate_content`) with
response_modalities=["IMAGE"].
"""

import os
import threading

from google import genai
from google.genai import types

# Verified against Google's pricing page on 2026-08-31:
#
#   gemini-2.5-flash-image  FREE tier, ~500 images/day. RETIRES 2026-10-16
#                           along with the rest of the 2.5 series.
#   gemini-3.1-flash-image  PAID only. No free tier.
#   gemini-3-pro-image      PAID only. Highest quality, highest cost.
#
# Free-tier first by default, because a booth running on free credits that
# silently picks a paid-only model fails at the counter with a quota error.
# Flip GEMINI_PREFER_FREE_TIER=false once billing is enabled - and you will
# have to, before 2026-10-16, when the only free option disappears.
FREE_TIER_PREFERENCE = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
]

PAID_PREFERENCE = [
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
    "gemini-2.5-flash-image",
]


def model_preference():
    prefer_free = os.getenv("GEMINI_PREFER_FREE_TIER", "true").lower() == "true"
    return FREE_TIER_PREFERENCE if prefer_free else PAID_PREFERENCE


# Kept as the last-resort fallback when discovery cannot reach the API.
MODEL_PREFERENCE = FREE_TIER_PREFERENCE

_client = None
_resolved_model = None
_lock = threading.Lock()


class ImageGenError(Exception):
    """Raised with a message safe to show a booth visitor."""


def resolve_api_key():
    """
    The one place the key is read. video_dance.py builds its own client (video
    generation needs a much longer HTTP timeout) and calls this for the key.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ImageGenError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://aistudio.google.com/apikey"
        )
    return api_key


def get_client():
    global _client
    if _client is not None:
        return _client

    api_key = resolve_api_key()

    with _lock:
        if _client is None:
            _client = genai.Client(api_key=api_key)
    return _client


def list_image_models():
    """Every image-capable model this API key can actually see."""
    client = get_client()
    found = []
    for model in client.models.list():
        name = (model.name or "").replace("models/", "")
        actions = getattr(model, "supported_actions", None) or []
        if "image" in name.lower() and (not actions or "generateContent" in actions):
            found.append(name)
    return found


def resolve_model():
    """
    Pick an image model once and reuse it.

    Set GEMINI_IMAGE_MODEL in .env to pin a specific one and skip discovery.
    """
    global _resolved_model
    if _resolved_model:
        return _resolved_model

    # Deliberately outside the try below: a missing or rejected key must reach
    # the caller, so /api/health reports "not ready" instead of a false OK.
    get_client()

    pinned = os.getenv("GEMINI_IMAGE_MODEL", "").strip()
    if pinned:
        _resolved_model = pinned
        print(f"[Gemini] Using pinned image model: {pinned}")
        return _resolved_model

    try:
        available = list_image_models()
    except Exception as e:
        print(f"[Gemini] Model discovery failed ({e}); falling back to {MODEL_PREFERENCE[0]}")
        _resolved_model = MODEL_PREFERENCE[0]
        return _resolved_model

    for candidate in model_preference():
        if any(candidate in name for name in available):
            _resolved_model = candidate
            break
    else:
        _resolved_model = available[0] if available else MODEL_PREFERENCE[0]

    print(f"[Gemini] Resolved image model: {_resolved_model}")
    if available:
        print(f"[Gemini] Image models visible to this key: {', '.join(available)}")
    return _resolved_model


def compose_image(prompt, images, aspect_ratio="1:1", allow_minors=None):
    """
    Send `prompt` plus every image in `images` to Gemini, return one image.

    images       -- list of (bytes, mime_type) tuples, in the order the prompt
                    refers to them ("the first photo", "the second photo").
    allow_minors -- only has an effect on Vertex AI; ignored on the Developer
                    API. See the note in the body. Defaults to GEMINI_ALLOW_MINORS.

    Returns (image_bytes, mime_type).
    """
    if not images:
        raise ImageGenError("At least one input image is required.")

    if allow_minors is None:
        allow_minors = os.getenv("GEMINI_ALLOW_MINORS", "true").lower() == "true"

    client = get_client()
    model = resolve_model()

    parts = [types.Part.from_text(text=prompt)]
    for data, mime_type in images:
        parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))

    image_kwargs = {"aspect_ratio": aspect_ratio}

    # person_generation is a Vertex-only knob. On the Developer API (the plain
    # GEMINI_API_KEY path this booth uses) the SDK rejects it client-side, for
    # every model, before the request is even sent - so passing it would break
    # both image stations outright. Family photos are therefore governed by the
    # API's default people-handling, which we cannot loosen from here.
    if getattr(client, "vertexai", False):
        image_kwargs["person_generation"] = "ALLOW_ALL" if allow_minors else "ALLOW_ADULT"

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(**image_kwargs),
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=config,
        )
    except Exception as e:
        raise ImageGenError(_friendly_error(e)) from e

    return _extract_image(response)


def _extract_image(response):
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ImageGenError(
            "The model returned nothing. This usually means the safety filter "
            "blocked the photo — try a different picture."
        )

    candidate = candidates[0]
    content = getattr(candidate, "content", None)
    for part in (getattr(content, "parts", None) or []):
        blob = getattr(part, "inline_data", None)
        if blob and blob.data:
            return blob.data, (blob.mime_type or "image/png")

    # No image came back. Any text part usually explains why.
    reason = getattr(candidate, "finish_reason", None)
    note = ""
    for part in (getattr(content, "parts", None) or []):
        if getattr(part, "text", None):
            note = f" Model said: {part.text.strip()[:200]}"
            break
    raise ImageGenError(
        f"No image in the response (finish_reason={reason}).{note}"
    )


def _friendly_error(e):
    text = str(e)
    lowered = text.lower()
    if "api key" in lowered or "unauthenticated" in lowered or "401" in text:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in your .env."
    if "resource_exhausted" in lowered or "429" in text or "quota" in lowered:
        return "Free-tier quota reached. It resets at midnight Pacific Time."
    if "not found" in lowered or "404" in text:
        return (
            "That image model isn't available to this key. Run "
            "`python -m booth.gemini_image` to list the ones that are, then set "
            "GEMINI_IMAGE_MODEL in .env."
        )
    if "safety" in lowered or "blocked" in lowered:
        return "The safety filter blocked this request. Try a different photo or prompt."
    return f"Image generation failed: {text[:300]}"


if __name__ == "__main__":
    # Handy diagnostic: python -m booth.gemini_image
    from dotenv import load_dotenv

    load_dotenv()
    try:
        models = list_image_models()
        print("Image-capable models visible to this API key:")
        for name in models:
            print(f"  - {name}")
        print(f"\nWould use: {resolve_model()}")
    except ImageGenError as e:
        print(f"Error: {e}")
