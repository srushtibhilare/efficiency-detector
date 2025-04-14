from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import os
from facedetector import get_last_elapsed_time  # Import the function

app = Flask(__name__)
CORS(app)

DATABASE = 'table_data.db'  # Changed from timer_data.db to table_data.db
FACES_DIR = 'faces'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/run-detection', methods=['GET'])
def detect():
    from facedetector import run_detection
    import threading
    threading.Thread(target=run_detection).start()
    return jsonify({"message": "Face detection started in the background"})

@app.route('/api/timer_logs', methods=['GET'])
def get_timer_logs():
    conn = get_db()
    cursor = conn.cursor()
    
    # First check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='timer_logs'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        conn.close()
        return jsonify({
            "logs": [],
            "last_elapsed_time": None,
            "latest_elapsed_from_db": None
        })
    
    # Get the latest log
    cursor.execute("SELECT id, timestamp, elapsed_time, face_image_path FROM timer_logs ORDER BY id DESC LIMIT 1")
    latest_log = cursor.fetchone()
    
    # Get all logs
    cursor.execute("SELECT id, timestamp, elapsed_time, face_image_path FROM timer_logs ORDER BY id DESC")
    all_logs = cursor.fetchall()
    conn.close()

    last_elapsed = get_last_elapsed_time()  # Get the last stopped time from facedetector

    latest_elapsed_from_db = None
    if latest_log:
        latest_elapsed_from_db = latest_log['elapsed_time']

    return jsonify({
        "logs": [dict(log) for log in all_logs],
        "last_elapsed_time": last_elapsed,
        "latest_elapsed_from_db": latest_elapsed_from_db
    })

@app.route('/api/faces/<path:filename>')
def get_face_image(filename):
    from flask import send_from_directory
    return send_from_directory(FACES_DIR, filename)

if __name__ == '__main__':
    # Ensure the database and table exist
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timer_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            elapsed_time REAL NOT NULL,
            face_image_path TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    app.run(debug=True, port=5000)