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
# Fastar
MOTOR_ADDRESS = 0x50
motor_speed = 220
search_direction = 1
last_search_switch_time = 0


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
        1.0 = Alveg áfram

    turn:
        -1.0 = Beygja vinstri
         0.0 = Beint
         1.0 = Beygja hægri
    """

    forward = max(-1.0, min(1.0, forward))
    turn = max(-1.0, min(1.0, turn))

    
    forward_power = motor_speed * forward
    turn_power = motor_speed * turn

    m1 = forward_power + turn_power
    m2 = -forward_power + turn_power

    send_to_motor(m1, m2)


def safe_audio(sound_function):
    
    try:
        sound_function()
    except Exception as e:
        print("Audio error:", e)
        

def follow_person_step():
    """
    Eltir manneskju 

    AI camera:
        get_person_center_offset()
        -1.0 = Manneskja lengst vinstri
         0.0 = Manneskja í miðjunni
        +1.0 = Manneskja lengst hægri

    SRF02:
        stopar ef róbotinn er of nálægt
    """
    # Gildið segir hvort manneskjan sé vinstra megin, í miðju eða hægra megin.
    person_offset = get_person_center_offset()

    try:
        with i2c_lock:
            command, dist_L, dist_R = srf02.get_front_status()
    except OSError as e:
        print("FOLLOW: SRF02 I2C error:", e)
        # Uppfæra dashboard svo það sjáist að róbotinn er í follow mode,
        # en skynjarinn gaf villu og róbotinn hefur stoppað.
        dashboard.set_status(
            mode="follow",
            person_position="sensor error",
            follow_action="stopped",
            dist_L="error",
            dist_R="error",
        )
        stop()
        return

    closest_distance = min(dist_L, dist_R)

    # -----------------------------
    # Dashboard slider settings
    # -----------------------------
    settings = dashboard.get_follow_settings()
    TOO_CLOSE_CM = settings["too_close_cm"]
    TARGET_DISTANCE_CM = settings["target_distance_cm"]
    MOVE_FORWARD_CM = settings["move_forward_cm"]
    TURN_GAIN = settings["turn_gain"]
    FORWARD_SPEED = settings["follow_speed"]

    # -----------------------------
    # Steering settings
    # -----------------------------
    DEADZONE = 0.15
    EDGE_LIMIT = 0.65
    EDGE_TURN_GAIN = 0.85


    if person_offset is None:
        print("FOLLOW: no person")
        dashboard.set_status(
            mode="follow",
            person_position="no person",
            follow_action="stopped",
            dist_L=dist_L,
            dist_R=dist_R,
        )
        stop()
        return

    if closest_distance < TOO_CLOSE_CM:
        print("FOLLOW: too close")
        dashboard.set_status(
            mode="follow",
            person_position=f"offset={person_offset:.2f}",
            follow_action="too close - stopped",
            dist_L=dist_L,
            dist_R=dist_R,
        )
        stop()
        return


    if person_offset < -EDGE_LIMIT:
        # Manneskjan er næstum farin úr frame vinstra meginn
        turn = -EDGE_TURN_GAIN
        person_position = "far left"
        follow_action = "recover left"

    elif person_offset > EDGE_LIMIT:
        # Manneskjan er næstum farin úr frame hægra meginn
        turn = EDGE_TURN_GAIN
        person_position = "far right"
        follow_action = "recover right"

    elif abs(person_offset) < DEADZONE:
        turn = 0.0
        person_position = "center"
        follow_action = "centered"

    elif person_offset < 0:
        turn = person_offset * TURN_GAIN
        person_position = "left"
        follow_action = "turn left"

    else:
        turn = person_offset * TURN_GAIN
        person_position = "right"
        follow_action = "turn right"

    # -----------------------------
    # áfram hreyfingar
    # -----------------------------
    if abs(person_offset) > EDGE_LIMIT:
        forward = 0.0

    elif closest_distance > MOVE_FORWARD_CM:
        forward = FORWARD_SPEED
        follow_action = follow_action + " + forward"

    elif closest_distance > TARGET_DISTANCE_CM:
        forward = FORWARD_SPEED * 0.5
        follow_action = follow_action + " + slow forward"

    else:
        forward = 0.0
        follow_action = follow_action + " + hold distance"

    # -----------------------------
    # Dashboard + motor output
    # -----------------------------
    dashboard.set_status(
        mode="follow",
        person_position=f"{person_position} offset={person_offset:.2f}",
        follow_action=follow_action,
        dist_L=dist_L,
        dist_R=dist_R,
    )

    print(
        f"FOLLOW: offset={person_offset:.2f} "
        f"turn={turn:.2f} "
        f"forward={forward:.2f} "
        f"dist={closest_distance} "
        f"action={follow_action}"
    )

    with i2c_lock:
        drive_smooth(forward, turn)


def search_person_step():
    """
    Search mode.

    Snýr hægri og vinstri til að leita af manneskju.

    Returns:
        True  = Manneskja fundinn
        False = Ekkert fundið
    """

    global search_direction, last_search_switch_time

    person_offset = get_person_center_offset()

    # Ef myndavélin sér manneskju hætta að leita
    if person_offset is not None:
        print("SEARCH: person found")
        stop()
        dashboard.set_status(
            mode="search",
            person_position=f"found offset={person_offset:.2f}",
            follow_action="person found",
        )
        return True

    now = time.time()

    # Breyta um stefnu hverjar 2 sec
    if now - last_search_switch_time > 3.0:
        search_direction *= -1
        last_search_switch_time = now

    search_speed = motor_speed * 0.35

    try:
        with i2c_lock:
            if search_direction < 0:
                print("SEARCH: turning left")
                send_to_motor(-search_speed, -search_speed)
                dashboard.set_status(
                    mode="search",
                    person_position="no person",
                    follow_action="searching left",
                )
            else:
                print("SEARCH: turning right")
                send_to_motor(search_speed, search_speed)
                dashboard.set_status(
                    mode="search",
                    person_position="no person",
                    follow_action="searching right",
                )

    except OSError as e:
        print("SEARCH motor I2C error:", e)
        stop()

    return False


def autopilot_step():
    """
    One step of autopilot.

    Priority order:

        1. AI gesture command
        2. SRF02 obstacle sensors
        3. Normal driving logic

    Gestures from ai_camera.py:

        "stop"  -> stop
        "left"  -> Beygja vinstri
        "right" -> Beygja hægti
        None    -> nota venjulegt SRF02 autopilot
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
