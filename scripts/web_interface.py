import os
from flask import Flask, request, jsonify, render_template_string
import subprocess
import threading

app = Flask(__name__)

SCRIPTS = {
    "auto_merge_dependabot": {
        "path": "/home/auto_merge_dependabot.py",
        "description": "Automatically merge open Dependabot PRs and notify via email and Telegram.",
        "args": []
    },
    # Add more scripts here if needed
}

# To track execution states
# States: None (not run), "running", "success", "error"
execution_status = {name: None for name in SCRIPTS.keys()}
execution_output = {name: None for name in SCRIPTS.keys()}

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
        .status-running {
            color: #0d6efd;
            font-weight: bold;
        }
        .status-success {
            color: #198754;
            font-weight: bold;
        }
        .status-error {
            color: #dc3545;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">GitHub Script Dashboard</h1>
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

                        {% if execution_output.get(name) %}
                        <div class="output mt-3">
                            <h6>Output:</h6>
                            <pre>{{ execution_output[name] }}</pre>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

def run_script_async(script_name):
    execution_status[script_name] = "running"
    execution_output[script_name] = None
    try:
        script = SCRIPTS[script_name]
        result = subprocess.run(
            ["python3", script["path"]],
            capture_output=True,
            text=True,
            timeout=600
        )
        output = result.stdout + "\n" + result.stderr
        execution_output[script_name] = output
        if result.returncode == 0:
            execution_status[script_name] = "success"
        else:
            execution_status[script_name] = "error"
    except Exception as e:
        execution_output[script_name] = f"Exception: {str(e)}"
        execution_status[script_name] = "error"

@app.route("/", methods=["GET"])
def home():
    return render_template_string(
        TEMPLATE,
        scripts=SCRIPTS,
        execution_status=execution_status,
        execution_output=execution_output
    )

@app.route("/run/<script_name>", methods=["POST"])
def run_script(script_name):
    if script_name not in SCRIPTS:
        return f"<pre>Error: Unknown script '{script_name}'</pre>"

    if execution_status.get(script_name) == "running":
        return f"<pre>Script '{script_name}' is already running.</pre>"

    # Run asynchronously so the UI doesn’t block
    thread = threading.Thread(target=run_script_async, args=(script_name,))
    thread.start()

    return (
        f"<html><body><p>Started script <b>{script_name}</b>. "
        f"Please refresh the <a href='/'>dashboard</a> to see status and output.</p></body></html>"
    )

@app.route("/health")
def health():
    return jsonify(status="ok")

if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", "80"))
    app.run(host="0.0.0.0", port=port)
