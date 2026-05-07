"""
gesture_ai_stop.py

This program uses the Raspberry Pi AI Camera to detect a human pose.

It watches the person's RIGHT arm.

If the right arm is stretched across the body toward the LEFT side
of the image, the program prints:

    STOP

Later, you can connect that STOP command to your robot's motor stop function.
"""

import argparse
import time
import numpy as np

from picamera2 import Picamera2
from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet


# ------------------------------------------------------------
# COCO pose keypoint numbers
# ------------------------------------------------------------
# The pose model finds 17 body points.
# Each point has:
#   x position
#   y position
#   confidence score
#
# These numbers come from the COCO human pose format.
#
# Important ones for this program:
#   right shoulder = 6
#   right elbow    = 8
#   right wrist    = 10
# ------------------------------------------------------------

LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10


# The camera preview/frame size.
# The format here is height, width.
WINDOW_SIZE_H_W = (480, 640)


# This remembers the previous command.
# It stops the program from printing STOP again and again every frame.
last_command = None


def right_arm_fully_left(person_keypoints, image_width=640, min_confidence=0.3):
    """
    Checks if the person's right arm is stretched left.

    Input:
        person_keypoints:
            The 17 detected body points for one person.

        image_width:
            Width of the camera image.
            We use 640 because the camera config is 640x480.

        min_confidence:
            Minimum confidence needed for shoulder, elbow, and wrist.
            If confidence is too low, we ignore the detection.

    Returns:
        True  = right arm looks like the stop gesture
        False = no stop gesture
    """

    # Get the right shoulder, elbow, and wrist points.
    right_shoulder = person_keypoints[RIGHT_SHOULDER]
    right_elbow = person_keypoints[RIGHT_ELBOW]
    right_wrist = person_keypoints[RIGHT_WRIST]

    # Each point has:
    #   x = left/right position in image
    #   y = up/down position in image
    #   c = confidence score
    sx, sy, sc = right_shoulder
    ex, ey, ec = right_elbow
    wx, wy, wc = right_wrist

    # If the camera is not confident enough, ignore this frame.
    if sc < min_confidence or ec < min_confidence or wc < min_confidence:
        return False

    # The wrist must be at least 20% of the image width
    # to the left of the shoulder.
    min_left_distance = image_width * 0.20

    # In image coordinates:
    #   smaller x = more left
    #   bigger x  = more right
    wrist_is_left_of_shoulder = wx < sx - min_left_distance
    elbow_is_left_of_shoulder = ex < sx

    # Check that the arm is roughly horizontal.
    # This helps avoid false STOP detections when the arm is just down.
    arm_is_roughly_horizontal = abs(wy - sy) < image_width * 0.20
    wrist_and_elbow_aligned = abs(wy - ey) < image_width * 0.15

    # If all these are true, we say the stop gesture was detected.
    return (
        wrist_is_left_of_shoulder
        and elbow_is_left_of_shoulder
        and arm_is_roughly_horizontal
        and wrist_and_elbow_aligned
    )


def parse_pose_output(metadata):
    """
    Converts the raw AI Camera output into useful pose keypoints.

    The AI Camera gives raw neural-network output.
    postprocess_higherhrnet() converts that output into:
        keypoints = body points
        scores    = confidence scores for people
        boxes     = bounding boxes
    """

    # Ask the IMX500 camera for the neural-network outputs.
    np_outputs = imx500.get_outputs(metadata=metadata, add_batch=True)

    # If there is no output yet, return nothing.
    if np_outputs is None:
        return None, None, None

    # Convert the neural-network output into human pose keypoints.
    keypoints, scores, boxes = postprocess_higherhrnet(
        outputs=np_outputs,
        img_size=WINDOW_SIZE_H_W,
        img_w_pad=(0, 0),
        img_h_pad=(0, 0),
        detection_threshold=args.detection_threshold,
        network_postprocess=True,
    )

    # If no person was found, return nothing.
    if scores is None or len(scores) == 0:
        return None, None, None

    # Reshape keypoints into:
    #   number_of_people x 17_keypoints x 3_values
    #
    # The 3 values are:
    #   x, y, confidence
    keypoints = np.reshape(np.stack(keypoints, axis=0), (len(scores), 17, 3))
    scores = np.array(scores)

    return keypoints, scores, boxes


def camera_callback(request):
    """
    This function runs automatically for every camera frame.

    Every frame:
        1. Get AI pose data
        2. Check each detected person
        3. If right arm is stretched left, print STOP
    """

    global last_command

    # Get metadata from this camera frame.
    # The AI Camera results are stored inside the metadata.
    metadata = request.get_metadata()

    # Convert metadata into body keypoints.
    keypoints, scores, boxes = parse_pose_output(metadata)

    # If no person/keypoints were detected, clear the command.
    if keypoints is None:
        last_command = None
        return

    stop_detected = False

    # Check every detected person.
    for person in keypoints:
        if right_arm_fully_left(person, image_width=640):
            stop_detected = True
            break

    if stop_detected:
        # Only print STOP once when the gesture first appears.
        if last_command != "stop":
            print("STOP")

            # ------------------------------------------------
            # Later you can connect your robot stop code here.
            #
            # Example:
            #
            # from autopilot import stop
            # stop()
            #
            # Be careful importing autopilot directly because your
            # autopilot.py starts a servo thread when imported.
            # ------------------------------------------------

        last_command = "stop"

    else:
        # Print clear once when the stop gesture disappears.
        if last_command == "stop":
            print("clear")

        last_command = None


def get_args():
    """
    Reads command-line options.

    Example:
        python3 gesture_ai_stop.py --preview

    Options:
        --preview
            Opens a local preview window.

        --fps
            Sets the AI detection frame rate.

        --detection-threshold
            Higher number = fewer false detections.
            Lower number  = detects people more easily.
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
    # Read command-line options.
    args = get_args()

    # Load the AI Camera neural-network model.
    #
    # Important:
    # IMX500 must be created before Picamera2.
    imx500 = IMX500(args.model)

    # Get model information.
    intrinsics = imx500.network_intrinsics

    # If the model has no intrinsics, make default ones.
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "pose estimation"

    # Make sure we are using a pose-estimation model.
    if intrinsics.task != "pose estimation":
        raise RuntimeError("This model is not a pose estimation model")

    # Set the AI inference speed.
    intrinsics.inference_rate = args.fps
    intrinsics.update_with_defaults()

    # Create the Picamera2 object using the AI Camera.
    picam2 = Picamera2(imx500.camera_num)

    # Configure the camera.
    #
    # main size:
    #   The image size we want from the camera.
    #
    # FrameRate:
    #   Matches the AI inference rate.
    config = picam2.create_preview_configuration(
        main={"size": (640, 480)},
        controls={"FrameRate": intrinsics.inference_rate},
        buffer_count=12,
    )

    print("Loading AI Camera model...")

    # Shows model loading progress in the terminal.
    imx500.show_network_fw_progress_bar()

    # Tell Picamera2 to run camera_callback() on every frame.
    picam2.pre_callback = camera_callback

    # Start the camera.
    #
    # If you run with --preview, you get a preview window.
    # If you do not use --preview, it runs without a window.
    picam2.start(config, show_preview=args.preview)

    # Make sure the AI model uses the correct image shape.
    imx500.set_auto_aspect_ratio()

    print("Running gesture detection.")
    print("Move your RIGHT arm across your body to the LEFT to print STOP.")
    print("Press Ctrl+C to quit.")

    try:
        # Keep the program alive.
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting.")

    finally:
        # Stop the camera cleanly.
        picam2.stop()
