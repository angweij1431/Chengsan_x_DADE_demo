import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

def init_cloudinary():
    """Initializes Cloudinary configuration."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        return True
    return False


def get_download_url(video_url):
    """
    Transforms Cloudinary video URL to force direct attachment download on mobile/desktop.
    Replaces /video/upload/ with /video/upload/fl_attachment/
    """
    if not video_url:
        return ""
    if "/video/upload/" in video_url and "/fl_attachment/" not in video_url:
        return video_url.replace("/video/upload/", "/video/upload/fl_attachment/")
    return video_url


def upload_video(video_path):
    """
    Uploads a video file to Cloudinary and returns secure URL.
    Falls back gracefully if Cloudinary credentials are not set.
    """
    if init_cloudinary():
        try:
            print(f"[Cloudinary] Uploading '{video_path}'...")
            result = cloudinary.uploader.upload(
                video_path,
                resource_type="video"
            )
            video_url = result.get("secure_url", result.get("url"))
            print("[Cloudinary] Upload successful:", video_url)
            return video_url
        except Exception as e:
            print(f"[Cloudinary Error] Upload failed ({e}). Returning local reference.")

    # Local fallback path for development mode without Cloudinary credentials
    filename = os.path.basename(video_path)
    return f"/static/videos/{filename}"