import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


def upload_video(video_path):

    result = cloudinary.uploader.upload(
        video_path,
        resource_type="video"
    )

    video_url = result["secure_url"]

    print("Video uploaded successfully!")
    print("Video URL:", video_url)

    return video_url