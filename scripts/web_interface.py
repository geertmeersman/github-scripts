import os
import subprocess
import threading
import datetime
import json
from flask import Flask, jsonify, render_template_string, redirect, url_for, flash, send_file, request
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret")
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="https://github.bee.mgweb.be")

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
LOG_DIR = "/var/log/github-scripts"
HISTORY_FILE = f"{LOG_DIR}/script_run_history.json"
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
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <title>GitHub Script Dashboard</title>
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
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
    </style>
</head>
<body>
    <div class=\"container\">
        <h1 class=\"mb-4\">GitHub Script Dashboard</h1>
        <div id=\"toast-container\"></div>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% for category, message in messages %}
            <div class=\"toast align-items-center text-white bg-{{ 'success' if category == 'success' else ('danger' if category == 'danger' else 'warning') }} border-0 show\" role=\"alert\" aria-live=\"assertive\" aria-atomic=\"true\">
              <div class=\"d-flex\">
                <div class=\"toast-body\">{{ message }}</div>
                <button type=\"button\" class=\"btn-close btn-close-white me-2 m-auto\" data-bs-dismiss=\"toast\" aria-label=\"Close\"></button>
              </div>
            </div>
          {% endfor %}
        {% endwith %}
        <div class=\"row\">
            {% for name, script in scripts.items() %}
            <div class=\"col-md-6\">
                <div class=\"card shadow-sm\">
                    <div class=\"card-body\">
                        <h5 class=\"card-title\">{{ name }}</h5>
                        <p class=\"card-text\">{{ script.description }}</p>
                        {% set status = execution_status.get(name) %}
                        {% if status == \"running\" %}
                            <p>Status: <span class=\"status-running\">Running...</span></p>
                        {% elif status == \"success\" %}
                            <p>Status: <span class=\"status-success\">Success ✔</span></p>
                        {% elif status == \"error\" %}
                            <p>Status: <span class=\"status-error\">Error ✘</span></p>
                        {% else %}
                            <p>Status: <span>Not run</span></p>
                        {% endif %}
                        <form method=\"post\" action=\"/run/{{ name }}\">
                            <button class=\"btn btn-primary\" type=\"submit\" {% if status == \"running\" %}disabled{% endif %}>Run Script</button>
                        </form>
                        {% if status == \"running\" %}
                        <form method=\"post\" action=\"/cancel/{{ name }}\" class=\"mt-2\">
                            <button class=\"btn btn-danger btn-sm\">Cancel Script</button>
                        </form>
                        {% endif %}
                        <a href=\"/download/{{ name }}\" class=\"btn btn-secondary mt-2\">Download</a>
                        <div class=\"output mt-3\">
                            <h6>Live Output:</h6>
                            <pre id=\"log-{{ name }}\">{{ execution_logs[name]|join('\n') }}</pre>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        <h3 class="mt-4">Run History</h3>
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr><th>Script</th><th>Start</th><th>End</th><th>Status</th></tr>
                </thead>
                <tbody id="run-history-body"></tbody>
            </table>
        </div>
        <nav>
            <ul class="pagination" id="history-pagination"></ul>
        </nav>
    </div>

    <div class=\"modal fade\" id=\"historyModal\" tabindex=\"-1\" aria-labelledby=\"historyModalLabel\" aria-hidden=\"true\">
      <div class=\"modal-dialog\">
        <div class=\"modal-content\">
          <div class=\"modal-header\">
            <h5 class=\"modal-title\" id=\"historyModalLabel\">Run Details</h5>
            <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>
          </div>
          <div class=\"modal-body\" id=\"modal-body-content\"></div>
        </div>
      </div>
    </div>

    <script src=\"https://cdn.socket.io/4.7.2/socket.io.min.js\"></script>
    <script>
      const socket = io();
      socket.on("log_update", (data) => {
        const pre = document.getElementById("log-" + data.script);
        if (pre) {
          pre.textContent += data.line + "\\n";
          pre.scrollTop = pre.scrollHeight;
        }
      });
        let currentPage = 1;
        const perPage = 10;

        function loadHistoryPage(page) {
            fetch(`/history?page=${page}&per_page=${perPage}`)
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById("run-history-body");
                    tbody.innerHTML = "";
                    for (const record of data.records) {
                        const row = document.createElement("tr");
                        row.innerHTML = `
                            <td>${record.script}</td>
                            <td>${new Date(record.start).toLocaleString()}</td>
                            <td>${new Date(record.end).toLocaleString()}</td>
                            <td>${record.status}</td>
                        `;
                        tbody.appendChild(row);
                    }

                    const pagination = document.getElementById("history-pagination");
                    pagination.innerHTML = "";

                    for (let i = 1; i <= data.pages; i++) {
                        const li = document.createElement("li");
                        li.className = `page-item ${i === data.page ? 'active' : ''}`;
                        li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
                        li.onclick = (e) => {
                            e.preventDefault();
                            currentPage = i;
                            loadHistoryPage(i);
                        };
                        pagination.appendChild(li);
                    }
                });
        }

        setInterval(() => loadHistoryPage(currentPage), 5000); // auto refresh
        loadHistoryPage(currentPage); // initial load
    </script>
    <script>
    document.querySelectorAll(".run-history-row").forEach(row => {
        row.addEventListener("click", () => {
        const logFile = row.getAttribute("data-logfile");
        fetch(`/logfile/${logFile}`)
            .then(res => res.json())
            .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const pre = document.getElementById("runHistoryDetails");
            pre.textContent = data.content || "(No log content)";
            const modal = new bootstrap.Modal(document.getElementById("runHistoryModal"));
            modal.show();
            })
            .catch(err => alert("Failed to load log: " + err));
        });
    });
    </script>
    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
</body>
</html>
"""

def run_script_with_live_output(script_name):
    execution_status[script_name] = "running"
    execution_logs[script_name] = []

    start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
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
            line = line.strip()
            execution_logs[script_name].append(line)
            socketio.emit("log_update", {"script": script_name, "line": line})

        process.wait()
        if process.returncode == 0:
            execution_status[script_name] = "success"
        else:
            execution_status[script_name] = "error"
    except Exception as e:
        execution_logs[script_name].append(f"Exception: {str(e)}")
        execution_status[script_name] = "error"
    finally:
        end_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_filename = f"{script_name}_{start_time.replace(':', '-')}.log"
        run_history.append({
            "script": script_name,
            "start": start_time,
            "end": end_time,
            "status": execution_status[script_name],
            "log_file": log_filename
        })
        with open(HISTORY_FILE, "w") as f:
            json.dump(run_history, f, indent=2)

        log_filename = f"{script_name}_{start_time.replace(':', '-')}.log"
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

@app.route("/logfile/<log_filename>")
def get_logfile(log_filename):
    safe_filename = os.path.basename(log_filename)  # avoid path traversal
    log_path = os.path.normpath(os.path.join(LOG_DIR, safe_filename))
    if not log_path.startswith(LOG_DIR) or not os.path.exists(log_path):
        return jsonify({"error": "Log file not found"}), 404
    with open(log_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})


@app.route("/history")
def get_history():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        page, per_page = 1, 10

    start = (page - 1) * per_page
    end = start + per_page
    total = len(run_history)

    return jsonify({
        "records": run_history[::-1][start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    })

@app.route("/health")
def health():
    return jsonify(status="ok")