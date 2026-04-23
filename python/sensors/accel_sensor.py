class AccelSensor:
    def __init__(self, delta_threshold=80):
        self.delta_threshold = delta_threshold
        self.baseline = None

    def detect_motion(self, value):
        if self.baseline is None:
            self.baseline = value
            return False
        return abs(value - self.baseline) >= self.delta_threshold
