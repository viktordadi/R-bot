import time
import json
import socket
import threading
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = 8081

# Dashboard status values.
# Other files can update these with:
#   dashboard.set_status(mode="manual")
robot_status = {
    "mode": "stopped",
    "camera_mode": "off",
    "gesture": None,
    "person_position": None,
    "follow_action": None,
    "dist_L": None,
    "dist_R": None,
}

# Follow mode settings.
# autopilot.py can read these with:
#   dashboard.get_follow_settings()
follow_settings = {
    "follow_speed": 0.55,
    "turn_gain": 0.40,
    "too_close_cm": 35,
    "target_distance_cm": 50,
    "move_forward_cm": 60,
}

status_lock = threading.Lock()
settings_lock = threading.Lock()

# Dashboard button command.
# main.py reads this with:
#   dashboard.get_pending_command()
pending_command = None
command_lock = threading.Lock()

server = None
server_thread = None


def get_ip():
    """
    Finds the Pi IP address.
    Used for showing the dashboard link in the terminal.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def set_status(**kwargs):
    """
    Updates dashboard values.

    Example:
        dashboard.set_status(mode="manual", dist_L=50, dist_R=60)
    """
    with status_lock:
        robot_status.update(kwargs)


def get_status_copy():
    """
    Returns a safe copy of the current dashboard status.
    """
    with status_lock:
        return robot_status.copy()


def set_follow_setting(name, value):
    """
    Updates one follow setting.
    """
    with settings_lock:
        if name in follow_settings:
            follow_settings[name] = value


def get_follow_settings():
    """
    Returns current follow mode slider settings.
    """
    with settings_lock:
        return follow_settings.copy()


def set_pending_command(command):
    """
    Stores a dashboard button command.
    main.py should read this and perform the action.
    """
    global pending_command

    with command_lock:
        pending_command = command


def get_pending_command():
    """
    main.py calls this every loop.

    Returns:
        "stop"
        "manual"
        "autopilot"
        "follow"
        "camera_ai"
        "camera_stream"
        "camera_off"
        "volume_up"
        "volume_down"
        None
    """
    global pending_command

    with command_lock:
        command = pending_command
        pending_command = None
        return command


def get_cpu_temp():
    """
    Reads Raspberry Pi CPU temperature.
    """
    try:
        output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
        return output.strip().replace("temp=", "")
    except Exception:
        return "unknown"


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_dashboard()
            return

        if self.path == "/status":
            self.send_status()
            return

        if self.path == "/settings":
            self.send_settings()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/command/"):
            command = self.path.replace("/command/", "")
            set_pending_command(command)

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path == "/settings":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()

            try:
                data = json.loads(body)

                for name, value in data.items():
                    if name in follow_settings:
                        set_follow_setting(name, float(value))

                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
                return

            except Exception as e:
                self.send_response(400)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        self.send_response(404)
        self.end_headers()

    def send_dashboard(self):
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>R-bot Dashboard</title>

    <style>
        body {
            background: #111;
            color: white;
            font-family: Arial, sans-serif;
            margin: 20px;
        }

        h1 {
            margin-bottom: 10px;
        }

        h2 {
            margin-top: 0;
        }

        .container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }

        .card {
            background: #222;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 20px;
        }

        img {
            width: 100%;
            max-width: 1280px;
            border-radius: 12px;
            background: black;
        }

        .value {
            font-size: 20px;
            margin: 10px 0;
        }

        .label {
            color: #aaa;
        }

        button {
            font-size: 17px;
            padding: 12px 16px;
            margin: 5px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            background: #444;
            color: white;
        }

        button:hover {
            background: #666;
        }

        .danger {
            background: #b00020;
            color: white;
            font-weight: bold;
            width: 100%;
            font-size: 22px;
            padding: 16px;
        }

        .danger:hover {
            background: #e00030;
        }

        .mode-button {
            background: #2454a6;
        }

        .camera-button {
            background: #236b3b;
        }

        .audio-button {
            background: #6b4a23;
        }

        .slider-row {
            margin: 16px 0;
        }

        input[type=range] {
            width: 100%;
        }

        .slider-value {
            font-weight: bold;
            color: #7ee787;
        }

        .small {
            color: #aaa;
            font-size: 14px;
            margin-top: 10px;
        }

        @media (max-width: 900px) {
            .container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>

<body>
    <h1>R-bot Dashboard</h1>

    <div class="container">
        <div>
            <div class="card">
                <h2>Camera</h2>
                <img id="camera" src="">
                <div class="small">
                    Camera stream uses port 8080. Dashboard uses port 8081.
                </div>
            </div>

            <div class="card">
                <h2>Follow Settings</h2>

                <div class="slider-row">
                    <label>Follow speed: <span class="slider-value" id="follow_speed_value"></span></label>
                    <input id="follow_speed" type="range" min="0.10" max="1.00" step="0.05">
                </div>

                <div class="slider-row">
                    <label>Turn gain: <span class="slider-value" id="turn_gain_value"></span></label>
                    <input id="turn_gain" type="range" min="0.10" max="1.00" step="0.05">
                </div>

                <div class="slider-row">
                    <label>Too close cm: <span class="slider-value" id="too_close_cm_value"></span></label>
                    <input id="too_close_cm" type="range" min="15" max="100" step="1">
                </div>

                <div class="slider-row">
                    <label>Target distance cm: <span class="slider-value" id="target_distance_cm_value"></span></label>
                    <input id="target_distance_cm" type="range" min="20" max="150" step="1">
                </div>

                <div class="slider-row">
                    <label>Move forward cm: <span class="slider-value" id="move_forward_cm_value"></span></label>
                    <input id="move_forward_cm" type="range" min="25" max="200" step="1">
                </div>

                <button onclick="saveSettings()">Save Follow Settings</button>

                <div class="small" id="settings_status"></div>
            </div>
        </div>

        <div>
            <div class="card">
                <h2>Status</h2>

                <div class="value"><span class="label">Mode:</span> <span id="mode">?</span></div>
                <div class="value"><span class="label">Camera:</span> <span id="camera_mode">?</span></div>
                <div class="value"><span class="label">Gesture:</span> <span id="gesture">?</span></div>
                <div class="value"><span class="label">Person:</span> <span id="person_position">?</span></div>
                <div class="value"><span class="label">Follow action:</span> <span id="follow_action">?</span></div>
                <div class="value"><span class="label">Left distance:</span> <span id="dist_L">?</span></div>
                <div class="value"><span class="label">Right distance:</span> <span id="dist_R">?</span></div>
                <div class="value"><span class="label">CPU temp:</span> <span id="cpu_temp">?</span></div>
            </div>

            <div class="card">
                <h2>Controls</h2>

                <button onclick="sendCommand('stop')" class="danger">STOP</button>

                <br><br>

                <button onclick="sendCommand('manual')" class="mode-button">Manual</button>
                <button onclick="sendCommand('autopilot')" class="mode-button">Autopilot</button>
                <button onclick="sendCommand('follow')" class="mode-button">Follow</button>

                <br><br>

                <button onclick="sendCommand('camera_ai')" class="camera-button">AI Camera</button>
                <button onclick="sendCommand('camera_stream')" class="camera-button">Stream Camera</button>
                <button onclick="sendCommand('camera_off')" class="camera-button">Camera Off</button>

                <br><br>

                <button onclick="sendCommand('volume_down')" class="audio-button">Volume -</button>
                <button onclick="sendCommand('volume_up')" class="audio-button">Volume +</button>

                <div class="small" id="command_status"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById("camera").src =
            "http://" + window.location.hostname + ":8080/stream.mjpg";

        function showValue(value) {
            if (value === null || value === undefined) {
                return "None";
            }
            return value;
        }

        async function updateStatus() {
            try {
                const response = await fetch("/status");
                const data = await response.json();

                document.getElementById("mode").textContent = showValue(data.mode);
                document.getElementById("camera_mode").textContent = showValue(data.camera_mode);
                document.getElementById("gesture").textContent = showValue(data.gesture);
                document.getElementById("person_position").textContent = showValue(data.person_position);
                document.getElementById("follow_action").textContent = showValue(data.follow_action);
                document.getElementById("dist_L").textContent = showValue(data.dist_L);
                document.getElementById("dist_R").textContent = showValue(data.dist_R);
                document.getElementById("cpu_temp").textContent = showValue(data.cpu_temp);
            } catch (error) {
                console.log(error);
            }
        }

        async function loadSettings() {
            try {
                const response = await fetch("/settings");
                const data = await response.json();

                for (const key in data) {
                    const slider = document.getElementById(key);
                    const label = document.getElementById(key + "_value");

                    if (slider && label) {
                        slider.value = data[key];
                        label.textContent = data[key];
                    }
                }
            } catch (error) {
                console.log(error);
            }
        }

        function updateSliderLabels() {
            const keys = [
                "follow_speed",
                "turn_gain",
                "too_close_cm",
                "target_distance_cm",
                "move_forward_cm"
            ];

            for (const key of keys) {
                const slider = document.getElementById(key);
                const label = document.getElementById(key + "_value");

                if (slider && label) {
                    label.textContent = slider.value;
                }
            }
        }

        async function saveSettings() {
            const data = {
                follow_speed: parseFloat(document.getElementById("follow_speed").value),
                turn_gain: parseFloat(document.getElementById("turn_gain").value),
                too_close_cm: parseFloat(document.getElementById("too_close_cm").value),
                target_distance_cm: parseFloat(document.getElementById("target_distance_cm").value),
                move_forward_cm: parseFloat(document.getElementById("move_forward_cm").value)
            };

            try {
                document.getElementById("settings_status").textContent = "Saving settings...";

                await fetch("/settings", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                document.getElementById("settings_status").textContent = "Settings saved";
            } catch (error) {
                document.getElementById("settings_status").textContent = "Settings failed";
                console.log(error);
            }
        }

        async function sendCommand(command) {
            try {
                document.getElementById("command_status").textContent =
                    "Sending command: " + command;

                await fetch("/command/" + command, {
                    method: "POST"
                });

                document.getElementById("command_status").textContent =
                    "Command sent: " + command;
            } catch (error) {
                document.getElementById("command_status").textContent =
                    "Command failed: " + command;
                console.log(error);
            }
        }

        const sliders = document.querySelectorAll("input[type=range]");
        sliders.forEach(slider => {
            slider.addEventListener("input", updateSliderLabels);
        });

        setInterval(updateStatus, 500);
        updateStatus();
        loadSettings();
    </script>
</body>
</html>
        """

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def send_status(self):
        data = get_status_copy()
        data["cpu_temp"] = get_cpu_temp()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_settings(self):
        data = get_follow_settings()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


def start():
    """
    Starts dashboard server.
    Call this once from main.py.
    """
    global server, server_thread

    if server is not None:
        print("Dashboard already running")
        return

    server = ThreadingHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    ip = get_ip()
    print(f"Dashboard running: http://{ip}:{PORT}/")


def stop():
    """
    Stops dashboard server.
    """
    global server, server_thread

    if server is not None:
        server.shutdown()
        server.server_close()
        server = None
        server_thread = None
        print("Dashboard stopped")


if __name__ == "__main__":
    start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()
