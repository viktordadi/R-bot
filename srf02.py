import time
from smbus2 import SMBus

i2c_bus = SMBus(1)
i2c_address = 0x70

while 1:
    i2c_bus.write_byte_data(i2c_address, 0, 0x51)  # Tell sensor to scan in mm

    high = i2c_bus.read_byte_data(i2c_address, 2)  # Read the high byte of the value
    #print(high) # print the value of High byte

    low = i2c_bus.read_byte_data(i2c_address, 3)  # Read the low byte of the value
    #print(low) # print the value of low byte

    current_value = high * 256 + low 

    print(current_value)

    time.sleep(0.1)  # Sleep for some
