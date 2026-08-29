import os
import qrcode

from generate_video import create_video
from upload_video import upload_video
from database import save_video


# ==========================================
# 1. Generate the video
# ==========================================

print("\n--- STEP 1: Generating video ---")

video_path = create_video()

print("Video created:", video_path)


# ==========================================
# 2. Upload video to Cloudinary
# ==========================================

print("\n--- STEP 2: Uploading video ---")

video_url = upload_video(video_path)


# ==========================================
# 3. Save video URL to Supabase
# ==========================================

print("\n--- STEP 3: Saving to database ---")

filename = os.path.basename(video_path)

video_id = save_video(
    filename,
    video_url
)


# ==========================================
# 4. Create download URL
# ==========================================

download_url = video_url.replace(
    "/video/upload/",
    "/video/upload/fl_attachment/"
)


# ==========================================
# 5. Generate QR code
# ==========================================

print("\n--- STEP 4: Generating QR code ---")

qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4
)

qr.add_data(download_url)
qr.make(fit=True)

qr_image = qr.make_image()

qr_path = "video_qr.png"

qr_image.save(qr_path)


# ==========================================
# 6. Finished
# ==========================================

print("\n===================================")
print("        PROJECT COMPLETE!")
print("===================================")

print("Video:", video_path)
print("Cloudinary URL:", video_url)
print("Database ID:", video_id)
print("QR Code:", qr_path)

print("\nScan video_qr.png with your phone.")
print("The MP4 should be downloaded.")