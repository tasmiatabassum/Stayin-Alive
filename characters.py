CHARACTERS = {
    "Badrul": {
        "name": "Badrul",
        "accel": 1.5,              # HUGE acceleration
        "friction": 0.95,          # SLIPPERY: Retains 95% of momentum (he will slide a lot)
        "max_speed": 7.0,          # Very fast top speed
        "dash_power": 18.0,        # Massive leap
        "dash_cooldown": 120,      
        "color": (185, 233, 1),
        "width": 30,
        "height": 30,
        "bio": "Badrul relies on momentum. He rarely looks both ways.",
        "tagline": "Yielding is for the weak."
    },
    "Mrittika": {
        "name": "Mrittika",
        "accel": 3.0,              # INSTANT acceleration (hits top speed immediately)
        "friction": 0.30,          # TIGHT: Retains only 30% momentum (she stops instantly)
        "max_speed": 3.5,          # Hard capped at a slower walking speed
        "dash_power": 9.0,         
        "dash_cooldown": 40,       
        "color": (252, 158, 232),
        "width": 26,               
        "height": 26,
        "bio": "Mrittika calculates the gap. Very nimble, but lacks top speed.",
        "tagline": "Patience is a virtue (until the bus honks)."
    }
}
