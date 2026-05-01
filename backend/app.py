import os
import random
import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Import the new ML Engine
from ml_models import ModelManager

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Ensure this is exactly the URL that worked for you!
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://hj7733324_db_user:Nl3e5W4KUEuGsEF0@clustercarbon.lfuitwb.mongodb.net/?appName=Clustercarbon")

DB_NAME = "carbon_db"
COLLECTION_NAME = "records"

client = None
db = None
mongo_ok = False

# Initialize the Machine Learning Manager
ml_manager = ModelManager()

def connect_to_mongo():
    global client, db, mongo_ok
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[DB_NAME]
        mongo_ok = True
        print("✅ Successfully connected to MongoDB!")
    except (ConnectionFailure, OperationFailure) as e:
        print(f"❌ Could not connect to MongoDB: {e}")
        mongo_ok = False

connect_to_mongo()

def get_sensor_data():
    return {
        "cpu": round(random.uniform(20.0, 90.0), 1),
        "power": round(random.uniform(150.0, 550.0), 1),
        "temperature": round(random.uniform(25.0, 50.0), 1),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

def get_dynamic_factor():
    hour = datetime.datetime.now().hour
    return 0.5 if 6 <= hour <= 18 else 0.9

@app.route("/api/data")
def data():
    if not mongo_ok:
        connect_to_mongo()
        
    sensor = get_sensor_data()
    factor = get_dynamic_factor()
    emission = round(sensor["power"] * factor, 1)

    # Process data through the Machine Learning Models
    ml_insights = ml_manager.process_datapoint(sensor, emission)

    if mongo_ok and db is not None:
        try:
            db[COLLECTION_NAME].insert_one({
                "sensor": sensor,
                "emission": emission,
                "ml_insights": ml_insights, # Save ML data to the database
                "timestamp": datetime.datetime.utcnow()
            })
        except Exception:
            pass

    return jsonify({
        "sensor": sensor,
        "emission": emission,
        "status": "SAFE" if emission < 300 else "UNSAFE",
        "ml": ml_insights, # Send ML insights to the React frontend
        "db_connected": mongo_ok,
        "factor": factor
    })

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "db_connected": mongo_ok})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
