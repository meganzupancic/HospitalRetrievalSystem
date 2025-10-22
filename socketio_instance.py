# socketio_instance.py

from flask import Flask
from flask_socketio import SocketIO

# Create the Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"  # Optional but recommended

# Create the SocketIO instance
socketio = SocketIO(app, cors_allowed_origins="*")
