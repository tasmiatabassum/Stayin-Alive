# spawner.py
import pygame
import random
import os
from vehicle import Vehicle
from config import SCREEN_WIDTH, FAR_LANE_Y, MIDDLE_LANE_Y, NEAR_LANE_Y, SUB_LANE_OFFSET_0, SUB_LANE_OFFSET_1

# ── Vehicle sizes (width, height) ─────────────────────────────────────────
ASSET_MAP = {
    "motorcycle": [("bike.png", (80, 35))],
    "cng": [("cng.png", (95, 45))],
    "car": [("car_blue.jpg", (140, 60)), ("car_red.png", (140, 60))],
    "truck": [("truck.png", (260, 75))],
    "bus": [("bus.png", (280, 75)), ("bus_grey.png", (280, 75)), ("bus_red.png", (280, 75))],
}

# Spawn convention:
# sub-lane 0 -> direction_left = False (travels RIGHT)
# sub-lane 1 -> direction_left = True  (travels LEFT)
_CORRECT_SUB = {False: 0, True: 1}

LANE_CHANGE_DIST = 200  # px ahead a vehicle looks for oncoming traffic


class Spawner:
    def __init__(self, round_manager, env_manager):
        self.round_manager = round_manager
        self.env_manager = env_manager
        self.vehicles = []
        self.spawn_timers = [0, 0, 0]
        self.images = {"car": [], "motorcycle": [], "bus": [], "truck": [], "cng": []}
        self._load_assets()

    def _load_assets(self):
        for vtype, assets in ASSET_MAP.items():
            for filename, size in assets:
                if os.path.exists(filename):
                    try:
                        img = pygame.image.load(filename).convert_alpha()
                        if filename == "bike.png":
                            img = pygame.transform.flip(img, True, False)
                        img = pygame.transform.scale(img, size)
                        img_right = pygame.transform.flip(img, True, False)
                        self.images[vtype].append({"left": img, "right": img_right, "size": size})
                    except Exception as e:
                        print(f"Warning: Could not load {filename}: {e}")

    def update(self):
        freq = self.round_manager.get_spawn_frequency()
        probs = self.round_manager.get_lane_activation_probs()
        weights = self.round_manager.get_vehicle_weights()
        vtypes = list(weights.keys())
        vprobs = list(weights.values())
        env_p_slow = self.env_manager.vehicle_p_slow_mult if self.env_manager else 1.0

        # 1. Smooth lane-change Y easing
        for v in self.vehicles:
            if hasattr(v, '_target_y'):
                diff = v._target_y - float(v.rect.y)
                if abs(diff) > 0.5:
                    v.rect.y = int(v.rect.y + diff * 0.14)
                    v.lane_y = v.rect.y

        # 2. Lane-change decisions (middle lane only)
        for v in self.vehicles:
            self._maybe_lane_change(v)

        # 3. NaSch CA physics (Now strictly sub-lane based)
        for v in self.vehicles:
            gap = self._calculate_gap_ahead(v)
            v.update(gap, env_p_slow)

        # 4. Cull off-screen
        self.vehicles = [v for v in self.vehicles if -500 < v.rect.x < SCREEN_WIDTH + 500]

        # 5. Spawn
        for lane_y, p_idx in [(NEAR_LANE_Y, 0), (MIDDLE_LANE_Y, 1), (FAR_LANE_Y, 2)]:
            self.spawn_timers[p_idx] += 1
            if self.spawn_timers[p_idx] > freq:
                if random.random() < probs[p_idx]:
                    self._try_spawn(random.choices(vtypes, weights=vprobs)[0], lane_y)
                self.spawn_timers[p_idx] = random.randint(-10, 10)

    def _maybe_lane_change(self, vehicle):
        if not hasattr(vehicle, '_base_lane_y') or vehicle._base_lane_y != MIDDLE_LANE_Y:
            return
        if vehicle._sub_lane is None:
            return
        if abs(getattr(vehicle, '_target_y', vehicle.rect.y) - vehicle.rect.y) > 12:
            return

        correct_sub = _CORRECT_SUB[vehicle.direction_left]

        # RULE 1: Yielding (Return to correct lane if we are in the wrong one)
        if vehicle._sub_lane != correct_sub:
            if self._is_sub_lane_clear(vehicle, correct_sub):
                vehicle._sub_lane = correct_sub
                offset = SUB_LANE_OFFSET_0 if correct_sub == 0 else SUB_LANE_OFFSET_1
                vehicle._target_y = float(MIDDLE_LANE_Y + offset - (vehicle.rect.height // 2) + 20)
                return

        # RULE 2: Panic Dodge (If we are in correct lane, but an oncoming car is trapped)
        oncoming_dist = None
        for other in self.vehicles:
            if other is vehicle or other.direction_left == vehicle.direction_left:
                continue
            # Check for oncoming cars explicitly in OUR sub-lane
            if other._base_lane_y == vehicle._base_lane_y and other._sub_lane == vehicle._sub_lane:
                if vehicle.direction_left and other.rect.left < vehicle.rect.left:
                    dist = vehicle.rect.left - other.rect.right
                    if 0 < dist < LANE_CHANGE_DIST: oncoming_dist = dist
                elif not vehicle.direction_left and other.rect.right > vehicle.rect.right:
                    dist = other.rect.left - vehicle.rect.right
                    if 0 < dist < LANE_CHANGE_DIST: oncoming_dist = dist

        if oncoming_dist is not None and oncoming_dist < 120:
            wrong_sub = 1 if correct_sub == 0 else 0
            if self._is_sub_lane_clear(vehicle, wrong_sub):
                vehicle._sub_lane = wrong_sub
                offset = SUB_LANE_OFFSET_0 if wrong_sub == 0 else SUB_LANE_OFFSET_1
                vehicle._target_y = float(MIDDLE_LANE_Y + offset - (vehicle.rect.height // 2) + 20)

    def _is_sub_lane_clear(self, vehicle, target_sub):
        """Checks if there is X-axis space in the target sub-lane to merge safely."""
        for o in self.vehicles:
            if o is vehicle or o._base_lane_y != vehicle._base_lane_y:
                continue
            if o._sub_lane == target_sub:
                if not (o.rect.right < vehicle.rect.left - 40 or o.rect.left > vehicle.rect.right + 40):
                    return False
        return True

    def _try_spawn(self, vtype, base_y):
        is_sub_0 = random.choice([True, False])
        sub_offset = SUB_LANE_OFFSET_0 if is_sub_0 else SUB_LANE_OFFSET_1
        y = base_y + sub_offset

        if base_y == FAR_LANE_Y:
            direction_left = False
        elif base_y == NEAR_LANE_Y:
            direction_left = True
        else:
            if random.random() < self.round_manager.get_middle_bidirectional_prob():
                direction_left = not is_sub_0
            else:
                direction_left = True

        asset_list = self.images.get(vtype, [])
        if asset_list:
            asset = random.choice(asset_list)
            image_dict = asset
            w, h = asset["size"]
        else:
            image_dict = None
            w, h = 120, 55

        x = SCREEN_WIDTH + 20 if direction_left else -w - 20
        y_centered = y - (h // 2) + 20
        target_sub = 0 if is_sub_0 else 1

        min_gap = self.round_manager.get_spawn_gap()
        for v in self.vehicles:
            # Check logic strictly against the assigned sub-lane
            if v._base_lane_y == base_y and v._sub_lane == target_sub and v.direction_left == direction_left:
                if direction_left and v.rect.x > SCREEN_WIDTH - min_gap: return
                if not direction_left and v.rect.x < min_gap: return

        speed = self.round_manager.get_speed_sample(vtype, lane=base_y)
        p_slow = self.round_manager.get_nasch_p_slow(vtype)
        new_v = Vehicle(vtype, x, y_centered, direction_left, speed, p_slow, image_dict, (w, h))
        new_v._sub_lane = target_sub
        new_v._base_lane_y = base_y
        new_v._target_y = float(y_centered)
        self.vehicles.append(new_v)

    def _calculate_gap_ahead(self, vehicle):
        min_gap = float('inf')

        for other in self.vehicles:
            if other is vehicle:
                continue

            # Physics are now STRICTLY decoupled from bounding boxes.
            # Vehicles only block each other if they are assigned to the exact same lane and sub-lane.
            if vehicle._base_lane_y != other._base_lane_y: continue
            if vehicle._sub_lane != other._sub_lane: continue

            if vehicle.direction_left == other.direction_left:
                if vehicle.direction_left:
                    if other.rect.right <= vehicle.rect.left + 15:
                        gap = vehicle.rect.left - other.rect.right
                        if gap < min_gap: min_gap = gap
                else:
                    if other.rect.left >= vehicle.rect.right - 15:
                        gap = other.rect.left - vehicle.rect.right
                        if gap < min_gap: min_gap = gap
            else:
                if vehicle.direction_left:
                    if other.rect.left <= vehicle.rect.left:
                        gap = vehicle.rect.left - other.rect.right
                        if gap < min_gap: min_gap = gap
                else:
                    if other.rect.right >= vehicle.rect.right:
                        gap = other.rect.left - vehicle.rect.right
                        if gap < min_gap: min_gap = gap

        return min_gap if min_gap != float('inf') else None

    def draw(self, surface):
        # NEW: Y-Sorting logic!
        # Vehicles further down the screen (higher Y) draw on top of vehicles higher up.
        # This prevents large sprites from glitching over each other when passing in tight sub-lanes.
        sorted_vehicles = sorted(self.vehicles, key=lambda v: v.rect.bottom)
        for v in sorted_vehicles:
            v.draw(surface)