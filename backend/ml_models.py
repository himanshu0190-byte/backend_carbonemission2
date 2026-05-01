"""
Real-time Machine Learning Models for Carbon Emission Prediction and Anomaly Detection
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from collections import deque
import json
import joblib
import os

class RealTimeEmissionPredictor:
    """
    Predicts carbon emissions using real-time sensor data.
    Uses Linear Regression and Random Forest for accurate forecasting.
    """
    
    def __init__(self, lookback_window=50):
        self.lookback_window = lookback_window
        self.data_buffer = deque(maxlen=lookback_window)
        self.scaler = StandardScaler()
        self.lr_model = LinearRegression()
        self.rf_model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            random_state=42
        )
        self.model_trained = False
        self.feature_columns = ['cpu', 'power', 'temperature', 'hour', 'day_of_week']
        
    def add_datapoint(self, sensor_data, emission):
        """Add a new sensor reading to the buffer."""
        timestamp = datetime.now()
        self.data_buffer.append({
            'cpu': sensor_data.get('cpu', 0),
            'power': sensor_data.get('power', 0),
            'temperature': sensor_data.get('temperature', 0),
            'emission': emission,
            'timestamp': timestamp,
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday()
        })
    
    def _prepare_features(self, data_list):
        """Convert raw data to feature matrix."""
        features = []
        for point in data_list:
            feature_vector = [
                point['cpu'],
                point['power'],
                point['temperature'],
                point['hour'],
                point['day_of_week']
            ]
            features.append(feature_vector)
        return np.array(features)
    
    def train(self):
        """Train models when sufficient data is available."""
        if len(self.data_buffer) < 10:
            return False
        
        try:
            data_list = list(self.data_buffer)
            X = self._prepare_features(data_list)
            y = np.array([d['emission'] for d in data_list])
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train both models
            self.lr_model.fit(X_scaled, y)
            self.rf_model.fit(X_scaled, y)
            
            self.model_trained = True
            return True
        except Exception as e:
            print(f"Error training models: {e}")
            return False
    
    def predict_next(self, sensor_data):
        """Predict next emission value."""
        if not self.model_trained:
            return None
        
        try:
            timestamp = datetime.now()
            feature_vector = np.array([[
                sensor_data.get('cpu', 0),
                sensor_data.get('power', 0),
                sensor_data.get('temperature', 0),
                timestamp.hour,
                timestamp.weekday()
            ]])
            
            X_scaled = self.scaler.transform(feature_vector)
            
            # Ensemble prediction: average of linear and random forest
            lr_pred = self.lr_model.predict(X_scaled)[0]
            rf_pred = self.rf_model.predict(X_scaled)[0]
            
            ensemble_pred = (lr_pred * 0.4 + rf_pred * 0.6)
            return round(max(0, ensemble_pred), 2)
        except Exception as e:
            print(f"Error making prediction: {e}")
            return None
    
    def predict_next_hour(self, sensor_data):
        """Predict emission trend for the next hour."""
        predictions = []
        current_sensor = sensor_data.copy()
        
        for i in range(60):  # 60-minute forecast
            pred = self.predict_next(current_sensor)
            if pred is not None:
                predictions.append(pred)
                # Simulate gradual change
                current_sensor['power'] *= 0.99
        
        if predictions:
            return {
                'avg': round(np.mean(predictions), 2),
                'min': round(np.min(predictions), 2),
                'max': round(np.max(predictions), 2),
                'trend': 'increasing' if predictions[-1] > predictions[0] else 'decreasing'
            }
        return None


class AnomalyDetector:
    """
    Detects anomalies in sensor data and emissions using Isolation Forest.
    Real-time monitoring for unusual patterns.
    """
    
    def __init__(self, contamination=0.05):
        self.contamination = contamination
        self.detector = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.data_buffer = deque(maxlen=200)
        self.model_trained = False
        self.anomaly_threshold = None
        
    def add_datapoint(self, sensor_data, emission):
        """Add a datapoint for anomaly detection."""
        feature_vector = [
            sensor_data.get('cpu', 0),
            sensor_data.get('power', 0),
            sensor_data.get('temperature', 0),
            emission
        ]
        self.data_buffer.append(feature_vector)
    
    def train(self):
        """Train the anomaly detector."""
        if len(self.data_buffer) < 20:
            return False
        
        try:
            X = np.array(list(self.data_buffer))
            self.detector.fit(X)
            self.model_trained = True
            return True
        except Exception as e:
            print(f"Error training anomaly detector: {e}")
            return False
    
    def detect(self, sensor_data, emission):
        """Check if current datapoint is anomalous."""
        if not self.model_trained:
            return False, 0.0
        
        try:
            feature_vector = np.array([[
                sensor_data.get('cpu', 0),
                sensor_data.get('power', 0),
                sensor_data.get('temperature', 0),
                emission
            ]])
            
            prediction = self.detector.predict(feature_vector)[0]
            score = self.detector.score_samples(feature_vector)[0]
            
            is_anomaly = prediction == -1
            anomaly_score = abs(score)  # Higher = more anomalous
            
            return is_anomaly, round(anomaly_score, 3)
        except Exception as e:
            print(f"Error detecting anomaly: {e}")
            return False, 0.0


class EmissionOptimizer:
    """
    Provides AI-powered optimization recommendations to reduce carbon emissions.
    Uses pattern analysis and predictive insights.
    """
    
    def __init__(self):
        self.historical_patterns = deque(maxlen=500)
        self.optimization_rules = self._init_rules()
        
    def _init_rules(self):
        """Initialize optimization rules based on domain knowledge."""
        return {
            'cpu_high': {'threshold': 80, 'recommendation': 'Distribute load across multiple cores'},
            'temperature_high': {'threshold': 40, 'recommendation': 'Optimize cooling efficiency'},
            'power_high': {'threshold': 400, 'recommendation': 'Schedule non-critical tasks'},
            'emission_peak': {'threshold': 350, 'recommendation': 'Defer heavy computation'},
            'night_shift': {'threshold_hour': 18, 'recommendation': 'Schedule batch jobs during day'},
        }
    
    def add_datapoint(self, sensor_data, emission):
        """Track historical patterns."""
        timestamp = datetime.now()
        self.historical_patterns.append({
            'cpu': sensor_data.get('cpu', 0),
            'power': sensor_data.get('power', 0),
            'temperature': sensor_data.get('temperature', 0),
            'emission': emission,
            'hour': timestamp.hour,
            'timestamp': timestamp
        })
    
    def get_optimization_recommendations(self, sensor_data, emission, predicted_emission=None):
        """
        Generate AI-powered recommendations to reduce emissions.
        Returns list of actionable insights.
        """
        recommendations = []
        
        # CPU-based recommendations
        cpu = sensor_data.get('cpu', 0)
        if cpu > self.optimization_rules['cpu_high']['threshold']:
            recommendations.append({
                'category': 'CPU_OPTIMIZATION',
                'priority': 'HIGH',
                'action': self.optimization_rules['cpu_high']['recommendation'],
                'estimated_savings': f"{min(cpu - 80, 20):.1f}%",
                'metric': f"Current CPU: {cpu}%"
            })
        
        # Temperature-based recommendations
        temp = sensor_data.get('temperature', 0)
        if temp > self.optimization_rules['temperature_high']['threshold']:
            temp_excess = temp - 40
            savings = temp_excess * 2.5  # Rough estimate
            recommendations.append({
                'category': 'THERMAL_OPTIMIZATION',
                'priority': 'HIGH',
                'action': self.optimization_rules['temperature_high']['recommendation'],
                'estimated_savings': f"{min(savings, 15):.1f}%",
                'metric': f"Current Temp: {temp}°C"
            })
        
        # Power efficiency
        power = sensor_data.get('power', 0)
        if power > self.optimization_rules['power_high']['threshold']:
            recommendations.append({
                'category': 'POWER_EFFICIENCY',
                'priority': 'MEDIUM',
                'action': self.optimization_rules['power_high']['recommendation'],
                'estimated_savings': f"{((power - 400) / power * 100):.1f}%",
                'metric': f"Current Power: {power}W"
            })
        
        # Emission peak handling
        if emission > self.optimization_rules['emission_peak']['threshold']:
            recommendations.append({
                'category': 'EMISSION_CONTROL',
                'priority': 'CRITICAL',
                'action': self.optimization_rules['emission_peak']['recommendation'],
                'estimated_savings': f"{((emission - 300) / emission * 100):.1f}%",
                'metric': f"Current Emission: {emission}g CO2"
            })
        
        # Time-based optimization
        hour = datetime.now().hour
        if hour >= 22 or hour <= 6:
            recommendations.append({
                'category': 'SCHEDULING',
                'priority': 'MEDIUM',
                'action': 'Consider deferring heavy workloads to daytime hours for lower emissions',
                'estimated_savings': '10-20%',
                'metric': f"Current Hour: {hour}:00"
            })
        
        # Predictive recommendations
        if predicted_emission and predicted_emission > 300:
            recommendations.append({
                'category': 'PREDICTIVE_ALERT',
                'priority': 'HIGH',
                'action': 'Emission will likely spike in the next hour. Proactive load reduction recommended.',
                'estimated_savings': '5-15%',
                'metric': f"Predicted: {predicted_emission}g CO2"
            })
        
        return recommendations
    
    def calculate_savings_potential(self):
        """Calculate potential CO2 savings from optimizations."""
        if len(self.historical_patterns) < 10:
            return None
        
        patterns = list(self.historical_patterns)
        avg_emission = np.mean([p['emission'] for p in patterns])
        max_emission = np.max([p['emission'] for p in patterns])
        
        # Conservative estimate: 15-25% reduction possible
        min_savings = avg_emission * 0.15
        max_savings = avg_emission * 0.25
        
        return {
            'current_avg': round(avg_emission, 2),
            'min_savings_potential': round(min_savings, 2),
            'max_savings_potential': round(max_savings, 2),
            'savings_percentage': '15-25%'
        }


class ModelManager:
    """Manages all ML models and provides unified interface."""
    
    def __init__(self):
        self.predictor = RealTimeEmissionPredictor()
        self.anomaly_detector = AnomalyDetector()
        self.optimizer = EmissionOptimizer()
    
    def process_datapoint(self, sensor_data, emission):
        """Process a new datapoint through all models."""
        # Add to all models
        self.predictor.add_datapoint(sensor_data, emission)
        self.anomaly_detector.add_datapoint(sensor_data, emission)
        self.optimizer.add_datapoint(sensor_data, emission)
        
        # Train models if ready
        self.predictor.train()
        self.anomaly_detector.train()
        
        # Get predictions and anomaly detection
        prediction = self.predictor.predict_next(sensor_data)
        next_hour_forecast = self.predictor.predict_next_hour(sensor_data)
        is_anomaly, anomaly_score = self.anomaly_detector.detect(sensor_data, emission)
        recommendations = self.optimizer.get_optimization_recommendations(
            sensor_data, emission, prediction
        )
        savings_potential = self.optimizer.calculate_savings_potential()
        
        return {
            'prediction': prediction,
            'next_hour_forecast': next_hour_forecast,
            'is_anomaly': is_anomaly,
            'anomaly_score': anomaly_score,
            'recommendations': recommendations,
            'savings_potential': savings_potential,
            'model_status': {
                'predictor_ready': self.predictor.model_trained,
                'anomaly_detector_ready': self.anomaly_detector.model_trained,
                'data_points_collected': len(self.predictor.data_buffer)
            }
        }
