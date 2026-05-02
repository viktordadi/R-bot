import time
import smbus
import pygame


# I2C motor controller address
I2C_ADDRESS = 0x50
bus = smbus.SMBus(1)

# Speed settings
MAX_SPEED = 160      # max forward/backward speed, 0-255
TURN_SPEED = 90      # steering strength
DEADZONE = 0.08      # joystick deadzone
TRIGGER_DEADZONE = 0.08  # ignore small trigger noise

# PS5 DualSense common mappings in pygame
LEFT_STICK_X_AXIS = 0
L2_AXIS = 2
R2_AXIS = 5

# Common DualSense button mapping:
# Cross/X = 0
# Circle  = 1
CIRCLE_BUTTON = 1

# L2 mapping was tested on this controller and is axis 2.
# L1 is not used.

# Set to True temporarily if R2 still acts strange; prints raw trigger values.
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

    The older version assumed that rest=0 always pressed toward +1.
    On some PS5 mappings R2 can move the other way, which made it look like
    R2 randomly stopped working. This version handles both directions.
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
    bus.write_i2c_block_data(I2C_ADDRESS, 0x00, data)


def stop_motors():
    try:
        send_motors(0, 0)
    except Exception as e:
        print("Could not stop motors:", e)


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

    running = True
    last_trigger_debug = 0

    try:
        while running:
            pygame.event.pump()

            # Read steering
            steering = controller.get_axis(LEFT_STICK_X_AXIS)
            steering = apply_deadzone(steering)

            # Read R2 for forward.
            r2_raw = controller.get_axis(R2_AXIS)
            r2 = trigger_to_0_1(r2_raw, r2_idle)

            # L2 controls backward. L1 is not used.
            l2_raw = controller.get_axis(L2_AXIS)
            backward = trigger_to_0_1(l2_raw, l2_idle)

            if DEBUG_TRIGGERS and time.time() - last_trigger_debug > 0.5:
                print(
                    f"R2 raw={r2_raw:.2f} value={r2:.2f} | "
                    f"L2 raw={l2_raw:.2f} value={backward:.2f}"
                )
                last_trigger_debug = time.time()

            # R2 forward, L2 backward.
            throttle = r2 - backward

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
        print("Check that i2cdetect -y 1 shows 0x50.")

    finally:
        stop_motors()
        pygame.quit()
        print("Robot stopped.")


if __name__ == "__main__":
    main()
