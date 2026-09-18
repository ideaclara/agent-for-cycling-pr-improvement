import json
from typing import Any
import gradio as gr
from agent import create_cycling_agent
from tools.strava import (
    syncStarredSegments,
    triggerEnrichmentSync,
    manageAdditionalSegments,
    getAthleteProfile,
)

agent = create_cycling_agent()

def format_response(data: Any) -> str:
    if isinstance(data, (dict, list)):
        try:
            return f"```json\n{json.dumps(data, indent=2, default=str)}\n```"
        except Exception:
            return f"```python\n{repr(data)}\n```"
    return str(data)

def chat_interface(message: str, history: list) -> str:
    if not message.strip():
        return ""
    try:
        response = agent(message)
        return str(response)
    except Exception as exc:
        return f"**Agent Execution Error:** `{str(exc)}`"

def on_sync_starred() -> str:
    res = syncStarredSegments()
    if isinstance(res, dict) and "error" in res:
        return f"❌ **Sync Failed:** `{res['error']}`"
    return f"✅ **Starred Catalog Synchronized**\n\n{format_response(res)}"

def on_trigger_enrichment() -> str:
    res = triggerEnrichmentSync()
    if isinstance(res, dict) and "error" in res:
        return f"❌ **Enrichment Trigger Failed:** `{res['error']}`"
    return f"🚀 **Enrichment Queued**\n\n{format_response(res)}"

def on_manage_segments(segment_ids_str: str, action: str) -> str:
    if not segment_ids_str.strip():
        return "⚠️ **Input Error:** Please enter at least one comma-separated segment ID."
    ids = [s.strip() for s in segment_ids_str.split(",") if s.strip()]
    res = manageAdditionalSegments(segmentIds=ids, action=action)
    if isinstance(res, dict) and "error" in res:
        return f"❌ **Update Failed:** `{res['error']}`"
    return f"📋 **Watchlist Updated (`{action}`)**\n\n{format_response(res)}"

def on_view_profile() -> str:
    res = getAthleteProfile()
    if isinstance(res, dict) and "error" in res:
        return f"❌ **Profile Lookup Failed:** `{res['error']}`"

    starred = res.get("starred_segment_list", [])
    additional = res.get("additional_segment_list", [])
    xert = res.get("xert_fitness_signature", {})

    return (
        f"### Athlete Status\n"
        f"* **Body Mass:** `{res.get('weight', 'N/A')} kg`\n"
        f"* **Fitness Signature:** TP/FTP `{xert.get('ftp', 'N/A')} W` | "
        f"HIE `{xert.get('hie', 'N/A')} kJ` | PP `{xert.get('pp', 'N/A')} W`\n"
        f"* **Starred Segments ({len(starred)}):** `{', '.join(starred) if starred else 'None'}`\n"
        f"* **Watchlist Segments ({len(additional)}):** `{', '.join(additional) if additional else 'None'}`"
    )

with gr.Blocks(title="Cycling AI Performance Director") as demo:
    gr.Markdown("## Cycling AI Tactical Director & Telemetry Hub")

    with gr.Row():
        with gr.Column(scale=3):
            gr.ChatInterface(
                fn=chat_interface,
                description="Ask for climb pacing, PR breakdowns, 'what-if' weight projections, or fueling advice.",
                examples=[
                    "Find Toy's Hill and predict my time if I weighed 74kg.",
                    "Show my true PR on Ide Hill Road and verify if it used a power meter.",
                    "What carbohydrate intake should I target before a 40-minute climb?",
                ],
            )

        with gr.Column(scale=2):
            gr.Markdown("### Segment Catalog Controls")

            with gr.Group():
                gr.Markdown("**Ingestion Triggers**")
                with gr.Row():
                    btn_sync_starred = gr.Button("Get Starred Segments from Strava", variant="secondary")
                    btn_enrich = gr.Button("Sync All Segments and Efforts", variant="primary")
                sync_output = gr.Markdown()

            with gr.Group():
                gr.Markdown("**Additional Segment Watchlist**")
                input_segment_ids = gr.Textbox(
                    label="Segment IDs",
                    placeholder="e.g. 6807785, 622392, 581297",
                    info="Comma-separated Strava numeric segment IDs",
                )
                action_radio = gr.Radio(
                    choices=["append", "replace"],
                    value="append",
                    label="Action",
                )
                btn_manage = gr.Button("Update Watchlist")
                manage_output = gr.Markdown()

            with gr.Accordion("Athlete Segment Lists Summary", open=False):
                btn_refresh_profile = gr.Button("Refresh Lists Overview")
                profile_output = gr.Markdown()

    btn_sync_starred.click(fn=on_sync_starred, outputs=sync_output)
    btn_enrich.click(fn=on_trigger_enrichment, outputs=sync_output)
    btn_manage.click(
        fn=on_manage_segments,
        inputs=[input_segment_ids, action_radio],
        outputs=manage_output,
    )
    btn_refresh_profile.click(fn=on_view_profile, outputs=profile_output)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=8000, inbrowser=True)