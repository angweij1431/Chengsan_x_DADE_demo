import os
import uuid
import datetime
from dotenv import load_dotenv

load_dotenv()

# Memory fallback storage if DB services are unconfigured during local test
_in_memory_db = {}

def save_video(filename, video_url, video_id=None):
    """
    Saves video metadata to database (Firebase Firestore or PostgreSQL).
    """
    if not video_id:
        video_id = str(uuid.uuid4())

    db_type = os.getenv("DB_TYPE", "firestore").lower()
    created_at = datetime.datetime.utcnow().isoformat()

    print(f"[Database] Saving video record via DB_TYPE='{db_type}'...")

    if db_type == "firestore":
        try:
            from firebase_setup import get_firestore_db
            db = get_firestore_db()
            if db:
                doc_ref = db.collection("videos").document(video_id)
                doc_ref.set({
                    "video_id": video_id,
                    "filename": filename,
                    "video_url": video_url,
                    "created_at": created_at
                })
                print(f"Video saved to Firestore collection 'videos' with ID: {video_id}")
                return video_id
        except Exception as e:
            print(f"[Firestore Warning] Failed to save to Firestore ({e}). Falling back to memory storage.")

    elif db_type == "postgres":
        try:
            import psycopg2
            connection = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "dance_db"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "")
            )
            cursor = connection.cursor()
            query = """
                INSERT INTO videos (video_id, filename, video_url)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (video_id, filename, video_url))
            connection.commit()
            cursor.close()
            connection.close()
            print(f"Video saved to PostgreSQL table 'videos' with ID: {video_id}")
            return video_id
        except Exception as e:
            print(f"[PostgreSQL Warning] Failed to save to PostgreSQL ({e}). Falling back to memory storage.")

    # Fallback in-memory storage for rapid offline testing
    _in_memory_db[video_id] = {
        "video_id": video_id,
        "filename": filename,
        "video_url": video_url,
        "created_at": created_at
    }
    print(f"Video saved to local memory store with ID: {video_id}")
    return video_id


def get_video(video_id):
    """
    Retrieves video metadata from database by video_id.
    """
    db_type = os.getenv("DB_TYPE", "firestore").lower()

    if db_type == "firestore":
        try:
            from firebase_setup import get_firestore_db
            db = get_firestore_db()
            if db:
                doc = db.collection("videos").document(video_id).get()
                if doc.exists:
                    return doc.to_dict()
        except Exception as e:
            print(f"[Firestore Warning] Could not fetch video from Firestore ({e})")

    elif db_type == "postgres":
        try:
            import psycopg2
            connection = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "dance_db"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "")
            )
            cursor = connection.cursor()
            query = "SELECT video_id, filename, video_url FROM videos WHERE video_id = %s"
            cursor.execute(query, (video_id,))
            row = cursor.fetchone()
            cursor.close()
            connection.close()
            if row:
                return {"video_id": row[0], "filename": row[1], "video_url": row[2]}
        except Exception as e:
            print(f"[PostgreSQL Warning] Could not fetch video from PostgreSQL ({e})")

    return _in_memory_db.get(video_id)