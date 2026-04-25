class DistanceSensor:
    def __init__(self, pass_threshold=300):
        self.pass_threshold = pass_threshold
        self.last_trigger = False

    def detect_passage_rising(self, value):
        trigger = value < self.pass_threshold
        rising = trigger and not self.last_trigger
        self.last_trigger = trigger
        return rising, trigger
