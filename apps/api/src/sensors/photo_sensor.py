class PhotoSensor:
    def __init__(self, delta_threshold=100):
        self.delta_threshold = delta_threshold
        self.baseline = None
        self.last_state = False

    def detect_door_change(self, value):
        if self.baseline is None:
            self.baseline = value
            return False
        return abs(value - self.baseline) >= self.delta_threshold

    def detect_rising(self, value):
        current = self.detect_door_change(value)
        is_rising = current and not self.last_state
        self.last_state = current
        return is_rising

    def detect_falling(self, value):
        current = self.detect_door_change(value)
        is_falling = (not current) and self.last_state
        self.last_state = current
        return is_falling
