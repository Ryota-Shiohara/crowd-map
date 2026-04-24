class LightSensor:
    def __init__(self, delta_threshold=120):
        self.delta_threshold = delta_threshold
        self.baseline = None
        self.is_lit = None

    def detect_presence_hint(self, value):
        lit, _, _ = self.detect_light_edges(value)
        return lit

    def detect_light_edges(self, value):
        if self.baseline is None:
            self.baseline = value
            self.is_lit = False
            return False, False, False

        lit_now = (value - self.baseline) >= self.delta_threshold

        if self.is_lit is None:
            self.is_lit = lit_now
            return lit_now, False, False

        rising = (not self.is_lit) and lit_now
        falling = self.is_lit and (not lit_now)
        self.is_lit = lit_now
        return lit_now, rising, falling
