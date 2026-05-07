
"""
gesture_ai_stop.py

This file is meant to be imported by autopilot.py.

It starts the Raspberry Pi AI Camera pose detector in the background.

Then autopilot.py can call:

    get_gesture_command()

That function returns:

    "stop"   if the right arm stop gesture is detected
    None     if no gesture is detected

Gesture:
    right arm stretched across the body toward the LEFT side of the image
"""

import time
import threading
import numpy as np

from picamera2 import Picamera2
from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet


# COCO pose keypoint numbers
RIGHT_SHOULDER = 6
RIGHT_ELBOW = 8
RIGHT_WRIST = 10

WINDOW_SIZE_H_W = (480, 640)

MODEL_PATH = "/usr/share/imx500-models/imx500_network_higherhrnet_coco.rpk"
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
FPS = 10
DETECTION_THRESHOLD = 0.3


# This is the value autopilot.py will read.
# It will be either:
#   "stop"
#   None
current_gesture_command = None

# Prevents two threads from reading/writing current_gesture_command at the same time.
gesture_lock = threading.Lock()

# Prevents starting the camera twice.
camera_started = False

# These are created in start_gesture_camera()
imx500 = None
picam2 = None


def right_arm_fully_left(person_keypoints, image_width=640, min_confidence=0.3):
    """
    Returns True if the right arm is stretched left across the body.
    Otherwise returns False.
    """

    right_shoulder = person_keypoints[RIGHT_SHOULDER]
    right_elbow = person_keypoints[RIGHT_ELBOW]
    right_wrist = person_keypoints[RIGHT_WRIST]

    sx, sy, sc = right_shoulder
    ex, ey, ec = right_elbow
    wx, wy, wc = right_wrist

    if sc < min_confidence or ec < min_confidence or wc < min_confidence:
        return False

    min_left_distance = image_width * 0.20

    wrist_is_left_of_shoulder = wx < sx - min_left_distance
    elbow_is_left_of_shoulder = ex < sx
    arm_is_roughly_horizontal = abs(wy - sy) < image_width * 0.20
    wrist_and_elbow_aligned = abs(wy - ey) < image_width * 0.15

    return (
        wrist_is_left_of_shoulder
        and elbow_is_left_of_shoulder
        and arm_is_roughly_horizontal
        and wrist_and_elbow_aligned
    )


def parse_pose_output(metadata):
    """
    Converts raw AI Camera output into pose keypoints.
    """

    outputs = imx500.get_outputs(metadata=metadata, add_batch=True)

    if outputs is None:
        return None

    keypoints, scores, boxes = postprocess_higherhrnet(
        outputs=outputs,
        img_size=WINDOW_SIZE_H_W,
        img_w_pad=(0, 0),
        img_h_pad=(0, 0),
        detection_threshold=DETECTION_THRESHOLD,
        network_postprocess=True,
    )

    if scores is None or len(scores) == 0:
        return None

    keypoints = np.reshape(np.stack(keypoints, axis=0), (len(scores), 17, 3))

    return keypoints


def camera_callback(request):
    """
    Runs automatically every camera frame.
    Updates current_gesture_command.
    """

    global current_gesture_command

    metadata = request.get_metadata()
    keypoints = parse_pose_output(metadata)

    command = None

    if keypoints is not None:
        for person in keypoints:
            if right_arm_fully_left(person, image_width=IMAGE_WIDTH):
                command = "stop"
                break

    with gesture_lock:
        current_gesture_command = command


def start_gesture_camera(show_preview=False):
    """
    Starts the AI Camera gesture detector.

    Call this once at the start of autopilot.py.
    """

    global camera_started, imx500, picam2

    if camera_started:
        return

    print("Starting AI gesture camera...")

    imx500 = IMX500(MODEL_PATH)

    intrinsics = imx500.network_intrinsics
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "pose estimation"

    if intrinsics.task != "pose estimation":
        raise RuntimeError("This model is not a pose estimation model")

    intrinsics.inference_rate = FPS
    intrinsics.update_with_defaults()

    picam2 = Picamera2(imx500.camera_num)

    config = picam2.create_preview_configuration(
        main={"size": (IMAGE_WIDTH, IMAGE_HEIGHT)},
        controls={"FrameRate": intrinsics.inference_rate},
        buffer_count=12,
    )

    imx500.show_network_fw_progress_bar()

    picam2.pre_callback = camera_callback
    picam2.start(config, show_preview=show_preview)

    imx500.set_auto_aspect_ratio()

    camera_started = True

    print("AI gesture camera started.")


def get_gesture_command():
    """
    Returns the latest gesture command.

    Returns:
        "stop" if stop gesture is currently detected
        None if no stop gesture is detected
    """

    with gesture_lock:
        return current_gesture_command


def stop_gesture_camera():
    """
    Stops the AI Camera cleanly.
    """

    global camera_started

    if picam2 is not None:
        picam2.stop()

    camera_started = False


if __name__ == "__main__":
    # Test mode.
    # Run:
    #   python3 gesture_ai_stop.py --preview
    #
    # For simple testing, this starts the camera and prints the command.

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    start_gesture_camera(show_preview=args.preview)

    try:
        last = None

        while True:
            command = get_gesture_command()

            if command != last:
                print(command)
                last = command

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting.")

    finally:
        stop_gesture_camera()
