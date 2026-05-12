import threading
import time
import dashboard
import servo
import srf02
import smbus
import audio

from ai_camera import (
    start_gesture_camera,
    get_gesture_command,
    get_person_position,
    get_person_center_offset,
    stop_gesture_camera,
)


i2c_lock = threading.Lock()

bus = smbus.SMBus(1)

MOTOR_ADDRESS = 0x50
motor_speed = 220


servo_thread = None
servo_loop_running = False


def servo_loop():
    global servo_loop_running

    while servo_loop_running:
        with i2c_lock:
            servo.scan()
        time.sleep(0.05)

    print("Servo loop exited")


def start_servo_loop():
    global servo_thread, servo_loop_running

    if servo_loop_running:
        return

    servo_loop_running = True
    servo_thread = threading.Thread(target=servo_loop, daemon=True)
    servo_thread.start()
    print("Servo loop started")


def stop_servo_loop():
    global servo_loop_running

    servo_loop_running = False
    print("Servo loop stopping")

# ------------------------------------------------------------
# Start AI gesture camera once
# ------------------------------------------------------------
# show_preview=True:
#   opens a preview on the Pi display.
#
# show_preview=False:
#   no preview, but detection still works.
# ------------------------------------------------------------
"""
try:
    start_gesture_camera(show_preview=True)
    print("Gesture camera started")
except Exception as e:
    print("Could not start gesture camera:", e)
"""

def send_to_motor(m1, m2):
    """
    Sends speed and direction to the motor controller over I2C.
    """

    m1 = max(-240, min(240, int(m1)))
    m2 = max(-240, min(240, int(m2)))

    m1_speed = abs(m1)
    m1_sign = 0 if m1 >= 0 else 1

    m2_speed = abs(m2)
    m2_sign = 0 if m2 >= 0 else 1

    data = [m1_speed, m1_sign, m2_speed, m2_sign]
    bus.write_i2c_block_data(MOTOR_ADDRESS, 0x00, data)


def go_forward():
    send_to_motor(motor_speed, -motor_speed*0.95)


def go_forward_slow():
    send_to_motor(motor_speed * 0.6, -motor_speed * 0.6*0.95)


def go_backwards_slow():
    send_to_motor(-motor_speed * 0.6, motor_speed * 0.6*0.95)


def go_right():
    send_to_motor(motor_speed, motor_speed)


def go_right_smooth():
    send_to_motor(motor_speed * 0.7, -motor_speed * 0.2)


def go_left():
    send_to_motor(-motor_speed, -motor_speed)


def go_left_smooth():
    send_to_motor(motor_speed * 0.2, -motor_speed * 0.7)

def go_right_very_smooth():
    send_to_motor(motor_speed * 0.45, -motor_speed * 0.10)


def go_left_very_smooth():
    send_to_motor(motor_speed * 0.10, -motor_speed * 0.45)


def stop():
    send_to_motor(0, 0)

def drive_smooth(forward, turn):
    """
    Smooth driving helper.

    forward:
        0.0 = stop
        1.0 = full forward

    turn:
        -1.0 = turn left
         0.0 = straight
         1.0 = turn right
    """

    forward = max(-1.0, min(1.0, forward))
    turn = max(-1.0, min(1.0, turn))

    # Tune these numbers.
    forward_power = motor_speed * forward
    turn_power = motor_speed * turn

    m1 = forward_power + turn_power
    m2 = -forward_power + turn_power

    send_to_motor(m1, m2)


def safe_audio(sound_function):
    """
    Runs an audio function without crashing the robot if audio fails.
    """

    try:
        sound_function()
    except Exception as e:
        print("Audio error:", e)

def follow_person_step():
    """
    Smooth person-follow mode.

    AI camera:
        tells us how far left/right the person is.

    SRF02:
        tells us distance so we do not crash.
    """

    person_offset = get_person_center_offset()

    with i2c_lock:
        command, dist_L, dist_R = srf02.get_front_status()

    closest_distance = min(dist_L, dist_R)

    # -----------------------------
    # Distance settings
    # -----------------------------
    settings = dashboard.get_follow_settings()
    TOO_CLOSE_CM = settings["too_close_cm"]

    # Robot tries to stay around this distance.
    TARGET_DISTANCE_CM = settings["target_distance_cm"]

    # If farther than this, move forward.
    MOVE_FORWARD_CM = settings["move_forward_cm"]

    # -----------------------------
    # Steering settings
    # -----------------------------
    DEADZONE = 0.15

    # Lower = turns less.
    TURN_GAIN = settings["turn_gain"]

    # Lower = drives slower.
    FORWARD_SPEED = settings["follow_speed"]

    # -----------------------------
    # Safety
    # -----------------------------

    if person_offset is None:
        print("FOLLOW: no person")
        stop()
        return

    if closest_distance < TOO_CLOSE_CM:
        print("FOLLOW: too close")
        stop()
        return

    # -----------------------------
    # Smooth steering
    # -----------------------------

    if abs(person_offset) < DEADZONE:
        turn = 0.0
    else:
        turn = person_offset * TURN_GAIN

    # -----------------------------
    # Forward movement
    # -----------------------------

    if closest_distance > MOVE_FORWARD_CM:
        forward = FORWARD_SPEED
    elif closest_distance > TARGET_DISTANCE_CM:
        forward = FORWARD_SPEED * 0.5
    else:
        forward = 0.0

    print(
        f"FOLLOW: offset={person_offset:.2f} "
        f"turn={turn:.2f} "
        f"forward={forward:.2f} "
        f"dist={closest_distance}"
    )

    with i2c_lock:
        drive_smooth(forward, turn)


def autopilot_step():
    """
    One step of autopilot.

    Priority order:

        1. AI gesture command
        2. SRF02 obstacle sensors
        3. Normal driving logic

    Gestures from ai_camera.py:

        "stop"  -> stop
        "left"  -> turn left
        "right" -> turn right
        None    -> use normal SRF02 autopilot
    """

    # --------------------------------------------------------
    # 1. AI gesture control
    # --------------------------------------------------------

    gesture_command = get_gesture_command()
    dashboard.set_status(gesture=gesture_command)

    if gesture_command == "stop":
        print("Gesture STOP")
        stop()
        safe_audio(audio.stop_faaah)
        return

    if gesture_command == "left":
        print("Gesture LEFT")
        safe_audio(audio.stop_faaah)
        go_left_smooth()
        return

    if gesture_command == "right":
        print("Gesture RIGHT")
        safe_audio(audio.stop_faaah)
        go_right_smooth()
        return

    # --------------------------------------------------------
    # 2. SRF02 obstacle sensors
    # --------------------------------------------------------

    with i2c_lock:
        command, dist_L, dist_R = srf02.get_front_status()
        
    dashboard.set_status(dist_L=dist_L, dist_R=dist_R)
    closest_distance = min(dist_L, dist_R)

    # Emergency stop if something is very close.
    if closest_distance < 25:
        print("Emergency obstacle stop")
        stop()
        safe_audio(audio.stop_faaah)
        time.sleep(0.2)
        return

    # --------------------------------------------------------
    # 3. Normal autopilot movement
    # --------------------------------------------------------

    if command == "C":
        print("Clear")

        if closest_distance < 60:
            if not audio.is_playing():
                safe_audio(audio.faaah)

            go_forward_slow()

        else:
            go_forward()
            safe_audio(audio.stop_faaah)

    elif command == "B":
        print("Both blocked")
        safe_audio(audio.stop_faaah)

        go_backwards_slow()
        time.sleep(0.3)

        if dist_L > dist_R:
            print("Turning left")
            go_left()
            safe_audio(audio.left)
        else:
            print("Turning right")
            go_right()
            safe_audio(audio.right)

        time.sleep(0.8)
        stop()

    elif command == "R":
        print("Obstacle right, turning left")
        go_left_smooth()

    elif command == "L":
        print("Obstacle left, turning right")
        go_right_smooth()

    else:
        print("Sensor error")
        stop()
        time.sleep(0.2)


def close():
    """
    Clean shutdown.
    """
    stop_servo_loop()
    stop()

    try:
        stop_gesture_camera()
    except Exception as e:
        print("Could not stop gesture camera:", e)


if __name__ == "__main__":
    try:
        while True:
            autopilot_step()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping robot")

    finally:
        close()
