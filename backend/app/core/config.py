from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "PSG IMSR Pulmonology API"
    debug: bool = False
    database_url: str = "postgresql://imsr:imsr@localhost:5432/imsr_pulmonology"
    redis_url: str = "redis://localhost:6379/0"
    synthetic_data_dir: str = str(BASE_DIR / "data" / "synthetic")
    model_artifacts_dir: str = str(BASE_DIR / "data" / "processed")
    forecast_horizon_days: int = 28
    max_patients_per_doctor: int = 18
    feasibility_threshold_green: int = 70
    feasibility_threshold_yellow: int = 40

    class Config:
        env_file = ".env"


settings = Settings()
