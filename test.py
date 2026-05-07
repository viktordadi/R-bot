#!/usr/bin/env python3

"""
gesture_ai_stop_web.py

This program does 3 things at the same time:

1. Uses the Raspberry Pi AI Camera to detect a person's pose.
2. Checks if the person's RIGHT arm is stretched across their body to the LEFT.
3. Creates a video preview that you can open in VLC or a web browser.
"""

import argparse
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np

from picamera2 import Picamera2, MappedArray
from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet


# ------------------------------------------------------------
# Pose keypoint numbers
# ------------------------------------------------------------
# The pose model detects 17 body points.
#
# These numbers are from the COCO pose format.
#
# For this program we only need:
#
#   right shoulder = 6
#   right elbow    = 8
#   right wrist    = 10
#
# We use those 3 points to decide if the right arm is
# stretched left across the body.
# ------------------------------------------------------------

RIGHT_SHOULDER = 6
RIGHT_ELBOW = 8
RIGHT_WRIST = 10


# Camera frame size.
#
# postprocess_higherhrnet expects this as:
#
#   height, width
#
# Our camera image is 640x480, so this is:
#
#   height = 480
#   width  = 640
WINDOW_SIZE_H_W = (480, 640)


# ------------------------------------------------------------
# Shared variables
# ------------------------------------------------------------
# latest_jpeg:
#   The most recent camera frame converted to JPEG.
#   The web/VLC stream sends this image repeatedly.
#
# latest_command:
#   Remembers if the last command was STOP or clear.
#   This stops the terminal from printing STOP every frame.
#
# frame_lock:
#   A lock so the camera thread and web server thread do not
#   access latest_jpeg at the exact same time.
# ------------------------------------------------------------

latest_jpeg = None
latest_command = None
frame_lock = threading.Lock()


def right_arm_fully_left(person_keypoints, image_width=640, min_confidence=0.3):
    """
    Decide if the right arm is stretched left across the body.

    Input:
        person_keypoints:
            Keypoints for one detected person.
            Shape is 17 body points.
            Each body point is:
                x, y, confidence

        image_width:
            Width of the camera image.
            We use 640 because our camera config is 640x480.

        min_confidence:
            Minimum confidence needed for the shoulder, elbow, and wrist.
            If the AI is not confident, we ignore the gesture.

    Returns:
        True:
            Right arm is probably making the STOP gesture.

        False:
            No STOP gesture.
    """

    # Get the three body points we need.
    right_shoulder = person_keypoints[RIGHT_SHOULDER]
    right_elbow = person_keypoints[RIGHT_ELBOW]
    right_wrist = person_keypoints[RIGHT_WRIST]

    # Split each point into x, y, confidence.
    #
    # x:
    #   Left/right position.
    #   Smaller x = more left.
    #   Bigger x  = more right.
    #
    # y:
    #   Up/down position.
    #   Smaller y = higher in the image.
    #   Bigger y  = lower in the image.
    #
    # confidence:
    #   How sure the AI model is about that point.
    sx, sy, sc = right_shoulder
    ex, ey, ec = right_elbow
    wx, wy, wc = right_wrist

    # If any point is weak, do not trust this frame.
    if sc < min_confidence or ec < min_confidence or wc < min_confidence:
        return False

    # The wrist must be far enough left of the shoulder.
    #
    # 0.20 means 20% of the image width.
    # For 640 pixels wide:
    #
    #   640 * 0.20 = 128 pixels
    #
    # So the wrist must be at least 128 pixels left of the shoulder.
    min_left_distance = image_width * 0.20

    # Check if wrist and elbow are to the left of the shoulder.
    wrist_is_left_of_shoulder = wx < sx - min_left_distance
    elbow_is_left_of_shoulder = ex < sx

    # Check if the arm is roughly horizontal.
    #
    # This helps avoid false detections when the arm is just hanging down.
    arm_is_roughly_horizontal = abs(wy - sy) < image_width * 0.20
    wrist_and_elbow_aligned = abs(wy - ey) < image_width * 0.15

    # All these must be true for STOP.
    return (
        wrist_is_left_of_shoulder
        and elbow_is_left_of_shoulder
        and arm_is_roughly_horizontal
        and wrist_and_elbow_aligned
    )


def parse_pose_output(metadata):
    """
    Convert raw AI Camera output into pose keypoints.

    The AI Camera produces raw neural-network data.

    This function converts it into something easier to use:

        keypoints[person][body_point] = x, y, confidence

    Example:

        keypoints[0][RIGHT_WRIST]

    means:

        first detected person's right wrist.
    """

    # Get neural-network output from the IMX500 AI Camera.
    np_outputs = imx500.get_outputs(metadata=metadata, add_batch=True)

    # Sometimes the camera has no AI output yet.
    # This is normal at startup or between frames.
    if np_outputs is None:
        return None

    # Convert raw model output into human pose keypoints.
    keypoints, scores, boxes = postprocess_higherhrnet(
        outputs=np_outputs,
        img_size=WINDOW_SIZE_H_W,
        img_w_pad=(0, 0),
        img_h_pad=(0, 0),
        detection_threshold=args.detection_threshold,
        network_postprocess=True,
    )

    # If no person was detected, return None.
    if scores is None or len(scores) == 0:
        return None

    # Reshape into:
    #
    #   number_of_people x 17_keypoints x 3_values
    #
    # The 3 values are:
    #
    #   x, y, confidence
    keypoints = np.reshape(np.stack(keypoints, axis=0), (len(scores), 17, 3))

    return keypoints


def draw_keypoint(frame, point, color):
    """
    Draw one body point on the preview image.

    frame:
        The camera image.

    point:
        x, y, confidence

    color:
        OpenCV color in BGR format.
        Example:
            (0, 255, 255) = yellow
    """

    x, y, confidence = point

    # Only draw the point if confidence is good enough.
    if confidence > 0.3:
        cv2.circle(frame, (int(x), int(y)), 5, color, -1)


def draw_line(frame, point_a, point_b, color):
    """
    Draw a line between two body points.

    This is used to draw:
        shoulder -> elbow
        elbow -> wrist
    """

    ax, ay, ac = point_a
    bx, by, bc = point_b

    # Only draw the line if both points are confident.
    if ac > 0.3 and bc > 0.3:
        cv2.line(
            frame,
            (int(ax), int(ay)),
            (int(bx), int(by)),
            color,
            2,
        )


def camera_callback(request):
    """
    This function runs automatically for every camera frame.

    Every frame it does this:

        1. Get AI pose data.
        2. Get the camera image.
        3. Draw the right arm keypoints.
        4. Check if the stop gesture is happening.
        5. Draw STOP or clear text on the image.
        6. Convert the image to JPEG for VLC/browser preview.
    """

    global latest_jpeg, latest_command

    # Get metadata from this camera frame.
    #
    # The AI Camera stores neural-network results in the metadata.
    metadata = request.get_metadata()

    # Convert AI output into pose keypoints.
    keypoints = parse_pose_output(metadata)

    # This becomes True if any detected person is doing the gesture.
    stop_detected = False

    # MappedArray lets us access the camera frame image.
    with MappedArray(request, "main") as m:
        frame = m.array

        # Picamera2 gives us RGB data.
        # OpenCV uses BGR data.
        #
        # If the frame has 4 channels, it is RGBA.
        # If it has 3 channels, it is RGB.
        if frame.shape[2] == 4:
            display = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        else:
            display = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # If people were detected, check each person.
        if keypoints is not None:
            for person in keypoints:
                # Get the right arm points.
                rs = person[RIGHT_SHOULDER]
                re = person[RIGHT_ELBOW]
                rw = person[RIGHT_WRIST]

                # Draw right arm lines on the preview.
                draw_line(display, rs, re, (255, 255, 255))
                draw_line(display, re, rw, (255, 255, 255))

                # Draw right arm points on the preview.
                draw_keypoint(display, rs, (0, 255, 255))
                draw_keypoint(display, re, (0, 255, 255))
                draw_keypoint(display, rw, (0, 255, 255))

                # Check if this person is doing the STOP gesture.
                if right_arm_fully_left(person, image_width=640):
                    stop_detected = True

        # Draw text on the video frame.
        if stop_detected:
            command = "STOP"

            cv2.putText(
                display,
                "STOP",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                2,
                (0, 0, 255),
                4,
            )

            # Later, this is where you can stop your robot:
            #
            # stop()
            #
            # Do not add motor code until the camera detection works reliably.

        else:
            command = "clear"

            cv2.putText(
                display,
                "clear",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 255, 0),
                3,
            )

        # Only print when the command changes.
        #
        # This prevents the terminal from printing:
        # STOP
        # STOP
        # STOP
        # STOP
        # every frame.
        if latest_command != command:
            print(command)
            latest_command = command

        # Convert the preview image to JPEG.
        #
        # MJPEG streaming is just many JPEG images sent one after another.
        ok, jpeg = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

        # Save the newest JPEG so the web server can send it to VLC/browser.
        if ok:
            with frame_lock:
                latest_jpeg = jpeg.tobytes()


class StreamHandler(BaseHTTPRequestHandler):
    """
    This creates a tiny web server.

    It gives you two URLs:

        http://ROBOT_IP:8080/

            Simple webpage with the camera preview.

        http://ROBOT_IP:8080/stream.mjpg

            Direct MJPEG stream.
            Open this one in VLC.
    """

    def do_GET(self):
        # If user opens /stream.mjpg, send the video stream.
        if self.path == "/stream.mjpg":
            self.send_mjpeg_stream()
            return

        # Otherwise send a simple webpage.
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(
            b"""
            <html>
            <head>
                <title>Robot Camera</title>
            </head>
            <body>
                <h1>Robot AI Camera Preview</h1>
                <p>Right arm across body to the left = STOP</p>
                <img src="/stream.mjpg" width="640" height="480">
            </body>
            </html>
            """
        )

    def send_mjpeg_stream(self):
        """
        Send the MJPEG stream.

        VLC and browsers can read this.

        It sends frames like this:

            JPEG frame
            JPEG frame
            JPEG frame
            JPEG frame

        many times per second.
        """

        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()

        try:
            while True:
                # Get the latest JPEG frame from the camera callback.
                with frame_lock:
                    frame = latest_jpeg

                # If a frame exists, send it.
                if frame is not None:
                    self.wfile.write(b"--FRAME\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")

                # Small delay.
                # 0.05 seconds is about 20 FPS maximum.
                time.sleep(0.05)

        except BrokenPipeError:
            # This happens when VLC/browser closes the stream.
            # It is not a serious error.
            pass


def start_server(port):
    """
    Start the web server.

    The server runs forever in a separate thread.
    """

    server = HTTPServer(("", port), StreamHandler)
    print(f"Preview server running on port {port}")
    server.serve_forever()


def get_args():
    """
    Read command-line options.

    Useful examples:

        python3 gesture_ai_stop_web.py

        python3 gesture_ai_stop_web.py --fps 15

        python3 gesture_ai_stop_web.py --port 8090

        python3 gesture_ai_stop_web.py --detection-threshold 0.4
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        type=str,
        default="/usr/share/imx500-models/imx500_network_higherhrnet_coco.rpk",
        help="Path to the AI Camera pose model",
    )

    parser.add_argument(
        "--detection-threshold",
        type=float,
        default=0.3,
        help="Person detection threshold. Higher = fewer false detections.",
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="AI detection frame rate",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Web/VLC preview port",
    )

    return parser.parse_args()


if __name__ == "__main__":
    # Read command-line options.
    args = get_args()

    # Load the IMX500 AI model.
    #
    # Important:
    # IMX500 must be created before Picamera2.
    imx500 = IMX500(args.model)

    # Get information about the model.
    intrinsics = imx500.network_intrinsics

    # If the model has no intrinsics, create default intrinsics.
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "pose estimation"

    # Set how fast the AI model should run.
    intrinsics.inference_rate = args.fps
    intrinsics.update_with_defaults()

    # Create Picamera2 using the AI Camera number.
    picam2 = Picamera2(imx500.camera_num)

    # Configure the camera.
    #
    # main:
    #   The video frame that we use for preview.
    #
    # RGB888:
    #   Gives a 3-channel RGB image, easier for OpenCV.
    #
    # FrameRate:
    #   Uses the same FPS as the AI model.
    #
    # buffer_count:
    #   More buffers can make the camera pipeline smoother.
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"},
        controls={"FrameRate": intrinsics.inference_rate},
        buffer_count=12,
    )

    print("Loading AI Camera model...")

    # Show progress while the model loads onto the AI Camera.
    imx500.show_network_fw_progress_bar()

    # Set our callback.
    #
    # This means camera_callback() will run every frame.
    server_thread = threading.Thread(
        target=start_server,
        args=(args.port,),
        daemon=True,
    )
    server_thread.start()

    picam2.pre_callback = camera_callback
    picam2.start(config, show_preview=False)
    imx500.set_auto_aspect_ratio()

    print("Gesture detection running.")
    print("Move RIGHT arm across body to the LEFT for STOP.")
    print()
    print("Open preview in browser:")
    print(f"  http://ROBOT_IP:{args.port}/")
    print()
    print("Open preview in VLC:")
    print(f"  http://ROBOT_IP:{args.port}/stream.mjpg")
    print()
    print("Find ROBOT_IP with:")
    print("  hostname -I")
    print()
    print("Press Ctrl+C to quit.")

    try:
        # Keep program alive.
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nExiting.")

    finally:
        # Stop camera cleanly.
        picam2.stop()
