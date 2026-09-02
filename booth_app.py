"""
Booth prototype server.

Three stations:
  1. /api/dance  photo -> dance video (template, or the visitor's own clip)
  2. /api/edit   photo + reference photo -> edited image
  3. /api/scene  photo + environment photo -> composited scene

Run:  python booth_app.py     then open http://localhost:5000

All three stations run on one GEMINI_API_KEY:
  - Stations 2 and 3 use a Gemini image model, which has a free tier.
  - Station 1 uses Gemini Omni 1.1 Flash, which does NOT. Billing must be
    enabled on the key's project, or set DANCE_PROVIDER=mock to run offline.
"""

import io
import os
import socket
import uuid

from dotenv import load_dotenv
from flask import (
    Flask, jsonify, make_response, request, send_file, send_from_directory
)
from flask_cors import CORS
from PIL import Image

from booth import limits, prompts
from booth.gemini_image import ImageGenError, compose_image, resolve_model
from booth.video_dance import (
    TEMPLATES, DanceError, generate_dance, get_provider, omni_preflight
)
from generate_qr import generate_qr_code

load_dotenv()

OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB per request
CORS(app)

SESSION_COOKIE = "booth_session"
MAX_INPUT_DIM = int(os.getenv("MAX_INPUT_DIM", 1536))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def session_id():
    return request.cookies.get(SESSION_COOKIE) or uuid.uuid4().hex


def with_session(response, sid):
    response.set_cookie(SESSION_COOKIE, sid, max_age=60 * 60 * 12, samesite="Lax")
    return response


def read_image(file_storage, field):
    """
    Decode an upload, strip EXIF rotation, downscale, re-encode as JPEG.

    Phone photos are routinely 12 MP and sideways. Normalising here keeps
    requests fast and stops the model seeing rotated faces.
    """
    if not file_storage or not file_storage.filename:
        raise ValueError(f"Missing '{field}'. Please choose a photo.")
    try:
        image = Image.open(file_storage.stream)
    except Exception as e:
        raise ValueError(f"'{field}' isn't a readable image file.") from e

    try:
        from PIL import ImageOps
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    image = image.convert("RGB")
    image.thumbnail((MAX_INPUT_DIM, MAX_INPUT_DIM), Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue(), "image/jpeg"


def save_output(data, mime_type, prefix):
    ext = ".png" if "png" in mime_type else ".jpg"
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)
    return filename


def lan_host():
    """
    Best-guess LAN address, so a phone scanning the QR reaches this laptop.
    localhost in a QR code is useless - the phone would resolve it to itself.
    """
    override = os.getenv("BOOTH_PUBLIC_HOST", "").strip()
    if override:
        return override.rstrip("/")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
    except Exception:
        ip = "localhost"
    return f"http://{ip}:{os.getenv('PORT', 5000)}"


def result_payload(filename, extra=None):
    share_url = f"{lan_host()}/download/{filename}"
    _, qr_base64 = generate_qr_code(share_url)
    payload = {
        "status": "success",
        "filename": filename,
        "view_url": f"/outputs/{filename}",
        "download_url": f"/download/{filename}",
        "share_url": share_url,
        "qr_code_base64": qr_base64,
    }
    if extra:
        payload.update(extra)
    return payload


def fail(message, code=400, scope=None):
    body = {"status": "error", "message": message}
    if scope:
        body["scope"] = scope
    return jsonify(body), code


# ---------------------------------------------------------------------------
# pages & config
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "booth.html")


@app.route("/api/config")
def config():
    sid = session_id()
    body = {
        "dance_provider": get_provider(),
        "dance_templates": [
            {k: t[k] for k in ("id", "name", "emoji")} for t in TEMPLATES
        ],
        "edit_presets": [
            {k: p[k] for k in ("id", "name", "emoji")} for p in prompts.EDIT_PRESETS
        ],
        "scene_presets": [
            {k: p[k] for k in ("id", "name", "emoji")} for p in prompts.SCENE_PRESETS
        ],
        "limits": {
            action: limits.remaining(sid, action) for action in limits.DEFAULT_LIMITS
        },
    }
    return with_session(make_response(jsonify(body)), sid)


@app.route("/api/health")
def health():
    provider = get_provider()
    report = {"dance_provider": provider, "gemini": "unknown", "dance": "unknown"}

    try:
        report["gemini_image_model"] = resolve_model()
        report["gemini"] = "ok"
    except Exception as e:
        report["gemini"] = f"error: {e}"

    # Station 1 is checked separately: it is the paid path, and a booth can run
    # usefully with images working and video down (or the other way round).
    if provider == "gemini_omni":
        try:
            report["omni"] = omni_preflight()
            report["dance"] = "ok"
        except Exception as e:
            report["dance"] = f"error: {e}"
    else:
        report["dance"] = f"ok ({provider}, not preflighted)"

    report["ok"] = report["gemini"] == "ok" and not report["dance"].startswith("error")
    return jsonify(report), (200 if report["ok"] else 503)


@app.route("/api/stats")
def stats():
    return jsonify(limits.stats_today())


# ---------------------------------------------------------------------------
# station 1 - dance video
# ---------------------------------------------------------------------------

@app.route("/api/dance", methods=["POST"])
def api_dance():
    sid = session_id()
    custom_clip = request.files.get("dance_video")
    action = "dance_custom" if custom_clip and custom_clip.filename else "dance_template"

    # Validate before consuming quota, so a forgotten photo doesn't cost a go.
    try:
        photo = read_image(request.files.get("photo"), "photo")
    except ValueError as e:
        return with_session(make_response(fail(str(e))), sid)

    try:
        limits.check_and_consume(sid, action)
    except limits.RateLimited as e:
        return with_session(make_response(fail(str(e), 429, e.scope)), sid)

    driving_path = None
    if action == "dance_custom":
        driving_path = os.path.join(UPLOAD_DIR, f"drive_{uuid.uuid4().hex[:8]}.mp4")
        custom_clip.save(driving_path)

    try:
        result = generate_dance(
            person_image=photo,
            template_id=request.form.get("template_id") or TEMPLATES[0]["id"],
            driving_video_path=driving_path,
        )
    except DanceError as e:
        limits.refund(sid, action)
        return with_session(make_response(fail(str(e), 502)), sid)
    except Exception as e:
        print(f"[Station 1] Unexpected error: {e}")
        limits.refund(sid, action)
        return with_session(make_response(fail("Dance generation failed unexpectedly.", 500)), sid)
    finally:
        if driving_path and os.path.exists(driving_path):
            os.remove(driving_path)

    payload = result_payload(
        result["filename"],
        {
            "provider": result["provider"],
            "template": result["template"],
            "note": result["note"],
            "is_video": result["filename"].lower().endswith((".mp4", ".webm")),
            "remaining": limits.remaining(sid, action),
        },
    )
    return with_session(make_response(jsonify(payload)), sid)


# ---------------------------------------------------------------------------
# stations 2 & 3 - image editing (same operation, different prompt)
# ---------------------------------------------------------------------------

def run_image_station(action, second_field, prompt_builder, aspect_ratio):
    sid = session_id()

    # Validate before consuming quota, so a missing photo doesn't cost a go.
    try:
        person = read_image(request.files.get("photo"), "photo")
        second = read_image(request.files.get(second_field), second_field)
    except ValueError as e:
        return with_session(make_response(fail(str(e))), sid)

    try:
        limits.check_and_consume(sid, action)
    except limits.RateLimited as e:
        return with_session(make_response(fail(str(e), 429, e.scope)), sid)

    prompt = prompt_builder(
        request.form.get("preset_id", ""), request.form.get("request", "")
    )

    try:
        data, mime_type = compose_image(
            prompt=prompt, images=[person, second], aspect_ratio=aspect_ratio
        )
    except ImageGenError as e:
        limits.refund(sid, action)
        return with_session(make_response(fail(str(e), 502)), sid)
    except Exception as e:
        print(f"[{action}] Unexpected error: {e}")
        limits.refund(sid, action)
        return with_session(make_response(fail("Image generation failed unexpectedly.", 500)), sid)

    filename = save_output(data, mime_type, action)
    payload = result_payload(
        filename, {"is_video": False, "remaining": limits.remaining(sid, action)}
    )
    return with_session(make_response(jsonify(payload)), sid)


@app.route("/api/edit", methods=["POST"])
def api_edit():
    return run_image_station(
        "edit_image", "reference", prompts.build_edit_prompt, "1:1"
    )


@app.route("/api/scene", methods=["POST"])
def api_scene():
    return run_image_station(
        "scene_image", "environment", prompts.build_scene_prompt, "16:9"
    )


# ---------------------------------------------------------------------------
# serving results
# ---------------------------------------------------------------------------

@app.route("/outputs/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/download/<path:filename>")
def download_output(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return fail("That file has expired or never existed.", 404)
    return send_file(path, as_attachment=True, download_name=filename)


@app.errorhandler(413)
def too_large(_):
    return fail("That file is too large. Please use a photo under 64 MB.", 413)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("=" * 62)
    print("  BOOTH PROTOTYPE")
    print(f"  Local:  http://localhost:{port}")
    print(f"  Phones: {lan_host()}")
    print(f"  Dance provider: {get_provider()}")
    try:
        print(f"  Gemini image model: {resolve_model()}")
    except Exception as e:
        print(f"  Gemini images: NOT READY -> {e}")
    if get_provider() == "gemini_omni":
        try:
            info = omni_preflight()
            print(f"  Gemini Omni: {info['model']} "
                  f"({info['duration']}s @ {info['resolution']}, BILLED PER SECOND)")
        except Exception as e:
            print(f"  Gemini Omni: NOT READY -> {e}")
    print("=" * 62)
    app.run(host="0.0.0.0", port=port, debug=True)
