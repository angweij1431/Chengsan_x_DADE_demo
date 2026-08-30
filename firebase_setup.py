import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

db_instance = None

def get_firestore_db():
    """
    Initializes and returns the Firestore database client.
    Supports credentials path from environment or default initialization.
    """
    global db_instance
    if db_instance is not None:
        return db_instance

    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print(f"[Firebase] Initialized with service account: {cred_path}")
            else:
                # Attempt default application credentials or project ID fallback
                project_id = os.getenv("FIREBASE_PROJECT_ID")
                if project_id:
                    firebase_admin.initialize_app(options={'projectId': project_id})
                    print(f"[Firebase] Initialized with Project ID: {project_id}")
                else:
                    print(f"[Firebase Warning] Service account file not found at '{cred_path}'. Running in unauthenticated or local mock mode.")
                    firebase_admin.initialize_app()

        db_instance = firestore.client()
        return db_instance
    except Exception as e:
        print(f"[Firebase Error] Could not initialize Firestore: {e}")
        return None
