import time
from smbus2 import SMBus

i2c_bus = SMBus(1)

sonic_r = 0x70
sonic_l = 0x71

# SRF02 með skipuninni 0x51 skilar fjarlægð í cm


def filter_distance(distance):
    '''Filterar augljóslega vitlaus gildi frá SRF02'''

    # 0 þýðir oft að ekkert fannst / out of range
    # Þá látum við það teljast sem mjög langt í burtu
    if distance == 0:
        return 9999

    # SRF02 mælir ekki áreiðanlega mjög nálægt
    # 4 cm er t.d. líklega glitch/cross-talk
    if distance < 15:
        return None

    # Of stór gildi eru líka óraunhæf fyrir SRF02
    if distance > 600:
        return None

    return distance


def scan_both():
    '''Skannar báða skynjara og skilar fjarlægð í cm'''

    # Byrjar mælingu hjá báðum skynjurum
    i2c_bus.write_byte_data(sonic_r, 0, 0x51)
    i2c_bus.write_byte_data(sonic_l, 0, 0x51)

    # Bíður eftir að mæling klárist
    time.sleep(0.12)

    # Les hægri skynjara
    high_r = i2c_bus.read_byte_data(sonic_r, 2)
    low_r = i2c_bus.read_byte_data(sonic_r, 3)

    # Les vinstri skynjara
    high_l = i2c_bus.read_byte_data(sonic_l, 2)
    low_l = i2c_bus.read_byte_data(sonic_l, 3)

    # Setur saman high og low byte
    r_dis = high_r * 256 + low_r
    l_dis = high_l * 256 + low_l

    # Filterar mælingarnar
    r_dis = filter_distance(r_dis)
    l_dis = filter_distance(l_dis)

    return r_dis, l_dis


def get_front_status(limit=25):
    '''
    Skannar og skilar stöðu:
    B = báðir skynjarar blockaðir
    R = hægri skynjari blockaður
    L = vinstri skynjari blockaður
    C = clear, ekkert blockað
    E = error / ótraust mæling
    '''

    r_dis, l_dis = scan_both()

    print("R:", r_dis, "cm | L:", l_dis, "cm")

    # Ef annar skynjarinn skilar None, þá er mælingin ótraust
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
