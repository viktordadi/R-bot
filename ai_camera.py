"""
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
import cv2

from picamera2 import Picamera2, Preview, MappedArray
from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet


# ------------------------------------------------------------
# COCO pose keypoint numbers
# ------------------------------------------------------------
NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16


# Skeleton connections (COCO-style)
SKELETON_LINES = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW),
    (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW),
    (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_HIP, LEFT_KNEE),
    (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_KNEE),
    (RIGHT_KNEE, RIGHT_ANKLE),
]


# ------------------------------------------------------------
# Camera / AI settings
# ------------------------------------------------------------
MODEL_PATH = "/usr/share/imx500-models/imx500_network_higherhrnet_coco.rpk"

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

# postprocess_higherhrnet expects (height, width)
WINDOW_SIZE_H_W = (IMAGE_HEIGHT, IMAGE_WIDTH)

# 10-15 is usually a good balance
FPS = 10

DETECTION_THRESHOLD = 0.3
MIN_KEYPOINT_CONFIDENCE = 0.1


# ------------------------------------------------------------
# Shared state
# ------------------------------------------------------------
current_gesture_command = None
gesture_lock = threading.Lock()

camera_started = False

imx500 = None
picam2 = None

current_person_position = None
person_lock = threading.Lock()


def point_ok(point, min_confidence=MIN_KEYPOINT_CONFIDENCE):
    x, y, confidence = point
    return confidence >= min_confidence


def left_arm_up(person_keypoints):
    shoulder = person_keypoints[LEFT_SHOULDER]
    wrist = person_keypoints[LEFT_WRIST]

    sx, sy, sc = shoulder
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(wrist):
        return False

    return wy < sy - 30


def right_arm_up(person_keypoints):
    shoulder = person_keypoints[RIGHT_SHOULDER]
    wrist = person_keypoints[RIGHT_WRIST]

    sx, sy, sc = shoulder
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(wrist):
        return False

    return wy < sy - 30


def left_arm_out_left(person_keypoints, image_width=IMAGE_WIDTH):
    shoulder = person_keypoints[LEFT_SHOULDER]
    wrist = person_keypoints[LEFT_WRIST]

    sx, sy, sc = shoulder
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(wrist):
        return False

    # Úlnliður þarf bara að vera nógu langt vinstra megin við öxlina
    min_side_distance = image_width * 0.12

    wrist_left_of_shoulder = wx < sx - min_side_distance

    # Ekki leyfa "arm up" að teljast sem left
    not_too_high = wy > sy - image_width * 0.25

    return wrist_left_of_shoulder and not_too_high


def right_arm_out_right(person_keypoints, image_width=IMAGE_WIDTH):
    shoulder = person_keypoints[RIGHT_SHOULDER]
    wrist = person_keypoints[RIGHT_WRIST]

    sx, sy, sc = shoulder
    wx, wy, wc = wrist

    if not point_ok(shoulder):
        return False
    if not point_ok(wrist):
        return False

    # Úlnliður þarf bara að vera nógu langt hægra megin við öxlina
    min_side_distance = image_width * 0.12

    wrist_right_of_shoulder = wx > sx + min_side_distance

    # Ekki leyfa "arm up" að teljast sem right
    not_too_high = wy > sy - image_width * 0.25

    return wrist_right_of_shoulder and not_too_high


def get_pose_command(person_keypoints):
    left_shoulder = person_keypoints[LEFT_SHOULDER]
    right_shoulder = person_keypoints[RIGHT_SHOULDER]
    left_wrist = person_keypoints[LEFT_WRIST]
    right_wrist = person_keypoints[RIGHT_WRIST]

    if not point_ok(left_shoulder):
        return None
    if not point_ok(right_shoulder):
        return None
    if not point_ok(left_wrist):
        return None
    if not point_ok(right_wrist):
        return None

    lsx, lsy, lsc = left_shoulder
    rsx, rsy, rsc = right_shoulder
    lwx, lwy, lwc = left_wrist
    rwx, rwy, rwc = right_wrist

    shoulder_center_y = (lsy + rsy) / 2

    # finna hvor öxlin er vinstra/hægra megin í myndinni
    left_edge_x = min(lsx, rsx)
    right_edge_x = max(lsx, rsx)

    margin = 80

    # STOP: einhver úlnliður greinilega fyrir ofan axlir
    if lwy < shoulder_center_y - 40 or rwy < shoulder_center_y - 40:
        print("DEBUG gesture: stop")
        return "stop"

    # LEFT: einhver hönd er vel fyrir utan vinstri öxl
    if lwx < left_edge_x - margin or rwx < left_edge_x - margin:
        print("DEBUG gesture: left")
        return "left"

    # RIGHT: einhver hönd er vel fyrir utan hægri öxl
    if lwx > right_edge_x + margin or rwx > right_edge_x + margin:
        print("DEBUG gesture: right")
        return "right"

    return None

def parse_pose_output(metadata):
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


def draw_keypoint(frame, point, radius=5):
    x, y, confidence = point
    if confidence >= MIN_KEYPOINT_CONFIDENCE:
        cv2.circle(frame, (int(x), int(y)), radius, (255, 255, 255), -1)


def draw_line(frame, point_a, point_b, thickness=2):
    ax, ay, ac = point_a
    bx, by, bc = point_b

    if ac >= MIN_KEYPOINT_CONFIDENCE and bc >= MIN_KEYPOINT_CONFIDENCE:
        cv2.line(
            frame,
            (int(ax), int(ay)),
            (int(bx), int(by)),
            (255, 255, 255),
            thickness,
        )


def draw_skeleton(frame, person_keypoints):
    # Draw skeleton lines
    for a, b in SKELETON_LINES:
        draw_line(frame, person_keypoints[a], person_keypoints[b])

    # Draw all visible keypoints
    for point in person_keypoints:
        draw_keypoint(frame, point)


def draw_command_text(frame, command):
    if command == "stop":
        text = "STOP"
        color = (255, 255, 255)
    elif command == "left":
        text = "LEFT"
        color = (255, 255, 255)
    elif command == "right":
        text = "RIGHT"
        color = (255, 255, 255)
    else:
        text = "NO GESTURE"
        color = (255, 255, 255)

    cv2.putText(
        frame,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        2,
    )


def get_person_follow_command(person_keypoints):
    """
    Returns:
        "left"        = person is left, robot should turn left
        "center"      = person is centered, robot can go forward
        "right"       = person is right, robot should turn right
        "stop_edge"   = person is nearly out of frame
        None          = person not reliable
    """

    # Use shoulders and hips to estimate body position.
    points_to_use = [
        person_keypoints[LEFT_SHOULDER],
        person_keypoints[RIGHT_SHOULDER],
        person_keypoints[LEFT_HIP],
        person_keypoints[RIGHT_HIP],
    ]

    good_points = []

    for point in points_to_use:
        x, y, confidence = point
        if confidence >= MIN_KEYPOINT_CONFIDENCE:
            good_points.append(point)

    if len(good_points) < 2:
        return None

    xs = [p[0] for p in good_points]

    person_left_x = min(xs)
    person_right_x = max(xs)
    person_center_x = sum(xs) / len(xs)

    image_center_x = IMAGE_WIDTH / 2

    # If person is close to the edge, stop.
    edge_margin = IMAGE_WIDTH * 0.12

    if person_left_x < edge_margin:
        print("FOLLOW: person nearly out of frame left")
        return "stop_edge"

    if person_right_x > IMAGE_WIDTH - edge_margin:
        print("FOLLOW: person nearly out of frame right")
        return "stop_edge"

    # How far from center before turning.
    center_deadzone = IMAGE_WIDTH * 0.15

    if person_center_x < image_center_x - center_deadzone:
        return "left"

    if person_center_x > image_center_x + center_deadzone:
        return "right"

    return "center"


def get_person_position():
    """
    Used by autopilot follow mode.

    Returns:
        "left"
        "center"
        "right"
        "stop_edge"
        None
    """

    with person_lock:
        return current_person_position


def camera_callback(request):
    """
    Runs automatically every camera frame.
    Updates current_gesture_command and draws the skeleton on the preview.
    """

    global current_gesture_command, current_person_position

    metadata = request.get_metadata()
    keypoints = parse_pose_output(metadata)

    command = None
    person_position = None

    with MappedArray(request, "main") as m:
        frame = m.array

        if keypoints is not None:
            for person in keypoints:
                draw_skeleton(frame, person)

                person_command = get_pose_command(person)

                if command is None and person_command is not None:
                    command = person_command

                if person_position is None:
                    person_position = get_person_follow_command(person)
    
        draw_command_text(frame, command)

        with gesture_lock:
            current_gesture_command = command

        with person_lock:
            current_person_position = person_position

def start_gesture_camera(show_preview=False):
    """
    Starts the AI Camera gesture detector.
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
        main={"size": (IMAGE_WIDTH, IMAGE_HEIGHT), "format": "XRGB8888"},
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
    with gesture_lock:
        return current_gesture_command


def stop_gesture_camera():
    global camera_started, picam2, imx500

    if picam2 is not None:
        try:
            picam2.stop()
        except Exception as e:
            print("AI camera stop error:", e)

        try:
            picam2.close()
        except Exception as e:
            print("AI camera close error:", e)

    picam2 = None
    imx500 = None
    camera_started = False

    time.sleep(1.0)


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
