# QR code generation logic
import qrcode
import os

def generate_qr_code(user_id):
    qr_data = f"http://yourapp.com/user/{user_id}"
    qr_img = qrcode.make(qr_data)
    os.makedirs("app/static/qr_codes", exist_ok=True)
    qr_img.save(f"app/static/qr_codes/{user_id}.png")
    return f"/static/qr_codes/{user_id}.png"