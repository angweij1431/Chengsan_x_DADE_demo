import os
import uuid
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv

from generate_video import generate_ai_dance_video, trim_video_to_8s
from upload_video import upload_video, get_download_url
from database import save_video, get_video
from generate_qr import generate_qr_code

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
OUTPUT_FOLDER = os.path.join(os.getcwd(), "videos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------------------------------------------------------
# FRONTEND ROUTE
# -------------------------------------------------------------------
@app.route("/")
def index():
    """Serves the main 5-step SPA template (index.html)."""
    return send_from_directory(".", "index.html")

# -------------------------------------------------------------------
# REST API ENDPOINTS
# -------------------------------------------------------------------

@app.route("/api/upload-video", methods=["POST"])
def upload_source_video():
    """
    Endpoint for uploading source TikTok / dancing videos.
    Checks duration, auto-trims to 8 seconds if exceeded, and returns notification details.
    """
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "Empty filename"}), 400

    filename = f"upload_{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Trim to 8s maximum duration
    trimmed_path, was_trimmed = trim_video_to_8s(file_path, max_duration=8.0)
    final_filename = os.path.basename(trimmed_path)

    response_data = {
        "status": "success",
        "filename": final_filename,
        "file_url": f"/uploads/{final_filename}",
        "was_trimmed": was_trimmed,
        "message": "Video exceeds 8 seconds. Automatically trimmed to first 8 seconds!" if was_trimmed else "Video uploaded successfully!"
    }
    return jsonify(response_data)


@app.route("/api/process-dance", methods=["POST"])
def process_dance():
    """
    Endpoint for processing dance video generation:
    1. Triggers AI Body-Swapping pipeline (generate_ai_dance_video)
    2. Uploads output video to Cloudinary (upload_video)
    3. Saves video metadata to Firebase Firestore / DB (save_video)
    4. Generates mobile QR code (generate_qr_code)
    """
    data = request.json or {}
    dance_style = data.get("dance_style", "cyber_hiphop")
    source_media = data.get("source_media", "")
    user_media = data.get("user_media", "")

    video_id = f"dance_{uuid.uuid4().hex[:8]}"
    output_path = os.path.join(OUTPUT_FOLDER, f"{video_id}.mp4")

    # 1. Generate Dance Video
    print(f"[API Process] Generating dance video for ID: {video_id}, style: {dance_style}")
    generated_file = generate_ai_dance_video(
        source_dance_path=source_media,
        user_person_path=user_media,
        dance_style=dance_style,
        output_path=output_path
    )

    # 2. Upload to Cloudinary
    video_url = upload_video(generated_file)
    download_url = get_download_url(video_url)

    # 3. Save to Firebase Firestore / DB
    filename = os.path.basename(generated_file)
    db_id = save_video(filename, video_url, video_id=video_id)

    # 4. Generate Download QR Code
    # QR code points to the direct mobile download endpoint or Cloudinary download link
    qr_target_url = request.host_url.rstrip('/') + f"/download/{video_id}"
    qr_file_path = os.path.join(OUTPUT_FOLDER, f"{video_id}_qr.png")
    _, qr_code_base64 = generate_qr_code(qr_target_url, output_path=qr_file_path)

    return jsonify({
        "status": "success",
        "video_id": video_id,
        "filename": filename,
        "video_url": video_url,
        "download_url": download_url,
        "qr_target_url": qr_target_url,
        "qr_code_base64": qr_code_base64
    })


@app.route("/api/video/<video_id>", methods=["GET"])
def get_video_info(video_id):
    """Retrieves video metadata from Firebase Firestore / DB."""
    video = get_video(video_id)
    if not video:
        return jsonify({"status": "error", "message": "Video not found"}), 404
    
    video_url = video.get("video_url", "")
    download_url = get_download_url(video_url)
    return jsonify({
        "status": "success",
        "video": video,
        "download_url": download_url
    })


@app.route("/download/<video_id>", methods=["GET"])
def direct_download(video_id):
    """
    Direct mobile download redirect endpoint.
    When mobile users scan the QR code, this endpoint redirects directly to Cloudinary's MP4 attachment download link!
    """
    video = get_video(video_id)
    if video and "video_url" in video:
        download_url = get_download_url(video["video_url"])
        return redirect(download_url)
    return jsonify({"status": "error", "message": "Video unavailable for download"}), 404


@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/videos/<path:filename>")
def serve_videos(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"==================================================")
    print(f" GrooveAI Server Running on http://localhost:{port}")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=True)