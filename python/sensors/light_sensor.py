class LightSensor:
    def __init__(self, delta_threshold=120):
        self.delta_threshold = delta_threshold
        self.baseline = None

    def detect_presence_hint(self, value):
        if self.baseline is None:
            self.baseline = value
            return False
        return (value - self.baseline) >= self.delta_threshold
