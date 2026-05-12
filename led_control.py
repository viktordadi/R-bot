import time
import threading

import board
import neopixel


NUM_LEDS = 11
PIN = board.D18

pixels = neopixel.NeoPixel(
    PIN,
    NUM_LEDS,
    brightness=0.15,
    auto_write=False,
    pixel_order=neopixel.GRB,
)

led_thread = None
led_running = False
led_lock = threading.Lock()

current_brightness = 0.15


def stop_effect():
    global led_running, led_thread

    led_running = False

    if led_thread is not None:
        led_thread.join(timeout=1.0)
        led_thread = None


def set_brightness(value):
    global current_brightness

    value = float(value)
    value = max(0.0, min(1.0, value))

    current_brightness = value

    with led_lock:
        pixels.brightness = value
        pixels.show()


def set_color(r, g, b):
    stop_effect()

    with led_lock:
        pixels.fill((int(r), int(g), int(b)))
        pixels.show()


def off():
    stop_effect()

    with led_lock:
        pixels.fill((0, 0, 0))
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


def rainbow_loop():
    global led_running

    offset = 0

    while led_running:
        with led_lock:
            for i in range(NUM_LEDS):
                color_index = (i * 256 // NUM_LEDS + offset) % 256
                pixels[i] = wheel(color_index)

            pixels.show()

        offset = (offset + 5) % 256
        time.sleep(0.05)


def rainbow():
    global led_thread, led_running

    stop_effect()

    led_running = True
    led_thread = threading.Thread(target=rainbow_loop, daemon=True)
    led_thread.start()


def blink_loop(r, g, b):
    global led_running

    while led_running:
        with led_lock:
            pixels.fill((int(r), int(g), int(b)))
            pixels.show()

        time.sleep(0.35)

        with led_lock:
            pixels.fill((0, 0, 0))
            pixels.show()

        time.sleep(0.35)


def blink(r=255, g=0, b=0):
    global led_thread, led_running

    stop_effect()

    led_running = True
    led_thread = threading.Thread(target=blink_loop, args=(r, g, b), daemon=True)
    led_thread.start()
