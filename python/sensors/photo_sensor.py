class PhotoSensor:
    def __init__(self, delta_threshold=100):
        self.delta_threshold = delta_threshold
        self.baseline = None

    def detect_door_change(self, value):
        if self.baseline is None:
            self.baseline = value
            return False
        return abs(value - self.baseline) >= self.delta_threshold
