import time
from smbus2 import SMBus


i2c_bus = SMBus(1)

sonic_r = 0x71
sonic_l = 0x70


def filter_distance(distance):
    """
    hreinsar fjarlægðargildi frá skynjara.

    distance:
        Hrá fjarlægð frá SRF02 skynjara í cm.

    Returns:
        9999 = mjög langt í burtu eða ekkert marktækt sést
        None = ógilt gildi / of nálægt / villa
        distance = gilt fjarlægðargildi
    """

    # Ef skynjarinn skilar 0, þá er það líklega ekki raunveruleg fjarlægð.
    # Við setjum það sem 9999 svo róbotinn túlki það sem "ekkert nálægt".
    if distance == 0:
        return 9999

    # Ef fjarlægðin er undir 10 cm, teljum við gildið óáreiðanlegt.
    # SRF02 getur verið ónákvæmur mjög nálægt hlutum.
    if distance < 10:
        return None

    # Ef fjarlægðin er yfir 600 cm, þá er hún líklega fyrir utan nothæft svið.
    # Við setjum það sem 9999, sem þýðir "langt í burtu".
    if distance > 600:
        return 9999

    # Annars er fjarlægðin talin gild.
    return distance


def scan_one(address):
    """
    Les einn SRF02 fjarlægðarskynjara.

    Returns:
        Fjarlægð í cm, 9999 eða None.
    """

    try:
        i2c_bus.write_byte_data(address, 0, 0x51)

        # Bíða eftir að skynjarinn klári mælinguna.
        time.sleep(0.075)

        high = i2c_bus.read_byte_data(address, 2)

        low = i2c_bus.read_byte_data(address, 3)

        # Sameina high og low í eina tölu.
        distance = high * 256 + low

        # Sía fjarlægðina áður en henni er skilað.
        return filter_distance(distance)

    except OSError as e:
        # Ef I2C samskipti við skynjarann klikka, prenta villu.
        print(f"I2C error on sensor 0x{address:02X}: {e}")

        # Skila None svo aðrir hlutar forritsins viti að villa kom upp.
        return None


def scan_both():
    """
    Les bæði hægri og vinstri SRF02 skynjara.

    Returns:
        r_dis:
            Fjarlægð frá hægri skynjara.

        l_dis:
            Fjarlægð frá vinstri skynjara.
    """

    # Lesa hægri skynjara fyrst.
    r_dis = scan_one(sonic_r)

    # Lítil bið milli skynjara svo mælingar trufli ekki hvor aðra.
    time.sleep(0.05)

    # Lesa vinstri skynjara.
    l_dis = scan_one(sonic_l)

    # Skila fjarlægð frá hægri og vinstri skynjara.
    return r_dis, l_dis


def get_front_status(limit=40):
    """
    Athugar stöðuna fyrir framan róbotinn.

    limit:
        Fjarlægðarmörk í cm.
        Ef skynjari sér eitthvað nær en þetta, telst það sem hindrun.

    Returns:
        command, dist_L, dist_R

        command:
            "C" = Clear / ekkert fyrir framan
            "B" = Both / hindrun hjá báðum skynjurum
            "R" = Right / hindrun hægra megin
            "L" = Left / hindrun vinstra megin
            "E" = Error / skynjaravilla

        dist_L:
            Fjarlægð vinstra megin.

        dist_R:
            Fjarlægð hægra megin.
    """

    # Lesa báða skynjara.
    r_dis, l_dis = scan_both()

    # Ef annar skynjarinn skilar None, þá er skynjaravilla.
    if r_dis is None or l_dis is None:
        return "E", 9999, 9999

    # Ef báðir skynjarar sjá hindrun innan marka.
    if r_dis <= limit and l_dis <= limit:
        return "B", l_dis, r_dis

    # Ef hægri skynjari sér hindrun.
    elif r_dis <= limit:
        return "R", l_dis, r_dis

    # Ef vinstri skynjari sér hindrun.
    elif l_dis <= limit:
        return "L", l_dis, r_dis

    # Annars er leiðin laus.
    else:
        return "C", l_dis, r_dis
