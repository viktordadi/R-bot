import time
import pygame

# Speed/control settings
DEADZONE = 0.08
TRIGGER_DEADZONE = 0.08

# Mapping á tökkunum
LEFT_STICK_X_AXIS = 0
L2_AXIS = 2
R2_AXIS = 5
CIRCLE_BUTTON = 1

DEBUG_TRIGGERS = False


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def apply_deadzone(value):
# Gert þannig hann hreyfist ekki ef joystickin eru búin að hreyfast smá
    if abs(value) < DEADZONE:
        return 0.0
    return value


def trigger_to_0_1(value, idle_value=-1.0):
    """
    Breytir hvað þú færð úr R2 og L2 í 0.0 - 1.0.
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
    Setur upp pygame og PS5 fjarstýringuna.

    Returns:
        controller, l2_idle, r2_idle
    """
    pygame.init()
    pygame.joystick.init()
    # Athuga hvort einhver fjarstýring sé tengd.
    # Ef engin fjarstýring finnst, þá stoppar forritið með villu.
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

    time.sleep(0.5)
    # Lesa pygame events nokkrum sinnum til að uppfæra stöðu fjarstýringarinnar.
    # Þetta hjálpar til við að fá rétt og stöðug gildi áður en calibration er gerð
    for _ in range(10):
        pygame.event.pump()
        time.sleep(0.02)

    l2_idle = controller.get_axis(L2_AXIS)
    r2_idle = controller.get_axis(R2_AXIS)

    print(f"Trigger idle calibration: L2={l2_idle:.2f}, R2={r2_idle:.2f}")

    return controller, l2_idle, r2_idle


def read_controller(controller, l2_idle, r2_idle):
   """
    Les PS5 fjarstýringuna einu sinni.

    Returns:
        throttle, steering, quit_pressed

    throttle:
        +1.0 = full áfram
         0.0 = stoppa
        -1.0 = full afturábak

    steering:
        -1.0 = beygja til vinstri
         0.0 = keyra beint
        +1.0 = beygja til hægri

    quit_pressed:
        True ef ýtt var á Circle takkann.
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
