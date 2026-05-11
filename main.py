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
import audio
import pygame
import manual_control
import autopilot
import ai_camera
import camera_stream




# PS5 button mappings in pygame
CROSS_BUTTON = 0       # X = manual / handstýring
CIRCLE_BUTTON = 1      # Circle = stoppa og hætta
TRIANGLE_BUTTON = 2    # Triangle = autopilot
SQUARE_BUTTON = 3      # switch camera mode

# Settings
LOOP_DELAY = 0.05

MODE_STOPPED = "stopped"
MODE_MANUAL = "manual"
MODE_AUTOPILOT = "autopilot"

CAMERA_OFF = "off"
CAMERA_AI = "ai"
CAMERA_STREAM = "stream"

camera_mode = CAMERA_OFF

def stop_all_camera_modes():
    try:
        ai_camera.stop_gesture_camera()
    except Exception as e:
        print("AI camera stop error:", e)

    try:
        camera_stream.stop()
    except Exception as e:
        print("Stream camera stop error:", e)

    time.sleep(1.0)


def switch_camera_mode():
    """
    Cycles camera mode:

        off -> AI camera -> normal browser stream -> off
    """

    global camera_mode

    if camera_mode == CAMERA_OFF:
        print("Switching camera mode: AI camera")
        stop_all_camera_modes()
        ai_camera.start_gesture_camera(show_preview=True)
        camera_mode = CAMERA_AI

    elif camera_mode == CAMERA_AI:
        print("Switching camera mode: normal browser stream")
        stop_all_camera_modes()
        camera_stream.start(open_browser=True)
        camera_mode = CAMERA_STREAM

    else:
        print("Switching camera mode: off")
        stop_all_camera_modes()
        camera_mode = CAMERA_OFF


def print_controls():
    print("--- Robot main control ---")
    print("X / Cross    = manual / handstýring")
    print("Triangle     = autopilot")
    print("Circle       = stoppa og hætta")
    print("Square       = Switch camera mode")
    print("R2 / L2      = áfram / afturábak í manual")
    print("Left stick   = beygja í manual")
    print("--------------------------")


def close():
    manual_control.close()

def get_pressed_buttons():
    buttons = set()
    dpad = (0, 0)
    for event in pygame.event.get():
        if event.type == pygame.JOYBUTTONDOWN:
            buttons.add(event.button)
        if event.type == pygame.JOYHATMOTION:
            dpad = event.value
    return buttons, dpad

def main():
    mode = MODE_STOPPED
    print_controls()
    autopilot.stop()
    manual_control.stop()

    try:
        while True:
            # Lesum bara mode-takkana hér.
            # Sjálf handstýringin er inni í manual_control.manual_step().
            pressed, dpad = get_pressed_buttons()
            manual_pressed = CROSS_BUTTON in pressed      # athugar set
            autopilot_pressed = TRIANGLE_BUTTON in pressed
            stop_pressed = CIRCLE_BUTTON in pressed
            camera_pressed = SQUARE_BUTTON in pressed
            rain_pressed = dpad == (0, 1)
            fireball_pressed = dpad == (0, -1)
            mr_pressed = dpad == (1, 0)
            speech_pressed = dpad == (-1, 0)

            if camera_pressed:
              switch_camera_mode()
            

            if stop_pressed:
                print("Stop button pressed. Stopping robot.")
                autopilot.stop_servo_loop()
                mode = MODE_STOPPED
                autopilot.stop()
                manual_control.stop()
                break

            if rain_pressed:
              audio.rain_over_me()

            if fireball_pressed:
              audio.fireball()

            if mr_pressed:
              audio.mr_worldwide()

            

            if manual_pressed and mode != MODE_MANUAL:
                mode = MODE_MANUAL
                autopilot.stop_servo_loop()
                autopilot.stop()
                manual_control.stop()
                print("Mode: manual / handstýring")

            elif autopilot_pressed and mode != MODE_AUTOPILOT:
              mode = MODE_AUTOPILOT
              autopilot.start_servo_loop()
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
        stop_all_camera_modes()
        autopilot.stop_servo_loop()
        autopilot.stop()
        manual_control.stop()
        manual_control.close()
        pygame.quit()
        print("Robot stopped.")


if __name__ == "__main__":
    main()
