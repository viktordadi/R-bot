import smbus
import time
import sys
import termios
import tty

I2C_ADDRESS = 0x50
bus = smbus.SMBus(1)

SPEED = 50



def send_motors(m1, m2):
    """
    m1/m2 range:
      -255 = reverse
         0 = stop
       255 = forward
    """
    m1 = max(-255, min(255, int(m1)))
    m2 = max(-255, min(255, int(m2)))

    m1_speed = abs(m1)
    m1_sign = 0 if m1 >= 0 else 1

    m2_speed = abs(m2)
    m2_sign = 0 if m2 >= 0 else 1

    data = [m1_speed, m1_sign, m2_speed, m2_sign]
    bus.write_i2c_block_data(I2C_ADDRESS, 0x00, data)
    time.sleep(0.03)


def stop():
    try:
        send_motors(0, 0)
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


print("WASD motor control")
print("------------------")
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
            send_motors(SPEED, -SPEED)
            print("Forward")

        elif key == "s":
            send_motors(-SPEED, SPEED)
            print("Backward")

        elif key == "a":
            send_motors(SPEED, SPEED)
            print("Left")

        elif key == "d":
            send_motors(-SPEED, -SPEED)
            print("Right")

        elif key == "x" or key == " ":
            stop()
            print("Stop")

        elif key == "+" or key == "=":
            SPEED = min(255, SPEED + 10)
            TURN_SPEED = min(255, TURN_SPEED + 10)
            print(f"Speed: {SPEED}")

        elif key == "-" or key == "_":
            SPEED = max(0, SPEED - 10)
            TURN_SPEED = max(0, TURN_SPEED - 10)
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
