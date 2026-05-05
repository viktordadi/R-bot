"""
Takkar:
  X / Cross      = manual / handstýring
  Triangle       = autopilot
  Circle         = stoppa og hætta

Handstýring:
  R2             = áfram
  L2             = afturábak
  Vinstri pinni  = beygja vinstri/hægri
"""

import importlib.util
import os
import time

import pygame

import autopilot


# --- PS5 button mappings in pygame ---
CROSS_BUTTON = 0      # X takkinn: manual
CIRCLE_BUTTON = 1     # Circle: stop / quit
TRIANGLE_BUTTON = 3   # Triangle: autopilot

# --- Settings ---
LOOP_DELAY = 0.05
MAX_SPEED = autopilot.motor_speed
MAX_TURN = autopilot.motor_speed

MODE_STOPPED = "stopped"
MODE_MANUAL = "manual"
MODE_AUTOPILOT = "autopilot"


# This loader also works if you later rename it to "controller.py".
def load_controller_module():
    here = os.path.dirname(os.path.abspath(__file__))

    for filename in "controller.py":
        path = os.path.join(here, filename)
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("controller_module", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

    raise FileNotFoundError("Could not find controller.py or controller (8).py")


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def send_motors(m1, m2):
    """Small wrapper so the rest of main.py matches your comments."""
    autopilot.send_to_motor(m1, m2)


def manual_drive(throttle, steering):
    """
    Mixes throttle and steering into the motor mapping you wrote:
      forward  = (+speed, -speed)
      backward = (-speed, +speed)
      right    = (+turn, +turn)
      left     = (-turn, -turn)
    """
    speed = throttle * MAX_SPEED
    turn = steering * MAX_TURN

    m1 = speed + turn
    m2 = -speed + turn

    m1 = clamp(m1, -MAX_SPEED, MAX_SPEED)
    m2 = clamp(m2, -MAX_SPEED, MAX_SPEED)

    send_motors(m1, m2)


def print_controls():
    print("\n--- Robot main control ---")
    print("X / Cross    = manual / handstýring")
    print("Triangle     = autopilot")
    print("Circle       = stoppa og hætta")
    print("R2 / L2      = áfram / afturábak í manual")
    print("Left stick   = beygja í manual")
    print("--------------------------\n")


def main():
    controller_module = load_controller_module()
    controller, l2_idle, r2_idle = controller_module.setup_controller()

    mode = MODE_STOPPED
    print_controls()
    autopilot.stop()

    try:
        while True:
            throttle, steering, quit_pressed = controller_module.read_controller(
                controller, l2_idle, r2_idle
            )

            # Extra button checks for mode select.
            # read_controller() already calls pygame.event.pump(), so get_button() is up to date.
            manual_pressed = controller.get_button(CROSS_BUTTON)
            autopilot_pressed = controller.get_button(TRIANGLE_BUTTON)
            stop_pressed = controller.get_button(CIRCLE_BUTTON) or quit_pressed

            if stop_pressed:
                print("Stop button pressed. Stopping robot.")
                mode = MODE_STOPPED
                autopilot.stop()
                break

            if manual_pressed and mode != MODE_MANUAL:
                mode = MODE_MANUAL
                autopilot.stop()
                print("Mode: manual / handstýring")

            elif autopilot_pressed and mode != MODE_AUTOPILOT:
                mode = MODE_AUTOPILOT
                autopilot.stop()
                print("Mode: autopilot")

            if mode == MODE_MANUAL:
                manual_drive(throttle, steering)

            elif mode == MODE_AUTOPILOT:
                autopilot.autopilot_step()

            else:
                autopilot.stop()

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt. Stopping robot.")

    finally:
        autopilot.stop()
        controller_module.close_controller()
        pygame.quit()
        print("Robot stopped.")


if __name__ == "__main__":
    main()
