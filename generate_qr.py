import qrcode

# Your Cloudinary video URL
video_url = "https://res.cloudinary.com/fqcmh6bx/video/upload/v1787986431/rwhg6srdqaij8pjpplp2.mp4"

# Create QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4
)

qr.add_data(video_url)
qr.make(fit=True)

# Generate image
qr_image = qr.make_image()

# Save QR code
qr_image.save("video_qr.png")

print("QR code generated successfully!")
print("Saved as: video_qr.png")