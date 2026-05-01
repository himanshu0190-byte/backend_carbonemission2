import os
import random
import datetime
import time
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

app = Flask(__name__)

# --- CONFIGURATION ---
# Restrict origins in production!
# For Vercel, it might look like: "https://your-frontend-url.vercel.app"
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Place your live MongoDB URI here. Get this from your cloud provider (e.g., MongoDB Atlas).
# If this variable is not set on your hosting platform, it defaults to localhost.
MONGO_URI = os.environ.get("mongodb+srv://hj7733324_db_user:Nl3e5W4KUEuGsEF0@clustercarbon.lfuitwb.mongodb.net/?appName=Clustercarbon")

DB_NAME = "carbon_db"
COLLECTION_NAME = "records"

# --- MONGODB SETUP ---
client = None
db = None
mongo_ok = False

def connect_to_mongo():
    global client, db, mongo_ok
    try:
        # Increase timeout for cloud connections
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # The 'ping' command is cheap and reliable to verify connectivity
        client.admin.command('ping')
        db = client[DB_NAME]
        mongo_ok = True
        print("✅ Successfully connected to MongoDB!") # Print part of URI safely
    except (ConnectionFailure, OperationFailure) as e:
        print(f"❌ Could not connect to MongoDB: {e}")
        mongo_ok = False
        db = None
        client = None

# Perform initial connection
connect_to_mongo()

# --- REAL-TIME DATA SIMULATION ---
def get_sensor_data():
    """
    Simulates real-time sensor data.
    Replace these functions with calls to actual hardware APIs or libraries.
    """
    # Simulate slightly more varying and dynamic data
    cpu = random.uniform(20.0, 90.0)
    power = random.uniform(150.0, 550.0)
    temperature = random.uniform(25.0, 50.0)

    # Return slightly different structure than the original for better realism
    return {
        "cpu": round(cpu, 1),
        "power": round(power, 1),
        "temperature": round(temperature, 1),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z" # ISO-8601 format
    }

def get_dynamic_factor():
    """Calculates a simulated emissions factor based on the hour of day."""
    hour = datetime.datetime.now().hour
    # Daytime (6 AM to 6 PM) is cleaner, nighttime is dirtier
    return 0.5 if 6 <= hour <= 18 else 0.9

def get_recommendation(cpu, temp, emission):
    """Generates recommendations based on the data."""
    suggestions = []
    if cpu > 80:
        suggestions.append("Redistribute workload")
    if temp > 35:
        suggestions.append("Improve cooling")
    if emission > 300:
        suggestions.append("Shift to low-carbon hours")
    return suggestions

# --- API ROUTES ---
@app.route("/api/data")
def data():
    # If not connected, try to reconnect (or handle as an error)
    if not mongo_ok:
        connect_to_mongo()
        # Return static data if still not connected
        sensor = {"cpu": 85, "power": 420, "temperature": 36.8}
        factor = 0.5
        emission = 284.5
        suggestions = ["Redistribute workload", "Improve cooling"]
        db_connected = False
        print("Using static data because MongoDB is not connected.")
    else:
        # Get live simulated data
        sensor = get_sensor_data()
        factor = get_dynamic_factor()
        emission = round(sensor["power"] * factor, 1)
        suggestions = get_recommendation(sensor["cpu"], sensor["temperature"], emission)
        db_connected = True

        # Save to MongoDB
        try:
            db[COLLECTION_NAME].insert_one({
                "sensor": sensor,
                "emission": emission,
                "timestamp": datetime.datetime.utcnow()
            })
            print("Record saved to MongoDB.")
        except Exception as e:
            print(f"Failed to save record to MongoDB: {e}")
            # Do not crash the API, but log the error

    return jsonify({
        "sensor": sensor,
        "emission": emission,
        "status": "SAFE" if emission < 300 else "UNSAFE",
        "suggestions": suggestions,
        "db_connected": db_connected,
        "factor": factor
    })

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "db_connected": mongo_ok,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    })

# --- RUN THE APP ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Production configuration: debug=False
    app.run(host="0.0.0.0", port=port, debug=False)
