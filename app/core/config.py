import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME: str = "Industrial Equipment Monitoring Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Storage and Database paths
    DATA_DIR: Path = BASE_DIR
    SQLITE_DB_PATH: Path = BASE_DIR / "data" / "equipment_monitoring.db"
    
    @property
    def DATABASE_URL(self) -> str:
        # Ensure data folder exists
        self.SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}")

    # Threshold defaults if not present in asset catalog
    DEFAULT_RATED_MAX_TEMP_C: float = 85.0
    DEFAULT_RATED_MAX_VIB_MM_S: float = 8.5
    DEFAULT_BASELINE_POWER_KW: float = 25.0
    
    # Staleness threshold in seconds (e.g. 24 hours for batch simulation)
    STALENESS_THRESHOLD_SECONDS: int = 86400

settings = Settings()
