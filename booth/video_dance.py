"""
Station 1: turn a visitor's photo into a dance video.

The backend is pluggable and chosen with DANCE_PROVIDER:

  gemini_omni - Gemini Omni 1.1 Flash (released 2026-08-27). THE DEFAULT.
                First-party image-to-video, and accepts a ~3s reference clip via
                <VIDEO_REF_0> to carry motion and character style. Handles both
                the templates and visitor-supplied clips. ~$0.10/sec at 720p.
                PAID: no Gemini video model has a free tier, so the project
                behind GEMINI_API_KEY must have billing enabled.
  mock        - no API key, no cost. Renders a real MP4 locally so the whole
                booth flow is demoable offline. Set this as the fallback if a
                paid provider dies mid-event.
  replicate   - Wan 2.2 Animate. True frame-by-frame motion transfer from an
                arbitrary-length driving video. Reproduces a specific
                choreography more faithfully than Omni's style reference, and
                is cheaper per clip (~$0.20-0.40 per 5s).
  veo         - Google Veo. Prompt-driven image-to-video with no driving-clip
                support at all, so templates only. Superseded by gemini_omni;
                kept for accounts that only have Veo access.

Choosing between gemini_omni and replicate: Omni's video reference is a style
and motion *hint* capped around 3 seconds, so it captures the vibe of a dance.
Wan Animate copies the actual choreography. If a visitor expects to see their
exact routine reproduced, use replicate.

Every provider returns the same dict so the Flask layer never branches on which
one is active.
"""

import base64
import mimetypes
import os
import re
import subprocess
import time
import uuid

import requests

OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
TEMPLATE_DIR = os.path.join(os.getcwd(), "dance_templates")

REPLICATE_MODEL = os.getenv(
    "REPLICATE_DANCE_MODEL", "wan-video/wan-2.2-animate-animation"
)

# Built-in choreography. `driving_video` is used by motion-transfer providers;
# `prompt` is used by prompt-driven ones (Veo) and as the caption everywhere.
TEMPLATES = [
    {
        "id": "cyber_hiphop",
        "name": "Cyber Hip-Hop",
        "emoji": "🕺",
        "driving_video": "cyber_hiphop.mp4",
        "prompt": (
            "The person in the photo performs an energetic hip-hop dance: sharp "
            "popping arm waves, a confident bounce on the beat, feet shifting "
            "side to side. Neon-lit stage, cinematic lighting, camera locked off."
        ),
    },
    {
        "id": "salsa_fiesta",
        "name": "Salsa Fiesta",
        "emoji": "💃",
        "driving_video": "salsa_fiesta.mp4",
        "prompt": (
            "The person in the photo dances salsa: rhythmic hip sway, "
            "cross-body footwork, one fluid spin. Warm festive lighting, "
            "camera locked off."
        ),
    },
    {
        "id": "kpop_idol",
        "name": "K-Pop Idol",
        "emoji": "✨",
        "driving_video": "kpop_idol.mp4",
        "prompt": (
            "The person in the photo performs a crisp K-pop point choreography: "
            "synchronised arm points, a heart pose, light bouncing steps. "
            "Bright studio lighting, camera locked off."
        ),
    },
    {
        "id": "breakdance",
        "name": "Breakdance",
        "emoji": "⚡",
        "driving_video": "breakdance.mp4",
        "prompt": (
            "The person in the photo breakdances: six-step footwork, a floor "
            "sweep, ending in a freeze pose. Street setting, dramatic lighting, "
            "camera locked off."
        ),
    },
]


class DanceError(Exception):
    """Raised with a message safe to show a booth visitor."""


def get_provider():
    return os.getenv("DANCE_PROVIDER", "gemini_omni").strip().lower()


def get_template(template_id):
    for template in TEMPLATES:
        if template["id"] == template_id:
            return template
    raise DanceError(f"Unknown dance template '{template_id}'.")


def template_video_path(template):
    path = os.path.join(TEMPLATE_DIR, template["driving_video"])
    return path if os.path.exists(path) else None


def generate_dance(person_image, template_id=None, driving_video_path=None):
    """
    person_image        -- (bytes, mime_type) of the visitor's photo.
    template_id         -- one of TEMPLATES; used when no driving video is given.
    driving_video_path  -- visitor's own dance clip (the rate-limited path).

    Returns {"video_path", "filename", "provider", "template", "note"}.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    template = get_template(template_id) if template_id else TEMPLATES[0]
    if not driving_video_path:
        driving_video_path = template_video_path(template)

    provider = get_provider()
    job_id = f"dance_{uuid.uuid4().hex[:8]}"

    if provider == "mock":
        return _generate_mock(person_image, template, job_id)
    if provider == "gemini_omni":
        return _generate_omni(person_image, template, driving_video_path, job_id)
    if provider == "replicate":
        return _generate_replicate(person_image, template, driving_video_path, job_id)
    if provider == "veo":
        return _generate_veo(person_image, template, driving_video_path, job_id)
    raise DanceError(
        f"DANCE_PROVIDER='{provider}' is not recognised. "
        "Use mock, gemini_omni, replicate, or veo."
    )


# ---------------------------------------------------------------------------
# mock - local render, no API, no cost
# ---------------------------------------------------------------------------

def _generate_mock(person_image, template, job_id):
    """
    Renders the visitor's photo as a short video with a slow zoom, so the booth
    flow (upload -> generate -> QR -> download) is end-to-end testable offline.
    Uses ffmpeg when available and falls back to copying the still image.
    """
    image_bytes, mime_type = person_image
    ext = mimetypes.guess_extension(mime_type) or ".jpg"
    src = os.path.join(OUTPUT_DIR, f"{job_id}_src{ext}")
    with open(src, "wb") as f:
        f.write(image_bytes)

    out_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    if _have_ffmpeg():
        # 6s Ken Burns zoom, padded to even dimensions for H.264.
        vf = (
            "scale=720:-2,"
            "zoompan=z='min(zoom+0.0015,1.3)':d=180:s=720x900:fps=30,"
            "pad=ceil(iw/2)*2:ceil(ih/2)*2"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", src,
            "-vf", vf, "-t", "6", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", out_path,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            os.remove(src)
            return {
                "video_path": out_path,
                "filename": os.path.basename(out_path),
                "provider": "mock",
                "template": template["name"],
                "note": "Demo render (no AI). Set DANCE_PROVIDER=gemini_omni for real dancing.",
            }
        except Exception as e:
            print(f"[Dance/mock] ffmpeg failed ({e}); returning the still image.")

    still = os.path.join(OUTPUT_DIR, f"{job_id}{ext}")
    os.replace(src, still)
    return {
        "video_path": still,
        "filename": os.path.basename(still),
        "provider": "mock",
        "template": template["name"],
        "note": "ffmpeg not installed, so this is a still image. Install ffmpeg or set DANCE_PROVIDER=gemini_omni.",
    }


def _have_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# gemini_omni - Gemini Omni 1.1 Flash via the Interactions API
# ---------------------------------------------------------------------------

OMNI_MODEL = os.getenv("OMNI_MODEL", "gemini-omni-1.1-flash")

# Omni's own limits, from the model docs. Enforced here so a bad .env value
# fails on startup-ish with a clear message instead of a 400 from the API.
OMNI_RESOLUTIONS = {"360p", "720p", "1080p", "4k"}
OMNI_MIN_DURATION = 3
OMNI_MAX_DURATION = 10

_omni_client = None


def _omni_get_client():
    """
    Omni gets its own client, separate from the image one.

    A video generation call blocks for minutes; the SDK's default HTTP timeout
    is far shorter, so sharing the image client would abort mid-render after
    the request had already been billed.
    """
    global _omni_client
    if _omni_client is not None:
        return _omni_client

    from google import genai
    from google.genai import types

    from .gemini_image import ImageGenError, resolve_api_key

    # resolve_api_key raises ImageGenError, which the Flask layer only handles
    # for the image stations. Convert it so a missing key gives the visitor the
    # real reason instead of a generic 500.
    try:
        api_key = resolve_api_key()
    except ImageGenError as e:
        raise DanceError(str(e)) from e

    seconds = int(os.getenv("OMNI_TIMEOUT", 600))
    _omni_client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=seconds * 1000),  # milliseconds
    )
    return _omni_client


def _omni_duration():
    raw = os.getenv("OMNI_DURATION", "6").strip().lower().rstrip("s")
    try:
        value = int(raw)
    except ValueError:
        raise DanceError(f"OMNI_DURATION must be a whole number of seconds, got '{raw}'.")
    if not OMNI_MIN_DURATION <= value <= OMNI_MAX_DURATION:
        raise DanceError(
            f"OMNI_DURATION must be between {OMNI_MIN_DURATION} and "
            f"{OMNI_MAX_DURATION} seconds (Omni's limit). Got {value}."
        )
    # The API wants a duration string with the unit: "6s", not "6".
    return value, f"{value}s"


def _omni_resolution():
    value = os.getenv("OMNI_RESOLUTION", "720p").strip().lower()
    if value not in OMNI_RESOLUTIONS:
        raise DanceError(
            f"OMNI_RESOLUTION='{value}' is not valid. "
            f"Use one of: {', '.join(sorted(OMNI_RESOLUTIONS))}."
        )
    return value


def _normalize_file_uri(uri):
    """Files API URIs come back with query params; the Interactions API wants them bare."""
    match = re.search(r"files/([a-zA-Z0-9]+)", uri or "")
    if match:
        return f"https://generativelanguage.googleapis.com/files/{match.group(1)}"
    return uri


def _upload_for_omni(client, path, timeout=180):
    """
    Push a local file through the Files API and wait for it to go ACTIVE.

    Omni takes media by File API URI only - inline bytes are not accepted in an
    interactions input part, so every input goes through here first.

    The upload gets its own, much shorter HTTP timeout. The client's OMNI_TIMEOUT
    is sized for a video render; letting an upload inherit it means a stalled
    connection holds a booth visitor at the counter for ten minutes.
    """
    from google.genai import types

    upload_seconds = int(os.getenv("OMNI_UPLOAD_TIMEOUT", 120))
    try:
        uploaded = client.files.upload(
            file=path,
            config=types.UploadFileConfig(
                http_options=types.HttpOptions(timeout=upload_seconds * 1000)
            ),
        )
    except Exception as e:
        raise DanceError(f"Upload to the Gemini Files API failed: {str(e)[:200]}") from e

    deadline = time.time() + timeout
    while getattr(uploaded.state, "name", str(uploaded.state)) == "PROCESSING":
        if time.time() > deadline:
            raise DanceError("Timed out waiting for the upload to process.")
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    if getattr(uploaded.state, "name", str(uploaded.state)) == "FAILED":
        raise DanceError("Gemini could not process that file. Try a shorter clip.")

    return _normalize_file_uri(uploaded.uri), uploaded.mime_type


def _prep_reference_clip(src_path, job_id):
    """
    Trim and shrink a visitor's clip before upload.

    Omni's guidance is that a reference video should be about 3 seconds; longer
    ones work but upload slowly, which is dead time at a booth queue. Best
    effort - if ffmpeg is missing we upload the original.
    """
    seconds = int(os.getenv("OMNI_REFERENCE_SECONDS", 3))
    if not _have_ffmpeg():
        return src_path

    trimmed = os.path.join(OUTPUT_DIR, f"{job_id}_ref.mp4")
    cmd = [
        "ffmpeg", "-y", "-i", src_path, "-t", str(seconds),
        "-vf", "scale='min(720,iw)':-2", "-r", "24",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", trimmed,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        return trimmed
    except Exception as e:
        print(f"[Dance/omni] Could not pre-trim the clip ({e}); uploading it as-is.")
        return src_path


def _generate_omni(person_image, template, driving_video_path, job_id):
    client = _omni_get_client()
    duration, duration_str = _omni_duration()
    resolution = _omni_resolution()

    image_bytes, mime_type = person_image
    ext = mimetypes.guess_extension(mime_type) or ".jpg"
    frame_path = os.path.join(OUTPUT_DIR, f"{job_id}_frame{ext}")
    reference_path = None

    try:
        with open(frame_path, "wb") as f:
            f.write(image_bytes)

        # The visitor's photo is the opening frame, so they recognisably start
        # the shot rather than appearing as a lookalike the model invented.
        frame_uri, frame_mime = _upload_for_omni(client, frame_path)
        parts = [{"type": "image", "uri": frame_uri, "mime_type": frame_mime}]

        if driving_video_path:
            # Visitor's own clip becomes a motion/character reference. Omni treats
            # this as style guidance, not frame-exact choreography - see module docstring.
            reference_path = _prep_reference_clip(driving_video_path, job_id)
            ref_uri, ref_mime = _upload_for_omni(client, reference_path)
            parts.append({"type": "video", "uri": ref_uri, "mime_type": ref_mime})
            prompt = (
                "<FIRST_FRAME> The person in the first frame dances like the dancer "
                "in <VIDEO_REF_0>, matching their rhythm, footwork and arm movements. "
                "Keep the person's face and clothing exactly the same. "
                "A single continuous shot, static camera, no scene cuts. "
                "Include upbeat background music. No dialogue."
            )
        else:
            prompt = (
                f"<FIRST_FRAME> {template['prompt']} "
                "Keep the person's face and clothing exactly the same. "
                "A single continuous shot, static camera, no scene cuts. "
                "Include upbeat background music. No dialogue."
            )

        parts.append({"type": "text", "text": prompt})

        print(f"[Dance/omni] Submitting to {OMNI_MODEL} "
              f"({duration}s @ {resolution}, billed per second)...")
        try:
            interaction = client.interactions.create(
                model=OMNI_MODEL,
                input=parts,
                response_format={
                    "type": "video",
                    "delivery": "uri",
                    "aspect_ratio": os.getenv("OMNI_ASPECT_RATIO", "9:16"),
                    "duration": duration_str,
                    "resolution": resolution,
                },
            )
        except Exception as e:
            raise DanceError(_omni_error(e, bool(driving_video_path))) from e

        output = getattr(interaction, "output_video", None)
        if not output or not getattr(output, "uri", None):
            raise DanceError(_omni_error(None, bool(driving_video_path)))

        out_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
        try:
            with open(out_path, "wb") as f:
                f.write(client.files.download(file=output.uri))
        except Exception as e:
            raise DanceError(f"Omni generated the video but the download failed: {str(e)[:200]}") from e
    finally:
        # Never leave a visitor's face or clip sitting in outputs/, which is served.
        for path in (frame_path, reference_path):
            if path and path != driving_video_path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    return {
        "video_path": out_path,
        "filename": os.path.basename(out_path),
        "provider": "gemini_omni",
        "template": template["name"],
        "note": "",
    }


def omni_preflight():
    """
    Cheap readiness check for /api/health - validates config and reaches the API
    without submitting a (billed) generation.
    """
    client = _omni_get_client()
    duration, _ = _omni_duration()
    resolution = _omni_resolution()
    try:
        list(client.models.list())
    except Exception as e:
        raise DanceError(f"Could not reach the Gemini API: {str(e)[:200]}") from e
    return {"model": OMNI_MODEL, "duration": duration, "resolution": resolution}


def _omni_error(e, used_reference):
    text = str(e) if e else "Gemini Omni returned no video."
    lowered = text.lower()
    if "quota" in lowered or "resource_exhausted" in lowered or "429" in text:
        return (
            "Gemini Omni quota reached. Omni has no free tier — check that "
            "billing is enabled on the project behind GEMINI_API_KEY."
        )
    if "permission" in lowered or "403" in text or "not found" in lowered:
        return (
            "This API key can't reach Gemini Omni. It needs a billing-enabled "
            "project; the free tier does not include video generation."
        )
    if used_reference:
        # Empty output with a reference clip is the documented symptom.
        return (
            f"{text} Note: uploading reference videos is not available in the "
            "EEA, Switzerland, the UK, or some US states. If you are in one of "
            "those regions, use a built-in template or DANCE_PROVIDER=replicate."
        )
    return f"Gemini Omni generation failed: {text[:300]}"


# ---------------------------------------------------------------------------
# replicate - Wan 2.2 Animate (motion transfer)
# ---------------------------------------------------------------------------

def _data_uri(path_or_bytes, mime_type=None):
    if isinstance(path_or_bytes, tuple):
        raw, mime_type = path_or_bytes
    else:
        with open(path_or_bytes, "rb") as f:
            raw = f.read()
        mime_type = mime_type or mimetypes.guess_type(path_or_bytes)[0] or "application/octet-stream"
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode()}"


def _generate_replicate(person_image, template, driving_video_path, job_id):
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise DanceError(
            "REPLICATE_API_TOKEN is not set. Get one at https://replicate.com/account "
            "or switch back to DANCE_PROVIDER=mock."
        )
    if not driving_video_path or not os.path.exists(driving_video_path):
        raise DanceError(
            f"No driving video for '{template['name']}'. Motion transfer needs a "
            f"reference clip: put one at dance_templates/{template['driving_video']}, "
            "or let the visitor upload their own."
        )

    payload = {
        "input": {
            "image": _data_uri(person_image),
            "video": _data_uri(driving_video_path),
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait",  # Replicate holds the connection open briefly
    }
    url = f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions"

    print(f"[Dance/replicate] Submitting to {REPLICATE_MODEL}...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
    except requests.RequestException as e:
        raise DanceError(f"Could not reach Replicate: {e}") from e

    if response.status_code not in (200, 201):
        raise DanceError(f"Replicate error {response.status_code}: {response.text[:300]}")

    prediction = response.json()
    output_url = _poll_replicate(prediction, headers)
    return _download_video(output_url, job_id, "replicate", template)


def _poll_replicate(prediction, headers, timeout=600):
    deadline = time.time() + timeout
    while prediction.get("status") in ("starting", "processing"):
        if time.time() > deadline:
            raise DanceError("Replicate timed out after 10 minutes.")
        time.sleep(3)
        get_url = prediction.get("urls", {}).get("get")
        if not get_url:
            raise DanceError("Replicate response had no polling URL.")
        prediction = requests.get(get_url, headers=headers, timeout=30).json()

    if prediction.get("status") != "succeeded":
        raise DanceError(
            f"Generation {prediction.get('status')}: {prediction.get('error') or 'no detail'}"
        )

    output = prediction.get("output")
    if isinstance(output, list):
        output = output[0] if output else None
    if not output:
        raise DanceError("Replicate succeeded but returned no video.")
    return output


def _download_video(url, job_id, provider, template):
    out_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    return {
        "video_path": out_path,
        "filename": os.path.basename(out_path),
        "provider": provider,
        "template": template["name"],
        "note": "",
    }


# ---------------------------------------------------------------------------
# veo - Gemini API (templates only; cannot follow a driving clip)
# ---------------------------------------------------------------------------

def _generate_veo(person_image, template, driving_video_path, job_id):
    from google.genai import types

    from .gemini_image import ImageGenError, get_client

    if driving_video_path:
        raise DanceError(
            "Veo cannot copy a specific dance video. Use DANCE_PROVIDER=gemini_omni "
            "or replicate for visitor-supplied clips, or pick a template instead."
        )

    model = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview")
    image_bytes, mime_type = person_image
    try:
        client = get_client()
    except ImageGenError as e:
        raise DanceError(str(e)) from e

    print(f"[Dance/veo] Submitting to {model} (billed per second, no free tier)...")
    try:
        operation = client.models.generate_videos(
            model=model,
            prompt=template["prompt"],
            image=types.Image(image_bytes=image_bytes, mime_type=mime_type),
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                number_of_videos=1,
                person_generation="allow_adult",
            ),
        )
        deadline = time.time() + 600
        while not operation.done:
            if time.time() > deadline:
                raise DanceError("Veo timed out after 10 minutes.")
            time.sleep(5)
            operation = client.operations.get(operation)
    except DanceError:
        raise
    except Exception as e:
        raise DanceError(f"Veo generation failed: {str(e)[:300]}") from e

    videos = getattr(operation.response, "generated_videos", None) or []
    if not videos:
        raise DanceError("Veo returned no video.")

    out_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    client.files.download(file=videos[0].video)
    videos[0].video.save(out_path)
    return {
        "video_path": out_path,
        "filename": os.path.basename(out_path),
        "provider": "veo",
        "template": template["name"],
        "note": "",
    }
