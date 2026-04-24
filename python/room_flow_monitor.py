import csv
import os
import time
from collections import deque
from datetime import datetime

import matplotlib.pyplot as plt
import serial
from matplotlib.animation import FuncAnimation

from sensors import AccelSensor, DistanceSensor, LightSensor, PhotoSensor, PyroSensor

# ===== 通信設定 =====
PORT = "COM3"
BAUD_RATE = 115200
DELIMITER = ","
CHANNEL_COUNT = 5

# ===== 可視化設定 =====
MAX_POINTS = 100
Y_MIN = 0
Y_MAX = 1023

# ===== ログ設定 =====
SENSOR_LOG_FILE = "sensor_log.csv"
SENSOR_LOG_HEADERS = [
    "timestamp",
    "sensor_distance",
    "sensor_accel",
    "sensor_photo",
    "sensor_light",
    "sensor_pyro",
]

EVENT_LOG_FILE = "event_log.csv"
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

# ===== 検知設定（暫定値。現地テストで調整） =====
DISTANCE_PASS_THRESHOLD = 300
ACCEL_DELTA_THRESHOLD = 80
PHOTO_DELTA_THRESHOLD = 100
LIGHT_DELTA_THRESHOLD = 120
PYRO_THRESHOLD = 600

# E-Iラインの方向は焦電センサーのエッジで自動検知
# 焦電 0→1（接近）= I→E、焦電 1→0（離脱）= E→I
EI_DIRECTION_AUTO_DETECT = True

# 現在のレイアウトではI-Oラインは一方通行
IO_GATE_OUT = ("I", "O")  # 加速度ライン
IO_GATE_IN = ("O", "I")   # フォトリフレクターライン

SENSOR_LABELS = ["Distance", "Accel(X)", "Photo", "Light", "Pyro"]

# ===== 部屋人流設定 =====
ROOMS = ["K", "E", "I", "O"]

# Kには同時に1人までしか入れない
ROOM_CAPACITY = {
    "K": 1,
}

# 各部屋の初期人数はここで編集
INITIAL_COUNTS = {
    "K": 0,
    "E": 0,
    "I": 0,
    "O": 10,
}


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


def apply_room_transition(room_counts, from_room, to_room):
    if room_counts[from_room] <= 0:
        return False

    capacity = ROOM_CAPACITY.get(to_room)
    if capacity is not None and room_counts[to_room] >= capacity:
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

    sensor_log_file, sensor_log_writer = init_csv_logger(SENSOR_LOG_FILE, SENSOR_LOG_HEADERS)
    event_log_file, event_log_writer = init_csv_logger(EVENT_LOG_FILE, EVENT_LOG_HEADERS)

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
                    accel_rising = accel_sensor.detect_rising(accel_val)
                    photo_rising = photo_sensor.detect_rising(photo_val)
                    _, light_rising, light_falling = light_sensor.detect_light_edges(light_val)
                    pyro_rising, pyro_falling = pyro_sensor.detect_edges(pyro_val)

                    event_label = "idle"
                    event_from_room = ""
                    event_to_room = ""

                    # 光ONで I->K、光OFFで K->I とみなす
                    if light_rising:
                        event_from_room, event_to_room = "I", "K"
                        moved = apply_room_transition(room_counts, event_from_room, event_to_room)
                        if moved:
                            event_label = "ik_move_confirmed"
                        else:
                            event_label = "ik_blocked"

                    if light_falling:
                        event_from_room, event_to_room = "K", "I"
                        moved = apply_room_transition(room_counts, event_from_room, event_to_room)
                        if moved:
                            event_label = "ki_move_confirmed"
                        else:
                            event_label = "ki_blocked"

                    # E-I境界（測距センサーライン）
                    if passage_rising:
                        # 焦電エッジで方向判定
                        if EI_DIRECTION_AUTO_DETECT:
                            if pyro_rising:
                                # 焦電が 0→1: 人がセンサーに接近中 = I→E（Iから来た）
                                event_from_room, event_to_room = "I", "E"
                            elif pyro_falling:
                                # 焦電が 1→0: 人がセンサーから離脱 = E→I（Eから来た）
                                event_from_room, event_to_room = "E", "I"
                            else:
                                # 焦電が安定中（判定スキップ）
                                event_label = "ei_passage_unclear_pyro_stable"
                        else:
                            event_from_room, event_to_room = "I", "E"  # フォールバック

                            if event_from_room and event_to_room:
                                moved = apply_room_transition(room_counts, event_from_room, event_to_room)
                                if moved:
                                    event_label = "ei_move_confirmed"
                                else:
                                    event_label = "ei_blocked_no_person"

                    # I->O 一方通行ゲート（加速度ライン）
                    if accel_rising:
                        event_from_room, event_to_room = IO_GATE_OUT
                        moved = apply_room_transition(room_counts, event_from_room, event_to_room)
                        if moved:
                            event_label = "io_out_move_confirmed"
                        else:
                            event_label = "io_out_blocked_no_person"

                    # O->I 一方通行ゲート（フォトリフレクターライン）
                    if photo_rising:
                        event_from_room, event_to_room = IO_GATE_IN
                        moved = apply_room_transition(room_counts, event_from_room, event_to_room)
                        if moved:
                            event_label = "io_in_move_confirmed"
                        else:
                            event_label = "io_in_blocked_no_person"

                    append_sensor_log(sensor_log_writer, sensor_log_file, values)

                    if event_label != "idle":
                        append_event_log(
                            event_log_writer,
                            event_log_file,
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
                    f"Layout: K/E-I-O (Distance=E-I, Accel=I->O, Photo=O->I)\n"
                    f"Latest: {latest_text}\n"
                    f"Counts: {count_text}"
                )

            return tuple(lines) + (value_text,)

        ani = FuncAnimation(fig, update, interval=100, cache_frame_data=False)

        try:
            plt.show()
        finally:
            ser.close()
            sensor_log_file.close()
            event_log_file.close()
            print("Serial closed")


if __name__ == "__main__":
    main()
