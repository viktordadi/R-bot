import time
from smbus2 import SMBus

i2c_bus = SMBus(1)

sonic_r = 0x70
sonic_l = 0x71



def filter_distance(distance):
    '''Filterar augljóslega vitlaus gildi frá SRF02'''

    if distance == 0:
        return 9999


    if distance > 600:
        return 9999

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


def get_front_status(limit=40):
    '''
    B = báðir blokkeraðir
    R = hægri blokkeraður
    L = vinstri blokkeraður
    C = clear
    E = error
    '''

    r_dis, l_dis = scan_both()


    if r_dis is None or l_dis is None:
        return "E"

    if r_dis <= limit and l_dis <= limit:
        return 'B', l_dis, r_dis
    elif r_dis <= limit:
        return "R", l_dis, r_dis
    elif l_dis <= limit:
        return "L", l_dis, r_dis
    else:
        return "C", l_dis, r_dis


# Test loop
while True:
    status = get_front_status()
    print("Status:", status)
    time.sleep(0.05)
