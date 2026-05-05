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

import time
import pygame

import controller
import autopilot


# PS5 button mappings in pygame
CROSS_BUTTON = 0       # X = manual / handstýring
CIRCLE_BUTTON = 1      # Circle = stoppa og hætta
TRIANGLE_BUTTON = 3    # Triangle = autopilot

# Settings
LOOP_DELAY = 0.05
MAX_SPEED = autopilot.motor_speed
MAX_TURN = autopilot.motor_speed

MODE_STOPPED = "stopped"
MODE_MANUAL = "manual"
MODE_AUTOPILOT = "autopilot"


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def send_motors(m1, m2):
    """Wrapper svo skipanirnar passi við kommentin í verkefninu."""
    autopilot.send_to_motor(m1, m2)


def manual_drive(throttle, steering):
    """
    Breytir throttle + steering í tvo mótora.

    forward  = send_motors(+speed, -speed)
    backward = send_motors(-speed, +speed)
    right    = send_motors(+turn, +turn)
    left     = send_motors(-turn, -turn)
    """
    speed = throttle * MAX_SPEED
    turn = steering * MAX_TURN

    m1 = speed + turn
    m2 = -speed + turn

    m1 = clamp(m1, -MAX_SPEED, MAX_SPEED)
    m2 = clamp(m2, -MAX_SPEED, MAX_SPEED)

    send_motors(m1, m2)


def print_controls():
    print("
--- Robot main control ---")
    print("X / Cross    = manual / handstýring")
    print("Triangle     = autopilot")
    print("Circle       = stoppa og hætta")
    print("R2 / L2      = áfram / afturábak í manual")
    print("Left stick   = beygja í manual")
    print("--------------------------")


def main():
    ps5, l2_idle, r2_idle = controller.setup_controller()

    mode = MODE_STOPPED
    print_controls()
    autopilot.stop()

    try:
        while True:
            throttle, steering, quit_pressed = controller.read_controller(
                ps5, l2_idle, r2_idle
            )

            manual_pressed = ps5.get_button(CROSS_BUTTON)
            autopilot_pressed = ps5.get_button(TRIANGLE_BUTTON)
            stop_pressed = ps5.get_button(CIRCLE_BUTTON) or quit_pressed

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
        print("
KeyboardInterrupt. Stopping robot.")

    finally:
        autopilot.stop()
        controller.close_controller()
        pygame.quit()
        print("Robot stopped.")


if __name__ == "__main__":
    main()
