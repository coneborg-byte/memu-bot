import os
import json
import time
import logging

# Configuration
MISSION_DIR = os.environ.get("MISSION_CONTROL_MISSIONS_DIR", "missions")
LIBRARY_DIR = "library"
# Use host.docker.internal if we suspect it might run in a container,
# but localhost is usually fine for a host-resident script.
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MISSION_CONTROL - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("logs", "mission_control.log")),
        logging.StreamHandler()
    ]
)


def process_pending_missions():
    if not os.path.exists(MISSION_DIR):
        try:
            os.makedirs(MISSION_DIR)
        except Exception as e:
            logging.error(f"Could not create mission directory: {e}")
            return

    for filename in os.listdir(MISSION_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(MISSION_DIR, filename)
            try:
                # Wait for file write to complete
                time.sleep(0.5)

                with open(filepath, "r+", encoding="utf-8") as f:
                    try:
                        mission = json.load(f)
                    except json.JSONDecodeError:
                        logging.warning(f"⚠️ Partial JSON in {filename}, skipping...")
                        continue

                    if mission.get("status") == "pending":
                        action = mission.get("action")
                        data = mission.get("data", {})

                        logging.info(f"🚀 Processing Mission: {action}...")

                        # Local Autonomous Logic
                        if action == "save_research":
                            mission["status"] = "completed"
                            logging.info(f"✅ Research archived: {data.get('title')}")

                        elif action == "scout_x":
                            if mission.get("status") == "pending":
                                mission["status"] = "notified_cloud"
                                msg = f"📡 [HANDOFF] Scout triggered for '{data.get('topic')}'"
                                logging.info(msg)

                        # Save updated status
                        f.seek(0)
                        json.dump(mission, f, indent=2)
                        f.truncate()
            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    logging.info("🦾 Mission Control initializing...")

    # Wait for containers to spike and settle
    logging.info("⏳ Waiting 15 seconds for system stabilization...")
    time.sleep(15)

    logging.info("🦾 Mission Control is online and watching missions/...")
    while True:
        process_pending_missions()
        time.sleep(5)  # responsive 5s loop

