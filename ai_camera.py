"""
get_gesture_command() skilar:

    "stop"   = hönd/armur upp
    "left"   = hönd langt til vinstri
    "right"  = hönd langt til hægri
    None     = ekkert gesture

get_person_center_offset() skilar:

    -1.0  = manneskja langt til vinstri
     0.0  = manneskja í miðju
    +1.0  = manneskja langt til hægri
    None  = engin manneskja sést

get_person_position() skilar:

    "left"
    "center"
    "right"
    None
"""

import time
import threading

import cv2
import numpy as np

from picamera2 import Picamera2, Preview, MappedArray
from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet


# ------------------------------------------------------------
# COCO pose keypoint númer
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


# Línur sem teikna beinagrindina á preview
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
# Camera / AI stillingar
# ------------------------------------------------------------

MODEL_PATH = "/usr/share/imx500-models/imx500_network_higherhrnet_coco.rpk"

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

# postprocess_higherhrnet vill fá stærð sem (height, width)
WINDOW_SIZE_H_W = (IMAGE_HEIGHT, IMAGE_WIDTH)

FPS = 10

DETECTION_THRESHOLD = 0.3

# Lægra gildi = auðveldara að samþykkja keypoints, en getur verið minna nákvæmt
MIN_KEYPOINT_CONFIDENCE = 0.1


# ------------------------------------------------------------
# Shared state
# ------------------------------------------------------------

current_gesture_command = None
current_person_offset = None

gesture_lock = threading.Lock()
person_lock = threading.Lock()

camera_started = False

imx500 = None
picam2 = None


# ------------------------------------------------------------
# Hjálparföll fyrir keypoints
# ------------------------------------------------------------

def point_ok(point, min_confidence=MIN_KEYPOINT_CONFIDENCE):
    """
    Athugar hvort keypoint sé nógu öruggt.

    point er:
        (x, y, confidence)

    Skilar:
        True ef confidence er nógu hátt
        False annars
    """

    x, y, confidence = point
    return confidence >= min_confidence


def get_torso_points(person_keypoints):
    """
    Sækir torso punkta sem eru notaðir til að finna miðju manneskju.

    Við notum axlir og mjaðmir því það er stöðugra en að nota höfuð,
    sérstaklega þegar myndavélin er lág og hausinn fer út úr mynd.

    Skilar lista af punktum.
    """

    return [
        person_keypoints[LEFT_SHOULDER],
        person_keypoints[RIGHT_SHOULDER],
        person_keypoints[LEFT_HIP],
        person_keypoints[RIGHT_HIP],
    ]


def get_good_points(points):
    """
    Tekur lista af keypoints og skilar bara þeim sem eru með nógu hátt confidence.
    """

    good_points = []

    for point in points:
        if point_ok(point):
            good_points.append(point)

    return good_points


# ------------------------------------------------------------
# Velja target person
# ------------------------------------------------------------

def choose_center_person(keypoints):
    """
    Velur þá manneskju sem er næst miðju myndarinnar.

    Þetta er notað svo robotinn fylgi ekki einhverjum sem er út á hlið
    ef fleiri en ein manneskja sést.

    Inntak:
        keypoints = allar manneskjur sem AI camera finnur

    Skilar:
        keypoints fyrir eina manneskju
        None ef engin nothæf manneskja fannst
    """

    if keypoints is None or len(keypoints) == 0:
        return None

    image_center_x = IMAGE_WIDTH / 2

    best_person = None
    best_distance = None

    for person in keypoints:
        torso_points = get_torso_points(person)
        good_points = get_good_points(torso_points)

        # Við þurfum að minnsta kosti tvo torso punkta til að treysta staðsetningu
        if len(good_points) < 2:
            continue

        xs = [point[0] for point in good_points]
        person_center_x = sum(xs) / len(xs)

        distance_from_center = abs(person_center_x - image_center_x)

        if best_distance is None or distance_from_center < best_distance:
            best_distance = distance_from_center
            best_person = person

    return best_person


def get_person_offset(person_keypoints):
    """
    Reiknar hversu langt manneskjan er frá miðju myndarinnar.

    Skilar:
        -1.0 = langt til vinstri
         0.0 = í miðju
        +1.0 = langt til hægri
        None = ekki nógu góð gögn

    Þetta er notað í smooth follow mode.
    """

    torso_points = get_torso_points(person_keypoints)
    good_points = get_good_points(torso_points)

    if len(good_points) < 2:
        return None

    xs = [point[0] for point in good_points]

    person_center_x = sum(xs) / len(xs)
    image_center_x = IMAGE_WIDTH / 2

    offset_pixels = person_center_x - image_center_x
    offset_normalized = offset_pixels / image_center_x

    # Passa að gildið fari ekki út fyrir -1.0 til +1.0
    offset_normalized = max(-1.0, min(1.0, offset_normalized))

    return offset_normalized


def get_person_center_offset():
    """
    Skilar nýjasta offset gildi fyrir follow mode.

    Skilar:
        -1.0 til +1.0
        None ef engin manneskja sést

    Þetta fall er kallað úr autopilot.py.
    """

    with person_lock:
        return current_person_offset

# ------------------------------------------------------------
# Gesture detection
# ------------------------------------------------------------

def left_arm_up(person_keypoints):
    """
    Athugar hvort vinstri úlnliður sé fyrir ofan vinstri öxl.

    Skilar:
        True ef vinstri armur virðist vera uppi
        False annars
    """

    shoulder = person_keypoints[LEFT_SHOULDER]
    wrist = person_keypoints[LEFT_WRIST]

    if not point_ok(shoulder):
        return False

    if not point_ok(wrist):
        return False

    sx, sy, sc = shoulder
    wx, wy, wc = wrist

    return wy < sy - 30


def right_arm_up(person_keypoints):
    """
    Athugar hvort hægri úlnliður sé fyrir ofan hægri öxl.

    Skilar:
        True ef hægri armur virðist vera uppi
        False annars
    """

    shoulder = person_keypoints[RIGHT_SHOULDER]
    wrist = person_keypoints[RIGHT_WRIST]

    if not point_ok(shoulder):
        return False

    if not point_ok(wrist):
        return False

    sx, sy, sc = shoulder
    wx, wy, wc = wrist

    return wy < sy - 30


def get_pose_command(person_keypoints):
    """
    Finnur gesture frá einni manneskju.

    Gestures:
        Hönd fyrir ofan axlir      -> "stop"
        Hönd langt til vinstri     -> "left"
        Hönd langt til hægri       -> "right"

    Skilar:
        "stop"
        "left"
        "right"
        None
    """

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

    left_edge_x = min(lsx, rsx)
    right_edge_x = max(lsx, rsx)

    margin = 80

    # STOP: einhver hönd er greinilega fyrir ofan axlir
    if lwy < shoulder_center_y - 40 or rwy < shoulder_center_y - 40:
        return "stop"

    # LEFT: einhver hönd er langt vinstra megin við líkamann
    if lwx < left_edge_x - margin or rwx < left_edge_x - margin:
        return "left"

    # RIGHT: einhver hönd er langt hægra megin við líkamann
    if lwx > right_edge_x + margin or rwx > right_edge_x + margin:
        return "right"

    return None


def get_gesture_command():
    """
    Skilar nýjasta gesture command frá AI camera.

    Þetta fall er kallað úr autopilot.py eða main.py.

    Skilar:
        "stop"
        "left"
        "right"
        None
    """

    with gesture_lock:
        return current_gesture_command


# ------------------------------------------------------------
# AI output parsing
# ------------------------------------------------------------

def parse_pose_output(metadata):
    """
    Les AI output frá IMX500 og breytir því í keypoints.

    Inntak:
        metadata frá camera request

    Skilar:
        keypoints með shape:
            (fjöldi_manneskja, 17, 3)

        eða None ef engin manneskja fannst.
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


# ------------------------------------------------------------
# Teikna skeleton / texta á preview
# ------------------------------------------------------------

def draw_keypoint(frame, point, radius=5):
    """
    Teiknar einn punkt á myndina ef confidence er nógu hátt.
    """

    x, y, confidence = point

    if confidence >= MIN_KEYPOINT_CONFIDENCE:
        cv2.circle(
            frame,
            (int(x), int(y)),
            radius,
            (255, 255, 255),
            -1,
        )


def draw_line(frame, point_a, point_b, thickness=2):
    """
    Teiknar línu milli tveggja keypoints ef báðir punktar eru nógu öruggir.
    """

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
    """
    Teiknar beinagrind fyrir eina manneskju á preview myndina.
    """

    for a, b in SKELETON_LINES:
        draw_line(frame, person_keypoints[a], person_keypoints[b])

    for point in person_keypoints:
        draw_keypoint(frame, point)


def draw_command_text(frame, command):
    """
    Teiknar gesture command texta á myndina.
    """

    if command == "stop":
        text = "STOP"
    elif command == "left":
        text = "LEFT"
    elif command == "right":
        text = "RIGHT"
    else:
        text = "NO GESTURE"

    cv2.putText(
        frame,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2,
    )


def draw_target_text(frame, person_offset):
    """
    Teiknar TARGET og offset upplýsingar á preview.
    """

    cv2.putText(
        frame,
        "TARGET",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2,
    )

    if person_offset is not None:
        cv2.putText(
            frame,
            f"OFFSET: {person_offset:.2f}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )


# ------------------------------------------------------------
# Camera callback
# ------------------------------------------------------------

def camera_callback(request):
    """
    Þetta fall keyrir sjálfkrafa fyrir hvern camera frame.

    Það gerir:
        1. Les pose output frá AI camera
        2. Velur manneskjuna sem er næst miðju
        3. Uppfærir gesture command
        4. Uppfærir person offset fyrir follow mode
        5. Teiknar skeleton og texta á preview
    """

    global current_gesture_command
    global current_person_offset

    metadata = request.get_metadata()
    keypoints = parse_pose_output(metadata)

    command = None
    person_offset = None

    center_person = choose_center_person(keypoints)

    with MappedArray(request, "main") as mapped:
        frame = mapped.array

        if keypoints is not None:
            for person in keypoints:
                draw_skeleton(frame, person)

        if center_person is not None:
            command = get_pose_command(center_person)
            person_offset = get_person_offset(center_person)
            draw_target_text(frame, person_offset)

        draw_command_text(frame, command)

    with gesture_lock:
        current_gesture_command = command

    with person_lock:
        current_person_offset = person_offset


# ------------------------------------------------------------
# Start / stop camera
# ------------------------------------------------------------

def start_gesture_camera(show_preview=False):
    """
    Startar AI gesture camera.

    show_preview=True:
        Opnar local preview glugga á Pi skjá.

    show_preview=False:
        Keyrir AI camera án local preview.
        Þetta er yfirleitt betra þegar þú notar dashboard/systemd.
    """

    global camera_started
    global imx500
    global picam2

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
        main={
            "size": (IMAGE_WIDTH, IMAGE_HEIGHT),
            "format": "XRGB8888",
        },
        controls={
            "FrameRate": intrinsics.inference_rate,
        },
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


def stop_gesture_camera():
    """
    Stoppar AI camera og losar myndavélina.

    Þetta er mikilvægt svo önnur camera mode geti notað myndavélina
    og svo þú fáir ekki:
        Device or resource busy
    """

    global camera_started
    global picam2
    global imx500
    global current_gesture_command
    global current_person_offset

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

    with gesture_lock:
        current_gesture_command = None

    with person_lock:
        current_person_offset = None

    time.sleep(1.0)


# ------------------------------------------------------------
# Test mode
# ------------------------------------------------------------

if __name__ == "__main__":
    """
    Testar ai_camera.py beint.

    Keyra:
        python3 ai_camera.py

    Með preview:
        python3 ai_camera.py --preview
    """

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    start_gesture_camera(show_preview=args.preview)

    try:
        last_command = None
        last_position = None

        while True:
            command = get_gesture_command()
            position = get_person_position()

            if command != last_command or position != last_position:
                print("gesture:", command, "person:", position)
                last_command = command
                last_position = position

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting.")

    finally:
        stop_gesture_camera()
