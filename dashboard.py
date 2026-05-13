import time
import json
import socket
import threading
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = 8081
# Skilgreina status á robotinum
robot_status = {
    "mode": "stopped",
    "camera_mode": "off",
    "gesture": None,
    "person_position": None,
    "follow_action": None,
    "dist_L": None,
    "dist_R": None,
}
# skilgreina hvernig setting byrja
settings = {
    "follow_speed": 0.55,
    "turn_gain": 0.40,
    "too_close_cm": 35,
    "target_distance_cm": 50,
    "move_forward_cm": 60,
    "volume_percent": 80,
}

status_lock = threading.Lock()
settings_lock = threading.Lock()

pending_command = None
command_lock = threading.Lock()

pending_tts_text = None
tts_lock = threading.Lock()

pending_led_command = None
led_command_lock = threading.Lock()

server = None
server_thread = None

# fá ip á pi
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def set_status(**kwargs):
    with status_lock:
        robot_status.update(kwargs)


def get_status_copy():
    with status_lock:
        return robot_status.copy()


def set_setting(name, value):
    with settings_lock:
        if name in settings:
            settings[name] = value


def get_settings():
    with settings_lock:
        return settings.copy()


def get_follow_settings():
    with settings_lock:
        return {
            "follow_speed": settings["follow_speed"],
            "turn_gain": settings["turn_gain"],
            "too_close_cm": settings["too_close_cm"],
            "target_distance_cm": settings["target_distance_cm"],
            "move_forward_cm": settings["move_forward_cm"],
        }


def set_system_volume(percent):
    try:
        percent = max(0, min(150, int(percent)))
        subprocess.run(
            ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%"],
            check=False,
        )
    except Exception as e:
        print("Volume set error:", e)


def set_pending_command(command):
    global pending_command

    with command_lock:
        pending_command = command


def get_pending_command():
    global pending_command

    with command_lock:
        command = pending_command
        pending_command = None
        return command


def set_pending_tts(text):
    global pending_tts_text

    with tts_lock:
        pending_tts_text = text


def get_pending_tts():
    global pending_tts_text

    with tts_lock:
        text = pending_tts_text
        pending_tts_text = None
        return text


def set_pending_led_command(command):
    global pending_led_command

    with led_command_lock:
        pending_led_command = command


def get_pending_led_command():
    global pending_led_command

    with led_command_lock:
        command = pending_led_command
        pending_led_command = None
        return command


def get_cpu_temp():
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

        if self.path == "/tts":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()

            try:
                data = json.loads(body)
                text = data.get("text", "")
                set_pending_tts(text)

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

        if self.path == "/led":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()

            try:
                data = json.loads(body)
                set_pending_led_command(data)

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

        if self.path == "/settings":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()

            try:
                data = json.loads(body)

                for name, value in data.items():
                    if name in settings:
                        value = float(value)
                        set_setting(name, value)

                        if name == "volume_percent":
                            set_system_volume(value)

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
            font-weight: bold;
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

        .search-button {
            background: #7b3fb8;
        }

        .camera-button {
            background: #236b3b;
        }

        .audio-button {
            background: #6b4a23;
        }

        .sound-button {
            background: #673ab7;
        }

        .led-button {
            background: #008080;
        }

        .slider-row {
            margin: 16px 0;
        }

        input[type=range] {
            width: 100%;
        }

        input[type=text] {
            width: 100%;
            box-sizing: border-box;
            font-size: 18px;
            padding: 12px;
            border-radius: 10px;
            border: none;
            margin-top: 8px;
        }

        input[type=color] {
            width: 100%;
            height: 50px;
            border: none;
            border-radius: 10px;
            background: none;
            cursor: pointer;
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

        .saved {
            color: #7ee787;
        }

        .saving {
            color: #ffd866;
        }

        .failed {
            color: #ff6b6b;
        }

        .control-section {
            margin-top: 16px;
            padding-top: 10px;
            border-top: 1px solid #444;
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
                <h2>Live Settings</h2>

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

                <div class="slider-row">
                    <label>Volume %: <span class="slider-value" id="volume_percent_value"></span></label>
                    <input id="volume_percent" type="range" min="0" max="150" step="5">
                </div>

                <div class="small" id="settings_status"></div>
            </div>

            <div class="card">
                <h2>LED Underglow</h2>

                <label>Color:</label>
                <input id="led_color" type="color" value="#8000ff">

                <br><br>

                <label>LED brightness: <span class="slider-value" id="led_brightness_value">0.15</span></label>
                <input id="led_brightness" type="range" min="0.01" max="1.00" step="0.01" value="0.15">

                <br><br>

                <button onclick="setLedColor()" class="led-button">Set Color</button>
                <button onclick="ledRainbow()" class="sound-button">Rainbow</button>
                <button onclick="ledBlink()" class="sound-button">Blink</button>
                <button onclick="ledOff()" class="danger">LED Off</button>

                <div class="small" id="led_status"></div>
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
                <h2>Text To Speech</h2>

                <input
                    id="tts_text"
                    type="text"
                    placeholder="Type something for the robot to say"
                >

                <br><br>

                <button onclick="sendTTS()" class="audio-button">Speak</button>

                <div class="small" id="tts_status"></div>
            </div>

            <div class="card">
                <h2>Soundboard</h2>

                <button onclick="sendCommand('sound_fireball')" class="sound-button">Fireball</button>
                <button onclick="sendCommand('sound_rain')" class="sound-button">Rain Over Me</button>
                <button onclick="sendCommand('sound_mr')" class="sound-button">Mr. Worldwide</button>
                <button onclick="sendCommand('sound_speech')" class="sound-button">Speech</button>
                <button onclick="sendCommand('sound_faaah')" class="sound-button">Faaah</button>
                <button onclick="sendCommand('sound_honk')" class="sound-button">Honk</button>
                <button onclick="sendCommand('sound_exit')" class="sound-button">Exit</button>

                <div class="small">
                    Plays MP3 files stored on the Raspberry Pi.
                </div>
            </div>

            <div class="card">
                <h2>Controller Controls</h2>

                <div class="control-section">
                    <div class="value"><span class="label">X / Cross:</span> Manual mode</div>
                    <div class="value"><span class="label">Triangle:</span> Autopilot mode</div>
                    <div class="value"><span class="label">Circle:</span> Stop and quit</div>
                    <div class="value"><span class="label">Square:</span> Switch camera mode</div>
                </div>

                <div class="control-section">
                    <div class="value"><span class="label">R2:</span> Drive forward</div>
                    <div class="value"><span class="label">L2:</span> Drive backward</div>
                    <div class="value"><span class="label">Left joystick:</span> Steering</div>
                </div>

                <div class="control-section">
                    <div class="value"><span class="label">L1:</span> Start/stop live mic receiver</div>
                    <div class="value"><span class="label">R1:</span> Follow person mode</div>
                    <div class="value"><span class="label">L3:</span> Volume down</div>
                    <div class="value"><span class="label">R3:</span> Volume up</div>
                </div>

                <div class="control-section">
                    <div class="value"><span class="label">D-pad Up:</span> Play Rain Over Me</div>
                    <div class="value"><span class="label">D-pad Down:</span> Play Fireball</div>
                    <div class="value"><span class="label">D-pad Right:</span> Play Mr. Worldwide</div>
                    <div class="value"><span class="label">D-pad Left:</span> Play Speech</div>
                </div>
            </div>

            <div class="card">
                <h2>Dashboard Controls</h2>

                <button onclick="sendCommand('stop')" class="danger">STOP</button>

                <br><br>

                <button onclick="sendCommand('manual')" class="mode-button">Manual</button>
                <button onclick="sendCommand('autopilot')" class="mode-button">Autopilot</button>
                <button onclick="sendCommand('follow')" class="mode-button">Follow</button>
                <button onclick="sendCommand('search')" class="search-button">Search</button>

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

        let saveTimer = null;

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

        function getSliderData() {
            return {
                follow_speed: parseFloat(document.getElementById("follow_speed").value),
                turn_gain: parseFloat(document.getElementById("turn_gain").value),
                too_close_cm: parseFloat(document.getElementById("too_close_cm").value),
                target_distance_cm: parseFloat(document.getElementById("target_distance_cm").value),
                move_forward_cm: parseFloat(document.getElementById("move_forward_cm").value),
                volume_percent: parseFloat(document.getElementById("volume_percent").value)
            };
        }

        function updateSliderLabels() {
            const keys = [
                "follow_speed",
                "turn_gain",
                "too_close_cm",
                "target_distance_cm",
                "move_forward_cm",
                "volume_percent"
            ];

            for (const key of keys) {
                const slider = document.getElementById(key);
                const label = document.getElementById(key + "_value");

                if (slider && label) {
                    label.textContent = slider.value;
                }
            }
        }

        function scheduleSaveSettings() {
            updateSliderLabels();

            const status = document.getElementById("settings_status");
            status.textContent = "Saving...";
            status.className = "small saving";

            if (saveTimer !== null) {
                clearTimeout(saveTimer);
            }

            saveTimer = setTimeout(saveSettings, 150);
        }

        async function saveSettings() {
            const data = getSliderData();

            try {
                await fetch("/settings", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                const status = document.getElementById("settings_status");
                status.textContent = "Settings saved";
                status.className = "small saved";

            } catch (error) {
                const status = document.getElementById("settings_status");
                status.textContent = "Settings failed";
                status.className = "small failed";
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

        async function sendTTS() {
            const text = document.getElementById("tts_text").value;

            try {
                document.getElementById("tts_status").textContent = "Sending speech...";

                await fetch("/tts", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ text: text })
                });

                document.getElementById("tts_status").textContent = "Speech sent";
            } catch (error) {
                document.getElementById("tts_status").textContent = "Speech failed";
                console.log(error);
            }
        }

        function hexToRgb(hex) {
            hex = hex.replace("#", "");

            return {
                r: parseInt(hex.substring(0, 2), 16),
                g: parseInt(hex.substring(2, 4), 16),
                b: parseInt(hex.substring(4, 6), 16)
            };
        }

        async function sendLedCommand(data) {
            try {
                document.getElementById("led_status").textContent = "Sending LED command...";

                await fetch("/led", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                document.getElementById("led_status").textContent = "LED command sent";
            } catch (error) {
                document.getElementById("led_status").textContent = "LED command failed";
                console.log(error);
            }
        }

        function setLedColor() {
            const color = hexToRgb(document.getElementById("led_color").value);
            const brightness = parseFloat(document.getElementById("led_brightness").value);

            sendLedCommand({
                mode: "color",
                r: color.r,
                g: color.g,
                b: color.b,
                brightness: brightness
            });
        }

        function ledRainbow() {
            const brightness = parseFloat(document.getElementById("led_brightness").value);

            sendLedCommand({
                mode: "rainbow",
                brightness: brightness
            });
        }

        function ledBlink() {
            const color = hexToRgb(document.getElementById("led_color").value);
            const brightness = parseFloat(document.getElementById("led_brightness").value);

            sendLedCommand({
                mode: "blink",
                r: color.r,
                g: color.g,
                b: color.b,
                brightness: brightness
            });
        }

        function ledOff() {
            sendLedCommand({
                mode: "off"
            });
        }

        const sliders = document.querySelectorAll("input[type=range]");
        sliders.forEach(slider => {
            if (slider.id === "led_brightness") {
                slider.addEventListener("input", function() {
                    document.getElementById("led_brightness_value").textContent = this.value;
                });
            } else {
                slider.addEventListener("input", scheduleSaveSettings);
            }
        });

        document.getElementById("tts_text").addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                sendTTS();
            }
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
        data = get_settings()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


def start():
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
