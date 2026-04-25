import time
from collections import deque

import matplotlib.pyplot as plt
import serial
from matplotlib.animation import FuncAnimation

from config import settings
from sensors import DistanceSensor, LightSensor, PhotoSensor, PyroSensor

CHANNEL_COUNT = 5
MAX_POINTS = 100
Y_MIN = 0
Y_MAX = 1023
DELIMITER = ","
SENSOR_LABELS = ["Distance", "Photo(Slide)", "Photo", "Light", "Pyro"]


def main():
    latest_values = [None] * CHANNEL_COUNT
    sample_count = 0

    x_data = deque(maxlen=MAX_POINTS)
    y_data = [deque(maxlen=MAX_POINTS) for _ in range(CHANNEL_COUNT)]

    # センサー初期化だけ行い、波形表示に必要な値の流れを見やすくする
    distance_sensor = DistanceSensor(settings.distance_pass_threshold)
    slide_photo_sensor = PhotoSensor(settings.slide_photo_delta_threshold)
    photo_sensor = PhotoSensor(settings.photo_delta_threshold)
    light_sensor = LightSensor(settings.light_delta_threshold)
    pyro_sensor = PyroSensor(settings.pyro_threshold)

    with serial.Serial(settings.serial_port, settings.baud_rate, timeout=1) as ser:
        print(f"Serial connected: {settings.serial_port}")
        time.sleep(2)

        fig, ax = plt.subplots()
        lines = []
        for idx in range(CHANNEL_COUNT):
            line_obj, = ax.plot([], [], label=SENSOR_LABELS[idx])
            lines.append(line_obj)

        ax.set_title("Real-time Sensor Waveform")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Value")
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.set_xlim(0, MAX_POINTS - 1)
        ax.legend(loc="upper right")

        value_text = ax.text(0.02, 0.95, "", transform=ax.transAxes, verticalalignment="top")

        def update(frame):
            nonlocal latest_values
            nonlocal sample_count

            while ser.in_waiting > 0:
                line_raw = ser.readline().decode("utf-8", errors="ignore").strip()
                parts = [part.strip() for part in line_raw.split(DELIMITER)]
                if len(parts) != CHANNEL_COUNT:
                    continue

                try:
                    values = [int(part) for part in parts]
                except ValueError:
                    continue

                latest_values = values
                distance_val, slide_photo_val, photo_val, light_val, pyro_val = values

                # センサーの状態更新は保持しておくと、波形を見るときに判定の切り替わりが追いやすい
                distance_sensor.detect_passage_rising(distance_val)
                slide_photo_sensor.detect_rising(slide_photo_val)
                photo_sensor.detect_rising(photo_val)
                light_sensor.detect_light_edges(light_val)
                pyro_sensor.detect_edges(pyro_val)

                x_data.append(sample_count)
                for idx, value in enumerate(values):
                    y_data[idx].append(value)
                sample_count += 1

            if len(x_data) > 0:
                x_plot = list(range(len(x_data)))
                for idx, line_obj in enumerate(lines):
                    line_obj.set_data(x_plot, list(y_data[idx]))
                ax.set_xlim(0, max(MAX_POINTS - 1, len(x_plot) - 1))

                latest_text = ", ".join(
                    f"{SENSOR_LABELS[idx]}={value}"
                    for idx, value in enumerate(latest_values)
                )
                value_text.set_text(f"Latest: {latest_text}")

            return tuple(lines) + (value_text,)

        ani = FuncAnimation(fig, update, interval=100, cache_frame_data=False)

        try:
            plt.show()
        finally:
            ser.close()
            print("Serial closed")


if __name__ == "__main__":
    main()
