import os
import qrcode

# Setup directory
base_dir = os.path.dirname(os.path.abspath(__file__))
qr_dir = os.path.join(base_dir, 'core', 'static', 'review_qrs')
os.makedirs(qr_dir, exist_ok=True)

# Generate 8 QR codes for review
base_url = "http://127.0.0.1:8000/review/"

for i in range(1, 9):
    url = base_url
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="gold") # Gold for premium feel
    img_path = os.path.join(qr_dir, f"review_{i}.png")
    img.save(img_path)
    print(f"Generated Review QR Code {i} at {img_path}")
