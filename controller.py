import time
import threading
import smbus
import pygame
import srf02

# I2C motor controller address
I2C_ADDRESS = 0x50
bus = smbus.SMBus(1)

# Speed settings
MAX_SPEED = 160          # max forward/backward speed, 0-255
TURN_SPEED = 90          # steering strength
DEADZONE = 0.08          # joystick deadzone
TRIGGER_DEADZONE = 0.08  # ignore small trigger noise

# SRF02 front safety settings
FRONT_LIMIT_CM = 40      # if an object is closer than this, forward is blocked
SENSOR_INTERVAL = 0.15   # seconds between SRF02 checks

# Motors and SRF02 sensors share I2C, so guard I2C access.
i2c_lock = threading.Lock()

# Latest SRF02 status, updated by background thread
front_status = "C"       # C=clear, B=both, L=left, R=right, E=error
front_left_cm = 9999
front_right_cm = 9999
front_blocked = False

# PS5 DualSense mappings tested on this controller
LEFT_STICK_X_AXIS = 0
L2_AXIS = 2
R2_AXIS = 5

# Common DualSense button mapping:
# Cross/X = 0
# Circle  = 1
CIRCLE_BUTTON = 1

# Set to True temporarily if R2/L2 still act strange; prints raw trigger values.
DEBUG_TRIGGERS = False


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def apply_deadzone(value):
    if abs(value) < DEADZONE:
        return 0.0
    return value


def trigger_to_0_1(value, idle_value=-1.0):
    """
    Converts trigger axis value to 0.0 - 1.0.

    Different pygame/controller setups report trigger rest position differently:
      rest=-1, pressed=+1
      rest=+1, pressed=-1
      rest=0,  pressed=+1 OR pressed=-1
    """
    if idle_value >= 0.5:
        # Rest is near +1, pressed moves toward -1
        pressed = (idle_value - value) / (idle_value + 1.0)
    elif idle_value <= -0.5:
        # Rest is near -1, pressed moves toward +1
        pressed = (value - idle_value) / (1.0 - idle_value)
    else:
        # Rest is near 0. Some systems move toward +1, others toward -1.
        pressed = abs(value - idle_value)

    pressed = clamp(pressed, 0.0, 1.0)
    if pressed < TRIGGER_DEADZONE:
        return 0.0
    return pressed


def send_motors(m1, m2):
    """
    Sends motor values to the ATmega over I2C.

    m1/m2 range:
      -255 = reverse
         0 = stop
       255 = forward
    """
    m1 = int(clamp(m1, -255, 255))
    m2 = int(clamp(m2, -255, 255))

    m1_speed = abs(m1)
    m1_sign = 0 if m1 >= 0 else 1

    m2_speed = abs(m2)
    m2_sign = 0 if m2 >= 0 else 1

    data = [m1_speed, m1_sign, m2_speed, m2_sign]
    with i2c_lock:
        bus.write_i2c_block_data(I2C_ADDRESS, 0x00, data)


def stop_motors():
    try:
        send_motors(0, 0)
    except Exception as e:
        print("Could not stop motors:", e)


def srf02_loop():
    """
    Reads both SRF02 sensors in the background.

    This is not autopilot. It only sets front_blocked=True when the sensors
    detect something too close. The main controller loop then blocks only
    forward throttle; backward and left/right steering still work.
    """
    global front_status, front_left_cm, front_right_cm, front_blocked

    while True:
        try:
            with i2c_lock:
                status, left_cm, right_cm = srf02.get_front_status(limit=FRONT_LIMIT_CM)

            front_status = status
            front_left_cm = left_cm
            front_right_cm = right_cm
            front_blocked = status in ("B", "L", "R")

        except Exception as e:
            print("SRF02 error:", e)
            front_status = "E"
            front_left_cm = 9999
            front_right_cm = 9999
            front_blocked = False

        time.sleep(SENSOR_INTERVAL)


def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No PS5 controller found.")
        print("Connect your controller with USB or Bluetooth and try again.")
        return

    controller = pygame.joystick.Joystick(0)
    controller.init()

    print("Controller connected:")
    print(controller.get_name())
    print()
    print("Controls:")
    print("  R2 = forward")
    print("  L2 = backward")
    print("  Left joystick = steering")
    print("  Circle = stop and quit")
    print("  SRF02 = blocks only forward when object is too close")
    print()
    print("Lift the robot wheels before testing.")
    time.sleep(1)

    # Let pygame receive the first stable controller state, then calibrate
    # the trigger rest positions. Do not touch L2/R2 while this starts.
    for _ in range(10):
        pygame.event.pump()
        time.sleep(0.02)

    l2_idle = controller.get_axis(L2_AXIS)
    r2_idle = controller.get_axis(R2_AXIS)
    print(f"Trigger idle calibration: L2={l2_idle:.2f}, R2={r2_idle:.2f}")

    threading.Thread(target=srf02_loop, daemon=True).start()

    running = True
    last_trigger_debug = 0
    last_front_message = 0
    last_clear_message = 0

    try:
        while running:
            pygame.event.pump()

            # Read steering
            steering = controller.get_axis(LEFT_STICK_X_AXIS)
            steering = apply_deadzone(steering)

            # Read triggers
            r2_raw = controller.get_axis(R2_AXIS)
            l2_raw = controller.get_axis(L2_AXIS)

            r2 = trigger_to_0_1(r2_raw, r2_idle)
            l2 = trigger_to_0_1(l2_raw, l2_idle)

            if DEBUG_TRIGGERS and time.time() - last_trigger_debug > 0.5:
                print(
                    f"R2 raw={r2_raw:.2f} value={r2:.2f} | "
                    f"L2 raw={l2_raw:.2f} value={l2:.2f}"
                )
                last_trigger_debug = time.time()

            # R2 forward, L2 backward
            throttle = r2 - l2

            # SRF02 safety:
            # If either/both front sensors see something too close, do not
            # allow forward throttle. Backward and turning still work.
            if throttle > 0 and front_blocked:
                throttle = 0.0
                if time.time() - last_front_message > 0.5:
                    print(
                        f"Forward blocked by SRF02: status={front_status}, "
                        f"L={front_left_cm} cm, R={front_right_cm} cm"
                    )
                    last_front_message = time.time()
            elif front_status == "C" and time.time() - last_clear_message > 2.0:
                # Occasional status so you can see the sensors are alive.
                print(f"Front clear: L={front_left_cm} cm, R={front_right_cm} cm")
                last_clear_message = time.time()

            # Your robot motor mapping:
            # forward  = send_motors(+speed, -speed)
            # backward = send_motors(-speed, +speed)
            # right    = send_motors(+turn, +turn)
            # left     = send_motors(-turn, -turn)
            motor1 = throttle * MAX_SPEED + steering * TURN_SPEED
            motor2 = -throttle * MAX_SPEED + steering * TURN_SPEED

            motor1 = clamp(motor1, -255, 255)
            motor2 = clamp(motor2, -255, 255)

            send_motors(motor1, motor2)

            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == CIRCLE_BUTTON:
                        print("Circle pressed. Stopping and quitting.")
                        stop_motors()
                        running = False

            time.sleep(0.04)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt. Stopping.")

    except OSError as e:
        print("I2C error:", e)
        print("Check that i2cdetect -y 1 shows motor 0x50 and SRF02 0x70/0x71.")

    finally:
        stop_motors()
        pygame.quit()
        print("Robot stopped.")


if __name__ == "__main__":
    main()
