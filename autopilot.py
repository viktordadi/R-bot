import threading
import time

import servo
import srf02
import smbus
import audio

from ai_camera import (
    start_gesture_camera,
    get_gesture_command,
    stop_gesture_camera,
)


i2c_lock = threading.Lock()

bus = smbus.SMBus(1)

MOTOR_ADDRESS = 0x50
motor_speed = 120


def servo_loop():
    while True:
        with i2c_lock:
            servo.scan()
        time.sleep(0.05)


threading.Thread(target=servo_loop, daemon=True).start()


# ------------------------------------------------------------
# Start AI gesture camera once
# ------------------------------------------------------------
# show_preview=True:
#   opens a preview on the Pi display.
#
# show_preview=False:
#   no preview, but detection still works.
#
# If you run from SSH and get display errors, use False.
# ------------------------------------------------------------

try:
    start_gesture_camera(show_preview=True)
    print("Gesture camera started")
except Exception as e:
    print("Could not start gesture camera:", e)


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
    send_to_motor(motor_speed, -motor_speed)


def go_forward_slow():
    send_to_motor(motor_speed * 0.6, -motor_speed * 0.6)


def go_backwards_slow():
    send_to_motor(-motor_speed * 0.6, motor_speed * 0.6)


def go_right():
    send_to_motor(motor_speed, motor_speed)


def go_right_smooth():
    send_to_motor(motor_speed * 0.7, -motor_speed * 0.2)


def go_left():
    send_to_motor(-motor_speed, -motor_speed)


def go_left_smooth():
    send_to_motor(motor_speed * 0.2, -motor_speed * 0.7)


def stop():
    send_to_motor(0, 0)


def safe_audio(sound_function):
    """
    Runs an audio function without crashing the robot if audio fails.
    """

    try:
        sound_function()
    except Exception as e:
        print("Audio error:", e)


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
