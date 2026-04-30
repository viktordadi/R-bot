import time
from smbus2 import SMBus

i2c_bus = SMBus(1)
sonic_r = 0x70
sonic_l = 0x71

def scan_both():
    i2c_bus.write_byte_data(sonic_r, 0, 0x51)
    i2c_bus.write_byte_data(sonic_l, 0, 0x51)

    time.sleep(0.07)

    high_r = i2c_bus.read_byte_data(sonic_r, 2)
    low_r  = i2c_bus.read_byte_data(sonic_r, 3)

    high_l = i2c_bus.read_byte_data(sonic_l, 2)
    low_l  = i2c_bus.read_byte_data(sonic_l, 3)

    r = high_r * 256 + low_r
    l = high_l * 256 + low_l

    return r, l

def get_front_status(limit=250):
    '''Skannar og prentar fjarðlægð frá skynjurum og hlut. Skilar B ef að báðir eru blockaðir, R ef að hægri er bara bloockaður, L ef að vinstri er bara blockaður eða C ef að enginn err blockaður. Limit er sjálfkrafa á 250mm en hægt er að breyta'''
    r_dis, l_dis = scan_both() # Scannar með báðum og gefur fjarðlægð til baka

    print("R:", r_dis, "L:", l_dis) # Prentar fjarlægð beggja skynjara (má taka úr)

    if r_dis <= limit and l_dis <= limit:
        return "B" # Skilar B ef að báðir eru blockaðir
    elif r_dis <= limit:
        return "R" # Skilar R ef að bara hægri er blockaður
    elif l_dis <= limit:
        return "L" # Skilar L ef að bara vinstri er blockaður
    else:
        return "C" # Ef að ekkert er fyrir skilar hann C sem að gott er að skilgriena sem True fyrir While lykkju

# Test
while True:
    bilun = get_front_status()
    print(bilun)
