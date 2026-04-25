import threading
import time

import serial
from serial import SerialException

from .config import settings
from .domain.occupancy_engine import OccupancyEngine
from .infra.csv_logger import (
    SENSOR_LOG_HEADERS,
    EVENT_LOG_HEADERS,
    append_event_log,
    append_sensor_log,
    init_csv_logger,
)


class SerialWorker:
    def __init__(self, state_store):
        self.state_store = state_store
        self.stop_event = threading.Event()
        self.thread = None

        self.engine = OccupancyEngine(
            initial_counts=settings.initial_counts,
            room_capacity=settings.room_capacity,
            distance_pass_threshold=settings.distance_pass_threshold,
            slide_photo_delta_threshold=settings.slide_photo_delta_threshold,
            photo_delta_threshold=settings.photo_delta_threshold,
            light_delta_threshold=settings.light_delta_threshold,
            pyro_threshold=settings.pyro_threshold,
            ei_direction_auto_detect=settings.ei_direction_auto_detect,
        )

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True, name="SerialWorker")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _run(self):
        sensor_log_file, sensor_log_writer = init_csv_logger(settings.sensor_log_file, SENSOR_LOG_HEADERS)
        event_log_file, event_log_writer = init_csv_logger(settings.event_log_file, EVENT_LOG_HEADERS)

        try:
            try:
                with serial.Serial(settings.serial_port, settings.baud_rate, timeout=1) as ser:
                    print(f"Serial connected: {settings.serial_port}")
                    time.sleep(2)

                    while not self.stop_event.is_set():
                        if ser.in_waiting <= 0:
                            time.sleep(0.01)
                            continue

                        line_raw = ser.readline().decode("utf-8", errors="ignore").strip()
                        parts = [part.strip() for part in line_raw.split(",")]
                        if len(parts) != 5:
                            continue

                        try:
                            values = [int(part) for part in parts]
                        except ValueError:
                            continue

                        append_sensor_log(sensor_log_writer, sensor_log_file, values)
                        result = self.engine.process_values(values)
                        if result is None:
                            continue

                        event_label, from_room, to_room, room_counts = result
                        append_event_log(
                            event_log_writer,
                            event_log_file,
                            from_room,
                            to_room,
                            event_label,
                            room_counts,
                        )
                        self.state_store.update(room_counts, event_label, from_room, to_room)
            except SerialException as exc:
                print(f"Serial port open failed: {settings.serial_port} ({exc})")
        finally:
            sensor_log_file.close()
            event_log_file.close()
