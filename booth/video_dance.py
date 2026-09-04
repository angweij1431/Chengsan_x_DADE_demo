"""
Station 1: turn a visitor's photo into a dance video.

The backend is pluggable and chosen with DANCE_PROVIDER:

  minimax   - MiniMax Hailuo image-to-video. THE DEFAULT. Sends the visitor's
              photo as the first frame plus a text prompt describing the dance.
              PAID: MiniMax video has no free tier.
  mock      - no API key, no cost. Renders a real MP4 locally so the whole booth
              flow is demoable offline. Set this as the fallback if the paid
              provider dies mid-event.
  replicate - Wan 2.2 Animate. True frame-by-frame motion transfer from a
              driving video. The ONLY provider that reproduces a specific
              choreography exactly. Not MiniMax - a separate account and token.

HOW THE "BRING YOUR OWN DANCE CLIP" PATH WORKS ON MINIMAX

MiniMax's image-to-video endpoint takes a first frame and a text prompt. It has
no driving-video input, so a visitor's clip cannot be used as motion directly.
Instead the clip is turned into words: ffmpeg pulls a few frames, the vision
model describes the dance, and that description becomes the prompt.

The result therefore captures the *kind* of dance in their clip, not their exact
choreography. If a visitor expects their precise moves reproduced onto
themselves, that needs DANCE_PROVIDER=replicate.

Every provider returns the same dict so the Flask layer never branches on which
one is active.

Docs:
  https://platform.minimax.io/docs/api-reference/video-generation-i2v
  https://platform.minimax.io/docs/api-reference/video-generation-query
  https://platform.minimax.io/docs/api-reference/file-management-retrieve
"""

import mimetypes
import os
import subprocess
import time
import uuid

import requests

from .minimax_client import MinimaxError, data_uri, get_json, post_json

OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
TEMPLATE_DIR = os.path.join(os.getcwd(), "dance_templates")

REPLICATE_MODEL = os.getenv(
    "REPLICATE_DANCE_MODEL", "wan-video/wan-2.2-animate-animation"
)

# Built-in choreography. `prompt` drives prompt-based providers (MiniMax);
# `driving_video` is used by motion-transfer providers (replicate).
TEMPLATES = [
    {
        "id": "chill_groove",
        "name": "Chill Groove",
        "emoji": "\U0001F3A7",
        "driving_video": "chill_groove.mp4",
        "prompt": (
            "The person sways gently side to side in a relaxed groove, weight "
            "shifting slowly between feet. Hands stay loose and mostly still "
            "close to the body, with only a subtle sway. The head tilts softly "
            "on the beat. Calm, smooth energy, warm ambient lighting."
        ),
    },
    {
        "id": "ballroom_waltz",
        "name": "Ballroom Waltz",
        "emoji": "\U0001F483",
        "driving_video": "ballroom_waltz.mp4",
        "prompt": (
            "The person performs a slow, elegant waltz step, gliding gently "
            "from side to side with poised posture. The arms stay in a soft, "
            "held frame close to the body, moving slowly with minimal reach. "
            "Calm, graceful energy, warm ballroom lighting."
        ),
    },
    {
        "id": "kpop_idol",
        "name": "K-Pop Idol",
        "emoji": "✨",
        "driving_video": "kpop_idol.mp4",
        "prompt": (
            "The person performs a crisp K-pop point choreography: synchronised "
            "arm points, a heart pose, light bouncing steps. Bright studio lighting."
        ),
    },
    {
        "id": "runway_pose",
        "name": "Runway Pose",
        "emoji": "\U0001F9CD",
        "driving_video": "runway_pose.mp4",
        "prompt": (
            "The person stands in a confident runway stance, slowly shifting "
            "weight onto one hip and holding the pose for a beat before a slow "
            "turn. One hand rests lightly at the waist; the other stays relaxed "
            "and still at the side. Slow, deliberate, poised energy, clean "
            "studio lighting."
        ),
    },
]


class DanceError(Exception):
    """Raised with a message safe to show a booth visitor."""


def get_provider():
    return os.getenv("DANCE_PROVIDER", "minimax").strip().lower()


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
    provider = get_provider()

    # Only motion-transfer providers use the template's bundled driving clip.
    # MiniMax works from the template's text prompt, so handing it a template
    # video would make it think the visitor brought their own.
    if not driving_video_path and provider == "replicate":
        driving_video_path = template_video_path(template)

    job_id = f"dance_{uuid.uuid4().hex[:8]}"

    if provider == "mock":
        return _generate_mock(person_image, template, job_id)
    if provider == "minimax":
        return _generate_minimax(person_image, template, driving_video_path, job_id)
    if provider == "replicate":
        return _generate_replicate(person_image, template, driving_video_path, job_id)
    raise DanceError(
        f"DANCE_PROVIDER='{provider}' is not recognised. "
        "Use minimax, mock, or replicate."
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
                "note": "Demo render (no AI). Set DANCE_PROVIDER=minimax for real dancing.",
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
        "note": (
            "ffmpeg not installed, so this is a still image. Install ffmpeg or "
            "set DANCE_PROVIDER=minimax."
        ),
    }


def _have_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# minimax - Hailuo image-to-video
# ---------------------------------------------------------------------------

VIDEO_MODEL = os.getenv("MINIMAX_VIDEO_MODEL", "MiniMax-Hailuo-2.3")

# From the i2v reference: resolution -> the durations that resolution allows,
# per model. Enforced here so a bad .env value is caught before a request is
# paid for, instead of coming back as an opaque parameter error.
#
# This has to be per-model, not one flat list. The combinations genuinely
# differ: Hailuo-2.3 has no 512P at all, and the I2V-01 series is 720P/6s only.
# A flat "is it one of these four?" check waves 512P through on the default
# model, which is precisely the mistake this is here to catch.
MODEL_CAPABILITIES = {
    "MiniMax-Hailuo-2.3":      {"768P": {6, 10}, "1080P": {6}},
    "MiniMax-Hailuo-2.3-Fast": {"768P": {6, 10}, "1080P": {6}},
    "MiniMax-Hailuo-02":       {"512P": {6, 10}, "768P": {6, 10}, "1080P": {6}},
    "I2V-01":                  {"720P": {6}},
    "I2V-01-Director":         {"720P": {6}},
    "I2V-01-live":             {"720P": {6}},
}

# MiniMax caps the video prompt at 2000 characters.
VIDEO_PROMPT_LIMIT = 2000


def _video_settings():
    raw_duration = os.getenv("MINIMAX_DURATION", "6").strip().lower().rstrip("s")
    try:
        duration = int(raw_duration)
    except ValueError:
        raise DanceError(
            f"MINIMAX_DURATION must be a whole number of seconds, got '{raw_duration}'."
        )

    resolution = os.getenv("MINIMAX_RESOLUTION", "768P").strip().upper()

    allowed = MODEL_CAPABILITIES.get(VIDEO_MODEL)
    if allowed is None:
        # An unrecognised model is assumed to be newer than this table rather
        # than wrong: MINIMAX_VIDEO_MODEL exists so a new model can be dropped
        # in without a code change. Let MiniMax judge the combination.
        print(f"[Dance/minimax] '{VIDEO_MODEL}' is not in the known-model table, "
              "so duration/resolution are not checked locally.")
        return duration, resolution

    if resolution not in allowed:
        raise DanceError(
            f"{VIDEO_MODEL} does not support MINIMAX_RESOLUTION={resolution}. "
            f"It supports: {', '.join(sorted(allowed))}."
        )

    # Failing loudly beats silently charging for something other than what the
    # .env asked for. 1080P is 6s-only on every current model.
    if duration not in allowed[resolution]:
        options = " or ".join(f"{d}" for d in sorted(allowed[resolution]))
        raise DanceError(
            f"{VIDEO_MODEL} at {resolution} only supports MINIMAX_DURATION={options}, "
            f"not {duration}."
        )

    return duration, resolution


def _describe_dance(driving_video_path, job_id):
    """
    Turn a visitor's clip into a text description of the dance.

    MiniMax i2v has no driving-video input, so this is how their clip is used at
    all. ffmpeg tiles a few frames into one image and the vision model reads it.
    """
    from .minimax_image import describe_image

    if not _have_ffmpeg():
        raise DanceError(
            "Using your own dance clip needs ffmpeg installed on the booth "
            "laptop, so the video can be read. Install ffmpeg and restart, pick "
            "a built-in template instead, or switch to DANCE_PROVIDER=replicate."
        )

    montage = os.path.join(OUTPUT_DIR, f"{job_id}_frames.jpg")
    cmd = [
        "ffmpeg", "-y", "-t", "6", "-i", driving_video_path,
        "-frames:v", "1", "-vf", "fps=1,scale=360:-2,tile=3x2", montage,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except Exception as e:
        raise DanceError(f"Could not read that video file: {str(e)[:150]}") from e

    try:
        with open(montage, "rb") as f:
            frames = (f.read(), "image/jpeg")
        try:
            description = describe_image(
                frames,
                "These are frames from a dance video, in order. In under 70 "
                "words, describe the dance movements: the style, the footwork, "
                "what the arms and hips do, and the energy level. Describe only "
                "the movement, not the people or the background. Reply with the "
                "description only.",
            )
        except MinimaxError as e:
            raise DanceError(f"Could not interpret the dance in that clip: {e}") from e
    finally:
        if os.path.exists(montage):
            try:
                os.remove(montage)
            except OSError:
                pass

    return description


def _generate_minimax(person_image, template, driving_video_path, job_id):
    duration, resolution = _video_settings()

    if driving_video_path:
        movement = _describe_dance(driving_video_path, job_id)
        prompt = (
            f"The person in the image dances. {movement} "
            "One continuous shot. [Static shot]"
        )
        note = (
            "Your clip was used as a style reference, so the moves match its "
            "energy rather than copying it exactly."
        )
    else:
        prompt = f"{template['prompt']} One continuous shot. [Static shot]"
        note = ""

    payload = {
        "model": VIDEO_MODEL,
        "prompt": prompt[:VIDEO_PROMPT_LIMIT],
        "first_frame_image": data_uri(person_image),
        "duration": duration,
        "resolution": resolution,
        "prompt_optimizer": True,
    }

    print(f"[Dance/minimax] Submitting to {VIDEO_MODEL} "
          f"({duration}s @ {resolution}, billed per clip)...")
    try:
        created = post_json(
            "/v1/video_generation", payload, timeout=120,
            context="MiniMax video generation",
        )
    except MinimaxError as e:
        raise DanceError(str(e)) from e

    task_id = created.get("task_id")
    if not task_id:
        raise DanceError("MiniMax accepted the request but returned no task ID.")

    file_id, direct_url = _poll_minimax(task_id)
    if not direct_url:
        direct_url = _minimax_download_url(file_id)

    result = _download_video(direct_url, job_id, "minimax", template)
    result["note"] = note
    return result


def _poll_minimax(task_id, timeout=None):
    """
    Poll until the task finishes. Returns (file_id, direct_url).

    Newer MiniMax models hand back a ready-to-use URL in the status response;
    older ones return a file_id that has to be exchanged separately. Both shapes
    are handled so this doesn't break when an account is on either.
    """
    timeout = timeout or int(os.getenv("MINIMAX_TIMEOUT", 600))
    deadline = time.time() + timeout
    delay = 5

    while True:
        try:
            status_body = get_json(
                "/v1/query/video_generation", {"task_id": task_id}, timeout=60,
                context="MiniMax status check",
            )
        except MinimaxError as e:
            raise DanceError(str(e)) from e

        status = (status_body.get("status") or "").lower()

        if status == "success":
            file_id = status_body.get("file_id")
            content = status_body.get("content")
            direct_url = content.get("url") if isinstance(content, dict) else None
            if not file_id and not direct_url:
                raise DanceError(
                    "MiniMax reported success but returned no video reference."
                )
            return file_id, direct_url

        if status == "fail":
            reason = (status_body.get("base_resp") or {}).get("status_msg") or "no detail"
            raise DanceError(f"MiniMax could not generate this video ({reason}).")

        if status not in ("preparing", "queueing", "processing", ""):
            raise DanceError(f"MiniMax returned an unexpected status '{status}'.")

        if time.time() > deadline:
            raise DanceError(
                f"MiniMax is still working after {timeout}s. The generation may "
                "still finish - check the MiniMax console before retrying, so "
                "you don't pay twice."
            )

        time.sleep(delay)
        delay = min(delay + 2, 15)  # back off; renders take 1-5 minutes


def _minimax_download_url(file_id):
    try:
        body = get_json(
            "/v1/files/retrieve", {"file_id": file_id}, timeout=60,
            context="MiniMax file retrieve",
        )
    except MinimaxError as e:
        raise DanceError(str(e)) from e

    url = (body.get("file") or {}).get("download_url")
    if not url:
        raise DanceError("MiniMax returned no download URL for the finished video.")
    return url


def minimax_preflight(check_key=True):
    """
    Cheap readiness check for /api/health - validates the .env video settings
    without submitting a (billed) generation.

    check_key=False skips the credential probe, for callers that have already
    validated the same MINIMAX_API_KEY. The probe costs a fraction of a cent,
    but /api/health can be polled, so it is worth not paying for it twice.
    """
    from .minimax_client import ping

    duration, resolution = _video_settings()
    if check_key:
        try:
            ping()
        except MinimaxError as e:
            raise DanceError(str(e)) from e
    return {"model": VIDEO_MODEL, "duration": duration, "resolution": resolution}


# ---------------------------------------------------------------------------
# replicate - Wan 2.2 Animate (motion transfer)
# ---------------------------------------------------------------------------

def _generate_replicate(person_image, template, driving_video_path, job_id):
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise DanceError(
            "REPLICATE_API_TOKEN is not set. Get one at https://replicate.com/account "
            "or switch back to DANCE_PROVIDER=minimax."
        )
    if not driving_video_path or not os.path.exists(driving_video_path):
        raise DanceError(
            f"No driving video for '{template['name']}'. Motion transfer needs a "
            f"reference clip: put one at dance_templates/{template['driving_video']}, "
            "or let the visitor upload their own."
        )

    payload = {
        "input": {
            "image": data_uri(person_image),
            "video": data_uri(driving_video_path),
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


# ---------------------------------------------------------------------------
# shared
# ---------------------------------------------------------------------------

def _download_video(url, job_id, provider, template):
    out_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    try:
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
    except requests.RequestException as e:
        raise DanceError(
            f"The video was generated but could not be downloaded: {str(e)[:150]}"
        ) from e
    return {
        "video_path": out_path,
        "filename": os.path.basename(out_path),
        "provider": provider,
        "template": template["name"],
        "note": "",
    }
