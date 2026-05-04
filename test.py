import smbus
import time

I2C_ADDRESS = 0x50
bus = smbus.SMBus(1)

def send_motors(left, right):
    left = max(-255, min(255, int(left)))
    right = max(-255, min(255, int(right)))

    left_speed = abs(left)
    left_sign = 0 if left >= 0 else 1

    right_speed = abs(right)
    right_sign = 0 if right >= 0 else 1

    data = [left_speed, left_sign, right_speed, right_sign]
    print(data)
    bus.write_i2c_block_data(I2C_ADDRESS, 0x00, data)

print("Forward")
send_motors(100, -100)
time.sleep(2)

print("Backward")
send_motors(-100, 100)
time.sleep(2)

print("Stop")
send_motors(0, 0)
