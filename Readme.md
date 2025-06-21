# SyncYou Mental Well-being App - Python Flask Backend

This repository contains the Python Flask backend for the "SyncYou" mental well-being application. This backend serves as the API layer, handling data persistence with Firebase Firestore, integrating AI capabilities via the Google Gemini API, and managing sensitive logic securely.

This backend was entirely developed and committed using only a mobile device's browser in desktop mode, showcasing the flexibility of cloud-based development.

## Features

-   **Firebase Firestore Integration:**
    -   Secure storage and retrieval of user-specific mood logs and journal entries.
    -   Management of user settings, including consent for data sharing and a list of designated "well-wishers."
    -   Contribution to a public, anonymized mood board for community insights.
-   **Google Gemini API Integration:**
    -   **Journal Summarization:** Provides concise summaries of journal entries.
    -   **Mood-Based Coping Suggestions:** Offers positive suggestions based on a user's logged mood.
    -   **AI Chatbot:** An interactive assistant for general well-being queries.
-   **Simulated Medical/Psychological Alert:**
    -   Logic to detect prolonged periods of depressed mood.
    -   If consent is given and well-wishers are designated, simulates a notification to them for support.
-   **Secure API Key Handling:** Utilizes environment variables to keep sensitive API keys out of the codebase.
-   **CORS Enabled:** Allows secure communication with a separate frontend application (like a React app).

## Architecture

This Flask backend serves as the core logic for the SyncYou application, communicating with a separate frontend application (e.g., a React app).
## Setup and Running Locally

To run this Flask backend locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/SyncYou-Flask-Backend.git](https://github.com/YOUR_USERNAME/SyncYou-Flask-Backend.git)
    cd SyncYou-Flask-Backend
    ```
    (Replace `YOUR_USERNAME` with your GitHub username).

2.  **Create a Python Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    ```
    * On Windows: `.\venv\Scripts\activate`
    * On macOS/Linux: `source venv/bin/activate`

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Firebase Service Account Key:**
    * Go to your Firebase project settings in the Firebase Console: `Project settings` -> `Service accounts` -> `Generate new private key`. This will download a JSON file.
    * **Important:** For local development, you have two options (for production, use environment variables):
        * **Option A (Simpler for local):** Place the downloaded JSON file (e.g., `my-firebase-key.json`) in the same directory as `app.py`. Then, in `app.py`, change the line `cred = credentials.Certificate('path/to/your/serviceAccountKey.json')` to `cred = credentials.Certificate('my-firebase-key.json')`.
        * **Option B (Better practice):** Copy the *entire JSON content* from the downloaded file. Create a `.env` file in this directory and add a line like:
            ```
            FIREBASE_SERVICE_ACCOUNT_KEY='{"type": "service_account", "project_id": "your-project-id", ...}'
            ```
            (Ensure the entire JSON is on one line and correctly escaped if needed, or better yet, just copy-paste the raw JSON string if your shell/editor handles multiline strings properly. It's often safer to base64 encode it for environment variables in real deployment.)

5.  **Google Gemini API Key:**
    * Obtain your Gemini API key from the Google AI Studio or Google Cloud Console.
    * Add it to your `.env` file:
        ```
        GEMINI_API_KEY='YOUR_GEMINI_API_KEY_HERE'
        ```
    * Also add your `APP_ID` (from the Canvas environment or any string you prefer for local testing):
        ```
        CANVAS_APP_ID='default-app-id' # Or the actual __app_id you use in your frontend
        ```

6.  **Run the Flask Application:**
    ```bash
    flask run
    # Or, if that doesn't work:
    # python app.py
    ```
    The Flask app will typically run on `http://127.0.0.1:5000/`.

## Contributing

Feel free to fork this repository, suggest improvements, or submit pull requests.
