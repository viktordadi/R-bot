import io
import time
import socket
import threading
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput


camera = None
server = None
server_thread = None
recording = False

frame_lock = threading.Lock()
latest_frame = b""

PORT = 8080


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def open_stream_link():
    """
    Tries to make VS Code open the browser link.

    This works best when you are using VS Code Remote SSH.
    If it does not open automatically, copy the printed URL.
    """
    ip = get_ip()
    url = f"http://{ip}:{PORT}/"

    print(f"Browser stream: {url}")

    try:
        subprocess.Popen(["code", "--open-url", url])
    except Exception as e:
        print("Could not auto-open VS Code/browser link:", e)
        print("Open this manually:", url)


class StreamOutput(io.BufferedIOBase):
    def write(self, buf):
        global latest_frame

        with frame_lock:
            latest_frame = buf

        return len(buf)


class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"""
                <html>
                <body>
                    <h1>Robot Camera Stream</h1>
                    <img src="/stream.mjpg" style="width: 100%; height: auto;">
                </body>
                </html>
                """
            )
            return

        if self.path != "/stream.mjpg":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        try:
            while True:
                with frame_lock:
                    frame = latest_frame

                if frame:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")

                time.sleep(0.02)

        except BrokenPipeError:
            pass
        except ConnectionResetError:
            pass

    def log_message(self, format, *args):
        pass


def start(open_browser=True):
    global camera, server, server_thread, recording

    if recording:
        print("Camera stream already running")
        return

    print("Starting normal camera stream...")

    try:
        camera = Picamera2()
        camera.configure(
            camera.create_video_configuration(
                main={"size": (1920, 1080)}
            )
        )
    except Exception as e:
        print("Could not start normal camera stream:", e)
        camera = None
        recording = False
        return

    output = StreamOutput()
    camera.start_recording(MJPEGEncoder(), FileOutput(output))

    server = ThreadingHTTPServer(("0.0.0.0", PORT), StreamHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    recording = True

    print(f"Stream running on port {PORT}")

    if open_browser:
        open_stream_link()


def stop():
    global camera, server, server_thread, recording

    if not recording:
        return

    print("Stopping normal camera stream...")

    try:
        if camera is not None:
            camera.stop_recording()
            camera.close()
    except Exception as e:
        print("Camera stream stop error:", e)

    try:
        if server is not None:
            server.shutdown()
            server.server_close()
    except Exception as e:
        print("Server stop error:", e)

    camera = None
    server = None
    server_thread = None
    recording = False

    print("Normal camera stream stopped")
