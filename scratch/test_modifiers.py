import sys
import os
sys.path.append(os.path.abspath('.'))

from src.processors.pitcher_scorer import calculate_pitcher_score, calculate_fatigue_penalty

# Test inputs
whip_high = {"whip": 1.5}
k9_low = {"k9": 6.0}
control_elite = {"bb9": 1.5}
short_innings = [{"innings_pitched": 4.5}, {"innings_pitched": 4.5}]

print("--- TESTING WITHOUT OVERRIDES (Must match original baseline) ---")

# WHIP tinggi
score, reasons = calculate_pitcher_score(whip_high)
print(f"WHIP tinggi (1.5) without override: score={score}, reasons={reasons}")
assert score == 0.3, f"Expected 0.3, got {score}"

# K/9 rendah
score, reasons = calculate_pitcher_score(k9_low)
print(f"K/9 rendah (6.0) without override: score={score}, reasons={reasons}")
assert score == 0.3, f"Expected 0.3, got {score}"

# Kontrol elit
score, reasons = calculate_pitcher_score(control_elite)
print(f"Kontrol elit (1.5) without override: score={score}, reasons={reasons}")
assert score == -0.3, f"Expected -0.3, got {score}"

# Inning pendek
penalty, reasons = calculate_fatigue_penalty(short_innings)
print(f"Inning pendek without override: penalty={penalty}, reasons={reasons}")
assert penalty == 0.2, f"Expected 0.2, got {penalty}"

print("\n--- TESTING WITH v4.0 OVERRIDES ---")
v4_override = {
    "hr9_risk_modifier": 0.25,
    "whip_high_modifier": 0.15,
    "k9_low_modifier": 0.15,
    "control_elite_modifier": -0.15,
    "short_innings_run_modifier": 0.0,
    "enable_dynamic_gap": True,
}

# WHIP tinggi
score, reasons = calculate_pitcher_score(whip_high, params_override=v4_override)
print(f"WHIP tinggi (1.5) with override: score={score}, reasons={reasons}")
assert score == 0.15, f"Expected 0.15, got {score}"

# K/9 rendah
score, reasons = calculate_pitcher_score(k9_low, params_override=v4_override)
print(f"K/9 rendah (6.0) with override: score={score}, reasons={reasons}")
assert score == 0.15, f"Expected 0.15, got {score}"

# Kontrol elit
score, reasons = calculate_pitcher_score(control_elite, params_override=v4_override)
print(f"Kontrol elit (1.5) with override: score={score}, reasons={reasons}")
assert score == -0.15, f"Expected -0.15, got {score}"

# Inning pendek
penalty, reasons = calculate_fatigue_penalty(short_innings, params_override=v4_override)
print(f"Inning pendek with override: penalty={penalty}, reasons={reasons}")
assert penalty == 0.0, f"Expected 0.0, got {penalty}"

print("\nAll verification assertions PASSED successfully!")
