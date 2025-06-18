import json
import datetime
import subprocess
import fcntl
import sys
import os

LOG_DIR = "/var/log/github-scripts"
HISTORY_FILE = os.path.join(LOG_DIR, "script_run_history.json")
os.makedirs(LOG_DIR, exist_ok=True)

def append_run_history(script_name, status, start_time, end_time, duration_seconds, log_filename):
    record = {
        "script": script_name,
        "start": start_time,
        "end": end_time,
        "duration": duration_seconds,
        "status": status,
        "log_file": log_filename
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

    start_dt = datetime.datetime.now()
    start_time = start_dt.strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f"{script_name}_{start_time}.log"
    log_path = os.path.join(LOG_DIR, log_filename)
    status = "error"

    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                [sys.executable, script_path],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy()
            )
            if result.returncode == 0:
                status = "success"
    except Exception as e:
        with open(log_path, "a") as log_file:
            log_file.write(f"\nException running script: {e}\n")

    end_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    duration_seconds = (end_time - start_time).total_seconds()
    append_run_history(script_name, status, start_time, end_time, duration_seconds, log_filename)
