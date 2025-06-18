import os
import sys
import re
import subprocess
import threading
from datetime import datetime
import json
from flask import Flask, jsonify, render_template_string, send_file, request
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret")
socketio = SocketIO(
    app,
    async_mode="eventlet",
    cors_allowed_origins=os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "https://github.bee.mgweb.be"
    )
)

def is_safe_args(arg_list, allowed_args_config):
    allowed_flags = {f"--{arg['name']}": arg for arg in allowed_args_config}

    if len(arg_list) % 2 != 0:
        return False, "Arguments must be in flag/value pairs"

    for i in range(0, len(arg_list), 2):
        flag = arg_list[i]
        value = arg_list[i + 1]

        if flag not in allowed_flags:
            return False, f"Unexpected flag: {flag}"

        # For example: allow GitHub usernames like 'geertmeersman' or 'dependabot[bot]'
        if flag == "--user" and not re.fullmatch(r"[a-zA-Z0-9\[\]_-]{1,40}", value):
            return False, f"Invalid value for {flag}: {value}"

        # You can extend validation here based on more metadata if needed

    return True, ""

def read_version():
    try:
        with open("/VERSION", "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading VERSION file: {e}")
        return "Unknown"

SCRIPTS_FILE = "/home/scripts/scripts.json"

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
    <link rel="icon" href="https://github.githubassets.com/favicons/favicon.png" type="image/png">
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
    <style>
        body {
            padding: 2rem;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            flex: 1;
        }
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

        #toast-container {
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 9999;
        }

        .footer {
            background: #e9ecef;
            text-align: center;
            padding: 0.75rem;
            font-size: 0.85rem;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }

        .header-title img {
            vertical-align: middle;
            margin-right: 0.5rem;
        }

        .run-history-row:hover {
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class=\"container\">
        <h1 class="mb-4 header-title">
            <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub" width="32" height="32">
            GitHub Script Dashboard
            <button class=\"btn btn-sm btn-secondary float-end\" onclick=\"showEnvModal()\">Show Environment</button>
        </h1>        
        <div class="mb-3">
            <span id="ws-status" class="badge bg-secondary">WebSocket: Connecting...</span>
        </div>
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
            
            <div class=\"card-header d-flex justify-content-between align-items-center\" onclick=\"toggleCardBody(this)\" style=\"cursor: pointer;\">
                        <strong>{{ name }}</strong>
                        {% set status = execution_status.get(name) %}
                        {% if status == 'running' %}
                            <span class=\"status-running\">Running...</span>
                        {% elif status == 'success' %}
                            <span class=\"status-success\">Success ✔</span>
                        {% elif status == 'error' %}
                            <span class=\"status-error\">Error ✘</span>
                        {% elif status == 'aborted' %}
                            <span class=\"text-warning fw-bold\">Aborted ⚠</span>                            
                        {% else %}
                            <span>Not running</span>
                        {% endif %}
                    </div>
                    <div class=\"card-body d-none\">
                        <p>{{ script.description }}</p>
                        <form onsubmit=\"return runScript(event, '{{ name }}')\">
                            {% for arg in script.args %}
                            <div class=\"form-group mb-2\">
                                {% set safe_name = name|replace(' ', '_') %}
                                <label for=\"arg-{{ safe_name }}-{{ arg.name }}\">{{ arg.label }}</label>
                                <input type=\"text\" class=\"form-control\" name=\"{{ arg.name }}\" id=\"arg-{{ safe_name }}-{{ arg.name }}\" value=\"{{ arg.default or '' }}\" {% if arg.required %}required{% endif %}>
                            </div>
                            {% endfor %}
                            <button class=\"btn btn-primary run-btn\" type=\"submit\" {% if status == 'running' %}style=\"display:none;\"{% endif %}>Run Script</button>
                        </form>
                        <form onsubmit=\"return cancelScript(event, '{{ name }}')\" class=\"mt-2 cancel-form\" {% if status != 'running' %}style=\"display:none;\"{% endif %}>
                            <button class=\"btn btn-danger btn-sm\">Cancel Script</button>
                        </form>
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

        <h3 class=\"mt-4 d-flex justify-content-between align-items-center\">
            <span>Run History</span>
            <button onclick=\"clearLogs()\" class=\"btn btn-sm btn-warning\">Clear Logs</button>
        </h3>
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr><th>Script</th><th>Start</th><th>End</th><th>Duration</th><th>Status</th></tr>
                </thead>
                <tbody id="run-history-body"></tbody>
            </table>
        </div>
        <nav>
            <ul class="pagination" id="history-pagination"></ul>
        </nav>
    </div>

    <div class=\"modal fade\" id=\"historyModal\" tabindex=\"-1\" aria-labelledby=\"historyModalLabel\" aria-hidden=\"true\">
      <div class=\"modal-dialog modal-lg\">
        <div class=\"modal-content\">
          <div class=\"modal-header\">
            <h5 class=\"modal-title\" id=\"historyModalLabel\">Run Details</h5>
            <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>
          </div>
          <div class=\"modal-body\" id=\"modal-body-content\"></div>
        </div>
      </div>
    </div>
    <div class=\"modal fade\" id=\"envModal\" tabindex=\"-1\" aria-labelledby=\"envModalLabel\" aria-hidden=\"true\">
        <div class=\"modal-dialog modal-lg\">
            <div class=\"modal-content\">
            <div class=\"modal-header\">
                <h5 class=\"modal-title\" id=\"envModalLabel\">Environment Variables</h5>
                <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>
            </div>
            <div class=\"modal-body\" id=\"env-modal-body\">
                <pre id=\"env-content\">Loading...</pre>
            </div>
            </div>
        </div>
    </div>
    <script src=\"https://cdn.socket.io/4.7.2/socket.io.min.js\"></script>
    <script>
        const socket = io({
            reconnection: true,
            reconnectionAttempts: 10,      // try 10 times
            reconnectionDelay: 1000,       // wait 1 second before trying to reconnect
            reconnectionDelayMax: 5000,    // max 5 seconds delay between attempts
            timeout: 20000,                // connection timeout
        });
        const wsStatus = document.getElementById("ws-status");

        function setWsStatus(state, color) {
            wsStatus.textContent = "WebSocket: " + state;
            wsStatus.className = "badge bg-" + color;
        }

        socket.on("connect", () => {
            console.log("✅ Socket.IO connected");
            setWsStatus("Connected", "success");
            // 🔥 Remove the disconnect toast if it exists
            const lostToast = document.getElementById("ws-disconnect-toast");
            if (lostToast) lostToast.remove();            
        });

        socket.on("disconnect", (reason) => {
            console.warn("⚠️ Socket.IO disconnected:", reason);
            setWsStatus("Disconnected", "danger")
            const toastId = "ws-disconnect-toast";
            const toast = document.createElement("div");
            toast.id = toastId; // ← add ID
            toast.className = "toast align-items-center text-white bg-danger border-0 show";
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">⚠️ Connection lost. Trying to reconnect...</div>
                </div>
            `;
            document.getElementById("toast-container").appendChild(toast);
        });

        socket.on("connect_error", () => setWsStatus("Error", "danger"));

        socket.on("reconnect_attempt", (attempt) => {
            console.log(`🔁 Reconnect attempt ${attempt}`);
            setWsStatus("Reconnecting...", "warning")
        });

        socket.on("reconnect_failed", () => {
            console.error("❌ Socket.IO failed to reconnect after max attempts");
            setWsStatus("Reconnect failed", "danger")
        });

        socket.on("log_update", (data) => {
            const pre = document.getElementById("log-" + data.script);
            if (pre) {
            pre.textContent += data.line + "\\n";
            pre.scrollTop = pre.scrollHeight;
            }
        });
        socket.on("status_update", (data) => {
            const headers = document.querySelectorAll(".card-header");
            headers.forEach(header => {
                if (header.textContent.trim().startsWith(data.script)) {
                    const card = header.closest(".card");
                    const statusSpan = header.querySelector("span");
                    if (statusSpan) {
                        if (data.status === "running") {
                            statusSpan.className = "status-running";
                            statusSpan.textContent = "Running...";
                        } else if (data.status === "success") {
                            statusSpan.className = "status-success";
                            statusSpan.textContent = "Success ✔";
                        } else if (data.status === "error") {
                            statusSpan.className = "status-error";
                            statusSpan.textContent = "Error ✘";
                        } else if (data.status === "aborted") {
                            statusSpan.className = "text-warning fw-bold";
                            statusSpan.textContent = "Aborted ⚠";
                        } else {
                            statusSpan.className = "";
                            statusSpan.textContent = "Not running";
                        }
                    }
                    const runBtn = card.querySelector(".run-btn");
                    const cancelForm = card.querySelector(".cancel-form");
                    if (data.status === "running") {
                        if (runBtn) runBtn.style.display = "none";
                        if (cancelForm) cancelForm.style.display = "block";
                    } else {
                        if (runBtn) runBtn.style.display = "inline-block";
                        if (cancelForm) cancelForm.style.display = "none";
                    }
                }
            });
        });

        let currentPage = 1;
        const perPage = 10;

        function formatSimpleDate(raw) {
            if (!raw) return "";
            const [date, time] = raw.split("_");
            return date + " " + time.replace(/-/g, ":");
        }
        function bindHistoryRowClicks() {
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
                    const modalBody = document.getElementById("modal-body-content");
                    const modalTitle = document.getElementById("historyModalLabel");
                    modalBody.innerHTML = `<pre>${data.content || "(No log content)"}</pre>`;
                    modalTitle.textContent = `${row.getAttribute("data-script")} - ${row.getAttribute("data-start")}`;
                    const modal = new bootstrap.Modal(document.getElementById("historyModal"));
                    modal.show();
                    })
                    .catch(err => alert("Failed to load log: " + err));
                });
            });
        }

        function loadHistoryPage(page) {
            fetch(`/history?page=${page}&per_page=${perPage}`)
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById("run-history-body");
                    tbody.innerHTML = "";
                    for (const record of data.records) {
                        const row = document.createElement("tr");
                        row.className = "run-history-row";
                        row.setAttribute("data-logfile", record.log_file);
                        row.setAttribute("data-script", record.script);
                        row.setAttribute("data-start", formatSimpleDate(record.start));
                        row.innerHTML = `
                            <td>${record.script}</td>
                            <td>${formatSimpleDate(record.start)}</td>
                            <td>${formatSimpleDate(record.end)}</td>
                            <td>${(record.duration || 0).toFixed(1)}s</td>
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

                    // ✅ Re-bind clicks **after** DOM update
                    bindHistoryRowClicks();
                });
        }

        function showEnvModal() {
            fetch('/env')
                .then(res => res.json())
                .then(data => {
                    const pre = document.getElementById("env-content");
                    pre.textContent = Object.entries(data).map(([key, val]) => `${key}=${val}`).join("\\n");
                    const modal = new bootstrap.Modal(document.getElementById("envModal"));
                    modal.show();
                })
                .catch(err => alert("Failed to load environment variables: " + err));
        }

        function toggleCardBody(header) {
            const cardBody = header.nextElementSibling;
            cardBody.classList.toggle("d-none");
        }

        function runScript(event, scriptName) {
            event.preventDefault();
            const form = event.target;
            const formData = new FormData(form);

            fetch(`/run/${scriptName}`, {
                method: "POST",
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                showToast(data.error ? "danger" : "info", data.message || data.error);
            })
            .catch(err => showToast("danger", "Failed to start script."));
            return false;
        }

        function cancelScript(event, scriptName) {
            event.preventDefault();
            fetch(`/cancel/${scriptName}`, { method: "POST" })
            .then(res => res.json())
            .then(data => {
                showToast(data.error ? "danger" : "warning", data.message || data.error);
            })
            .catch(err => showToast("danger", "Failed to cancel script."));
            return false;
        }

        function showToast(type, message) {
            const toast = document.createElement("div");
            toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>`;
            document.getElementById("toast-container").appendChild(toast);
            setTimeout(() => toast.remove(), 5000);
        }

        function clearLogs() {
            if (!confirm("Are you sure you want to delete all logs and history?")) return;
            fetch("/clear_logs", { method: "POST" })
                .then(res => res.json())
                .then(data => showToast("warning", data.message || data.error))
                .catch(err => showToast("danger", "Failed to clear logs."));
        }
                setInterval(() => loadHistoryPage(currentPage), 5000); // auto refresh
        loadHistoryPage(currentPage); // initial load
    </script>
    
    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
    <footer class="footer">
        <div>
            Version: <code>{{ version }}</code> &nbsp;|&nbsp;
            <a href="https://github.com/geertmeersman/github-scripts" target="_blank" style="color: #6c757d; text-decoration: none;">
                View on GitHub
            </a>
        </div>
        <div style="margin-top: 0.25rem;">
            &copy; {{ year }} Geert Meersman
        </div>
    </footer>
</body>
</html>
"""

def run_script_with_live_output(script_name, arg_values=None):
    if arg_values is None:
        arg_values = []
    execution_status[script_name] = "running"
    execution_logs[script_name] = []
    socketio.emit("status_update", {"script": script_name, "status": "running"})  # ← NEW

    start_time = datetime.now()
    start_str = start_time.strftime('%Y-%m-%d_%H-%M-%S')
    end_time = None

    try:
        script = SCRIPTS[script_name]
        script_path = os.path.abspath(script["path"])
        arg_definitions = script.get("args", [])
        # Validate user-provided args
        valid, reason = is_safe_args(arg_values, arg_definitions)
        if not valid:
            raise ValueError(f"Unsafe or invalid arguments: {reason}")
        process = subprocess.Popen(
            [sys.executable, "-u", script_path, *arg_values],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line-buffered output
            env=os.environ.copy()
        )
        app.logger.info("Running script: %s %s", script_path, arg_values)
        script_threads[script_name] = {"thread": threading.current_thread(), "process": process}

        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            execution_logs[script_name].append(line)
            socketio.emit("log_update", {"script": script_name, "line": line})

        process.wait()
        if execution_status[script_name] == "aborted":
            # Already handled by cancel route
            pass
        elif process.returncode == 0:
            execution_status[script_name] = "success"
            socketio.emit("status_update", {"script": script_name, "status": "success"})
        else:
            execution_status[script_name] = "error"
            socketio.emit("status_update", {"script": script_name, "status": "error"})
    except Exception as e:
        execution_logs[script_name].append(f"Exception: {str(e)}")
        if execution_status[script_name] != "aborted":
            execution_status[script_name] = "error"
            socketio.emit("status_update", {"script": script_name, "status": "error"})
    finally:
        end_time = datetime.now()
        end_str = end_time.strftime('%Y-%m-%d_%H-%M-%S')
        duration_seconds = (end_time - start_time).total_seconds()
        log_filename = f"{script_name}_{start_str.replace(':', '-')}.log"
        run_history.append({
            "script": script_name,
            "start": start_str,
            "end": end_str,
            "duration": duration_seconds,
            "status": execution_status[script_name],
            "log_file": log_filename
        })
        with open(HISTORY_FILE, "w") as f:
            json.dump(run_history, f, indent=2)

        log_path = os.path.join(LOG_DIR, log_filename)
        with open(log_path, "w") as log_file:
            log_file.write("\n".join(execution_logs[script_name]))

@app.route("/")
def home():
    version = read_version()
    year = datetime.now().year
    return render_template_string(
        TEMPLATE,
        scripts=SCRIPTS,
        execution_status=execution_status,
        execution_logs=execution_logs,
        run_history=run_history,
        version=version,
        year=year
    )
@app.route("/run/<script_name>", methods=["POST"])
def run_script(script_name):
    if script_name not in SCRIPTS:
        return jsonify({"error": f"Unknown script '{script_name}'"}), 400
    if execution_status.get(script_name) == "running":
        return jsonify({"error": f"Script '{script_name}' is already running."}), 409

    script_args = SCRIPTS[script_name].get("args", [])
    arg_values = []
    for arg in script_args:
        value = request.form.get(arg["name"], "")
        if value:
            arg_values.extend([f"--{arg['name']}", value])

    thread = threading.Thread(target=run_script_with_live_output, args=(script_name, arg_values))
    thread.start()
    return jsonify({"message": f"Started script '{script_name}'."}), 200

@app.route("/cancel/<script_name>", methods=["POST"])
def cancel_script(script_name):
    thread_info = script_threads.get(script_name)
    if thread_info and thread_info["process"]:
        process = thread_info["process"]
        if process.poll() is None:
            process.terminate()
            execution_status[script_name] = "aborted"
            execution_logs[script_name].append("Script was aborted by user.")
            socketio.emit("status_update", {"script": script_name, "status": "aborted"})
            return jsonify({"message": f"Aborted script '{script_name}'."}), 200
        else:
            return jsonify({"message": f"Script '{script_name}' already finished."}), 200
    else:
        return jsonify({"error": f"No running script found for '{script_name}'."}), 404

@app.route("/logs", methods=["GET"])
def logs():
    return jsonify(execution_logs)

@app.route("/download/<script_name>")
def download_script(script_name):
    if script_name not in SCRIPTS:
        return "Script not found", 404
    path = SCRIPTS[script_name]["path"]
    return send_file(path, as_attachment=True)

@app.route("/env")
def environment_variables():
    hidden_keys = ["GITHUB_TOKEN", "TELEGRAM_BOT_ID", "SMTP_PWD", "GPG_KEY", "PYTHON_SHA256"]
    safe_env = {}
    for k, v in os.environ.items():
        if any(sensitive in k.upper() for sensitive in hidden_keys):
            safe_env[k] = "***FILTERED***"
        else:
            safe_env[k] = v
    return jsonify(safe_env)

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
        return jsonify({"error": "Invalid pagination parameters"}), 400

    # Always read from disk and sort by start timestamp (newest first)
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
            history.sort(
                key=lambda x: datetime.strptime(x["start"], "%Y-%m-%d_%H-%M-%S"),
                reverse=True
            )
    except Exception as e:
        app.logger.error(f"Failed to read history: {str(e)}")
        return jsonify({"error": "An internal error occurred while reading history."}), 500

    total = len(history)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    records = history[start:end]

    return jsonify({
        "records": records,
        "page": page,
        "pages": pages,
        "total": total
    })

@app.route("/clear_logs", methods=["POST"])
def clear_logs():
    try:
        global run_history
        for record in run_history:
            log_file = record.get("log_file")
            if log_file:
                log_path = os.path.join(LOG_DIR, log_file)
                if os.path.exists(log_path):
                    os.remove(log_path)
        run_history = []
        with open(HISTORY_FILE, "w") as f:
            json.dump(run_history, f, indent=2)
        return jsonify({"message": "Logs and history cleared."}), 200
    except Exception as e:
        app.logger.error(f"Failed to clear logs: {str(e)}")
        return jsonify({"error": "An internal error occurred while clearing logs."}), 500

@app.route("/health")
def health():
    return jsonify(status="ok")
