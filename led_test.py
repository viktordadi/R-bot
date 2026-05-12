import board
import neopixel
import time

NUM_LEDS = 26

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_LEDS,
    brightness=0.3,
    auto_write=True,
    pixel_order=neopixel.GRB
)

pixels.fill((255, 0, 0))
time.sleep(1)

pixels.fill((0, 255, 0))
time.sleep(1)

pixels.fill((0, 0, 255))
time.sleep(1)

pixels.fill((0, 0, 0))
