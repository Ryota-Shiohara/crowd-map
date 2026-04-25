import csv
import os
from datetime import datetime


SENSOR_LOG_HEADERS = [
    "timestamp",
    "sensor_distance",
    "sensor_accel",
    "sensor_photo",
    "sensor_light",
    "sensor_pyro",
]

EVENT_LOG_HEADERS = [
    "timestamp",
    "from_room",
    "to_room",
    "event_label",
    "count_K",
    "count_E",
    "count_I",
    "count_O",
]


def init_csv_logger(path, headers):
    file_exists = os.path.exists(path)
    need_header = (not file_exists) or os.path.getsize(path) == 0
    log_file = open(path, "a", newline="", encoding="utf-8")
    writer = csv.writer(log_file)
    if need_header:
        writer.writerow(headers)
        log_file.flush()
    return log_file, writer


def append_sensor_log(writer, log_file, values):
    timestamp = datetime.now().isoformat(timespec="seconds")
    writer.writerow([
        timestamp,
        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
    ])
    log_file.flush()


def append_event_log(writer, log_file, from_room, to_room, event_label, room_counts):
    timestamp = datetime.now().isoformat(timespec="seconds")
    writer.writerow([
        timestamp,
        from_room,
        to_room,
        event_label,
        room_counts["K"],
        room_counts["E"],
        room_counts["I"],
        room_counts["O"],
    ])
    log_file.flush()
