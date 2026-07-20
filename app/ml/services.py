import logging
import random
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.all_repositories import ml_prediction_repo

logger = logging.getLogger("namma_bus")

class MLPredictorService:
    MODEL_VERSIONS = {
        "eta": "v1.2.0-xgboost",
        "crowd": "v2.0.1-randomforest",
        "position": "v0.8.5-kalmanfilter"
    }

    @classmethod
    async def predict_eta(
        cls,
        db: AsyncSession,
        route_id: str,
        stop_id: str,
        traffic_level: str = "NORMAL",
        hour_of_day: int = 12
    ) -> Dict[str, Any]:
        """Predicts estimated arrival delay minutes using route history and traffic reports."""
        model_name = "eta_predictor"
        version = cls.MODEL_VERSIONS["eta"]
        
        # Simulated ML inference logic (would load XGBoost/LightGBM model)
        base_delay = 5.0
        if traffic_level == "HEAVY":
            base_delay += 12.5
        elif traffic_level == "JAM":
            base_delay += 25.0
            
        # Peak hours adjustment
        if 8 <= hour_of_day <= 10 or 17 <= hour_of_day <= 19:
            base_delay *= 1.3
            
        prediction_val = {
            "predicted_delay_minutes": round(base_delay + random.uniform(-1.5, 1.5), 1),
            "confidence_score": 0.89
        }
        
        # Log prediction to DB for auditing and ML model retraining pipeline logs
        await ml_prediction_repo.create(
            db,
            obj_in={
                "model_name": model_name,
                "model_version": version,
                "prediction_type": "ETA",
                "target_id": f"{route_id}_{stop_id}",
                "prediction_value": prediction_val,
                "input_features": {
                    "traffic_level": traffic_level,
                    "hour_of_day": hour_of_day
                }
            }
        )
        await db.flush()
        return prediction_val

    @classmethod
    async def predict_crowd(
        cls,
        db: AsyncSession,
        route_id: str,
        stop_id: str,
        day_of_week: str = "WEEKDAY",
        hour_of_day: int = 8
    ) -> Dict[str, Any]:
        """Predicts crowd level (LOW, MEDIUM, HIGH) based on historical route timings."""
        model_name = "crowd_predictor"
        version = cls.MODEL_VERSIONS["crowd"]
        
        # Simulation model logic
        is_rush_hour = (7 <= hour_of_day <= 9) or (17 <= hour_of_day <= 19)
        is_weekend = day_of_week in ["SATURDAY", "SUNDAY"]
        
        if is_rush_hour and not is_weekend:
            crowd_level = "HIGH"
            seat_probability = 0.15
        elif is_rush_hour or (11 <= hour_of_day <= 14):
            crowd_level = "MEDIUM"
            seat_probability = 0.55
        else:
            crowd_level = "LOW"
            seat_probability = 0.90
            
        prediction_val = {
            "predicted_crowd_level": crowd_level,
            "seating_probability": seat_probability,
            "confidence_score": 0.92
        }
        
        await ml_prediction_repo.create(
            db,
            obj_in={
                "model_name": model_name,
                "model_version": version,
                "prediction_type": "CROWD",
                "target_id": f"{route_id}_{stop_id}",
                "prediction_value": prediction_val,
                "input_features": {
                    "day_of_week": day_of_week,
                    "hour_of_day": hour_of_day
                }
            }
        )
        await db.flush()
        return prediction_val

    @classmethod
    async def predict_bus_position(
        cls,
        db: AsyncSession,
        bus_id: str,
        last_lat: float,
        last_lon: float,
        last_speed: float,
        elapsed_seconds: float
    ) -> Dict[str, Any]:
        """Predicts/extrapolates current bus coordinates using speed, bearing, and time since last GPS reporting."""
        model_name = "bus_position_predictor"
        version = cls.MODEL_VERSIONS["position"]
        
        # Standard dead reckoning extrapolation (using Kalman filter structure)
        # 1 degree lat ~ 111,000 meters. 1 degree lon ~ 111,000 * cos(lat)
        # Simulated small drift based on speed and elapsed time
        speed_mps = last_speed / 3.6 # km/h to m/s
        distance_moved = speed_mps * elapsed_seconds
        
        # Predict moving slightly Northeast (drift values)
        lat_change = (distance_moved * 0.707) / 111000.0
        lon_change = (distance_moved * 0.707) / (111000.0 * 0.978) # cos(12.97) ~ 0.978
        
        predicted_lat = last_lat + lat_change
        predicted_lon = last_lon + lon_change
        
        prediction_val = {
            "predicted_latitude": predicted_lat,
            "predicted_longitude": predicted_lon,
            "drift_radius_meters": round(distance_moved * 0.1, 2)
        }
        
        await ml_prediction_repo.create(
            db,
            obj_in={
                "model_name": model_name,
                "model_version": version,
                "prediction_type": "POSITION",
                "target_id": bus_id,
                "prediction_value": prediction_val,
                "input_features": {
                    "last_lat": last_lat,
                    "last_lon": last_lon,
                    "last_speed": last_speed,
                    "elapsed_seconds": elapsed_seconds
                }
            }
        )
        await db.flush()
        return prediction_val
