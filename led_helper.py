import sys
import time
import board
import neopixel

NUM_LEDS = 11

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_LEDS,
    brightness=0.15,
    auto_write=False,
    pixel_order=neopixel.GRB,
)


def off():
    pixels.fill((0, 0, 0))
    pixels.show()


def color(r, g, b, brightness):
    pixels.brightness = brightness
    pixels.fill((int(r), int(g), int(b)))
    pixels.show()


def wheel(pos):
    pos = int(pos) % 256

    if pos < 85:
        return 255 - pos * 3, pos * 3, 0

    if pos < 170:
        pos -= 85
        return 0, 255 - pos * 3, pos * 3

    pos -= 170
    return pos * 3, 0, 255 - pos * 3


def rainbow(brightness):
    pixels.brightness = brightness

    for offset in range(0, 256, 5):
        for i in range(NUM_LEDS):
            color_index = (i * 256 // NUM_LEDS + offset) % 256
            pixels[i] = wheel(color_index)

        pixels.show()
        time.sleep(0.03)


def blink(r, g, b, brightness):
    pixels.brightness = brightness

    for _ in range(6):
        pixels.fill((int(r), int(g), int(b)))
        pixels.show()
        time.sleep(0.25)

        pixels.fill((0, 0, 0))
        pixels.show()
        time.sleep(0.25)


if __name__ == "__main__":
    mode = sys.argv[1]

    if mode == "off":
        off()

    elif mode == "color":
        r = int(sys.argv[2])
        g = int(sys.argv[3])
        b = int(sys.argv[4])
        brightness = float(sys.argv[5])
        color(r, g, b, brightness)

    elif mode == "rainbow":
        brightness = float(sys.argv[2])
        rainbow(brightness)

    elif mode == "blink":
        r = int(sys.argv[2])
        g = int(sys.argv[3])
        b = int(sys.argv[4])
        brightness = float(sys.argv[5])
        blink(r, g, b, brightness)
