def detect_right_arm_fully_left(keypoints, image_width, min_confidence=0.4):
    required = ["right_shoulder", "right_elbow", "right_wrist"]

    for name in required:
        if name not in keypoints or keypoints[name] is None:
            return None

    sx, sy, sc = keypoints["right_shoulder"]
    ex, ey, ec = keypoints["right_elbow"]
    wx, wy, wc = keypoints["right_wrist"]

    if sc < min_confidence or ec < min_confidence or wc < min_confidence:
        return None

    min_left_distance = image_width * 0.20

    wrist_is_left_of_shoulder = wx < sx - min_left_distance
    elbow_is_left_of_shoulder = ex < sx
    arm_is_roughly_horizontal = abs(wy - sy) < image_width * 0.20
    wrist_and_elbow_aligned = abs(wy - ey) < image_width * 0.15

    if (
        wrist_is_left_of_shoulder
        and elbow_is_left_of_shoulder
        and arm_is_roughly_horizontal
        and wrist_and_elbow_aligned
    ):
        return "stop"

    return None


# Fake example keypoints, just to test the function
keypoints = {
    "right_shoulder": (420, 240, 0.9),
    "right_elbow": (320, 245, 0.8),
    "right_wrist": (230, 250, 0.8),
}

command = detect_right_arm_fully_left(keypoints, image_width=640)

print(command)
