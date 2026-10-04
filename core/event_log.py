"""In-memory security event log with CSV export."""

import csv
from datetime import datetime


class EventLog:
    FIELDS = ["time", "event", "object", "track_id", "confidence", "zone"]

    def __init__(self, max_events=100):
        self.items = []  # newest first
        self.max_events = max_events

    def __len__(self):
        return len(self.items)

    def add(self, event_type, class_name, track_id, confidence):
        event = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "event": event_type,
            "object": class_name,
            "track_id": track_id,
            "confidence": confidence,
            "zone": "ENTERED" if event_type == "INTRUSION" else "EXITED",
        }
        self.items.insert(0, event)
        del self.items[self.max_events:]
        return event

    def clear(self):
        self.items.clear()

    def export_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(self.FIELDS)
            for e in reversed(self.items):  # oldest first
                writer.writerow(
                    [e["time"], e["event"], e["object"], e["track_id"],
                     f'{e["confidence"]:.3f}', e["zone"]]
                )
