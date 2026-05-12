import time
import threading
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8081

robot_status = {
    "mode": "stopped",
    "camera_mode": "off",
    "gesture": None,
    "person_position": None,
    "dist_L": None,
    "dist_R": None,
}


def set_status(**kwargs):
    """
    Other files can call this to update dashboard values.

    Example:
        dashboard.set_status(mode="manual")
    """
    robot_status.update(kwargs)


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

                .container {
                    display: grid;
                    grid-template-columns: 2fr 1fr;
                    gap: 20px;
                }

                .card {
                    background: #222;
                    padding: 16px;
                    border-radius: 12px;
                }

                img {
                    width: 100%;
                    max-width: 1280px;
                    border-radius: 12px;
                    background: black;
                }

                .value {
                    font-size: 22px;
                    margin: 10px 0;
                }

                .label {
                    color: #aaa;
                }
            </style>
        </head>

        <body>
            <h1>R-bot Dashboard</h1>

            <div class="container">
                <div class="card">
                    <h2>Camera</h2>
                    <img src="http://10.98.211.36:8080/stream.mjpg">
                </div>

                <div class="card">
                    <h2>Status</h2>

                    <div class="value"><span class="label">Mode:</span> <span id="mode"></span></div>
                    <div class="value"><span class="label">Camera:</span> <span id="camera_mode"></span></div>
                    <div class="value"><span class="label">Gesture:</span> <span id="gesture"></span></div>
                    <div class="value"><span class="label">Person:</span> <span id="person_position"></span></div>
                    <div class="value"><span class="label">Left distance:</span> <span id="dist_L"></span></div>
                    <div class="value"><span class="label">Right distance:</span> <span id="dist_R"></span></div>
                    <div class="value"><span class="label">CPU temp:</span> <span id="cpu_temp"></span></div>
                </div>
            </div>

            <script>
                async function updateStatus() {
                    try {
                        const response = await fetch("/status");
                        const data = await response.json();

                        document.getElementById("mode").textContent = data.mode;
                        document.getElementById("camera_mode").textContent = data.camera_mode;
                        document.getElementById("gesture").textContent = data.gesture;
                        document.getElementById("person_position").textContent = data.person_position;
                        document.getElementById("dist_L").textContent = data.dist_L;
                        document.getElementById("dist_R").textContent = data.dist_R;
                        document.getElementById("cpu_temp").textContent = data.cpu_temp;
                    } catch (error) {
                        console.log(error);
                    }
                }

                setInterval(updateStatus, 500);
                updateStatus();
            </script>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def send_status(self):
        import json

        data = robot_status.copy()
        data["cpu_temp"] = get_cpu_temp()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


server = None


def start():
    global server

    if server is not None:
        print("Dashboard already running")
        return

    server = ThreadingHTTPServer(("0.0.0.0", PORT), DashboardHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"Dashboard running: http://10.98.211.36:{PORT}/")


def stop():
    global server

    if server is not None:
        server.shutdown()
        server.server_close()
        server = None
        print("Dashboard stopped")


if __name__ == "__main__":
    start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()
