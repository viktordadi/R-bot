import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

camera = Picamera2()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))

frame_lock = threading.Lock()
latest_frame = b""
server = None

class StreamOutput(io.BufferedIOBase):
    def write(self, buf):
        global latest_frame
        with frame_lock:
            latest_frame = buf

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        while True:
            with frame_lock:
                frame = latest_frame
            if frame:
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")

    def log_message(self, format, *args):
        pass

def start():
    global server
    output = StreamOutput()
    camera.start_recording(MJPEGEncoder(), FileOutput(output))
    server = HTTPServer(("0.0.0.0", 8080), StreamHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print("Stream á: http://<IP á Pi>:8080")

def stop():
    global server
    camera.stop_recording()
    if server:
        server.shutdown()
        server = None
