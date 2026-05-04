import smbus
import time

bus = smbus.SMBus(1)
I2C_ADDRESS = 0x50

def send(data):
    print("Sending:", data)
    bus.write_i2c_block_data(I2C_ADDRESS, 0x00, data)

# Old 2-motor format
send([100, 0, 100, 0])
time.sleep(1)

send([0, 0, 0, 0])
