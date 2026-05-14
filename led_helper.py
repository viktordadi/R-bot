import sys
import time
import board
import neopixel

NUM_LEDS = 11


# Búa til NeoPixel hlut.
pixels = neopixel.NeoPixel(
    board.D18,
    NUM_LEDS,
    brightness=0.15,
    auto_write=False,
    pixel_order=neopixel.GRB,
)


def off():
    """
    Slekkur á öllum LED ljósum.
    """

    # Setja öll LED ljós í svart.
    pixels.fill((0, 0, 0))

    # Senda breytinguna út á LED röðina.
    pixels.show()


def color(r, g, b, brightness):
    """
    Setur öll LED ljós í sama lit.

    r:
        Rauður litur, 0-255.

    g:
        Grænn litur, 0-255.

    b:
        Blár litur, 0-255.

    brightness:
        Birtustig, t.d. 0.05 til 1.0.
    """

    # Stilla birtustig.
    pixels.brightness = brightness

    # Setja öll LED í valinn lit.
    pixels.fill((int(r), int(g), int(b)))

    # Senda litinn út á LED röðina.
    pixels.show()


def wheel(pos):
    """
    Býr til rainbow lit út frá tölu frá 0 til 255.

    pos:
        Tala sem segir hvar í litahringnum við erum.

    Returns:
        RGB litur sem tuple, t.d. (255, 0, 0).
    """

    # Passa að pos sé alltaf á bilinu 0-255.
    pos = int(pos) % 256

    # Fyrsti hluti litahringsins.
    # Fer frá rauðum yfir í grænan.
    if pos < 85:
        return 255 - pos * 3, pos * 3, 0

    # Annar hluti litahringsins.
    # Fer frá grænum yfir í bláan.
    if pos < 170:
        pos -= 85
        return 0, 255 - pos * 3, pos * 3

    # Þriðji hluti litahringsins.
    # Fer frá bláum yfir í rauðan.
    pos -= 170
    return pos * 3, 0, 255 - pos * 3


def rainbow(brightness):
    """
    Keyrir rainbow effect einu sinni.

    brightness:
        Birtustig LED ljósa.
    """

    # Stilla birtustig.
    pixels.brightness = brightness

    # Offset færir litina áfram í hverju skrefi.
    for offset in range(0, 256, 5):

        # Fara í gegnum öll LED ljós.
        for i in range(NUM_LEDS):

            # Reikna hvaða rainbow lit hvert LED á að fá.
            color_index = (i * 256 // NUM_LEDS + offset) % 256

            # Setja lit á LED númer i.
            pixels[i] = wheel(color_index)

        # Sýna nýja LED stöðu.
        pixels.show()

        time.sleep(0.02)


def blink(r, g, b, brightness):
    """
    Blink effect sem keyrir endalaust.
    """

    # Stilla birtustig.
    pixels.brightness = brightness

    # Breyta litagildum í heiltölur.
    r = int(r)
    g = int(g)
    b = int(b)

    # Endalaus lykkja svo blink effect stoppi ekki sjálfur.
    while True:

        for head in range(NUM_LEDS):

            # Fara í gegnum öll LED ljós.
            for i in range(NUM_LEDS):

                # Reikna fjarlægð frá "hausnum".
                distance = abs(i - head)

                # Gera LED ljósin daufari eftir því sem þau eru lengra frá hausnum.
                # Ef distance er 0 er fade 1.0.
                # Ef distance er 4 eða meira verður fade 0.0.
                fade = max(0.0, 1.0 - distance / 4.0)

                # Setja lit á LED með fade áhrifum.
                pixels[i] = (
                    int(r * fade),
                    int(g * fade),
                    int(b * fade),
                )

            # Senda nýja LED stöðu út á ljósin.
            pixels.show()

            # Stjórnar hraðanum á wave effectinum.
            time.sleep(0.06)



if __name__ == "__main__":

    # Fyrsta command line argument segir hvaða LED mode á að keyra.
    mode = sys.argv[1]

    # Slökkva á LED ljósum.
    if mode == "off":
        off()

    # Setja fastan lit.
    elif mode == "color":
        r = int(sys.argv[2])
        g = int(sys.argv[3])
        b = int(sys.argv[4])
        brightness = float(sys.argv[5])
        color(r, g, b, brightness)

    # Keyra rainbow effect.
    elif mode == "rainbow":
        brightness = float(sys.argv[2])
        rainbow(brightness)

    # Keyra blink/wave effect.
    elif mode == "blink":
        r = int(sys.argv[2])
        g = int(sys.argv[3])
        b = int(sys.argv[4])
        brightness = float(sys.argv[5])
        blink(r, g, b, brightness)
