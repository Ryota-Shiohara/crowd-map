class PyroSensor:
    def __init__(self, threshold=600):
        self.threshold = threshold
        self.last_state = False  # 前フレームの状態

    def detect_presence(self, value):
        return value >= self.threshold

    def detect_edges(self, value):
        """1サンプル評価で焦電の立ち上がり/立ち下がりを返す。"""
        current = self.detect_presence(value)
        is_rising = current and not self.last_state
        is_falling = (not current) and self.last_state
        self.last_state = current
        return is_rising, is_falling

    def detect_rising(self, value):
        """焦電 0→1 遷移（人が接近）"""
        is_rising, _ = self.detect_edges(value)
        return is_rising

    def detect_falling(self, value):
        """焦電 1→0 遷移（人が離脱）"""
        _, is_falling = self.detect_edges(value)
        return is_falling
