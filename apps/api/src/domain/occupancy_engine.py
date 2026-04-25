from typing import List, Optional, Tuple

from ..sensors import DistanceSensor, LightSensor, PhotoSensor, PyroSensor


class OccupancyEngine:
    ROOMS = ["K", "E", "I", "O"]
    IO_GATE_OUT = ("I", "O")
    IO_GATE_IN = ("O", "I")

    def __init__(
        self,
        initial_counts: dict,
        room_capacity: dict,
        distance_pass_threshold: int,
        slide_photo_delta_threshold: int,
        photo_delta_threshold: int,
        light_delta_threshold: int,
        pyro_threshold: int,
        ei_direction_auto_detect: bool = True,
    ):
        self.room_counts = dict(initial_counts)
        self.room_capacity = room_capacity
        self.ei_direction_auto_detect = ei_direction_auto_detect

        self.distance_sensor = DistanceSensor(distance_pass_threshold)
        self.slide_photo_sensor = PhotoSensor(slide_photo_delta_threshold)
        self.photo_sensor = PhotoSensor(photo_delta_threshold)
        self.light_sensor = LightSensor(light_delta_threshold)
        self.pyro_sensor = PyroSensor(pyro_threshold)

    def apply_room_transition(self, from_room: str, to_room: str) -> bool:
        if self.room_counts[from_room] <= 0:
            return False

        capacity = self.room_capacity.get(to_room)
        if capacity is not None and self.room_counts[to_room] >= capacity:
            return False

        self.room_counts[from_room] -= 1
        self.room_counts[to_room] += 1
        return True

    def process_values(self, values: List[int]) -> Optional[Tuple[str, str, str, dict]]:
        distance_val, slide_photo_val, photo_val, light_val, pyro_val = values

        passage_rising, _ = self.distance_sensor.detect_passage_rising(distance_val)
        slide_photo_rising = self.slide_photo_sensor.detect_rising(slide_photo_val)
        photo_rising = self.photo_sensor.detect_rising(photo_val)
        _, light_rising, light_falling = self.light_sensor.detect_light_edges(light_val)
        pyro_rising, pyro_falling = self.pyro_sensor.detect_edges(pyro_val)

        event_label = "idle"
        event_from_room = ""
        event_to_room = ""

        if light_rising:
            event_from_room, event_to_room = "I", "K"
            moved = self.apply_room_transition(event_from_room, event_to_room)
            event_label = "ik_move_confirmed" if moved else "ik_blocked"

        if light_falling:
            event_from_room, event_to_room = "K", "I"
            moved = self.apply_room_transition(event_from_room, event_to_room)
            event_label = "ki_move_confirmed" if moved else "ki_blocked"

        if passage_rising:
            if self.ei_direction_auto_detect:
                if pyro_rising:
                    event_from_room, event_to_room = "I", "E"
                elif pyro_falling:
                    event_from_room, event_to_room = "E", "I"
                else:
                    event_label = "ei_passage_unclear_pyro_stable"

                if event_from_room and event_to_room:
                    moved = self.apply_room_transition(event_from_room, event_to_room)
                    event_label = "ei_move_confirmed" if moved else "ei_blocked_no_person"
            else:
                event_from_room, event_to_room = "I", "E"
                moved = self.apply_room_transition(event_from_room, event_to_room)
                event_label = "ei_move_confirmed" if moved else "ei_blocked_no_person"

        if slide_photo_rising:
            event_from_room, event_to_room = self.IO_GATE_OUT
            moved = self.apply_room_transition(event_from_room, event_to_room)
            event_label = "io_out_move_confirmed" if moved else "io_out_blocked_no_person"

        if photo_rising:
            event_from_room, event_to_room = self.IO_GATE_IN
            moved = self.apply_room_transition(event_from_room, event_to_room)
            event_label = "io_in_move_confirmed" if moved else "io_in_blocked_no_person"

        if event_label == "idle":
            return None

        return event_label, event_from_room, event_to_room, dict(self.room_counts)
