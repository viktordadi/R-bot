import time
import pygame

# Speed/control settings
DEADZONE = 0.08
TRIGGER_DEADZONE = 0.08

# PS5 DualSense pygame mappings for your controller
LEFT_STICK_X_AXIS = 0
L2_AXIS = 2
R2_AXIS = 5
CIRCLE_BUTTON = 1

# Set to True while testing trigger problems
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

    Supports different pygame trigger styles:
      rest=-1, pressed=+1
      rest=+1, pressed=-1
      rest=0,  pressed=+1 or -1
    """
    if idle_value >= 0.5:
        pressed = (idle_value - value) / (idle_value + 1.0)
    elif idle_value <= -0.5:
        pressed = (value - idle_value) / (1.0 - idle_value)
    else:
        pressed = abs(value - idle_value)

    pressed = clamp(pressed, 0.0, 1.0)

    if pressed < TRIGGER_DEADZONE:
        return 0.0

    return pressed


def setup_controller():
    """
    Initializes pygame and the PS5 controller.

    Returns:
        controller, l2_idle, r2_idle

    Use these values with read_controller().
    """
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No PS5 controller found. Connect it with USB or Bluetooth.")

    controller = pygame.joystick.Joystick(0)
    controller.init()

    print("Controller connected:")
    print(controller.get_name())
    print()
    print("Controls:")
    print("  R2 = forward")
    print("  L2 = backward")
    print("  Left joystick = steering")
    print("  Circle = quit/stop")
    print()
    print("Do not touch L2/R2 during calibration.")

    # Let pygame receive stable starting values before calibration
    time.sleep(0.5)
    for _ in range(10):
        pygame.event.pump()
        time.sleep(0.02)

    l2_idle = controller.get_axis(L2_AXIS)
    r2_idle = controller.get_axis(R2_AXIS)

    print(f"Trigger idle calibration: L2={l2_idle:.2f}, R2={r2_idle:.2f}")

    return controller, l2_idle, r2_idle


def read_controller(controller, l2_idle, r2_idle):
    """
    Reads the PS5 controller once.

    Returns:
        throttle, steering, quit_pressed

    throttle:
        +1.0 = full forward
         0.0 = stop
        -1.0 = full backward

    steering:
        -1.0 = left
         0.0 = straight
        +1.0 = right

    quit_pressed:
        True if Circle was pressed.
    """
    pygame.event.pump()

    steering = controller.get_axis(LEFT_STICK_X_AXIS)
    steering = apply_deadzone(steering)

    r2_raw = controller.get_axis(R2_AXIS)
    l2_raw = controller.get_axis(L2_AXIS)

    r2 = trigger_to_0_1(r2_raw, r2_idle)
    l2 = trigger_to_0_1(l2_raw, l2_idle)

    throttle = r2 - l2
    throttle = clamp(throttle, -1.0, 1.0)

    quit_pressed = False
    for event in pygame.event.get():
        if event.type == pygame.JOYBUTTONDOWN and event.button == CIRCLE_BUTTON:
            quit_pressed = True

    if DEBUG_TRIGGERS:
        print(
            f"R2 raw={r2_raw:.2f} value={r2:.2f} | "
            f"L2 raw={l2_raw:.2f} value={l2:.2f} | "
            f"throttle={throttle:.2f} steering={steering:.2f}"
        )

    return throttle, steering, quit_pressed


def close_controller():
    pygame.quit()


# Optional test mode:
# python3 controller.py
if __name__ == "__main__":
    controller, l2_idle, r2_idle = setup_controller()

    try:
        while True:
            throttle, steering, quit_pressed = read_controller(controller, l2_idle, r2_idle)
            print(f"throttle={throttle:.2f}, steering={steering:.2f}, quit={quit_pressed}")

            if quit_pressed:
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopping controller test.")

    finally:
        close_controller()
