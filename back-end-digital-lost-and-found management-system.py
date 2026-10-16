import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Allows your frontend folder to talk to this backend
socketio = SocketIO(app, cors_allowed_origins="*")

# Configurations
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Upload Limit

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    """Initializes the SQLite database tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Found',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/api/upload', methods=['POST'])
def upload_item():
    """Handles drag-and-drop image uploads and text descriptions."""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    description = request.form.get('description', '').strip()
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not description:
        return jsonify({"error": "Description is required"}), 400

    # Save physical file permanently
    filename = secure_filename(file.filename)
    # Append unique timestamp to filename if you want to avoid overwriting duplicates
    file_save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_save_path)
    
    # Save file pathway string to SQLite
    relative_path = f"uploads/{filename}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (image_path, description) VALUES (?, ?)", (relative_path, description))
    conn.commit()
    conn.close()

    return jsonify({"message": "Item registered successfully!"}), 201

@app.route('/api/items', methods=['GET'])
def get_items():
    """Returns all items for your frontend gallery."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE status = 'Found' ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    items = [dict(row) for row in rows]
    return jsonify(items)

@app.route('/uploads/<filename>')
def serve_image(filename):
    """Serves the uploaded images safely to the frontend gallery."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ⚡ REAL-TIME WEBSOCKET EVENT FOR SWAFO
@socketio.on('claim_item')
def handle_claim(data):
    """Triggered when someone clicks the claim button in the gallery."""
    item_id = data.get('item_id')
    item_description = data.get('description')
    
    print(f"Alert: Item ID {item_id} is being claimed!")
    
    # Instantly broadcasts a message to the SWAFO dashboard dashboard listener
    emit('swafo_notification', {
        "message": f"🚨 Real-time Claim Alert! Someone is inquiring about item #{item_id}: '{item_description}'",
        "item_id": item_id
    }, broadcast=True)

if __name__ == '__main__':
    init_db()
    # Note: Use socketio.run instead of app.run to enable real-time features!
    socketio.run(app, port=5000, debug=True)
