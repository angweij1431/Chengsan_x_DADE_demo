import io
import base64
import qrcode
from PIL import Image

def generate_qr_code(data_url, output_path=None):
    """
    Generates a QR Code for data_url.
    - If output_path is provided, saves image file to disk.
    - Returns (image_path, base64_uri)
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )

    qr.add_data(data_url)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white")

    if output_path:
        qr_image.save(output_path)
        print(f"[QR Code] Saved QR code image to '{output_path}'")

    # Generate base64 data URI for direct web image rendering
    buffered = io.BytesIO()
    qr_image.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode('utf-8')
    base64_uri = f"data:image/png;base64,{base64_data}"

    return output_path, base64_uri


if __name__ == "__main__":
    test_url = "https://res.cloudinary.com/demo/video/upload/fl_attachment/sample.mp4"
    path, b64 = generate_qr_code(test_url, "video_qr.png")
    print("Test QR code generated successfully!")