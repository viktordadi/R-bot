import time
from smbus2 import SMBus

i2c_bus = SMBus(1)

sonic_r = 0x70
sonic_l = 0x71

# SRF02 skilar í cm
LIMIT_CM = 25


def filter_distance(distance):
    '''Filterar augljóslega vitlaus gildi frá SRF02'''

    if distance == 0:
        return 9999

    if distance < 15:
        return None

    if distance > 600:
        return None

    return distance


def scan_one(address):
    '''Skannar einn skynjara'''

    i2c_bus.write_byte_data(address, 0, 0x51)
    time.sleep(0.1)

    high = i2c_bus.read_byte_data(address, 2)
    low  = i2c_bus.read_byte_data(address, 3)

    distance = high * 256 + low

    return filter_distance(distance)


def scan_both():
    '''Skannar báða skynjara EKKI á sama tíma (forðast truflun)'''

    # Hægri fyrst
    r_dis = scan_one(sonic_r)

    # Smá delay til að forðast cross-talk
    time.sleep(0.05)

    # Svo vinstri
    l_dis = scan_one(sonic_l)

    return r_dis, l_dis


def get_front_status(limit=LIMIT_CM):
    '''
    B = báðir blokkeraðir
    R = hægri blokkeraður
    L = vinstri blokkeraður
    C = clear
    E = error
    '''

    r_dis, l_dis = scan_both()

    print("R:", r_dis, "cm | L:", l_dis, "cm")

    if r_dis is None or l_dis is None:
        return "E"

    if r_dis <= limit and l_dis <= limit:
        return "B"
    elif r_dis <= limit:
        return "R"
    elif l_dis <= limit:
        return "L"
    else:
        return "C"


# Test loop
while True:
    status = get_front_status()
    print("Status:", status)
    time.sleep(0.1)
