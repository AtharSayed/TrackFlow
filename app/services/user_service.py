# User-related business logic
from app.models.user_model import User
from app.utils.qr_code_generator import generate_qr_code

def create_user(user_data):
    result = User.create(user_data)
    user_id = str(result.inserted_id)
    qr_code_url = generate_qr_code(user_id)
    return {"message": "User created successfully!", "qrCodeUrl": qr_code_url}