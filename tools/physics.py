import math
from typing import Dict, Any, Optional
from strands import tool
from config import settings
from tools.strava import getAthleteProfile, getSegmentDetails, getSegmentEfforts

def solve_velocity(power_watts: float, grade_pct: float, rider_weight_kg: float) -> float:
    """
    Solves velocity v (m/s) using binary search across aerodynamic and gravitational equilibrium:
    P_wheel = v * [ m*g*(sin(theta) + Cr*cos(theta)) + 0.5*rho*v^2*CdA ]
    """
    theta = math.atan(grade_pct / 100.0)
    mass = rider_weight_kg + 8.5  # Bike + kit allowance
    g = 9.81
    cr = 0.004      # Rolling resistance coefficient
    rho = 1.225     # Air density (kg/m^3)
    cda = 0.34      # Frontal drag area (m^2)
    eff = 0.97      # Drivetrain efficiency (3% loss)

    p_wheel = max(power_watts * eff, 0.0)

    low, high = 0.1, 35.0
    for _ in range(35):
        mid = (low + high) / 2.0
        f_grav = mass * g * math.sin(theta)
        f_roll = mass * g * cr * math.cos(theta)
        f_aero = 0.5 * rho * (mid ** 2) * cda
        p_req = mid * (f_grav + f_roll + f_aero)

        if p_req < p_wheel:
            low = mid
        else:
            high = mid
    return low

@tool
def calculate_allout_segment_time(
    segment_id: str,
    athlete_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculates an athlete's theoretical all-out duration and wattage using the local
    longitudinal road physics solver coupled with the Xert hyperbolic power ceiling.
    """
    aid = athlete_id or settings.athlete_id

    profile = getAthleteProfile(athleteId=aid)
    if "error" in profile:
        return {"error": f"Athlete lookup failed: {profile['error']}"}

    weight = float(profile.get("weight", 75.0))
    xert = profile.get("xert_fitness_signature", {})
    ftp = float(xert.get("ftp", 250.0))
    hie_kj = float(xert.get("hie", 20.0))
    pp = float(xert.get("pp", 1000.0))

    segment = getSegmentDetails(segmentId=segment_id, athleteId=aid)
    if "error" in segment:
        return {"error": f"Segment lookup failed: {segment['error']}"}

    distance_m = float(segment.get("distance", 1000.0))
    grade_pct = float(segment.get("average_grade", 0.0))

    # Seed trial duration from historical best effort or distance heuristic
    efforts = getSegmentEfforts(segmentId=segment_id, limit=10)
    valid_efforts = [e for e in efforts if isinstance(e, dict) and "elapsed_time" in e]
    t_est = (
        float(min(e["elapsed_time"] for e in valid_efforts))
        if valid_efforts
        else max(distance_m / 8.0, 30.0)
    )

    damping = 0.4
    p_target = ftp
    for _ in range(25):
        p_hyp = ftp + (hie_kj * 1000.0) / max(t_est, 15.0)
        p_target = min(p_hyp, pp)
        v_est = solve_velocity(p_target, grade_pct, weight)
        t_calc = distance_m / max(v_est, 0.5)

        if abs(t_est - t_calc) < 0.2:
            t_est = t_calc
            break
        t_est = damping * t_est + (1.0 - damping) * t_calc

    mins = int(t_est // 60)
    secs = int(t_est % 60)
    return {
        "segment_id": segment_id,
        "segment_name": segment.get("name", "Unknown"),
        "distance_m": round(distance_m, 1),
        "grade_pct": round(grade_pct, 2),
        "projected_time_seconds": round(t_est, 1),
        "projected_time_formatted": f"{mins}m {secs:02d}s",
        "target_power_watts": round(p_target, 1),
        "projected_speed_kmh": round((distance_m / t_est) * 3.6, 2),
        "rider_weight_kg": weight,
        "ftp_watts": ftp,
    }