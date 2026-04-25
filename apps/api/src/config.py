import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "logs"

load_dotenv(APP_DIR / ".env")


@dataclass
class Settings:
    serial_port: str = os.getenv("CROWD_SERIAL_PORT", "COM3")
    baud_rate: int = int(os.getenv("CROWD_BAUD_RATE", "115200"))
    host: str = os.getenv("CROWD_API_HOST", "127.0.0.1")
    port: int = int(os.getenv("CROWD_API_PORT", "8000"))

    distance_pass_threshold: int = int(os.getenv("CROWD_DISTANCE_PASS_THRESHOLD", "300"))
    slide_photo_delta_threshold: int = int(
        os.getenv("CROWD_SLIDE_PHOTO_DELTA_THRESHOLD", os.getenv("CROWD_ACCEL_DELTA_THRESHOLD", "80"))
    )
    photo_delta_threshold: int = int(os.getenv("CROWD_PHOTO_DELTA_THRESHOLD", "100"))
    light_delta_threshold: int = int(os.getenv("CROWD_LIGHT_DELTA_THRESHOLD", "120"))
    pyro_threshold: int = int(os.getenv("CROWD_PYRO_THRESHOLD", "600"))
    ei_use_pyro_for_decision: bool = os.getenv("CROWD_EI_USE_PYRO_FOR_DECISION", "true").lower() == "true"

    sensor_log_file: str = os.getenv("CROWD_SENSOR_LOG_FILE", str(DATA_DIR / "sensor_log.csv"))
    event_log_file: str = os.getenv("CROWD_EVENT_LOG_FILE", str(DATA_DIR / "event_log.csv"))

    initial_count_k: int = int(os.getenv("CROWD_INITIAL_COUNT_K", "0"))
    initial_count_e: int = int(os.getenv("CROWD_INITIAL_COUNT_E", "0"))
    initial_count_i: int = int(os.getenv("CROWD_INITIAL_COUNT_I", "0"))
    initial_count_o: int = int(os.getenv("CROWD_INITIAL_COUNT_O", "10"))

    capacity_k: int = int(os.getenv("CROWD_CAPACITY_K", "1"))
    ei_direction_auto_detect: bool = os.getenv("CROWD_EI_DIRECTION_AUTO_DETECT", "true").lower() == "true"

    @property
    def initial_counts(self) -> dict:
        return {
            "K": self.initial_count_k,
            "E": self.initial_count_e,
            "I": self.initial_count_i,
            "O": self.initial_count_o,
        }

    @property
    def room_capacity(self) -> dict:
        return {
            "K": self.capacity_k,
        }


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
