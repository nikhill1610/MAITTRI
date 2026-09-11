CROPS = [
    {
        "name": "Wheat", "seasons": ["rabi"], "duration": 120,
        "water": "medium", "base_cost": 22000, "yield_q_acre": 18,
        "price": 2500, "ideal_soils": ["Loamy soil", "Sandy loam", "Alluvial soil"],
        "n": 80, "p": 45, "k": 35
    },
    {
        "name": "Mustard", "seasons": ["rabi"], "duration": 110,
        "water": "low", "base_cost": 16000, "yield_q_acre": 10,
        "price": 5600, "ideal_soils": ["Loamy soil", "Sandy loam", "Alluvial soil"],
        "n": 60, "p": 30, "k": 25
    },
    {
        "name": "Rice", "seasons": ["kharif"], "duration": 135,
        "water": "high", "base_cost": 30000, "yield_q_acre": 24,
        "price": 2300, "ideal_soils": ["Clay soil", "Clay loam", "Alluvial soil"],
        "n": 100, "p": 50, "k": 45
    },
    {
        "name": "Maize", "seasons": ["kharif", "rabi"], "duration": 100,
        "water": "medium", "base_cost": 24000, "yield_q_acre": 22,
        "price": 2100, "ideal_soils": ["Loamy soil", "Sandy loam", "Alluvial soil"],
        "n": 90, "p": 45, "k": 35
    },
    {
        "name": "Potato", "seasons": ["rabi"], "duration": 100,
        "water": "medium", "base_cost": 50000, "yield_q_acre": 90,
        "price": 1200, "ideal_soils": ["Loamy soil", "Sandy loam"],
        "n": 120, "p": 60, "k": 70
    },
    {
        "name": "Tomato", "seasons": ["rabi", "kharif"], "duration": 110,
        "water": "medium", "base_cost": 55000, "yield_q_acre": 120,
        "price": 1200, "ideal_soils": ["Loamy soil", "Sandy loam", "Clay loam"],
        "n": 110, "p": 55, "k": 80
    },
]

SOIL_INFO = {
    "Sandy soil": {"drainage": "fast", "water_holding": "low"},
    "Loamy soil": {"drainage": "good", "water_holding": "good"},
    "Sandy loam": {"drainage": "good", "water_holding": "medium"},
    "Clay soil": {"drainage": "slow", "water_holding": "high"},
    "Clay loam": {"drainage": "medium", "water_holding": "high"},
    "Silty soil": {"drainage": "medium", "water_holding": "high"},
    "Black soil": {"drainage": "medium", "water_holding": "high"},
    "Red soil": {"drainage": "good", "water_holding": "medium"},
    "Alluvial soil": {"drainage": "good", "water_holding": "good"},
    "Laterite soil": {"drainage": "fast", "water_holding": "low"},
}
