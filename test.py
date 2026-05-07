import argparse
import time
import numpy as np

from picamera2 import Picamera2
from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet


# COCO keypoint indexes used by the pose model
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10

WINDOW_SIZE_H_W = (480, 640)

last_command = None


def right_arm_fully_left(person_keypoints, image_width=640, min_confidence=0.3):
    """
    Returns True if the right arm is extended left across the body.

    person_keypoints shape should be:
    17 keypoints, each as (x, y, confidence)
    """

    right_shoulder = person_keypoints[RIGHT_SHOULDER]
    right_elbow = person_keypoints[RIGHT_ELBOW]
    right_wrist = person_keypoints[RIGHT_WRIST]

    sx, sy, sc = right_shoulder
    ex, ey, ec = right_elbow
    wx, wy, wc = right_wrist

    # Ignore weak/missing detections
    if sc < min_confidence or ec < min_confidence or wc < min_confidence:
        return False

    # How far left the wrist must be from the shoulder
    min_left_distance = image_width * 0.20

    wrist_is_left_of_shoulder = wx < sx - min_left_distance
    elbow_is_left_of_shoulder = ex < sx

    # Arm should be roughly horizontal
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
    Gets pose keypoints from the AI Camera output tensor.
    """

    np_outputs = imx500.get_outputs(metadata=metadata, add_batch=True)

    if np_outputs is None:
        return None, None, None

    keypoints, scores, boxes = postprocess_higherhrnet(
        outputs=np_outputs,
        img_size=WINDOW_SIZE_H_W,
        img_w_pad=(0, 0),
        img_h_pad=(0, 0),
        detection_threshold=args.detection_threshold,
        network_postprocess=True,
    )

    if scores is None or len(scores) == 0:
        return None, None, None

    keypoints = np.reshape(np.stack(keypoints, axis=0), (len(scores), 17, 3))
    scores = np.array(scores)

    return keypoints, scores, boxes


def camera_callback(request):
    """
    Runs every camera frame.
    """

    global last_command

    metadata = request.get_metadata()
    keypoints, scores, boxes = parse_pose_output(metadata)

    if keypoints is None:
        last_command = None
        return

    stop_detected = False

    for person in keypoints:
        if right_arm_fully_left(person, image_width=640):
            stop_detected = True
            break

    if stop_detected:
        if last_command != "stop":
            print("STOP")

            # Later, connect your robot stop function here:
            # from autopilot import stop
            # stop()

        last_command = "stop"

    else:
        if last_command == "stop":
            print("clear")

        last_command = None


def get_args():
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
        help="Pose detection confidence threshold",
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="AI inference frame rate",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show camera preview window",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    # Must be created before Picamera2
    imx500 = IMX500(args.model)

    intrinsics = imx500.network_intrinsics
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "pose estimation"

    if intrinsics.task != "pose estimation":
        raise RuntimeError("This model is not a pose estimation model")

    intrinsics.inference_rate = args.fps
    intrinsics.update_with_defaults()

    picam2 = Picamera2(imx500.camera_num)

    config = picam2.create_preview_configuration(
        main={"size": (640, 480)},
        controls={"FrameRate": intrinsics.inference_rate},
        buffer_count=12,
    )

    print("Loading AI Camera model...")
    imx500.show_network_fw_progress_bar()

    picam2.pre_callback = camera_callback
    picam2.start(config, show_preview=args.preview)

    imx500.set_auto_aspect_ratio()

    print("Running gesture detection.")
    print("Move your RIGHT arm across your body to the LEFT to print STOP.")
    print("Press Ctrl+C to quit.")

    try:
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting.")

    finally:
        picam2.stop()
