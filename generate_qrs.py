import os
import qrcode

# Setup directory
base_dir = os.path.dirname(os.path.abspath(__file__))
qr_dir = os.path.join(base_dir, 'core', 'static', 'qr_codes')
os.makedirs(qr_dir, exist_ok=True)

# Generate 8 QR codes
# Since it's a local test environment, we'll assume the URL is just the root path /?table=N
base_url = "http://127.0.0.1:8000/?table="

for i in range(1, 9):
    url = f"{base_url}{i}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_path = os.path.join(qr_dir, f"table_{i}.png")
    img.save(img_path)
    print(f"Generated QR Code for Table {i} at {img_path}")
