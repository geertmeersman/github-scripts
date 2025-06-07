import json
import datetime
import subprocess
import fcntl
import sys
import os

HISTORY_FILE = "/var/log/github-scripts/script_run_history.json"

def append_run_history(script_name, status, start_time, end_time):
    record = {
        "script": script_name,
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "status": status,
    }
    try:
        if not os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "w") as f:
                f.write("[]")
        with open(HISTORY_FILE, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(record)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"Failed to update run history: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: wrapper.py <script_name> <script_path>")
        sys.exit(1)

    script_name = sys.argv[1]
    script_path = sys.argv[2]

    start_time = datetime.datetime.utcnow()
    status = "error"

    try:
        # Run the actual script
        result = subprocess.run(["python3", script_path], capture_output=True, text=True)
        if result.returncode == 0:
            status = "success"
        else:
            status = "error"
            print(result.stdout)
            print(result.stderr)
    except Exception as e:
        print(f"Exception running script: {e}")

    end_time = datetime.datetime.utcnow()
    append_run_history(script_name, status, start_time, end_time)
