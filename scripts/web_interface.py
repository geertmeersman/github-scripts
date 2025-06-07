import os
import subprocess
import threading
import time
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret")

SCRIPTS = {
    "auto_merge_dependabot": {
        "path": "/home/auto_merge_dependabot.py",
        "description": "Automatically merge open Dependabot PRs and notify via email and Telegram.",
        "args": []
    },
}

execution_status = {name: None for name in SCRIPTS.keys()}
execution_logs = {name: [] for name in SCRIPTS.keys()}
script_threads = {}

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GitHub Script Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
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
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">GitHub Script Dashboard</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
              </div>
            {% endfor %}
          {% endif %}
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
                        <div class="output mt-3">
                            <h6>Live Output:</h6>
                            <pre id="log-{{ name }}">{{ execution_logs[name]|join('\n') }}</pre>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
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
                            pre.textContent = lines.join("\n");
                        }
                    }
                    setTimeout(pollLogs, 3000);
                });
        };
        pollLogs();
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def run_script_with_live_output(script_name):
    execution_status[script_name] = "running"
    execution_logs[script_name] = []

    try:
        script = SCRIPTS[script_name]
        process = subprocess.Popen(
            ["python3", script["path"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in iter(process.stdout.readline, ''):
            execution_logs[script_name].append(line.strip())
        process.wait()
        if process.returncode == 0:
            execution_status[script_name] = "success"
        else:
            execution_status[script_name] = "error"
    except Exception as e:
        execution_logs[script_name].append(f"Exception: {str(e)}")
        execution_status[script_name] = "error"

@app.route("/", methods=["GET"])
def home():
    return render_template_string(
        TEMPLATE,
        scripts=SCRIPTS,
        execution_status=execution_status,
        execution_logs=execution_logs
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
    script_threads[script_name] = thread

    flash(f"Started script '{script_name}'.", "info")
    return redirect(url_for("home"))

@app.route("/logs", methods=["GET"])
def logs():
    return jsonify(execution_logs)

@app.route("/health")
def health():
    return jsonify(status="ok")
