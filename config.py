import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "eu-west-2")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    bedrock_kb_id: str = os.getenv("BEDROCK_KB_ID", "WZALS6RUMS")
    strava_api_base_url: str = os.getenv(
        "STRAVA_API_BASE_URL",
        "https://chd10yvm86.execute-api.eu-west-2.amazonaws.com",
    )
    athlete_id: str = os.getenv("ATHLETE_ID", "3634905")

settings = Settings()