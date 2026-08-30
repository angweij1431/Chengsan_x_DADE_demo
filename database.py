import psycopg2
import os
import uuid
from dotenv import load_dotenv

load_dotenv()


def save_video(filename, video_url):

    connection = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    cursor = connection.cursor()

    video_id = str(uuid.uuid4())

    query = """
        INSERT INTO videos (video_id, filename, video_url)
        VALUES (%s, %s, %s)
    """

    cursor.execute(
        query,
        (video_id, filename, video_url)
    )

    connection.commit()

    cursor.close()
    connection.close()

    print("Video information saved to database!")
    print("Video ID:", video_id)

    return video_id