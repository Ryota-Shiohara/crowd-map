class PyroSensor:
    def __init__(self, threshold=600):
        self.threshold = threshold

    def detect_presence(self, value):
        return value >= self.threshold
