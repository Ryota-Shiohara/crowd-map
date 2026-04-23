import csv
import os
import time
from collections import deque
from datetime import datetime

import matplotlib.pyplot as plt
import serial
from matplotlib.animation import FuncAnimation

from sensors import AccelSensor, DistanceSensor, LightSensor, PhotoSensor, PyroSensor

# ===== Communication settings =====
PORT = "COM3"
BAUD_RATE = 115200
DELIMITER = ","
CHANNEL_COUNT = 5

# ===== Visualization settings =====
MAX_POINTS = 100
Y_MIN = 0
Y_MAX = 1023

# ===== Logging settings =====
LOG_FILE = "sensor_log.csv"
LOG_HEADERS = [
    "timestamp",
    "sensor_distance",
    "sensor_accel",
    "sensor_photo",
    "sensor_light",
    "sensor_pyro",
    "from_room",
    "to_room",
    "event_label",
    "count_K",
    "count_E",
    "count_I",
    "count_O",
]

# ===== Detection settings (temporary values; tune during on-site tests) =====
DISTANCE_PASS_THRESHOLD = 300
ACCEL_DELTA_THRESHOLD = 80
PHOTO_DELTA_THRESHOLD = 100
LIGHT_DELTA_THRESHOLD = 120
PYRO_THRESHOLD = 600

# Door and passage events are linked within this time window.
DOOR_LINK_WINDOW_SEC = 3.0

SENSOR_LABELS = ["Distance", "Accel(X)", "Photo", "Light", "Pyro"]

# ===== Room flow settings =====
ROOMS = ["K", "E", "I", "O"]

# One monitoring node corresponds to one gate profile.
# For I and O, two one-way entrances are modeled explicitly.
GATE_PROFILES = {
    "K_to_I": ("K", "I"),
    "I_to_K": ("I", "K"),
    "E_to_I": ("E", "I"),
    "I_to_E": ("I", "E"),
    "O_to_I": ("O", "I"),
    "I_to_O": ("I", "O"),
}
ACTIVE_GATE = "I_to_O"

# Initial people count can be edited for each room.
INITIAL_COUNTS = {
    "K": 0,
    "E": 0,
    "I": 0,
    "O": 0,
}


def init_csv_logger(path):
    file_exists = os.path.exists(path)
    need_header = (not file_exists) or os.path.getsize(path) == 0
    log_file = open(path, "a", newline="", encoding="utf-8")
    writer = csv.writer(log_file)
    if need_header:
        writer.writerow(LOG_HEADERS)
        log_file.flush()
    return log_file, writer


def append_log(writer, log_file, values, from_room, to_room, event_label, room_counts):
    timestamp = datetime.now().isoformat(timespec="seconds")
    writer.writerow([
        timestamp,
        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
        from_room,
        to_room,
        event_label,
        room_counts["K"],
        room_counts["E"],
        room_counts["I"],
        room_counts["O"],
    ])
    log_file.flush()


def apply_room_transition(room_counts, from_room, to_room):
    if room_counts[from_room] <= 0:
        return False
    room_counts[from_room] -= 1
    room_counts[to_room] += 1
    return True


def main():
    latest_values = [None] * CHANNEL_COUNT
    sample_count = 0

    x_data = deque(maxlen=MAX_POINTS)
    y_data = [deque(maxlen=MAX_POINTS) for _ in range(CHANNEL_COUNT)]

    distance_sensor = DistanceSensor(DISTANCE_PASS_THRESHOLD)
    accel_sensor = AccelSensor(ACCEL_DELTA_THRESHOLD)
    photo_sensor = PhotoSensor(PHOTO_DELTA_THRESHOLD)
    light_sensor = LightSensor(LIGHT_DELTA_THRESHOLD)
    pyro_sensor = PyroSensor(PYRO_THRESHOLD)

    room_counts = dict(INITIAL_COUNTS)
    from_room, to_room = GATE_PROFILES[ACTIVE_GATE]

    door_link_deadline = 0.0

    log_file, log_writer = init_csv_logger(LOG_FILE)

    with serial.Serial(PORT, BAUD_RATE, timeout=1) as ser:
        print("Serial connected:", PORT)
        time.sleep(2)

        fig, ax = plt.subplots()
        lines = []
        for idx in range(CHANNEL_COUNT):
            line_obj, = ax.plot([], [], label=SENSOR_LABELS[idx])
            lines.append(line_obj)

        ax.set_title("Real-time Multi-Sensor Monitor")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Value")
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.set_xlim(0, MAX_POINTS - 1)
        ax.legend(loc="upper right")

        value_text = ax.text(0.02, 0.95, "", transform=ax.transAxes, verticalalignment="top")

        def update(frame):
            nonlocal latest_values
            nonlocal sample_count
            nonlocal room_counts
            nonlocal door_link_deadline

            while ser.in_waiting > 0:
                line_raw = ser.readline().decode("utf-8", errors="ignore").strip()

                try:
                    parts = [part.strip() for part in line_raw.split(DELIMITER)]
                    if len(parts) != CHANNEL_COUNT:
                        raise ValueError(f"expected {CHANNEL_COUNT} values, got {len(parts)}")

                    values = [int(part) for part in parts]
                    latest_values = values

                    distance_val, accel_val, photo_val, light_val, pyro_val = values

                    passage_rising, _ = distance_sensor.detect_passage_rising(distance_val)
                    accel_trigger = accel_sensor.detect_motion(accel_val)
                    photo_trigger = photo_sensor.detect_door_change(photo_val)
                    light_trigger = light_sensor.detect_presence_hint(light_val)
                    pyro_trigger = pyro_sensor.detect_presence(pyro_val)

                    now = time.time()
                    event_label = "idle"
                    event_from_room = ""
                    event_to_room = ""

                    if accel_trigger or photo_trigger:
                        door_link_deadline = now + DOOR_LINK_WINDOW_SEC
                        event_label = "door_motion"

                    if passage_rising:
                        if now <= door_link_deadline:
                            event_from_room = from_room
                            event_to_room = to_room
                            if light_trigger or pyro_trigger:
                                moved = apply_room_transition(room_counts, from_room, to_room)
                                if moved:
                                    event_label = "passage_move_confirmed"
                                else:
                                    event_label = "passage_blocked_no_person"
                            else:
                                event_label = "passage_low_confidence"
                        else:
                            event_label = "passage_only"

                    append_log(
                        log_writer,
                        log_file,
                        values,
                        event_from_room,
                        event_to_room,
                        event_label,
                        room_counts,
                    )

                    x_data.append(sample_count)
                    for idx, value in enumerate(values):
                        y_data[idx].append(value)
                    sample_count += 1

                except ValueError:
                    print("Invalid:", line_raw)

            if len(x_data) > 0:
                x_plot = list(range(len(x_data)))
                for idx, line_obj in enumerate(lines):
                    line_obj.set_data(x_plot, list(y_data[idx]))
                ax.set_xlim(0, max(MAX_POINTS - 1, len(x_plot) - 1))

                latest_text = ", ".join(
                    f"{SENSOR_LABELS[idx]}={value}"
                    for idx, value in enumerate(latest_values)
                )
                count_text = ", ".join(
                    f"{room}={room_counts[room]}"
                    for room in ROOMS
                )
                value_text.set_text(
                    f"Gate: {ACTIVE_GATE} ({from_room}->{to_room})\n"
                    f"Latest: {latest_text}\n"
                    f"Counts: {count_text}"
                )

            return tuple(lines) + (value_text,)

        ani = FuncAnimation(fig, update, interval=100, cache_frame_data=False)

        try:
            plt.show()
        finally:
            ser.close()
            log_file.close()
            print("Serial closed")


if __name__ == "__main__":
    main()
