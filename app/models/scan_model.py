# Scan model and schema
from datetime import datetime
from app import db

class Scan:
    @staticmethod
    def create(scan_data):
        scan_data["timestamp"] = datetime.now()
        return db.scans.insert_one(scan_data)