from typing import Dict, Any, List
import boto3
from strands import tool
from config import settings

_bedrock_client = boto3.client(
    "bedrock-agent-runtime",
    region_name=settings.aws_region,
)

@tool
def query_cycling_knowledge_base(query: str, max_results: int = 4) -> List[Dict[str, Any]]:
    """
    Retrieves authoritative cycling guidelines, pacing theory, and nutrition protocols
    from the Bedrock Knowledge Base vector index (WZALS6RUMS).
    """
    try:
        response = _bedrock_client.retrieve(
            knowledgeBaseId=settings.bedrock_kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": max_results
                }
            },
        )
        return [
            {
                "content": item.get("content", {}).get("text", ""),
                "source_uri": item.get("location", {}).get("s3Location", {}).get("uri", ""),
                "score": round(float(item.get("score", 0.0)), 3),
            }
            for item in response.get("retrievalResults", [])
        ]
    except Exception as exc:
        return [{"error": f"Bedrock Knowledge Base retrieval failed: {str(exc)}"}]