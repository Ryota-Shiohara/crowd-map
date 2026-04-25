class PyroSensor:
    def __init__(self, threshold=600):
        self.threshold = threshold
        self.last_state = False

    def detect_presence(self, value):
        return value >= self.threshold

    def detect_edges(self, value):
        current = self.detect_presence(value)
        is_rising = current and not self.last_state
        is_falling = (not current) and self.last_state
        self.last_state = current
        return is_rising, is_falling
