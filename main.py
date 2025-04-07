import cv2
import numpy as np
import qrcode
import json
import pymongo
from flask import Flask, request, jsonify, render_template, url_for # Added render_template, url_for
from flask_socketio import SocketIO, emit
import pyzbar.pyzbar as pyzbar
import os
from kafka import KafkaProducer # Assuming Kafka is still part of the desired architecture
import json
import uuid
from datetime import datetime
import time

# --- Basic Configuration ---
# Set KAFKA_BROKER to None if not using Kafka
#KAFKA_BROKER = 'localhost:9092' # Or None
KAFKA_BROKER = None  # Disable Kafka temporarily for testing

#MONGO_URI = "mongodb+srv://onShore:sahu9821@cluster0.a6ot5gp.mongodb.net/?retryWrites=true&w=majority"
MONGO_URI = "mongodb://localhost:27017"
QR_FOLDER_NAME = "qr_codes" # Subfolder within static
QR_STATIC_FOLDER = os.path.join("static", QR_FOLDER_NAME)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_for_flask_socketio!' # Change this!
# Allow all origins for simplicity in dev, restrict in production
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Ensure Directories Exist ---
if not os.path.exists("static"):
    os.makedirs("static")
if not os.path.exists(QR_STATIC_FOLDER):
    os.makedirs(QR_STATIC_FOLDER)
if not os.path.exists("templates"):
    os.makedirs("templates") # Ensure templates folder exists

# --- Kafka Producer Initialization ---
producer = None
if KAFKA_BROKER:
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3,
            request_timeout_ms=10000 # Shorter timeout for quicker feedback if Kafka is down
        )
        print("Attempting Kafka connection...")
        # Quick check if connection seems okay (might not catch all issues)
        producer.send('__test_topic__', {'test': 'connection'}).get(timeout=5)
        print("Kafka Producer seems connected.")
    except Exception as e:
        print(f"WARNING: Error connecting to Kafka or sending test message: {e}")
        print("Proceeding without Kafka producer.")
        producer = None
else:
    print("Kafka broker not configured. Running without Kafka producer.")

# --- MongoDB Connection ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.crowdManagement
    users_collection = db["users"]
    reports_collection = db["reports"]
    client.admin.command('ping')
    print("MongoDB connected successfully.")
except Exception as e:
    print(f"CRITICAL: Error connecting to MongoDB: {e}")
    exit()

# --- QR Code Generation ---
def generate_qr(data, filename):
    qr = qrcode.QRCode(
        version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4,
    )
    qr.add_data(json.dumps(data, sort_keys=True))
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    filepath = os.path.join(QR_STATIC_FOLDER, filename)
    img.save(filepath)

    return url_for('static', filename=f"{QR_FOLDER_NAME}/{filename}")

# --- HTML Rendering Route ---
@app.route('/')
def dashboard():
    """Renders the main dashboard HTML page."""
    return render_template("dashboard.html", title="Crowd Management")

# --- API and Action Routes ---

# <<< --- START OF NEW REGISTER ROUTE --- >>>
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get("name")
    phone = data.get("phone")
    address = data.get("address")
    family_members = data.get("family_members", [])
    friends = data.get("friends", [])             

    if not name or not phone:
        socketio.emit('registration_error', {'message': 'Registration failed: Name and phone are mandatory.'})
        return jsonify({"error": "Name and phone are required"}), 400

    processed_family = []
    for member in family_members:
        if isinstance(member, dict) and member.get('name') and member.get('phone'):
            if member.get("is_child"):
                 member["relation"] = "child" 
                 member["age"] = member.get("age", "Unknown")
                 member["gender"] = member.get("gender", "Unknown")
                 member["description"] = member.get("description", "No description provided")
                 member.pop("is_child", None)
            else:
                member["relation"] = "family"
                member.pop("age", None)
                member.pop("gender", None)
                member.pop("description", None)
                member.pop("is_child", None)
            processed_family.append(member)
        else:
            print(f"Skipping invalid family member data: {member}")


    processed_friends = []
    for friend in friends:
         if isinstance(friend, dict) and friend.get('name') and friend.get('phone'):
             processed_friends.append(friend)
         else:
              print(f"Skipping invalid friend data: {friend}")


    unique_id = phone 
    qr_filename = f"qr_{unique_id}.png"
    qr_data = { "id": unique_id, "name": name, "phone": phone } 

    try:
        qr_web_path = generate_qr(qr_data, qr_filename)
    except Exception as e:
        print(f"Error generating QR code: {e}")
        socketio.emit('registration_error', {'message': f'Registration failed for {name}: Could not generate QR code.'})
        return jsonify({"error": "Failed to generate QR code"}), 500

    user_document = {
        "_id": unique_id,
        "name": name,
        "phone": phone,
        "address": address,
        "family_members": processed_family,
        "friends": processed_friends,
        "qr_code_path": qr_web_path,
        "registration_time": datetime.utcnow()
    }

    try:
        users_collection.replace_one({"_id": unique_id}, user_document, upsert=True)
        print(f"User {name} registered/updated successfully.")

        notification_message = f"✅ Registration Confirmed: Welcome, {name}! Phone: {phone}. QR code generated."
        # Emit success message via WebSocket
        socketio.emit('new_registration', {
            'message': notification_message,
            'user': {'name': name, 'phone': phone, 'qr_code_path': qr_web_path}
        })
        # Return success response to the fetch request
        return jsonify({
            "message": "User registered successfully",
            "qr_code_path": qr_web_path, # Send path back to JS
            "user_id": unique_id
            }), 201

    except Exception as e:
        print(f"Error inserting/updating user in MongoDB: {e}")
        socketio.emit('registration_error', {'message': f'Registration failed for {name} due to database error.'})
        return jsonify({"error": "Database operation failed"}), 500



def scan_qr_code_from_camera():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video capture device.")
        return None, "Could not open camera."

    print("Camera opened. Looking for QR code... Press 'q' to quit.")
    scanned_data = None
    error_message = "No QR code detected or user quit."
    window_name = "QR Scanner - Press 'q' to quit"

    start_time = time.time()
    timeout_seconds = 30 

    while time.time() - start_time < timeout_seconds:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            time.sleep(0.1)
            continue

        try:
            decoded_objects = pyzbar.decode(frame)
            if decoded_objects:
                obj = decoded_objects[0] 
                qr_data_raw = obj.data.decode("utf-8")
                print(f"Raw QR Data: {qr_data_raw}")
                try:
                    scanned_data_dict = json.loads(qr_data_raw)
                    if "id" in scanned_data_dict and "name" in scanned_data_dict:
                        print("Valid QR Code Scanned:", scanned_data_dict)
                        user_details = users_collection.find_one({"_id": scanned_data_dict.get("id")})
                        if user_details:
                             scanned_data = user_details
                             scanned_data["_id"] = str(scanned_data["_id"]) 
                             scanned_data.pop('registration_time', None) 
                             error_message = None 
                             break 
                        else:
                             print(f"QR valid, but user ID {scanned_data_dict.get('id')} not found in database.")
                             scanned_data = None 
                             error_message = f"User ID {scanned_data_dict.get('id')} not found."
                             # Indicate error on frame
                             points = obj.polygon
                             if len(points) == 4:
                                pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
                                cv2.polylines(frame, [pts], isClosed=True, color=(0, 165, 255), thickness=2) # Orange for warning
                                cv2.putText(frame, "User Not Found", (obj.rect.left, obj.rect.top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

                    else:
                         print("QR Code data format is invalid (missing 'id' or 'name').")
                         points = obj.polygon
                         if len(points) == 4:
                            pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
                            cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2) # Red for error
                            cv2.putText(frame, "Invalid Format", (obj.rect.left, obj.rect.top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                         scanned_data = None 

                except json.JSONDecodeError:
                    print("Scanned QR Code contains invalid JSON data.")
                    
                    points = obj.polygon
                    if len(points) == 4:
                        pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
                        cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
                        cv2.putText(frame, "Invalid JSON", (obj.rect.left, obj.rect.top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                except Exception as e:
                    print(f"An unexpected error occurred during decoding/DB fetch: {e}")
                    error_message = "Error processing QR data."
                    scanned_data = None

            # Display the frame
            cv2.imshow(window_name, frame)

        except Exception as e:
             print(f"Error during frame processing or pyzbar decoding: {e}")

        # Check for 'q' key press to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Scan cancelled by user.")
            error_message = "Scan cancelled by user."
            break

    cap.release()
    cv2.destroyAllWindows()
    # Ensure window is definitely closed (sometimes needed on some OS)
    for i in range(5):
        cv2.waitKey(1)
    print("Camera closed.")
    # Return the full user data fetched from DB, or None if failed
    return scanned_data, error_message


@app.route('/scan_qr', methods=['GET'])
def trigger_scan_qr():
    print("Attempting to scan QR code via server camera...")
    # scanned_data now contains the *full user document* from the DB if successful
    scanned_user_data, error = scan_qr_code_from_camera()

    if error:
        print(f"Scan failed: {error}")
        socketio.emit('scan_result', {'success': False, 'message': f"Scan Error: {error}"})
        # Return error to the fetch request in JS
        return jsonify({"error": error}), 400

    if scanned_user_data:
        scan_event = {
            "scan_id": str(uuid.uuid4()),
            # Send the *full user data* fetched from DB
            "scanned_user_data": scanned_user_data,
            "scan_location": request.args.get("location", "Unknown Location"),
            "scan_time": datetime.utcnow().isoformat() + "Z",
            "scanner_id": request.args.get("scanner_id", "Scanner_01")
        }

        if producer:
            try:
                producer.send('qr_scans', scan_event)
                producer.flush()
                print(f"Scan event for {scanned_user_data.get('name', 'Unknown')} sent to Kafka.")
            except Exception as e:
                print(f"WARNING: Failed to send scan event to Kafka: {e}")
                # Proceed even if Kafka fails

        notification_message = f"👀 QR Scan Success: '{scanned_user_data.get('name', 'Unknown')}' (ID: {scanned_user_data.get('_id', 'N/A')}) scanned at {scan_event['scan_location']}."
        # Send full scan event data (including full user details) via WebSocket
        socketio.emit('scan_result', {
            'success': True,
            'message': notification_message,
            'data': scan_event
        })
        # Return success to the fetch request in JS
        return jsonify({"message": "QR Code Scanned", "data": scan_event}), 200
    else:
        # Should be caught by 'error' but as fallback
        socketio.emit('scan_result', {'success': False, 'message': 'Scan Failed: No valid user data found.'})
        return jsonify({"error": "No valid user data found"}), 404


@app.route('/submit_report', methods=['POST'])
def submit_report():
    data = request.json
    # JS will now send the full 'scanned_user_data' object received via WebSocket
    scanned_user_data = data.get("scanned_user_data")
    reporter_name = data.get("reporter_name", "Anonymous")
    reporter_contact = data.get("reporter_contact", "N/A")
    last_known_location = data.get("last_known_location")
    additional_details = data.get("additional_details", "")

    if not scanned_user_data or not isinstance(scanned_user_data, dict):
        return jsonify({"error": "Valid scanned_user_data (object) is required"}), 400
    if not last_known_location:
        return jsonify({"error": "Last known location is required"}), 400

    # Extract info from the full user data object
    person_id = scanned_user_data.get("_id") # Use _id from MongoDB document
    person_name = scanned_user_data.get("name")
    person_phone = scanned_user_data.get("phone")

    if not person_id or not person_name:
         # This shouldn't happen if scan_result sends the correct object
        return jsonify({"error": "Scanned data is missing required fields (_id, name)"}), 400

    report_id = str(uuid.uuid4())
    report_time = datetime.utcnow()

    report = {
        "report_id": report_id,
        "person_id": person_id, # This should already be a string from the scan process
        "person_name": person_name,
        "person_phone": person_phone,
        # Include details from the scanned data (which came from DB)
        "family_members_at_registration": scanned_user_data.get("family_members", []),
        "friends_at_registration": scanned_user_data.get("friends", []),
        "address_at_registration": scanned_user_data.get("address"),
        "reporter_name": reporter_name,
        "reporter_contact": reporter_contact,
        "last_known_location": last_known_location,
        "additional_details": additional_details,
        "report_time": report_time, # Keep as datetime object initially
        "status": "OPEN"
    }

    try:
        # Insert into MongoDB - This adds the ObjectId _id to the 'report' dict
        insert_result = reports_collection.insert_one(report)
        print(f"Lost person report {report_id} for {person_name} saved.")

        # --- FIX: Prepare data for Kafka ---
        if producer:
            try:
                # Create a copy specifically for Kafka
                report_kafka = report.copy()

                # Convert ObjectId _id to string IN THE KAFKA COPY
                report_kafka["_id"] = str(insert_result.inserted_id)

                # Convert datetime to ISO string IN THE KAFKA COPY
                report_kafka["report_time"] = report_time.isoformat() + "Z"

                # Ensure person_id is string (should be, but double-check if issues persist)
                if not isinstance(report_kafka.get("person_id"), str):
                     report_kafka["person_id"] = str(report_kafka.get("person_id"))


                producer.send('lost_person_reports', report_kafka)
                producer.flush()
                print(f"Report {report_id} sent to Kafka.")
            except Exception as e:
                # Catch potential serialization errors specifically if needed
                # import bson # You might need pip install bson
                # if isinstance(e, TypeError) and 'ObjectId' in str(e):
                #    print(f"WARNING: Potential ObjectId serialization error for Kafka: {e}")
                # else:
                print(f"WARNING: Failed to send report to Kafka: {e}")
                # print(f"DEBUG Data for Kafka: {report_kafka}") # Uncomment for debugging

        # --- Prepare data for WebSocket / API response ---
        notification_message = (f"⚠️ New Lost Person Report ({report_id}): "
                                f"'{person_name}' (ID: {person_id}) reported missing by {reporter_name}. "
                                f"Last seen near '{last_known_location}'. Status: OPEN.")

        # Create a separate copy for the response/WebSocket if needed, or reuse 'report'
        # Since we modified 'report_kafka', let's make a clean serializable dict
        report_serializable = report.copy() # Get the original dict again
        report_serializable["_id"] = str(insert_result.inserted_id) # Convert _id
        report_serializable["report_time"] = report_time.isoformat() + "Z" # Convert datetime

        socketio.emit('new_report', {
            'message': notification_message,
            'report': report_serializable # Send serializable version
        })
        return jsonify({"message": "Lost person report submitted successfully", "report_id": report_id}), 201

    except Exception as e:
        print(f"Error submitting report for {person_name}: {e}")
        socketio.emit('report_error', {'message': f'Failed to submit report for {person_name}: {e}'})
        return jsonify({"error": "Failed to submit report", "details": str(e)}), 500


# --- API Endpoints for Fetching Data (for JS) ---
@app.route('/api/reports', methods=['GET'])
def get_reports():
    try:
        status_filter = request.args.get('status')
        query = {}
        if status_filter:
            query['status'] = status_filter.upper()

        reports = list(reports_collection.find(query).sort("report_time", pymongo.DESCENDING).limit(50))
        # Convert ObjectId and datetime for JSON response
        for report in reports:
            report['_id'] = str(report['_id'])
            if isinstance(report.get('report_time'), datetime):
                report['report_time'] = report['report_time'].isoformat() + "Z"
        return jsonify(reports), 200
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return jsonify({"error": "Failed to fetch reports"}), 500

# --- WebSocket Event Handlers (Unchanged) ---
@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)
    emit('welcome', {'message': 'Connected to Crowd Management System updates!'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

# Example endpoint for alerts from backend systems (like Spark/AI)
@app.route('/internal/alert', methods=['POST'])
def receive_internal_alert():
    alert_data = request.json
    alert_type = alert_data.get('type', 'generic_alert')
    message = alert_data.get('message', 'An internal alert was received.')
    payload = alert_data.get('payload', {})
    print(f"Received internal alert: {alert_type} - {message}")

    ai_enhanced_message = f"🚨 System Alert ({alert_type.replace('_', ' ').title()}): {message}"
    # Add specific details based on type (same logic as before)
    # ... (add if/elif for density_warning, person_located etc.) ...
    if alert_type == 'person_located':
         ai_enhanced_message = f"✅ Update: Person '{payload.get('name', 'N/A')}' possibly located near {payload.get('location', 'N/A')}."
         report_id = payload.get('report_id')
         if report_id:
             try:
                 reports_collection.update_one(
                     {"report_id": report_id},
                     {"$set": {"status": "POTENTIALLY_LOCATED", "last_update_time": datetime.utcnow()}}
                 )
                 ai_enhanced_message += f" Report {report_id} status updated."
             except Exception as e:
                 print(f"Error updating report status for {report_id}: {e}")


    socketio.emit(alert_type, {'message': ai_enhanced_message, 'details': payload})
    return jsonify({"status": "Alert received and broadcasted"}), 200

# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    # Use host='0.0.0.0' to be accessible on your network
    # Ensure debug is False or use a production-ready WSGI server like gunicorn/waitress for deployment
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)