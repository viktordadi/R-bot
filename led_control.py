import subprocess

HELPER = "/home/viktor/R-bot/led_helper.py"


def run_helper(args):
    try:
        subprocess.Popen(
            ["sudo", "python3", HELPER] + args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print("LED helper error:", e)


def set_brightness(value):
    # Brightness is sent with each effect/color command.
    pass


def set_color(r, g, b):
    run_helper(["color", str(int(r)), str(int(g)), str(int(b)), "0.15"])


def set_color_with_brightness(r, g, b, brightness):
    run_helper(["color", str(int(r)), str(int(g)), str(int(b)), str(float(brightness))])


def rainbow(brightness=0.15):
    run_helper(["rainbow", str(float(brightness))])


def blink(r=255, g=0, b=0, brightness=0.15):
    run_helper(["blink", str(int(r)), str(int(g)), str(int(b)), str(float(brightness))])


def off():
    run_helper(["off"])
