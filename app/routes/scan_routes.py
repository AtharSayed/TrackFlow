# Routes for scan-related operations
from flask import Blueprint, request, jsonify
from app.services.scan_service import create_scan

scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/api/scans', methods=['POST'])
def create_scan_route():
    scan_data = request.json
    result = create_scan(scan_data)
    return jsonify(result)