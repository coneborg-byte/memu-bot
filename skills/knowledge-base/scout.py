import json
import os
import datetime

MISSION_DIR = "missions"

def create_scout_mission(topic, reasoning=""):
    os.makedirs(MISSION_DIR, exist_ok=True)
    mission_id = f"scout_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    mission = {
        "id": mission_id,
        "action": "scout_x",
        "status": "pending",
        "data": {
            "topic": topic,
            "reasoning": reasoning
        },
        "created_at": datetime.datetime.now().isoformat()
    }
    
    filepath = os.path.join(MISSION_DIR, f"{mission_id}.json")
    with open(filepath, "w") as f:
        json.dump(mission, f, indent=2)
    
    return mission_id

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scout.py \"topic\" [\"reasoning\"]")
        sys.exit(1)
        
    topic = sys.argv[1]
    reasoning = sys.argv[2] if len(sys.argv) > 2 else "User requested scouting."
    mid = create_scout_mission(topic, reasoning)
    print(f"📡 Scout mission {mid} created. Antigravity will handle the cloud scraping.")
