# Scan-related business logic
from app.models.scan_model import Scan

def create_scan(scan_data):
    result = Scan.create(scan_data)
    return {"message": "Scan successful!"}