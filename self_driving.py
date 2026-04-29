import smbus
import time

bus = smbus.SMBus(1)

# I2C addresses
MOTOR_ADDRESS = 0x50

LEFT_SENSOR = 0x71
RIGHT_SENSOR = 0x70  

# SRF02 registers
COMMAND_REG = 0x00
RANGE_HIGH_BYTE = 0x02
RANGE_LOW_BYTE = 0x03

# SRF02 command: measure in centimeters
MEASURE_CM = 0x51

# Driving settings
SPEED = 70
TURN_SPEED = int(SPEED * 2 / 3)

# Distance settings in cm
STOP_DISTANCE = 25       # stop/avoid if object is closer than this
CLEAR_DISTANCE = 35      # continue when space is clearer than this
BACKUP_TIME = 0.35
TURN_TIME = 0.45


def send_motors(m1, m2):
    """
    Sends motor values to ATmega motor controller.
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
    bus.write_i2c_block_data(MOTOR_ADDRESS, 0x00, data)
    time.sleep(0.03)


def stop():
    try:
        send_motors(0, 0)
    except Exception as e:
        print("Could not stop motors:", e)


def forward():
    send_motors(SPEED, -SPEED)


def backward():
    send_motors(-SPEED, SPEED)


def turn_left():
    send_motors(-TURN_SPEED, -TURN_SPEED)


def turn_right():
    send_motors(TURN_SPEED, TURN_SPEED)


def read_srf02_cm(address):
    """
    Reads distance from SRF02 ultrasonic sensor in centimeters.
    Returns distance in cm, or None if read fails.
    """
    try:
        bus.write_byte_data(address, COMMAND_REG, MEASURE_CM)
        time.sleep(0.075)

        high = bus.read_byte_data(address, RANGE_HIGH_BYTE)
        low = bus.read_byte_data(address, RANGE_LOW_BYTE)

        distance = (high << 8) + low
        return distance

    except OSError as e:
        print(f"Sensor error at 0x{address:02X}:", e)
        return None


def read_both_sensors():
    left = read_srf02_cm(LEFT_SENSOR)
    time.sleep(0.02)

    right = read_srf02_cm(RIGHT_SENSOR)
    time.sleep(0.02)

    return left, right


print("Autonomous SRF02 driving")
print("------------------------")
print("Raising wheels first is recommended.")
print("Press Ctrl+C to stop.")
print()
print(f"Motor controller: 0x{MOTOR_ADDRESS:02X}")
print(f"Left sensor:      0x{LEFT_SENSOR:02X}")
print(f"Right sensor:     0x{RIGHT_SENSOR:02X}")
print()

time.sleep(2)

try:
    while True:
        left_dist, right_dist = read_both_sensors()

        print(f"Left: {left_dist} cm | Right: {right_dist} cm")

        # If one sensor failed, stop for safety
        if left_dist is None or right_dist is None:
            print("Sensor read failed. Stopping.")
            stop()
            time.sleep(0.5)
            continue

        # Object detected close on either side
        if left_dist < STOP_DISTANCE or right_dist < STOP_DISTANCE:
            print("Object detected. Stopping.")
            stop()
            time.sleep(0.2)

            print("Backing up.")
            backward()
            time.sleep(BACKUP_TIME)

            stop()
            time.sleep(0.2)

            # Turn away from closer object
            if left_dist < right_dist:
                print("Object closer on left. Turning right.")
                turn_right()
            elif right_dist < left_dist:
                print("Object closer on right. Turning left.")
                turn_left()
            else:
                print("Object centered. Turning right.")
                turn_right()

            time.sleep(TURN_TIME)
            stop()
            time.sleep(0.2)

        else:
            print("Clear. Driving forward.")
            forward()

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopping robot.")

finally:
    stop()
