CHARACTERS = {
    "Badrul": {
        "name": "Badrul",
        "accel": 0.8,              # High acceleration (starts fast)
        "friction": 0.85,          # Low friction (slides a bit when stopping)
        "max_speed": 5.0,
        "dash_power": 15.0,        # Massive leap
        "dash_cooldown": 120,      # Takes 2 seconds to recover (60 frames/sec)
        "color": (0, 255, 127),
        "width": 30,
        "height": 30,
        "bio": "Badrul relies on momentum. He rarely looks both ways.",
        "tagline": "Yielding is for the weak."
    },
    "Mrittika": {
        "name": "Mrittika",
        "accel": 0.4,              # Slow to start walking
        "friction": 0.70,          # High friction (stops immediately, very precise)
        "max_speed": 3.5,
        "dash_power": 8.0,         # Short, quick hop
        "dash_cooldown": 45,       # Recovers quickly
        "color": (255, 105, 180),
        "width": 26,               # Smaller hitbox
        "height": 26,
        "bio": "Mrittika calculates the gap. Very nimble, but lacks top speed.",
        "tagline": "Patience is a virtue (until the bus honks)."
    }
}