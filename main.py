
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
import manual_control
import autopilot



# PS5 button mappings in pygame
CROSS_BUTTON = 0       # X = manual / handstýring
CIRCLE_BUTTON = 1      # Circle = stoppa og hætta
TRIANGLE_BUTTON = 2    # Triangle = autopilot

# Settings
LOOP_DELAY = 0.05

MODE_STOPPED = "stopped"
MODE_MANUAL = "manual"
MODE_AUTOPILOT = "autopilot"


def print_controls():
    print("--- Robot main control ---")
    print("X / Cross    = manual / handstýring")
    print("Triangle     = autopilot")
    print("Circle       = stoppa og hætta")
    print("R2 / L2      = áfram / afturábak í manual")
    print("Left stick   = beygja í manual")
    print("--------------------------")

def button_pressed(button):
    for event in pygame.event.get():
        if event.type == pygame.JOYBUTTONDOWN and event.button == button:
            return True
    return False

def close():
    manual_control.close()

def get_pressed_buttons():
    buttons = set()
    for event in pygame.event.get():
        if event.type == pygame.JOYBUTTONDOWN:
            buttons.add(event.button)
    return buttons

def main():
    mode = MODE_STOPPED
    print_controls()
    autopilot.stop()
    manual_control.stop()

    try:
        while True:
            # Lesum bara mode-takkana hér.
            # Sjálf handstýringin er inni í manual_control.manual_step().
            pressed = get_pressed_buttons()
            manual_pressed = CROSS_BUTTON in pressed      # athugar set
            autopilot_pressed = TRIANGLE_BUTTON in pressed
            stop_pressed = CIRCLE_BUTTON in pressed

            if stop_pressed:
                print("Stop button pressed. Stopping robot.")
                mode = MODE_STOPPED
                autopilot.stop()
                manual_control.stop()
                break

            if manual_pressed and mode != MODE_MANUAL:
                mode = MODE_MANUAL
                autopilot.stop()
                manual_control.stop()
                print("Mode: manual / handstýring")

            elif autopilot_pressed and mode != MODE_AUTOPILOT:
                mode = MODE_AUTOPILOT
                autopilot.stop()
                manual_control.stop()
                print("Mode: autopilot")

            if mode == MODE_MANUAL:
                keep_running = manual_control.manual_step()
                if keep_running is False:
                    print("Manual control requested stop.")
                    mode = MODE_STOPPED
                    break

            elif mode == MODE_AUTOPILOT:
                autopilot.autopilot_step()

            else:
                autopilot.stop()
                manual_control.stop()

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping robot.")

    finally:
        autopilot.stop()
        manual_control.stop()
        manual_control.close()
        pygame.quit()
        print("Robot stopped.")


if __name__ == "__main__":
    main()
