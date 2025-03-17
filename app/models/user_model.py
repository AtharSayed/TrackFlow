# User model and schema
from datetime import datetime
from app import db

class User:
    @staticmethod
    def create(user_data):
        user_data["createdAt"] = datetime.now()
        user_data["defaultZone"] = "Entrance"
        return db.users.insert_one(user_data)