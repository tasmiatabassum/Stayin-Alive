# logger.py
"""
Gap Acceptance Logger
=====================
Logs pedestrian gap acceptance events for post-session analysis.

A gap acceptance event fires each time the player steps from one zone
into a new traffic lane.  The 'accepted gap' is the time-gap (seconds)
to the nearest approaching vehicle at that crossing moment.

In real pedestrian simulation the critical gap is drawn from a
Log-Normal distribution (Petzoldt 2014; Hamed et al. 1988).  This
logger collects enough data to fit that distribution after a session.

Output: gap_acceptance_log.json  (appended per session)
"""

import json
import math
import os
from datetime import datetime

LOG_FILE = "gap_acceptance_log.json"


class GapAcceptanceLogger:
    def __init__(self, character_name: str, fps: int = 60):
        self.character_name = character_name
        self.fps            = fps
        self.events: list   = []
        self._prev_lane     = None

    # ── Lane detection ──────────────────────────────────────────────────
    @staticmethod
    def get_lane_id(player_y: int) -> str:
        from config import (FAR_LANE_Y, MIDDLE_LANE_Y, NEAR_LANE_Y,
                            LANE_HEIGHT, SCREEN_HEIGHT)
        if player_y >= SCREEN_HEIGHT - 50:
            return "sidewalk"
        elif player_y >= NEAR_LANE_Y:
            return "near"
        elif player_y >= MIDDLE_LANE_Y:
            return "middle"
        elif player_y >= FAR_LANE_Y:
            return "far"
        return "safe_zone"

    # ── Per-frame hook ──────────────────────────────────────────────────
    def check_and_log(self, player, vehicles: list,
                      frame: int, current_round: int) -> None:
        """
        Call every game frame.  Detects lane-entry transitions and logs
        the time-gap to the nearest approaching vehicle.
        """
        current_lane = self.get_lane_id(player.rect.y)

        if (self._prev_lane is not None
                and current_lane != self._prev_lane
                and current_lane not in ("sidewalk", "safe_zone")):

            time_gap = self._compute_time_gap(player, vehicles, current_lane)

            self.events.append({
                "frame":      frame,
                "round":      current_round,
                "from_zone":  self._prev_lane,
                "to_lane":    current_lane,
                "time_gap_s": round(time_gap, 3),
                "accepted":   True,   # player stepped in → accepted the gap
            })

        self._prev_lane = current_lane

    # ── Time-gap calculation ────────────────────────────────────────────
    def _compute_time_gap(self, player, vehicles: list,
                          lane_id: str) -> float:
        """
        time_gap = distance_to_nearest_approaching_vehicle / vehicle_speed
        Returns seconds.  Returns 99.9 when no vehicles are present.
        """
        from config import NEAR_LANE_Y, MIDDLE_LANE_Y, FAR_LANE_Y, LANE_HEIGHT

        lane_map = {
            "near":   NEAR_LANE_Y,
            "middle": MIDDLE_LANE_Y,
            "far":    FAR_LANE_Y,
        }
        target_y = lane_map.get(lane_id)
        if target_y is None:
            return 99.9

        px        = player.rect.centerx
        min_gap_s = 99.9

        for v in vehicles:
            if abs(v.lane_y - target_y) > LANE_HEIGHT:
                continue
            spd = abs(v.current_speed)
            if spd < 0.01:
                continue

            # Signed distance from vehicle to player along x-axis
            if v.direction_left:
                dist = v.rect.x - px        # vehicle arrives from right
            else:
                dist = px - v.rect.right    # vehicle arrives from left

            if dist > 0:
                gap_s     = (dist / spd) / self.fps
                min_gap_s = min(min_gap_s, gap_s)

        return min_gap_s

    # ── Persist ─────────────────────────────────────────────────────────
    def save(self) -> None:
        """Append this session to the JSON log file."""
        existing = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as fh:
                    existing = json.load(fh)
            except Exception:
                existing = []

        session_record = {
            "session_time": datetime.now().isoformat(),
            "character":    self.character_name,
            "events":       self.events,
            "summary":      self._compute_summary(),
        }
        existing.append(session_record)

        with open(LOG_FILE, "w") as fh:
            json.dump(existing, fh, indent=2)

    # ── Summary statistics ───────────────────────────────────────────────
    def _compute_summary(self) -> dict:
        gaps = [e["time_gap_s"] for e in self.events if e["time_gap_s"] < 99.0]
        n    = len(gaps)
        if n == 0:
            return {"n": 0}

        mean     = sum(gaps) / n
        variance = sum((g - mean) ** 2 for g in gaps) / n
        std      = math.sqrt(variance)

        # Log-normal fit: maximum-likelihood estimators
        log_gaps  = [math.log(g) for g in gaps if g > 0]
        mu_ln     = sum(log_gaps) / len(log_gaps) if log_gaps else None
        sigma_ln  = (math.sqrt(
            sum((x - mu_ln) ** 2 for x in log_gaps) / len(log_gaps)
        ) if log_gaps else None)

        return {
            "n":                n,
            "mean_gap_s":       round(mean, 3),
            "std_gap_s":        round(std, 3),
            "min_gap_s":        round(min(gaps), 3),
            "max_gap_s":        round(max(gaps), 3),
            "lognormal_mu":     round(mu_ln, 4)    if mu_ln    else None,
            "lognormal_sigma":  round(sigma_ln, 4) if sigma_ln else None,
        }

    def get_hud_lines(self) -> list[str]:
        """Short lines suitable for the in-game POST_SESSION screen."""
        s = self._compute_summary()
        if s["n"] == 0:
            return ["Gap events  : 0  (no lane crossings logged)"]
        return [
            f"Gap events  : {s['n']}",
            f"Mean gap    : {s['mean_gap_s']} s   Std: {s['std_gap_s']} s",
            f"Min / Max   : {s['min_gap_s']} s  /  {s['max_gap_s']} s",
            (f"LogNormal   : μ={s['lognormal_mu']}  σ={s['lognormal_sigma']}"
             if s.get("lognormal_mu") else "LogNormal   : insufficient data"),
        ]