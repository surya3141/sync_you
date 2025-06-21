# Import necessary libraries
from flask import Flask, request, jsonify
from flask_cors import CORS # For handling Cross-Origin Resource Sharing (important for frontend communication)
import firebase_admin
from firebase_admin import credentials, firestore, auth # auth is for server-side user management if needed
import google.generativeai as genai
import os # To access environment variables for sensitive info
import json # Added for parsing JSON from environment variable

# --- Firebase Admin SDK Initialization ---
# IMPORTANT: Replace 'path/to/your/serviceAccountKey.json' with the the actual content from your Firebase service account key file.
# For production, it's safer to store the JSON content in an environment variable or secure secret management.
# For local development, a file path is fine if you download the JSON, but environment variable is better.
try:
    # Attempt to initialize Firebase from an environment variable first
    firebase_config_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    if firebase_config_json:
        cred_dict = json.loads(firebase_config_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase Admin SDK initialized successfully from environment variable.")
    else:
        # Fallback for local development if environment variable is not set (e.g., using a local file)
        # In a real deployed app, you would ONLY use environment variables for keys.
        # This path below needs to be the actual path to your downloaded JSON key file.
        # For a GitHub repo, this file should NOT be committed.
        print("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not found. Attempting to initialize from file (for local dev only).")
        cred = credentials.Certificate('path/to/your/serviceAccountKey.json') # *** CHANGE THIS PATH FOR LOCAL TESTING ***
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase Admin SDK initialized successfully from file path.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    db = None # Set db to None if initialization failed


# --- Gemini API Configuration ---
# IMPORTANT: Store your Gemini API key securely, preferably as an environment variable.
# NEVER hardcode API keys in production code.
gemini_api_key = os.environ.get('GEMINI_API_KEY')
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel('gemini-2.0-flash') # Or 'gemini-pro' for more robust text generation
    print("Gemini API configured successfully.")
else:
    print("GEMINI_API_KEY environment variable not found. Gemini API not configured.")
    gemini_model = None # Set model to None if not configured

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes, allowing your React frontend to connect

# Helper to get current server timestamp for Firestore
def get_server_timestamp():
    return firestore.SERVER_TIMESTAMP

# Helper to map mood emojis to numerical values (matching frontend)
def get_mood_value(mood_emoji):
    mood_map = {
        '😊': 5,
        '😀': 4,
        '😐': 3,
        '😔': 2,
        '😢': 1,
        '😡': 1,
        '😴': 2,
        '🤪': 4,
    }
    return mood_map.get(mood_emoji, 3) # Default to neutral

# Set the APP_ID for Flask config. This uses the CANVAS_APP_ID from environment,
# falling back to 'default-app-id' if not set.
app.config['APP_ID'] = os.environ.get('CANVAS_APP_ID', 'default-app-id')


# --- AUTHENTICATION (Conceptual - for a full app, typically frontend sends ID token) ---
# For this Flask app, we'll assume the frontend has already authenticated with Firebase
# and sends the userId in requests. For a real server-side setup, you'd verify Firebase ID tokens.
# A simplified example:
@app.route('/api/auth/current_user', methods=['GET'])
def get_current_user_id():
    """
    Conceptual endpoint: In a real app, this might verify a Firebase ID token
    sent from the client and return the authenticated user's UID.
    For this example, we'll just return a placeholder or expect userId from client.
    """
    # This is highly simplified. In a real scenario, the client would send an ID token
    # in the Authorization header, and the backend would verify it using:
    # id_token = request.headers.get('Authorization').split('Bearer ')[1]
    # decoded_token = auth.verify_id_token(id_token)
    # uid = decoded_token['uid']
    # For now, we'll just indicate a successful connection.
    return jsonify({"message": "Backend ready for user interactions (assuming client-side Firebase Auth).", "status": "ok"}), 200


# --- USER SETTINGS ENDPOINTS ---
@app.route('/api/user/settings/<user_id>', methods=['GET'])
def get_user_settings(user_id):
    if not db: return jsonify({"error": "Firebase not initialized."}), 500
    try:
        settings_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/userSettings').document('settings')
        settings_doc = settings_ref.get()
        if settings_doc.exists:
            return jsonify(settings_doc.to_dict()), 200
        else:
            return jsonify({"hasAgreedToTerms": False, "wellWishers": []}), 200 # Default empty settings
    except Exception as e:
        print(f"Error fetching user settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/settings/<user_id>', methods=['POST'])
def update_user_settings(user_id):
    if not db: return jsonify({"error": "Firebase not initialized."}), 500
    data = request.json
    if not data:
        return jsonify({"error": "No data provided."}), 400
    try:
        settings_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/userSettings').document('settings')
        settings_ref.set(data, merge=True)
        return jsonify({"message": "Settings updated successfully"}), 200
    except Exception as e:
        print(f"Error updating user settings: {e}")
        return jsonify({"error": str(e)}), 500

# --- MOOD LOGGING ENDPOINTS ---
@app.route('/api/moods/<user_id>', methods=['POST'])
def add_mood_log(user_id):
    if not db: return jsonify({"error": "Firebase not initialized."}), 500
    data = request.json
    mood = data.get('mood')
    if not mood:
        return jsonify({"error": "Mood is required"}), 400

    try:
        # Add to private mood logs
        private_mood_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/moodLogs')
        private_mood_ref.add({
            "mood": mood,
            "timestamp": get_server_timestamp(),
            "userId": user_id
        })

        # Add to public mood board
        public_mood_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/public/data/publicMoods')
        public_mood_ref.add({
            "mood": mood,
            "timestamp": get_server_timestamp(),
            "userId": user_id # Keep userId for now, consider anonymizing in production
        })

        # Trigger check for prolonged depression (can be a background task in production)
        # For this demo, it's illustrative. In a real app, this would be asynchronous.
        # You'd query recent moods from Firestore here or from a different service.
        # This demo doesn't actually send emails, just prints to console.
        user_settings = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/userSettings').document('settings').get()
        if user_settings.exists:
            settings_data = user_settings.to_dict()
            if settings_data.get('hasAgreedToTerms') and settings_data.get('wellWishers'):
                # In a real app, you'd trigger a background job to check historical moods and notify.
                print(f"Simulating check for prolonged depression for user {user_id} and potential notification to well-wishers: {settings_data.get('wellWishers')}")


        return jsonify({"message": "Mood logged successfully"}), 201
    except Exception as e:
        print(f"Error adding mood log: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/moods/<user_id>/<mood_id>', methods=['DELETE'])
def delete_mood_log(user_id, mood_id):
    if not db: return jsonify({"error": "Firebase not initialized."}), 500
    try:
        doc_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/moodLogs').document(mood_id)
        doc_ref.delete()
        return jsonify({"message": "Mood log deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting mood log: {e}")
        return jsonify({"error": str(e)}), 500


# --- JOURNALING ENDPOINTS ---
@app.route('/api/journals/<user_id>', methods=['POST'])
def add_journal_entry(user_id):
    if not db: return jsonify({"error": "Firebase not initialized."}), 500
    data = request.json
    entry = data.get('entry')
    if not entry or len(entry.strip()) < 10 or len(entry.strip()) > 2000:
        return jsonify({"error": "Journal entry must be between 10 and 2000 characters."}), 400

    try:
        journal_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/journalEntries')
        journal_ref.add({
            "entry": entry.strip(),
            "timestamp": get_server_timestamp(),
            "userId": user_id
        })
        return jsonify({"message": "Journal entry saved successfully"}), 201
    except Exception as e:
        print(f"Error adding journal entry: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/journals/<user_id>/<journal_id>', methods=['PUT'])
def update_journal_entry(user_id, journal_id):
    if not db: return jsonify({"error": "Firebase not initialized."}), 500
    data = request.json
    entry = data.get('entry')
    if not entry or len(entry.strip()) < 10 or len(entry.strip()) > 2000:
        return jsonify({"error": "Journal entry must be between 10 and 2000 characters."}), 400

    try:
        doc_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/journalEntries').document(journal_id)
        doc_ref.update({
            "entry": entry.strip(),
            "updatedAt": get_server_timestamp()
        })
        return jsonify({"message": "Journal entry updated successfully"}), 200
    except Exception as e:
        print(f"Error updating journal entry: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/journals/<user_id>/<journal_id>', methods=['DELETE'])
def delete_journal_entry(user_id, journal_id):
    if not db: return jsonify({"error": "Firebase not initialized."}), 500
    try:
        doc_ref = db.collection(f'artifacts/{app.config["APP_ID"]}/users/{user_id}/journalEntries').document(journal_id)
        doc_ref.delete()
        return jsonify({"message": "Journal entry deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting journal entry: {e}")
        return jsonify({"error": str(e)}), 500

# --- AI INTEGRATION ENDPOINTS ---
@app.route('/api/ai/summarize_journal', methods=['POST'])
def summarize_journal():
    if not gemini_model: return jsonify({"error": "Gemini API not configured."}), 500
    data = request.json
    journal_text = data.get('text')
    if not journal_text:
        return jsonify({"error": "Journal text is required for summarization."}), 400

    try:
        prompt = f"Summarize the following journal entry concisely: \"{journal_text}\""
        response = gemini_model.generate_content(prompt)
        summary = response.text
        return jsonify({"summary": summary}), 200
    except Exception as e:
        print(f"Error summarizing journal: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/coping_suggestion', methods=['POST'])
def get_ai_coping_suggestion():
    if not gemini_model: return jsonify({"error": "Gemini API not configured."}), 500
    data = request.json
    mood = data.get('mood')
    if not mood:
        return jsonify({"error": "Mood is required for coping suggestion."}), 400

    try:
        prompt = f"Given that someone is feeling {mood}, provide a short, positive coping suggestion or a thoughtful insight (max 50 words)."
        response = gemini_model.generate_content(prompt)
        suggestion = response.text
        return jsonify({"suggestion": suggestion}), 200
    except Exception as e:
        print(f"Error getting coping suggestion: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/chat', methods=['POST'])
def chat_with_ai():
    if not gemini_model: return jsonify({"error": "Gemini API not configured."}), 500
    data = request.json
    user_message = data.get('message')
    if not user_message:
        return jsonify({"error": "Message is required for chat."}), 400

    try:
        # You might want to maintain chat history on the client and send it here
        # For simplicity, this example just takes the latest message
        response = gemini_model.generate_content(user_message)
        ai_response = response.text
        return jsonify({"response": ai_response}), 200
    except Exception as e:
        print(f"Error during AI chat: {e}")
        return jsonify({"error": str(e)}), 500


# --- RUN THE FLASK APP ---
if __name__ == '__main__':
    # Load environment variables explicitly for local run, as they might not be set in shell
    from dotenv import load_dotenv
    load_dotenv()

    # Re-read APP_ID after loading .env
    app.config['APP_ID'] = os.environ.get('CANVAS_APP_ID', 'default-app-id')
    print(f"Flask app running with APP_ID: {app.config['APP_ID']}")
    app.run(debug=True, port=5000) # Run on port 5000, debug=True for development (disable in production)
