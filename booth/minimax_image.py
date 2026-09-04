"""
MiniMax image generation & editing.

Powers Station 2 (person + reference photo -> edited image) and
Station 3 (person + environment photo -> composited scene).

IMPORTANT STRUCTURAL DIFFERENCE from a native multi-image editor:

MiniMax `image-01` accepts exactly ONE reference image, and it must be a
`character` subject reference. It has no second-image slot, no mask, and no
inpainting region. So the two-photo stations cannot hand both photos to the
model the way a native image editor would.

What happens instead, in two calls:

  1. The SECOND photo (the reference look, or the environment) is described in
     words by MiniMax's vision model.
  2. That description is folded into the text prompt, and the FIRST photo (the
     visitor) goes in as the character subject reference.

This preserves the two-photo booth experience, but it is a paraphrase, not a
composite. The output will match the *description* of the second photo rather
than its exact pixels - a specific jacket becomes "a red denim jacket", and a
specific void deck becomes "a covered concrete walkway with blue pillars".
Expect a good likeness of the person and a plausible-but-not-identical
rendering of the reference.

Docs:
  https://platform.minimax.io/docs/guides/image-generation
  https://platform.minimax.io/docs/api-reference/text-openai-api
"""

import base64
import os

import requests

from .minimax_client import MinimaxError, data_uri, get_json, ping, post_json

# `image-01` is MiniMax's image model. Kept as an env override so a newer one
# can be dropped in without a code change.
IMAGE_MODEL = os.getenv("MINIMAX_IMAGE_MODEL", "image-01")

# Vision is only on the M3 generation. The M2.x series is text-only and will
# silently ignore image content blocks, which would leave the booth describing
# photos it never saw.
TEXT_MODEL = os.getenv("MINIMAX_TEXT_MODEL", "MiniMax-M3")

VALID_ASPECT_RATIOS = {"1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9"}

# image-01's prompt budget is far tighter than a chat model's. Overrun gets
# rejected rather than truncated server-side, so it is capped here.
PROMPT_LIMIT = int(os.getenv("MINIMAX_PROMPT_LIMIT", 1500))

# Re-exported so callers can keep one exception type for the image path.
ImageGenError = MinimaxError


def resolve_model():
    """Named for symmetry with the video module; MiniMax has no discovery API."""
    return IMAGE_MODEL


def _aspect_ratio(value):
    if value in VALID_ASPECT_RATIOS:
        return value
    print(f"[MiniMax] aspect_ratio '{value}' not supported; falling back to 1:1.")
    return "1:1"


def describe_image(image, question, max_tokens=1024):
    """
    Ask the vision model what is in a photo, in words.

    `image` is a (bytes, mime_type) tuple. Returns a plain string.
    """
    payload = {
        "model": TEXT_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_uri(image)}},
                ],
            }
        ],
        "max_tokens": max_tokens,
        # Low temperature: this is a description task, not a creative one.
        "temperature": 0.2,
    }
    data = post_json(
        "/v1/chat/completions", payload, timeout=90,
        context="MiniMax photo description",
    )

    choices = data.get("choices") or []
    if not choices:
        raise MinimaxError("MiniMax's vision model returned no description.")

    content = (choices[0].get("message") or {}).get("content")

    # Content is a string for plain replies and a list of blocks for multimodal
    # ones; both shapes appear depending on the model.
    if isinstance(content, list):
        content = " ".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )

    text = (content or "").strip()

    # MiniMax-M3 is a reasoning model: it prefixes its real answer with a
    # <think>...</think> block. That block must not leak into the description
    # (it becomes a video/image prompt downstream), and a truncated one - cut
    # off by max_tokens before the model reached its answer - must not be
    # mistaken for a real description either.
    if "<think>" in text:
        if "</think>" not in text:
            raise MinimaxError(
                "MiniMax's vision model ran out of tokens while reasoning and "
                "never reached an answer. Retry, or raise max_tokens."
            )
        text = text.split("</think>", 1)[1].strip()

    if not text:
        raise MinimaxError("MiniMax's vision model returned an empty description.")
    return text


def compose_image(prompt, subject_image, aspect_ratio="1:1"):
    """
    Generate one image from `prompt`, using `subject_image` as the character.

    subject_image -- (bytes, mime_type) of the visitor's photo.

    Returns (image_bytes, mime_type).
    """
    if not subject_image:
        raise MinimaxError("A photo of the visitor is required.")

    if len(prompt) > PROMPT_LIMIT:
        print(f"[MiniMax] Prompt is {len(prompt)} chars; trimming to {PROMPT_LIMIT}.")
        prompt = prompt[:PROMPT_LIMIT].rsplit(" ", 1)[0]

    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "aspect_ratio": _aspect_ratio(aspect_ratio),
        "response_format": "base64",
        "n": 1,
        # Lets MiniMax rewrite the prompt for its own model. Helps far more than
        # it hurts on booth-style prompts.
        "prompt_optimizer": True,
        "subject_reference": [
            {"type": "character", "image_file": data_uri(subject_image)}
        ],
    }

    data = post_json(
        "/v1/image_generation", payload, timeout=180,
        context="MiniMax image generation",
    )
    return _extract_image(data)


def _extract_image(payload):
    body = payload.get("data") or {}

    encoded = body.get("image_base64") or []
    if encoded:
        try:
            return base64.b64decode(encoded[0]), "image/jpeg"
        except Exception as e:
            raise MinimaxError("MiniMax returned image data that could not be decoded.") from e

    # response_format is set to base64 above, but the API will hand back URLs in
    # some configurations. Follow them rather than failing on a valid result.
    urls = body.get("image_urls") or []
    if urls:
        try:
            response = requests.get(urls[0], timeout=120)
            response.raise_for_status()
        except requests.RequestException as e:
            raise MinimaxError(f"Could not download the generated image: {e}") from e
        return response.content, response.headers.get("Content-Type", "image/jpeg")

    raise MinimaxError(
        "MiniMax returned no image. This is usually the content filter — "
        "try a different photo."
    )


def preflight():
    """Config + credentials check for /api/health. Does not generate an image."""
    ping()
    return {"image_model": IMAGE_MODEL, "vision_model": TEXT_MODEL}


if __name__ == "__main__":
    # Diagnostic: python -m booth.minimax_image
    from dotenv import load_dotenv

    load_dotenv()
    try:
        print(f"Image model : {IMAGE_MODEL}")
        print(f"Vision model: {TEXT_MODEL}")
        print(f"API base    : {os.getenv('MINIMAX_API_BASE', 'https://api.minimax.io')}")
        preflight()
        print("\nAPI key works.")
    except MinimaxError as e:
        print(f"\nError: {e}")
