import subprocess

# Slóðin að helper skránni sem stjórnar LED ljósunum.
# Hún er keyrð með sudo því NeoPixel þarf oft root réttindi.
HELPER = "/home/viktor/R-bot/led_helper.py"


def run_helper(args):
    """
    Keyrir led_helper.py sem sér process.

    args:
        Listi af skipunum sem eru sendar til led_helper.py.
        Dæmi:
            ["color", "255", "0", "0", "0.15"]
            ["rainbow", "0.15"]
            ["off"]
    """

    try:
        # Ræsa led_helper.py með sudo og senda args með.
        subprocess.Popen(
            ["sudo", "python3", HELPER] + args,

            stdout=subprocess.DEVNULL,

            stderr=subprocess.DEVNULL,
        )

    except Exception as e:
        # Ef eitthvað fer úrskeiðis við að ræsa helperinn,
        # prenta villuna í terminal.
        print("LED helper error:", e)


def set_brightness(value):
    """
    Þetta fall gerir ekkert núna.

    Brightness er sent með hverri LED skipun,
    t.d. í set_color_with_brightness(), rainbow() eða blink().
    """
    pass


def set_color(r, g, b):
    """
    Setur LED ljósin í fastan lit með sjálfgefnu brightness 0.15.

    r = red / rauður
    g = green / grænn
    b = blue / blár
    """

    # Senda color skipun í helperinn.
    run_helper(["color", str(int(r)), str(int(g)), str(int(b)), "0.15"])


def set_color_with_brightness(r, g, b, brightness):
    """
    Setur LED ljósin í fastan lit með sér brightness.

    r:
        Rauður litur, 0-255.

    g:
        Grænn litur, 0-255.

    b:
        Blár litur, 0-255.

    brightness:
        Birtustig, t.d. 0.05 til 1.0.
    """

    # Senda color skipun með lit og brightness.
    run_helper(["color", str(int(r)), str(int(g)), str(int(b)), str(float(brightness))])


def rainbow(brightness=0.15):
    """
    Ræsir rainbow LED effect.

    brightness:
        Birtustig LED ljósa.
    """

    # Senda rainbow skipun í helperinn.
    run_helper(["rainbow", str(float(brightness))])


def blink(r=255, g=0, b=0, brightness=0.15):
    """
    Ræsir blink.

    Sjálfgefið:
        Rauður litur með brightness 0.15.
    """

    # Senda blink skipun með lit og brightness.
    run_helper(["blink", str(int(r)), str(int(g)), str(int(b)), str(float(brightness))])


def off():
    """
    Slekkur á LED ljósunum.
    """

    # Senda off skipun í helperinn.
    run_helper(["off"])
