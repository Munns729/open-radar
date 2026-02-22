"""
Pipeline status reporter.

Writes live pipeline state to src/web/state.json so the frontend dashboard
can poll it without a WebSocket connection.
"""
import json
import os
import time


class StatusReporter:
    """
    Manages the state of the Universe Scanner and writes it to a JSON file
    for the frontend dashboard to consume.
    """
    
    # Write to a location accessible by the mini-webserver
    STATE_FILE = "src/web/state.json"
    
    def __init__(self):
        # Initial State
        self.state = {
            "status": "idle", # running, completed, error
            "current_zone": 0, # 0=Init, 1=Discovery, 2=Extraction, 3=Enrichment/Scoring
            "current_action": "Waiting for start...", 
            "stats": {
                "total_found": 0,
                "enriched": 0,
                "scored": 0,
                "tier_1_count": 0
            },
            "recent_logs": [],
            "last_updated": time.time()
        }
        self.ensure_dir()
        self.update()

    def ensure_dir(self):
        try:
            os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
        except:
            pass

    def update(self):
        """Write current state to disk with retries"""
        self.state["last_updated"] = time.time()
        max_retries = 5
        for i in range(max_retries):
            try:
                # Write to temp (unique per process/thread if possible, but basic tmp is fine for now)
                temp_file = f"{self.STATE_FILE}.tmp.{time.time()}"
                with open(temp_file, "w") as f:
                    json.dump(self.state, f, indent=2)
                
                # Copy/Replace
                if os.path.exists(self.STATE_FILE):
                    try:
                        os.remove(self.STATE_FILE)
                    except Exception:
                        pass # Might be locked, retry loop handles next iteration
                
                try:
                    os.rename(temp_file, self.STATE_FILE)
                    break 
                except Exception:
                     # Clean up temp if rename failed
                     if os.path.exists(temp_file):
                         os.remove(temp_file)
                     raise
            except Exception as e:
                time.sleep(0.1)
                if i == max_retries - 1:
                    print(f"Warning: Could not write status file: {e}")

    def set_active(self):
        self.state["status"] = "running"
        self.update()

    def set_zone(self, zone_id: int, action: str):
        self.state["current_zone"] = zone_id
        self.state["current_action"] = action
        self.log(f"Entered Zone {zone_id}: {action}")
        self.update()

    def set_action(self, action: str):
        self.state["current_action"] = action
        self.update()

    def update_stats(self, key: str, value: int):
        if key in self.state["stats"]:
            self.state["stats"][key] = value
            self.update()
            
    def increment_stat(self, key: str, amount: int = 1):
        if key in self.state["stats"]:
            self.state["stats"][key] += amount
            self.update()

    def log(self, message: str):
        """Add a log message to the recent logs buffer"""
        entry = f"[{time.strftime('%H:%M:%S')}] {message}"
        # Prepend
        self.state["recent_logs"] = [entry] + self.state["recent_logs"] 
        self.state["recent_logs"] = self.state["recent_logs"][:10] # Keep last 10
        self.update()

# Singleton instance
reporter = StatusReporter()
