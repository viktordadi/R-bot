import io
import time
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput


# Heldur utan um Picamera2 hlutinn.
camera = None

# Heldur utan um HTTP serverinn sem sýnir myndavélarstrauminn.
server = None

# Þráðurinn sem keyrir HTTP serverinn í bakgrunni.
server_thread = None

# Segir hvort myndavélarstraumurinn sé í gangi.
recording = False

# Lock svo ekki sé lesið og skrifað í latest_frame á sama tíma.
frame_lock = threading.Lock()

# Hér er nýjasta JPEG myndin geymd sem bytes.
latest_frame = b""

# Portið sem browser stream notar.
PORT = 8080


def get_ip():
    """
    Finnur IP tölu Raspberry Pi á netinu.

    Returns:
        IP tala sem streng.
        Ef ekkert virkar, skilar það "127.0.0.1".
    """

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Tengjast Google DNS bara til að finna hvaða IP töluna Pi notar.
        s.connect(("8.8.8.8", 80))

        # Ná í local IP töluna.
        ip = s.getsockname()[0]

        # Loka socket.
        s.close()

        return ip

    except Exception:
        # Ef ekki tókst að finna IP, nota localhost.
        return "127.0.0.1"


class StreamOutput(io.BufferedIOBase):
    """
    Tekur við MJPEG myndum frá Picamera2.

    Picamera2 skrifar hverja JPEG mynd í write().
    Við vistum nýjustu myndina í latest_frame svo HTTP serverinn geti sent hana.
    """

    def write(self, buf):
        global latest_frame

        # Læsa latest_frame á meðan myndin er uppfærð.
        with frame_lock:
            latest_frame = buf

        return len(buf)


class StreamHandler(BaseHTTPRequestHandler):
    """
    HTTP handler sem birtir camera stream í browser.

    / sýnir einfalda HTML síðu.
    /stream.mjpg sendir MJPEG myndastraum.
    """

    def do_GET(self):
        # Ef notandi opnar aðalsíðuna, sýna HTML síðu með myndastraumi.
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

        # Ef slóðin er ekki /stream.mjpg, skila 404.
        if self.path != "/stream.mjpg":
            self.send_response(404)
            self.end_headers()
            return

        # Senda HTTP headera fyrir MJPEG stream.
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        try:
            # Senda myndir stöðugt á meðan browserinn er tengdur.
            while True:
                # Ná í nýjustu myndina.
                with frame_lock:
                    frame = latest_frame

                # Ef til er mynd, senda hana sem JPEG frame.
                if frame:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")

                time.sleep(0.02)

        except BrokenPipeError:
            # Gerist þegar browserinn lokar tengingunni.
            pass

        except ConnectionResetError:
            # Gerist þegar tengingin rofnar óvænt.
            pass

    def log_message(self, format, *args):
        # Slökkva á venjulegum HTTP loggum í terminal.
        pass


def start():
    """
    Ræsir venjulegan camera stream.

    Prentar bara linkinn sem hægt er að opna handvirkt.
    """

    global camera, server, server_thread, recording

    # Ef stream er nú þegar í gangi, ekki ræsa annað eintak.
    if recording:
        print("Camera stream already running")
        return

    print("Starting normal camera stream...")

    try:
        # Búa til Picamera2 hlut.
        camera = Picamera2()

        # Stilla myndavélina í video mode með 1280x720 upplausn.
        camera.configure(
            camera.create_video_configuration(
                main={"size": (1280, 720)}
            )
        )

    except Exception as e:
        # Ef myndavélin nær ekki að starta, hætta örugglega.
        print("Could not start normal camera stream:", e)
        camera = None
        recording = False
        return

    output = StreamOutput()

    # Byrja að taka upp MJPEG stream.
    camera.start_recording(MJPEGEncoder(), FileOutput(output))

    # Búa til HTTP server sem hlustar á öllum netkortum á porti 8080.
    server = ThreadingHTTPServer(("0.0.0.0", PORT), StreamHandler)

    # Keyra serverinn í sér þræði svo aðalforritið haldi áfram.
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Merkja að stream sé í gangi.
    recording = True

    # Prenta linkinn.
    ip = get_ip()
    print(f"Stream running on port {PORT}")
    print(f"Open camera stream manually: http://{ip}:{PORT}/")


def stop():
    """
    Stoppar camera stream og lokar HTTP servernum.
    """

    global camera, server, server_thread, recording

    # Ef stream er ekki í gangi, þarf ekkert að gera.
    if not recording:
        return

    print("Stopping normal camera stream...")

    try:
        # Stoppa upptöku og loka myndavélinni.
        if camera is not None:
            camera.stop_recording()
            camera.close()

    except Exception as e:
        print("Camera stream stop error:", e)

    try:
        # Stoppa HTTP serverinn.
        if server is not None:
            server.shutdown()
            server.server_close()

    except Exception as e:
        print("Server stop error:", e)

    # Núlla global breytur.
    camera = None
    server = None
    server_thread = None
    recording = False

    print("Normal camera stream stopped")
