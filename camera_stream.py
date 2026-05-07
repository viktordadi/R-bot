import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from picamera2 import Picamera2

camera = Picamera2()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
camera.start()

frame_lock = threading.Lock()
latest_frame = b""

def capture_loop():
    global latest_frame
    while True:
        stream = io.BytesIO()
        camera.capture_file(stream, format="jpeg")
        with frame_lock:
            latest_frame = stream.getvalue()

threading.Thread(target=capture_loop, daemon=True).start()

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        while True:
            with frame_lock:
                frame = latest_frame
            self.wfile.write(b"--frame\r\n")
            self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
            self.wfile.write(frame)
            self.wfile.write(b"\r\n")

    def log_message(self, format, *args):
        pass  # þaggar HTTP logs

server = HTTPServer(("0.0.0.0", 8080), StreamHandler)
print("Stream á: http://<IP á Pi>:8080")
server.serve_forever()
