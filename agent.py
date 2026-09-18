import sys
from strands import Agent
from strands.models import BedrockModel
from config import settings

from tools.strava import (
    getAthleteProfile,
    searchSegments,
    getSegmentDetails,
    getSegmentEfforts,
    syncStarredSegments,
    manageAdditionalSegments,
    triggerEnrichmentSync,
    predictSegmentEffort,
)
from tools.physics import calculate_allout_segment_time
from tools.knowledge_base import query_cycling_knowledge_base

SYSTEM_PROMPT = f"""
You are an expert cycling performance director, biomechanics engineer, and tactical coach.
Your primary athlete ID is '{settings.athlete_id}'. When no athlete ID is explicitly provided, always use this default.

OPERATIONAL WORKFLOW RULES:

1. Segment Resolution & Catalog Ingestion:
   - When the user refers to a segment by NAME, ALWAYS call `searchSegments(q=name)` first.
   - If an athlete wants to refresh their starred list from Strava without queued processing, invoke `syncStarredSegments`.
   - If the user asks to add or curate segments to monitor (without starring on Strava), invoke `manageAdditionalSegments(action='append'|'replace')`.
   - To trigger full background telemetry hydration across both starred and custom lists, invoke `triggerEnrichmentSync`.

2. PR Identification & Power Meter Validation:
   - Efforts from `getSegmentEfforts` are returned CHRONOLOGICALLY.
   - Locate the attempt where `personal_pr_rank == 1`.
   - Examine `device_watts`: if false, the power is an estimated figure by Strava. Identify the fastest effort with `device_watts == true` as the athlete's 'Verified Power PR'.

3. Performance Predictions & 'What-If' Scenarios:
   - For predictions on known segments or counterfactuals (e.g., 74kg body weight), call `predictSegmentEffort`.
   - Always report Mid Prediction time (m:ss) and Watts, the 90% Confidence Envelope, and Certainty score.
   - Formulate fueling and tactical pacing recommendations via `query_cycling_knowledge_base`.
"""

def create_cycling_agent() -> Agent:
    model = BedrockModel(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
        temperature=0.1,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            getAthleteProfile,
            searchSegments,
            getSegmentDetails,
            getSegmentEfforts,
            syncStarredSegments,
            manageAdditionalSegments,
            triggerEnrichmentSync,
            predictSegmentEffort,
            calculate_allout_segment_time,
            query_cycling_knowledge_base,
        ],
    )

if __name__ == "__main__":
    agent = create_cycling_agent()
    print(f"Cycling Agent active with {settings.bedrock_model_id}. Type 'exit' to quit.\n")
    while True:
        try:
            user_input = input("Rider > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break
            print(f"\nCoach > {agent(user_input)}\n")
        except KeyboardInterrupt:
            break