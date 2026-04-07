from flask import Flask, jsonify
import random, datetime
from pymongo import MongoClient
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

client = MongoClient("mongodb://localhost:27017/")
db = client["carbon_db"]



def get_sensor_data():
    return {
        "cpu": random.randint(10, 95),
        "power": random.randint(100, 500),
        "temperature": random.randint(20, 45)
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

@app.route('/api/data')
def data():
    
    sensor = get_sensor_data()
    factor = get_dynamic_factor()
    emission = sensor["power"] * factor
    db.records.insert_one({
    "sensor": sensor,
    "emission": emission
    })
    

    return jsonify({
        "sensor": sensor,
        "emission": emission,
        "status": "SAFE" if emission < 300 else "UNSAFE",
        "suggestions": get_recommendation(
            sensor["cpu"],
            sensor["temperature"],
            emission
            
        )
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
