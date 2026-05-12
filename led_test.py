import board
import neopixel
import time

NUM_LEDS = 60  # change this to your real LED count

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_LEDS,
    brightness=0.2,
    auto_write=False,
    pixel_order=neopixel.GRB
)

pixels.fill((255, 0, 0))
pixels.show()
time.sleep(2)

pixels.fill((0, 255, 0))
pixels.show()
time.sleep(2)

pixels.fill((0, 0, 255))
pixels.show()
time.sleep(2)

pixels.fill((0, 0, 0))
pixels.show()
