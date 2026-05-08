"""
ai_camera.py

Uses the Raspberry Pi AI Camera pose model.

This file is meant to be imported by autopilot.py.

autopilot.py can call:

    start_gesture_camera(show_preview=True or False)
    get_gesture_command()
    stop_gesture_camera()

get_gesture_command() returns:

    "stop"   = left arm up OR right arm up
    "left"   = left arm stretched out to the left
    "right"  = right arm stretched out to the right
    None     = no gesture detected

Gestures:

    Left arm up      -> stop
    Right arm up     -> stop
    Left arm out     -> go left
    Right arm out    -> go right
"""

import time
import threading
import numpy as np

from picamera2 import Picamera2, Preview
from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet


# ------------------------------------------------------------
# COCO pose keypoint numbers
# ------------------------------------------------------------
# The pose model detects 17 body points.
#
# These are the ones we need:
#
#   left shoulder  = 5
#   right shoulder = 6
#   left elbow     = 7
#   right elbow    = 8
#   left wrist     = 9
#   right wrist    = 10
# ------------------------------------------------------------

LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10


# ------------------------------------------------------------
# Camera / AI settings
# ------------------------------------------------------------

MODEL_PATH = "/usr/share/imx500-models/imx500_network_higherhrnet_coco.rpk"

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

# postprocess_higherhrnet wants height, width
WINDOW_SIZE_H_W = (IMAGE_HEIGHT, IMAGE_WIDTH)

# 10 or 15 is usually safer than 60 for AI pose detection.
# If you want lower delay, try FPS = 15.
FPS = 10

DETECTION_THRESHOLD = 0.3

# Confidence for shoulder/elbow/wrist points.
# Lower = easier to trigger, but more false gestures.
MIN_KEYPOINT_CONFIDENCE = 0.2


# ------------------------------------------------------------
# Shared state
# ------------------------------------------------------------

current_gesture_command = None
gesture_lock = threading.Lock()

camera_started = False

imx500 = None
picam2 = None


def point_ok(point, min_confidence=MIN_KEYPOINT_CONFIDENCE):
    """
    Returns True if the keypoint confidence is high enough.
    """

    x, y, confidence = point
    return confidence >= min_confidence


def left_arm_up(person_keypoints):
    """
    Returns True if the left arm is raised.

    Image coordinates:
        smaller y = higher in the image
        bigger y  = lower in the image
    """

    shoulder = person_keypoints[LEFT_SHOULDER]
    elbow = person_keypoints[LEFT_ELBOW]
    wrist = person_keypoints[LEFT_WRIST]

    sx, sy, sc = shoulder
    ex, ey, ec = elbow
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(elbow):
        return False
    if not point_ok(wrist):
        return False

    wrist_above_shoulder = wy < sy
    elbow_above_shoulder = ey < sy

    return wrist_above_shoulder and elbow_above_shoulder


def right_arm_up(person_keypoints):
    """
    Returns True if the right arm is raised.
    """

    shoulder = person_keypoints[RIGHT_SHOULDER]
    elbow = person_keypoints[RIGHT_ELBOW]
    wrist = person_keypoints[RIGHT_WRIST]

    sx, sy, sc = shoulder
    ex, ey, ec = elbow
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(elbow):
        return False
    if not point_ok(wrist):
        return False

    wrist_above_shoulder = wy < sy
    elbow_above_shoulder = ey < sy

    return wrist_above_shoulder and elbow_above_shoulder


def left_arm_out_left(person_keypoints, image_width=IMAGE_WIDTH):
    """
    Returns True if the left arm is stretched out to the left.
    """

    shoulder = person_keypoints[LEFT_SHOULDER]
    elbow = person_keypoints[LEFT_ELBOW]
    wrist = person_keypoints[LEFT_WRIST]

    sx, sy, sc = shoulder
    ex, ey, ec = elbow
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(elbow):
        return False
    if not point_ok(wrist):
        return False

    min_side_distance = image_width * 0.15

    wrist_left_of_shoulder = wx < sx - min_side_distance
    elbow_left_of_shoulder = ex < sx

    arm_horizontal = abs(wy - sy) < image_width * 0.20
    wrist_elbow_aligned = abs(wy - ey) < image_width * 0.15

    return (
        wrist_left_of_shoulder
        and elbow_left_of_shoulder
        and arm_horizontal
        and wrist_elbow_aligned
    )


def right_arm_out_right(person_keypoints, image_width=IMAGE_WIDTH):
    """
    Returns True if the right arm is stretched out to the right.
    """

    shoulder = person_keypoints[RIGHT_SHOULDER]
    elbow = person_keypoints[RIGHT_ELBOW]
    wrist = person_keypoints[RIGHT_WRIST]

    sx, sy, sc = shoulder
    ex, ey, ec = elbow
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(elbow):
        return False
    if not point_ok(wrist):
        return False

    min_side_distance = image_width * 0.15

    wrist_right_of_shoulder = wx > sx + min_side_distance
    elbow_right_of_shoulder = ex > sx

    arm_horizontal = abs(wy - sy) < image_width * 0.20
    wrist_elbow_aligned = abs(wy - ey) < image_width * 0.15

    return (
        wrist_right_of_shoulder
        and elbow_right_of_shoulder
        and arm_horizontal
        and wrist_elbow_aligned
    )


def get_pose_command(person_keypoints):
    """
    Converts pose keypoints into a robot command.

    Returns:
        "stop"
        "left"
        "right"
        None
    """

    # Stop has highest priority.
    if left_arm_up(person_keypoints) or right_arm_up(person_keypoints):
        return "stop"

    if left_arm_out_left(person_keypoints):
        return "left"

    if right_arm_out_right(person_keypoints):
        return "right"

    return None


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
            command = get_pose_command(person)

            if command is not None:
                break

    with gesture_lock:
        current_gesture_command = command


def start_gesture_camera(show_preview=False):
    """
    Starts the AI Camera gesture detector.

    Call this once from autopilot.py.
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
        buffer_count=3,
    )

    imx500.show_network_fw_progress_bar()

    picam2.pre_callback = camera_callback

    if show_preview:
        picam2.start_preview(Preview.QTGL)
        picam2.start(config)
    else:
        picam2.start(config, show_preview=False)

    imx500.set_auto_aspect_ratio()

    camera_started = True

    print("AI gesture camera started.")


def get_gesture_command():
    """
    Returns the latest gesture command.

    Returns:
        "stop"
        "left"
        "right"
        None
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
