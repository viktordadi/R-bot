import board
import neopixel
import time

NUM_LEDS = 60

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_LEDS,
    brightness=0.05,
    auto_write=False,
    pixel_order=neopixel.GRB
)

while True:
    for i in range(NUM_LEDS):
        pixels.fill((0, 0, 0))
        pixels[i] = (255, 0, 0)
        pixels.show()
        time.sleep(0.05)
