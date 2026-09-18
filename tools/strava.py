from typing import Optional, Dict, Any, List, Union
import requests
from strands import tool
from config import settings

_HEADERS = {"Content-Type": "application/json"}

def _request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Any:
    url = f"{settings.strava_api_base_url}{path}"
    resp = requests.request(
        method=method,
        url=url,
        headers=_HEADERS,
        params=params,
        json=json_body,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()

@tool
def getAthleteProfile(
    athleteId: Optional[str] = None,
    athlete_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieves athlete biometrics, 4-parameter Xert fitness signature,
    starred segment list, and additional watch-list segment IDs from DynamoDB.
    """
    aid = str(athleteId or athlete_id or settings.athlete_id)
    try:
        return _request("GET", f"/athlete/{aid}")
    except requests.RequestException as exc:
        return {"error": f"Failed retrieving profile for athlete {aid}: {str(exc)}"}

@tool
def searchSegments(q: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Searches the segment catalog using in-memory fuzzy matching on segment names.
    Returns segment IDs, geography, climb statistics, and KOM/QOM.
    Does not require an athlete ID.
    """
    params = {"q": q} if q else None
    try:
        return _request("GET", "/segments", params=params)
    except requests.RequestException as exc:
        return [{"error": f"Failed searching segments: {str(exc)}"}]

@tool
def getSegmentDetails(
    segmentId: Optional[Union[str, int]] = None,
    refresh: bool = False,
    athleteId: Optional[str] = None,
    segment_id: Optional[Union[str, int]] = None,
    athlete_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieves segment metadata (elevation high/low, coordinates, climb stats, KOM/QOM).
    Reads from DynamoDB cache by default with zero quota consumption.
    Only requires athleteId if refresh=True is requested to authorize an upstream fetch.
    """
    sid = str(segmentId or segment_id)
    params = {"refresh": "true"} if refresh else None
    aid = str(athleteId or athlete_id or settings.athlete_id)
    json_body = {"athleteId": aid} if refresh else None
    try:
        return _request("GET", f"/segments/{sid}", params=params, json_body=json_body)
    except requests.RequestException as exc:
        return {"error": f"Failed retrieving segment {sid}: {str(exc)}"}

@tool
def getSegmentEfforts(
    segmentId: Optional[Union[str, int]] = None,
    order: str = "desc",
    limit: int = 50,
    segment_id: Optional[Union[str, int]] = None,
    athleteId: Optional[str] = None,
    athlete_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves historical attempts on a segment in CHRONOLOGICAL order.
    Each record contains elapsed_time, moving_time, average_watts, device_watts, and personal_pr_rank.
    To identify the true PR, scan for personal_pr_rank == 1.
    Only efforts with device_watts == True represent verified power meter data.
    """
    sid = str(segmentId or segment_id)
    params = {"order": order, "limit": limit}
    try:
        return _request("GET", f"/segments/{sid}/efforts", params=params)
    except requests.RequestException as exc:
        return [{"error": f"Failed retrieving efforts for segment {sid}: {str(exc)}"}]

@tool
def syncStarredSegments(
    athleteId: Optional[str] = None,
    athlete_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synchronously fetches starred segments from Strava and overwrites the athlete's
    'starred_segment_list' in DynamoDB. Fast execution without background enrichment.
    """
    aid = str(athleteId or athlete_id or settings.athlete_id)
    try:
        return _request("POST", "/segments/sync-starred", json_body={"athleteId": aid})
    except requests.RequestException as exc:
        return {"error": f"Failed syncing starred segments: {str(exc)}"}

@tool
def manageAdditionalSegments(
    segmentIds: Optional[List[Union[str, int]]] = None,
    action: str = "append",
    athleteId: Optional[str] = None,
    segment_ids: Optional[List[Union[str, int]]] = None,
    athlete_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Appends to (action='append', POST) or replaces (action='replace', PUT)
    the athlete's curated 'additional_segment_list' in DynamoDB.
    """
    aid = str(athleteId or athlete_id or settings.athlete_id)
    raw_ids = segmentIds or segment_ids or []
    str_ids = [str(sid).strip() for sid in raw_ids]
    method = "PUT" if action.lower() == "replace" else "POST"
    try:
        return _request(
            method=method,
            path=f"/athlete/{aid}/additional-segments",
            json_body={"segmentIds": str_ids},
        )
    except requests.RequestException as exc:
        return {"error": f"Failed managing additional segments ({action}): {str(exc)}"}

@tool
def triggerEnrichmentSync(
    athleteId: Optional[str] = None,
    athlete_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronously initiates background enrichment for all segments in both
    'starred_segment_list' and 'additional_segment_list'.
    Queues batches to SQS and returns HTTP 202 Accepted.
    """
    aid = str(athleteId or athlete_id or settings.athlete_id)
    try:
        return _request("POST", "/segments/sync", json_body={"athleteId": aid})
    except requests.RequestException as exc:
        return {"error": f"Failed triggering enrichment sync: {str(exc)}"}

@tool
def predictSegmentEffort(
    segment_id: Optional[Union[str, int]] = None,
    segmentId: Optional[Union[str, int]] = None,
    athlete_id: Optional[str] = None,
    athleteId: Optional[str] = None,
    distance_m: Optional[float] = None,
    elevation_gain_m: Optional[float] = None,
    gradient_pct: Optional[float] = None,
    rider_mass_kg: Optional[float] = None,
    fitness_profile: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Predicts all-out cycling performance (expected power in Watts, duration in seconds,
    90% confidence bounds, and certainty score).
    Supports Option 1 (segment_id lookup) and Option 2 ('what-if' or custom parameters).
    """
    target_sid = segment_id or segmentId
    aid = str(athlete_id or athleteId or settings.athlete_id)
    try:
        has_custom = (rider_mass_kg is not None) or (fitness_profile is not None)
        if target_sid and not has_custom:
            return _request(
                "GET",
                f"/predict-segment-effort/{str(target_sid)}",
                json_body={"athleteId": aid},
            )

        if target_sid and has_custom:
            sid = str(target_sid)
            segment = _request("GET", f"/segments/{sid}")
            resolved_dist = distance_m or float(segment.get("distance", 0.0))
            high = float(segment.get("elevation_high", 0.0))
            low = float(segment.get("elevation_low", 0.0))
            resolved_elev = elevation_gain_m or (
                (high - low) if high > low else float(segment.get("total_elevation_gain", 0.0))
            )
            resolved_grade = gradient_pct or float(segment.get("average_grade", 0.0))

            resolved_weight = rider_mass_kg
            resolved_fitness = fitness_profile
            if resolved_weight is None or resolved_fitness is None:
                prof = _request("GET", f"/athlete/{aid}")
                xert = prof.get("xert_fitness_signature", {})
                resolved_weight = resolved_weight or float(prof.get("weight", 80.0))
                resolved_fitness = resolved_fitness or {
                    "threshold_power_watts": float(xert.get("ftp", 270.0)),
                    "high_intensity_energy_kj": float(xert.get("hie", 17.0)),
                    "peak_power_watts": float(xert.get("pp", 880.0)),
                }

            payload = {
                "distance_m": round(resolved_dist, 1),
                "elevation_gain_m": round(resolved_elev, 1),
                "gradient_pct": round(resolved_grade, 2),
                "rider_mass_kg": round(resolved_weight, 1),
                "fitness_profile": resolved_fitness,
            }
            return _request("GET", "/predict-segment-effort", json_body=payload)

        payload = {
            "distance_m": distance_m,
            "elevation_gain_m": elevation_gain_m,
            "gradient_pct": gradient_pct,
            "rider_mass_kg": rider_mass_kg,
            "fitness_profile": fitness_profile,
        }
        return _request(
            "GET",
            "/predict-segment-effort",
            json_body={k: v for k, v in payload.items() if v is not None},
        )
    except requests.RequestException as exc:
        return {"error": f"predictSegmentEffort failed: {str(exc)}"}

# Aliases for internal naming consistency
get_athlete_profile = getAthleteProfile
search_segments = searchSegments
get_segment_details = getSegmentDetails
get_segment_efforts = getSegmentEfforts
sync_starred_segments = syncStarredSegments
trigger_starred_sync = syncStarredSegments
manage_additional_segments = manageAdditionalSegments
trigger_enrichment_sync = triggerEnrichmentSync
predict_segment_effort = predictSegmentEffort