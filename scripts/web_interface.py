import os
import subprocess
import threading
import datetime
import json
import re
from flask import Flask, jsonify, render_template_string, redirect, url_for, flash, send_file, request, abort, Response

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret")

SCRIPTS_FILE = "/home/scripts.json"

def load_scripts():
    try:
        with open(SCRIPTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading scripts: {e}")
        return {}

SCRIPTS = load_scripts()

execution_status = {name: None for name in SCRIPTS.keys()}
execution_logs = {name: [] for name in SCRIPTS.keys()}
script_threads = {}
run_history = []
HISTORY_FILE = "/home/script_run_history.json"
LOG_DIR = "/var/log/github-scripts"
os.makedirs(LOG_DIR, exist_ok=True)

# Load existing run history from file if it exists
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        try:
            run_history = json.load(f)
        except json.JSONDecodeError:
            run_history = []

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>GitHub Script Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" />
    <style>
        body { padding: 2rem; background: #f8f9fa; }
        .card { margin-bottom: 1rem; }
        .output pre {
            background: #212529;
            color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 300px;
            overflow-y: auto;
        }
        .status-running { color: #0d6efd; font-weight: bold; }
        .status-success { color: #198754; font-weight: bold; }
        .status-error { color: #dc3545; font-weight: bold; }
        #toast-container { position: fixed; top: 1rem; right: 1rem; z-index: 9999; }
        tr.history-row:hover { background-color: #e9ecef; cursor: pointer; }
    </style>
</head>
<body>
<div class="container">
    <h1 class="mb-4">GitHub Script Dashboard</h1>
    <div id="toast-container"></div>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="toast align-items-center text-white bg-{{ 'success' if category == 'success' else ('danger' if category == 'danger' else 'warning') }} border-0 show" role="alert" aria-live="assertive" aria-atomic="true">
          <div class="d-flex">
            <div class="toast-body">{{ message }}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        </div>
      {% endfor %}
    {% endwith %}
    <div class="row">
        {% for name, script in scripts.items() %}
        <div class="col-md-6">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title">{{ name }}</h5>
                    <p class="card-text">{{ script.description }}</p>
                    {% set status = execution_status.get(name) %}
                    {% if status == "running" %}
                        <p>Status: <span class="status-running">Running...</span></p>
                    {% elif status == "success" %}
                        <p>Status: <span class="status-success">Success ✔</span></p>
                    {% elif status == "error" %}
                        <p>Status: <span class="status-error">Error ✘</span></p>
                    {% else %}
                        <p>Status: <span>Not run</span></p>
                    {% endif %}
                    <form method="post" action="/run/{{ name }}">
                        <button class="btn btn-primary" type="submit" {% if status == "running" %}disabled{% endif %}>Run Script</button>
                    </form>
                    {% if status == "running" %}
                    <form method="post" action="/cancel/{{ name }}" class="mt-2">
                        <button class="btn btn-danger btn-sm">Cancel Script</button>
                    </form>
                    {% endif %}
                    <a href="/download/{{ name }}" class="btn btn-secondary mt-2">Download</a>
                    <div class="output mt-3">
                        <h6>Live Output:</h6>
                        <pre id="log-{{ name }}">{{ execution_logs[name]|join('\\n') }}</pre>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>

    <h3 class="mt-4">Run History</h3>
    <table class="table table-striped" id="run-history-table">
        <thead>
            <tr><th>Script</th><th>Start</th><th>End</th><th>Status</th></tr>
        </thead>
        <tbody>
            {% for record in run_history[-10:]|reverse %}
            <tr class="history-row"
                data-script="{{ record.script }}"
                data-start="{{ record.start }}"
                style="cursor:pointer;">
                <td>{{ record.script }}</td>
                <td>{{ record.start }}</td>
                <td>{{ record.end }}</td>
                <td>{{ record.status }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- Modal -->
    <div class="modal fade" id="logModal" tabindex="-1" aria-labelledby="logModalLabel" aria-hidden="true">
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="logModalLabel">Script Log Output</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <pre id="modal-log-content" style="white-space: pre-wrap; max-height: 60vh; overflow-y: auto;">Loading...</pre>
          </div>
        </div>
      </div>
    </div>
</div>

<script>
const pollLogs = () => {
    fetch("/logs")
        .then(response => response.json())
        .then(data => {
            for (const [name, lines] of Object.entries(data)) {
                const pre = document.getElementById("log-" + name);
                if (pre) {
                    pre.textContent = lines.join("\\n");
                }
            }
            setTimeout(pollLogs, 3000);
        });
};
pollLogs();

document.addEventListener("DOMContentLoaded", function() {
    const modal = new bootstrap.Modal(document.getElementById('logModal'));
    const modalContent = document.getElementById('modal-log-content');
    const modalTitle = document.getElementById('logModalLabel');

    document.querySelectorAll(".history-row").forEach(row => {
        row.addEventListener("click", () => {
            const script = row.dataset.script;
            const start = row.dataset.start;

            modalTitle.textContent = `Log Output for ${script} (Started: ${start})`;
            modalContent.textContent = "Loading...";

            // Fetch logfile content
            fetch(`/logfile?script=${encodeURIComponent(script)}&timestamp=${encodeURIComponent(start)}`)
                .then(resp => {
                    if (!resp.ok) throw new Error(`Error ${resp.status}: ${resp.statusText}`);
                    return resp.text();
                })
                .then(text => {
                    modalContent.textContent = text || "(No log output)";
                })
                .catch(err => {
                    modalContent.textContent = "Failed to load log:\\n" + err.message;
                });

            modal.show();
        });
    });
});
</script>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def run_script_with_live_output(script_name):
    execution_status[script_name] = "running"
    execution_logs[script_name] = []

    start_time = datetime.datetime.utcnow().isoformat()
    end_time = None

    try:
        script = SCRIPTS[script_name]
        process = subprocess.Popen(
            ["python3", "-u", script["path"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        script_threads[script_name] = {"thread": threading.current_thread(), "process": process}

        for line in iter(process.stdout.readline, ''):
            execution_logs[script_name].append(line.rstrip('\n'))
        process.wait()
        if process.returncode == 0:
            execution_status[script_name] = "success"
        else:
            execution_status[script_name] = "error"
    except Exception as e:
        execution_logs[script_name].append(f"Exception: {str(e)}")
        execution_status[script_name] = "error"
    finally:
        end_time = datetime.datetime.utcnow().isoformat()
        run_history.append({
            "script": script_name,
            "start": start_time,
            "end": end_time,
            "status": execution_status[script_name]
        })
        with open(HISTORY_FILE, "w") as f:
            json.dump(run_history, f, indent=2)

        # Save log file
        safe_start_time = start_time.replace(":", "-")
        log_filename = f"{script_name}_{safe_start_time}.log"
        log_path = os.path.join(LOG_DIR, log_filename)
        with open(log_path, "w") as log_file:
            log_file.write("\n".join(execution_logs[script_name]))

@app.route("/", methods=["GET"])
def home():
    return render_template_string(
        TEMPLATE,
        scripts=SCRIPTS,
        execution_status=execution_status,
        execution_logs=execution_logs,
        run_history=run_history
    )

@app.route("/run/<script_name>", methods=["POST"])
def run_script(script_name):
    if script_name not in SCRIPTS:
        flash(f"Error: Unknown script '{script_name}'", "danger")
        return redirect(url_for("home"))

    if execution_status.get(script_name) == "running":
        flash(f"Script '{script_name}' is already running.", "warning")
        return redirect(url_for("home"))

    thread = threading.Thread(target=run_script_with_live_output, args=(script_name,))
    thread.start()
    flash(f"Started script '{script_name}'.", "info")
    return redirect(url_for("home"))

@app.route("/cancel/<script_name>", methods=["POST"])
def cancel_script(script_name):
    thread_info = script_threads.get(script_name)
    if thread_info and thread_info["process"]:
        process = thread_info["process"]
        if process.poll() is None:
            process.terminate()
            execution_status[script_name] = "error"
            execution_logs[script_name].append("Script was aborted by user.")
            flash(f"Aborted script '{script_name}'.", "warning")
        else:
            flash(f"Script '{script_name}' already finished.", "info")
    else:
        flash(f"No running script found for '{script_name}'.", "danger")
    return redirect(url_for("home"))

@app.route("/logs", methods=["GET"])
def logs():
    return jsonify(execution_logs)

@app.route("/download/<script_name>")
def download_script(script_name):
    if script_name not in SCRIPTS:
        return "Script not found", 404
    path = SCRIPTS[script_name]["path"]
    return send_file(path, as_attachment=True)

@app.route("/logfile")
def get_logfile():
    script = request.args.get("script")
    timestamp = request.args.get("timestamp")

    if not script or not timestamp:
        return abort(400, "Missing script or timestamp")

    # Sanitize timestamp (allow letters, digits, dashes, colons, T and dots)
    if not re.match(r"^[\w\-T:.]+$", timestamp):
        return abort(400, "Invalid timestamp format")

    safe_timestamp = timestamp.replace(":", "-")
    log_filename = f"{script}_{safe_timestamp}.log"
    log_path = os.path.join(LOG_DIR, log_filename)

    if not os.path.exists(log_path):
        return abort(404, "Log file not found")

    with open(log_path, "r") as f:
        content = f.read()

    return Response(content, mimetype="text/plain")

@app.route("/health")
def health():
    return jsonify(status="ok")
