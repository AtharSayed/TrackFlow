from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from app.services.user_service import create_user

user_bp = Blueprint('user', __name__)

# Root route
@user_bp.route('/')
def home():
    return redirect(url_for('user.user_details_page', user_id='default'))

# User details page
@user_bp.route('/user/<user_id>')
def user_details_page(user_id):
    return render_template('user_details.html', user_id=user_id)

# API to create a user
@user_bp.route('/api/users', methods=['POST'])
def create_user_route():
    user_data = request.json
    result = create_user(user_data)
    return jsonify(result)