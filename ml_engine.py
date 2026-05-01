"""
Real-time Machine Learning Engine for Carbon Emissions Monitoring
Includes: Time series forecasting, anomaly detection, clustering, and online learning
"""

import numpy as np
import datetime
from collections import deque
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
import json


class RealTimeMLEngine:
    """
    Handles real-time machine learning operations on streaming sensor data.
    Uses online learning for continuous model updates.
    """
    
    def __init__(self, history_size=100, forecast_horizon=5):
        """
        Initialize ML engine with configurable parameters.
        
        Args:
            history_size: Number of historical records to maintain
            forecast_horizon: Number of steps ahead to forecast
        """
        self.history_size = history_size
        self.forecast_horizon = forecast_horizon
        
        # Data buffers for streaming
        self.emission_history = deque(maxlen=history_size)
        self.sensor_history = deque(maxlen=history_size)
        self.timestamp_history = deque(maxlen=history_size)
        
        # ML Models
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=50
        )
        self.forecast_model = LinearRegression()
        self.clustering_model = KMeans(n_clusters=3, random_state=42, n_init=10)
        
        # State tracking
        self.is_fitted = False
        self.predictions_cache = {}
        self.baseline_stats = {'mean': 0, 'std': 1}
        
    def update(self, sensor_data, emission):
        """
        Update the ML engine with new data point.
        
        Args:
            sensor_data: dict with keys {cpu, power, temperature}
            emission: float, carbon emission value
        """
        # Append to history
        self.emission_history.append(emission)
        self.sensor_history.append(sensor_data)
        self.timestamp_history.append(datetime.datetime.utcnow())
        
        # Auto-fit when buffer is full enough
        if len(self.emission_history) > 10 and not self.is_fitted:
            self._fit_models()
    
    def _fit_models(self):
        """Fit all ML models on current historical data."""
        if len(self.emission_history) < 10:
            return
            
        emission_array = np.array(list(self.emission_history)).reshape(-1, 1)
        
        # Update baseline statistics for anomaly detection
        self.baseline_stats = {
            'mean': float(np.mean(emission_array)),
            'std': float(np.std(emission_array)) or 1.0
        }
        
        # Fit scaler
        self.scaler.fit(emission_array)
        
        # Fit anomaly detector
        scaled = self.scaler.transform(emission_array)
        try:
            self.anomaly_detector.fit(scaled)
        except Exception as e:
            print(f"Anomaly detector fitting failed: {e}")
        
        # Fit time series forecasting model
        if len(self.emission_history) > self.forecast_horizon:
            X, y = self._prepare_forecast_data()
            if X.shape[0] > 0:
                try:
                    self.forecast_model.fit(X, y)
                except Exception as e:
                    print(f"Forecast model fitting failed: {e}")
        
        # Fit clustering model
        sensor_features = self._extract_sensor_features()
        if sensor_features.shape[0] >= 3:
            try:
                self.clustering_model.fit(sensor_features)
            except Exception as e:
                print(f"Clustering model fitting failed: {e}")
        
        self.is_fitted = True
    
    def _prepare_forecast_data(self):
        """Prepare lagged features for time series forecasting."""
        emissions = np.array(list(self.emission_history))
        X, y = [], []
        
        for i in range(len(emissions) - self.forecast_horizon):
            X.append(emissions[i:i + self.forecast_horizon])
            y.append(emissions[i + self.forecast_horizon])
        
        return np.array(X), np.array(y)
    
    def _extract_sensor_features(self):
        """Extract and scale sensor features for clustering."""
        features = []
        for sensor in self.sensor_history:
            features.append([
                sensor.get('cpu', 0),
                sensor.get('power', 0),
                sensor.get('temperature', 0)
            ])
        
        features = np.array(features)
        if features.shape[0] > 0:
            scaler = StandardScaler()
            features = scaler.fit_transform(features)
        
        return features
    
    def detect_anomalies(self):
        """
        Detect anomalies in recent emission data.
        
        Returns:
            dict with anomaly information
        """
        if len(self.emission_history) < 2 or not self.is_fitted:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'severity': 'none',
                'details': 'Insufficient data for anomaly detection'
            }
        
        latest_emission = np.array([[self.emission_history[-1]]])
        scaled = self.scaler.transform(latest_emission)
        
        try:
            # -1 indicates anomaly, 1 indicates normal
            prediction = self.anomaly_detector.predict(scaled)[0]
            anomaly_score = abs(self.anomaly_detector.score_samples(scaled)[0])
            
            # Calculate Z-score
            z_score = (self.emission_history[-1] - self.baseline_stats['mean']) / self.baseline_stats['std']
            
            is_anomaly = prediction == -1
            severity = self._calculate_severity(anomaly_score, z_score)
            
            return {
                'is_anomaly': is_anomaly,
                'anomaly_score': float(anomaly_score),
                'z_score': float(z_score),
                'severity': severity,
                'details': f"Current emission: {self.emission_history[-1]:.1f} (mean: {self.baseline_stats['mean']:.1f})"
            }
        except Exception as e:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'severity': 'error',
                'details': str(e)
            }
    
    def forecast_emissions(self, steps=5):
        """
        Forecast future emission values.
        
        Args:
            steps: Number of steps to forecast (default 5)
            
        Returns:
            list of predicted emission values
        """
        if len(self.emission_history) < self.forecast_horizon or not self.is_fitted:
            return {
                'forecast': [],
                'confidence': 0.0,
                'details': 'Insufficient data or model not fitted'
            }
        
        try:
            emissions = np.array(list(self.emission_history))
            latest_window = emissions[-self.forecast_horizon:].reshape(1, -1)
            
            predictions = []
            current_window = latest_window.copy()
            
            for _ in range(steps):
                next_pred = self.forecast_model.predict(current_window)[0]
                predictions.append(float(next_pred))
                
                # Shift window
                current_window = np.append(current_window[0, 1:], next_pred)
                current_window = current_window.reshape(1, -1)
            
            # Calculate model confidence (R² score if possible)
            confidence = self._calculate_forecast_confidence()
            
            return {
                'forecast': predictions,
                'confidence': confidence,
                'steps': steps,
                'details': 'Forecast based on historical patterns'
            }
        except Exception as e:
            return {
                'forecast': [],
                'confidence': 0.0,
                'steps': steps,
                'details': f'Forecast failed: {str(e)}'
            }
    
    def _calculate_forecast_confidence(self):
        """Calculate confidence score for forecast model."""
        if len(self.emission_history) < 2 * self.forecast_horizon:
            return 0.5
        
        try:
            X, y = self._prepare_forecast_data()
            if X.shape[0] > 0:
                # Simple R² approximation
                predictions = self.forecast_model.predict(X)
                ss_res = np.sum((y - predictions) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                return float(np.clip(r2, 0, 1))
        except:
            pass
        
        return 0.5
    
    def cluster_operational_state(self):
        """
        Cluster current operational state based on sensor readings.
        
        Returns:
            dict with cluster information and recommendations
        """
        if len(self.sensor_history) < 3 or not self.is_fitted:
            return {
                'cluster_id': -1,
                'cluster_name': 'Unknown',
                'characteristics': {},
                'details': 'Insufficient data for clustering'
            }
        
        try:
            sensor_features = self._extract_sensor_features()
            cluster_id = int(self.clustering_model.predict(sensor_features[-1:].reshape(1, -1))[0])
            
            cluster_names = ['Low Load', 'Medium Load', 'High Load']
            cluster_characteristics = [
                {'cpu_avg': 'Low', 'power_avg': 'Low', 'temp_avg': 'Normal'},
                {'cpu_avg': 'Medium', 'power_avg': 'Medium', 'temp_avg': 'Normal'},
                {'cpu_avg': 'High', 'power_avg': 'High', 'temp_avg': 'Elevated'}
            ]
            
            return {
                'cluster_id': cluster_id,
                'cluster_name': cluster_names[cluster_id],
                'characteristics': cluster_characteristics[cluster_id],
                'details': f'Current operational state: {cluster_names[cluster_id]}'
            }
        except Exception as e:
            return {
                'cluster_id': -1,
                'cluster_name': 'Error',
                'characteristics': {},
                'details': str(e)
            }
    
    def _calculate_severity(self, anomaly_score, z_score):
        """Calculate severity level based on anomaly metrics."""
        if anomaly_score < 0.5 and abs(z_score) < 2:
            return 'none'
        elif anomaly_score < 1.0 and abs(z_score) < 3:
            return 'low'
        elif anomaly_score < 1.5 and abs(z_score) < 4:
            return 'medium'
        else:
            return 'high'
    
    def get_statistics(self):
        """Return current emission statistics."""
        if len(self.emission_history) == 0:
            return {
                'count': 0,
                'mean': 0,
                'std': 0,
                'min': 0,
                'max': 0,
                'latest': 0
            }
        
        emissions = np.array(list(self.emission_history))
        return {
            'count': len(emissions),
            'mean': float(np.mean(emissions)),
            'std': float(np.std(emissions)),
            'min': float(np.min(emissions)),
            'max': float(np.max(emissions)),
            'latest': float(emissions[-1]),
            'trend': self._calculate_trend()
        }
    
    def _calculate_trend(self):
        """Calculate recent trend (up/down/stable)."""
        if len(self.emission_history) < 5:
            return 'insufficient_data'
        
        recent = np.array(list(self.emission_history)[-5:])
        old = np.array(list(self.emission_history)[-10:-5])
        
        recent_mean = np.mean(recent)
        old_mean = np.mean(old)
        
        diff_pct = ((recent_mean - old_mean) / old_mean) * 100 if old_mean != 0 else 0
        
        if diff_pct > 5:
            return 'increasing'
        elif diff_pct < -5:
            return 'decreasing'
        else:
            return 'stable'
    
    def get_ml_insights(self):
        """
        Get comprehensive ML insights in one call.
        
        Returns:
            dict with all ML analysis results
        """
        self._fit_models() if len(self.emission_history) > 10 else None
        
        return {
            'statistics': self.get_statistics(),
            'anomaly': self.detect_anomalies(),
            'forecast': self.forecast_emissions(),
            'cluster': self.cluster_operational_state(),
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
        }


# Global ML engine instance
ml_engine = RealTimeMLEngine(history_size=100, forecast_horizon=5)
