import json
import datetime
import pandas as pd

LOG_FILE = "governance_logs.json"

def log_interaction(prompt, response, issues, model):
    log_entry = {
        "timestamp": str(datetime.datetime.utcnow()),
        "model": model,
        "prompt": prompt,
        "response": response[:300] + ("..." if len(response) > 300 else ""),
        "response_length": len(response),
        "issues": issues
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def load_logs():
    try:
        with open(LOG_FILE, "r") as f:
            lines = [json.loads(line) for line in f]
        return pd.DataFrame(lines)
    except FileNotFoundError:
        return pd.DataFrame(columns=["timestamp", "model", "prompt", "response", "response_length", "issues"])