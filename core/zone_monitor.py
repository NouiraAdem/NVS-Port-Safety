"""Safety-zone state machine (no Qt, easy to test)."""


class ZoneMonitor:
    """
    Per-track debounce:
      ENTER: `enter_frames` consecutive inside frames -> one INTRUSION event
      EXIT : `exit_frames` consecutive outside frames -> one EXIT event
    """

    def __init__(
        self,
        rect,
        enter_frames=10,
        exit_frames=15,
        min_confidence=0.60,
        target_class="person",
    ):
        self.set_rect(*rect)
        self.enter_frames = enter_frames
        self.exit_frames = exit_frames
        self.min_confidence = min_confidence
        self.target_class = target_class

        self.alert_count = 0
        self.current_intruders = set()
        self._tracks = {}

    @property
    def rect(self):
        return (self.x1, self.y1, self.x2, self.y2)

    def set_rect(self, x1, y1, x2, y2):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    def contains(self, cx, cy):
        return self.x1 <= cx <= self.x2 and self.y1 <= cy <= self.y2

    def people_in_zone(self, detections):
        inside = {}

        for index, d in enumerate(detections):
            if d["class_name"].lower() != self.target_class:
                continue
            if d["confidence"] < self.min_confidence:
                continue
            if not self.contains(d["cx"], d["cy"]):
                continue

            track_id = (
                d["track_id"] if d["track_id"] is not None else 100000 + index
            )
            inside[track_id] = {
                "class_name": d["class_name"],
                "confidence": d["confidence"],
            }

        return inside

    def update(self, detections):
        """
        Returns (current_intruders, events) where each event is
        (event_type, class_name, track_id, confidence).
        """
        people = self.people_in_zone(detections)
        events = []

        for track_id, info in people.items():
            state = self._tracks.setdefault(
                track_id,
                {
                    "inside_frames": 0,
                    "outside_frames": 0,
                    "active": False,
                    "class_name": info["class_name"],
                    "confidence": info["confidence"],
                },
            )

            state["class_name"] = info["class_name"]
            state["confidence"] = info["confidence"]
            state["inside_frames"] += 1
            state["outside_frames"] = 0

            if not state["active"] and state["inside_frames"] >= self.enter_frames:
                state["active"] = True
                self.alert_count += 1
                events.append(
                    ("INTRUSION", state["class_name"], track_id, state["confidence"])
                )

        for track_id, state in list(self._tracks.items()):
            if track_id in people:
                continue

            state["outside_frames"] += 1
            state["inside_frames"] = 0

            if state["active"] and state["outside_frames"] >= self.exit_frames:
                state["active"] = False
                events.append(
                    ("EXIT", state["class_name"], track_id, state["confidence"])
                )

        self.current_intruders = {
            tid for tid, s in self._tracks.items() if s["active"]
        }

        for track_id, state in list(self._tracks.items()):
            if not state["active"] and state["outside_frames"] > 60:
                del self._tracks[track_id]

        return set(self.current_intruders), events

    def reset_tracks(self):
        self._tracks.clear()
        self.current_intruders = set()

    def reset(self):
        self.reset_tracks()
        self.alert_count = 0
