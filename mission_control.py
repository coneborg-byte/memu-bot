import os
import json
import time
import datetime
import requests
import logging

# Configuration
MISSION_DIR = "missions"
LIBRARY_DIR = "library"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - MISSION_CONTROL - %(message)s')

def process_pending_missions():
    if not os.path.exists(MISSION_DIR):
        return

    for filename in os.listdir(MISSION_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(MISSION_DIR, filename)
            try:
                with open(filepath, "r+", encoding="utf-8") as f:
                    mission = json.load(f)
                    
                    if mission.get("status") == "pending":
                        action = mission.get("action")
                        data = mission.get("data", {})
                        
                        logging.info(f"🚀 Processing Mission: {action}...")
                        
                        # Local Autonomous Logic
                        if action == "save_research":
                            # This is already handled by Morpheus, we just mark it complete
                            mission["status"] = "completed"
                            logging.info(f"✅ Research archived: {data.get('title')}")
                        
                        elif action == "scout_x":
                            # This REQUIRES Antigravity (Cloud Muscles), so we leave it for the AI turn
                            # But we can update the status to 'notified_cloud'
                            logging.info(f"📡 Scout Mission Waiting for Antigravity: {data.get('topic')}")
                            continue 
                        
                        # Save updated status
                        f.seek(0)
                        json.dump(mission, f, indent=2)
                        f.truncate()
            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    logging.info("🦾 Mission Control Local Agent is online and watching missions/...")
    while True:
        process_pending_missions()
        time.sleep(10) # check every 10 seconds
