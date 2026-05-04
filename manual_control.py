import smbus
import time
import sys
import termios
import tty

I2C_ADDRESS = 0x50
bus = smbus.SMBus(1)

SPEED = 70
TURN_SPEED = SPEED * (2 / 3)


def clamp(value, min_value=-255, max_value=255):
    return max(min_value, min(max_value, int(value)))


def motor_to_bytes(value):
    value = clamp(value)
    speed = abs(value)
    sign = 0 if value >= 0 else 1
    return speed, sign


def send_motors(m1, m2, m3, m4):
    """
    Motor values:
      -255 = reverse
         0 = stop
       255 = forward

    Expected robot layout:
      m1 = front left
      m2 = front right
      m3 = rear left
      m4 = rear right
    """

    m1_speed, m1_sign = motor_to_bytes(m1)
    m2_speed, m2_sign = motor_to_bytes(m2)
    m3_speed, m3_sign = motor_to_bytes(m3)
    m4_speed, m4_sign = motor_to_bytes(m4)

    data = [
        m1_speed, m1_sign,
        m2_speed, m2_sign,
        m3_speed, m3_sign,
        m4_speed, m4_sign
    ]

    bus.write_i2c_block_data(I2C_ADDRESS, 0x00, data)
    time.sleep(0.03)


def stop():
    try:
        send_motors(0, 0, 0, 0)
    except Exception as e:
        print("Could not stop motors:", e)


def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return key


print("WASD 4-motor control")
print("--------------------")
print("W = forward")
print("S = backward")
print("A = turn left")
print("D = turn right")
print("X or Space = stop")
print("+ = increase speed")
print("- = decrease speed")
print("Q = quit")
print()
print("Lift the robot wheels before testing.")
print(f"Current speed: {SPEED}")

try:
    while True:
        key = get_key().lower()

        if key == "w":
            # left motors forward, right motors forward
            send_motors(SPEED, -SPEED, SPEED, -SPEED)
            print("Forward")

        elif key == "s":
            send_motors(-SPEED, SPEED, -SPEED, SPEED)
            print("Backward")

        elif key == "a":
            send_motors(-TURN_SPEED, -TURN_SPEED, -TURN_SPEED, -TURN_SPEED)
            print("Left")

        elif key == "d":
            send_motors(TURN_SPEED, TURN_SPEED, TURN_SPEED, TURN_SPEED)
            print("Right")

        elif key == "x" or key == " ":
            stop()
            print("Stop")

        elif key == "+" or key == "=":
            SPEED = min(255, SPEED + 10)
            TURN_SPEED = SPEED * (2 / 3)
            print(f"Speed: {SPEED}")

        elif key == "-" or key == "_":
            SPEED = max(0, SPEED - 10)
            TURN_SPEED = SPEED * (2 / 3)
            print(f"Speed: {SPEED}")

        elif key == "q":
            stop()
            print("Quit")
            break

        else:
            print("Unknown key:", key)

except KeyboardInterrupt:
    print("\nStopping motors.")
    stop()
