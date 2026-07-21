import sys
import traceback
from datetime import datetime, timezone

import config
from lib.auth import get_access_token
from lib.gmail_client import fetch_gemini_emails
from lib.docs_client import read_doc_text, read_radar_doc, read_radar_annotations, append_to_radar
from lib.radar_store import load_radar, save_radar, add_ideas, update_annotations, update_trends
from lib.analyzer import run_pipeline
from lib.doc_renderer import build_full_update
from lib.web_renderer import render_dashboard
from lib.slack_notify import notify_high_scores
from state import load_state, save_state, is_processed, mark_processed, prune_old_entries


def validate_config() -> list[str]:
    errors = []
    if not config.RADAR_DOC_ID:
        errors.append("RADAR_DOC_ID not set")
    if not config.GOOGLE_CLIENT_ID:
        errors.append("GOOGLE_CLIENT_ID not set")
    if not config.GOOGLE_CLIENT_SECRET:
        errors.append("GOOGLE_CLIENT_SECRET not set")
    if not config.GOOGLE_REFRESH_TOKEN:
        errors.append("GOOGLE_REFRESH_TOKEN not set")
    if not config.LLM_API_KEY:
        errors.append("LLM_API_KEY not set")
    return errors


def main():
    errors = validate_config()
    if errors:
        print(f"Configuration errors: {', '.join(errors)}")
        sys.exit(2)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Meeting Miner starting")

    try:
        token = get_access_token()
    except Exception:
        state = load_state(config.STATE_FILE)
        state = prune_old_entries(state)
        save_state(state, config.STATE_FILE)
        raise

    state = load_state(config.STATE_FILE)
    state = prune_old_entries(state)
    radar = load_radar(config.RADAR_FILE)

    print("Checking Gmail for new Gemini notes...")
    emails = fetch_gemini_emails(token, config.GMAIL_QUERY)
    new_emails = [e for e in emails if not is_processed(state, e["id"])]
    print(f"Found {len(emails)} Gemini emails, {len(new_emails)} new")

    if not new_emails:
        print("No new meetings to process. Syncing annotations only.")
        try:
            radar_text = read_radar_doc(token)
            annotations = read_radar_annotations(radar_text)
            if annotations:
                radar = update_annotations(radar, annotations)
                save_radar(radar, config.RADAR_FILE)
                print(f"Synced {len(annotations)} annotations from Radar doc")
        except Exception as e:
            print(f"Annotation sync failed (non-fatal): {e}")
        save_state(state, config.STATE_FILE)
        print("Done (no new ideas).")
        return

    print("Reading transcripts...")
    transcripts = []
    for email in new_emails:
        try:
            text = read_doc_text(email["doc_url"], token)
            transcripts.append({
                "meeting_name": email["meeting_name"],
                "date": email["date"],
                "text": text,
                "doc_url": email["doc_url"],
            })
            state = mark_processed(state, email["id"], email["meeting_name"])
            print(f"  Read: {email['meeting_name']}")
        except Exception as e:
            print(f"  Failed to read {email['meeting_name']}: {e}")

    if not transcripts:
        print("No transcripts could be read. Exiting.")
        save_state(state, config.STATE_FILE)
        return

    print(f"Running analysis pipeline on {len(transcripts)} transcripts...")
    new_ideas, signals = run_pipeline(transcripts, radar.get("ideas", []))
    print(f"Generated {len(new_ideas)} ideas")

    radar["meeting_signals"] = signals.get("meeting_summaries", [])

    radar = add_ideas(radar, new_ideas)
    radar = update_trends(radar)

    try:
        radar_text = read_radar_doc(token)
        annotations = read_radar_annotations(radar_text)
        radar = update_annotations(radar, annotations)
    except Exception as e:
        print(f"Annotation sync failed (non-fatal): {e}")

    save_radar(radar, config.RADAR_FILE)
    print(f"Saved {len(radar['ideas'])} total ideas to radar.json")

    print("Updating Google Doc...")
    requests = build_full_update(radar, new_ideas, signals, meetings_count=len(transcripts))
    append_to_radar(token, requests)
    print("Google Doc updated")

    print("Generating HTML dashboard...")
    render_dashboard(radar, config.DASHBOARD_FILE)
    print(f"Dashboard written to {config.DASHBOARD_FILE}")

    if config.DASHBOARD_DRIVE_FOLDER_ID:
        try:
            from lib.google_api import drive_upload_or_update, drive_find_file
            existing_id = drive_find_file(token, "meeting-miner-dashboard.html", config.DASHBOARD_DRIVE_FOLDER_ID)
            result = drive_upload_or_update(
                token, config.DASHBOARD_FILE, "meeting-miner-dashboard.html", "text/html",
                folder_id=config.DASHBOARD_DRIVE_FOLDER_ID, file_id=existing_id,
            )
            print(f"Dashboard uploaded to Drive (id: {result.get('id', '?')})")
        except Exception as e:
            print(f"Dashboard Drive upload failed (non-fatal): {e}")

    sent = notify_high_scores(new_ideas)
    if sent:
        print(f"Sent {sent} Slack notifications")

    save_state(state, config.STATE_FILE)
    print(f"[{datetime.now(timezone.utc).isoformat()}] Meeting Miner complete. {len(new_ideas)} new ideas.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(3)
