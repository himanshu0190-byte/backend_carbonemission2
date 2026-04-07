
import os
import random
import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

app = Flask(__name__)

# Allow requests from any origin in production (restrict to your Vercel URL if preferred)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# MongoDB URI from environment variable (set on Render dashboard)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    db = client["carbon_db"]
    mongo_ok = True
except ConnectionFailure:
    mongo_ok = False
    db = None


def get_sensor_data():
    return {
        "cpu": random.randint(10, 95),
        "power": random.randint(100, 500),
        "temperature": random.randint(20, 45),
    }


def get_dynamic_factor():
    hour = datetime.datetime.now().hour
    return 0.5 if 6 <= hour <= 18 else 0.9


def get_recommendation(cpu, temp, emission):
    suggestions = []
    if cpu > 80:
        suggestions.append("Redistribute workload")
    if temp > 35:
        suggestions.append("Improve cooling")
    if emission > 300:
        suggestions.append("Shift to low-carbon hours")
    return suggestions


@app.route("/api/data")
def data():
    sensor = get_sensor_data()
    factor = get_dynamic_factor()
    emission = round(sensor["power"] * factor, 1)

    if mongo_ok and db is not None:
        try:
            db.records.insert_one({
                "sensor": sensor,
                "emission": emission,
                "timestamp": datetime.datetime.utcnow(),
            })
        except Exception:
            pass  # Don't crash the API if DB write fails

    return jsonify({
        "sensor": sensor,
        "emission": emission,
        "status": "SAFE" if emission < 300 else "UNSAFE",
        "suggestions": get_recommendation(
            sensor["cpu"], sensor["temperature"], emission
        ),
        "db_connected": mongo_ok,
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "db_connected": mongo_ok})


if __name__ == "__main__":
    port = int(os.environ.get("PORT",8000))
    app.run(host="0.0.0.0", port=port, debug=False)
