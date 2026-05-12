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
import dashboard




# PS5 button mappings in pygame
R1_BUTTON = 5          # R1 = follow person mode
MENU_BUTTON = 8
L3_BUTTON = 11         # L3 = volume down
R3_BUTTON = 12         # R3 = volume up
L1_BUTTON = 4          # L1 = start/stop live mic receiver
CROSS_BUTTON = 0       # X = manual / handstýring
CIRCLE_BUTTON = 1      # Circle = stoppa og hætta
TRIANGLE_BUTTON = 2    # Triangle = autopilot
SQUARE_BUTTON = 3      # switch camera mode

# Settings
LOOP_DELAY = 0.05

MODE_STOPPED = "stopped"
MODE_MANUAL = "manual"
MODE_AUTOPILOT = "autopilot"
MODE_FOLLOW = "follow"
MODE_SEARCH = "search"

CAMERA_OFF = "off"
CAMERA_AI = "ai"
CAMERA_STREAM = "stream"

camera_mode = CAMERA_OFF

live_mic_running = False

live_mic_running = False

def handle_dashboard_command(command, mode):
    global camera_mode

    if command is None:
        return mode

    print("Dashboard command:", command)

    if command == "stop":
        autopilot.stop_servo_loop()
        autopilot.stop()
        manual_control.stop()
        dashboard.set_status(mode="stopped")
        return MODE_STOPPED

    if command == "manual":
        autopilot.stop_servo_loop()
        autopilot.stop()
        manual_control.stop()
        dashboard.set_status(mode="manual")
        return MODE_MANUAL

    if command == "autopilot":
        autopilot.start_servo_loop()
        autopilot.stop()
        manual_control.stop()
        dashboard.set_status(mode="autopilot")
        return MODE_AUTOPILOT

    if command == "follow":
        if camera_mode != CAMERA_AI:
            stop_all_camera_modes()
            ai_camera.start_gesture_camera(show_preview=False)
            camera_mode = CAMERA_AI
            dashboard.set_status(camera_mode="ai")

        autopilot.stop_servo_loop()
        autopilot.stop()
        manual_control.stop()
        dashboard.set_status(mode="follow")
        return MODE_FOLLOW

    if command == "search":
        if camera_mode != CAMERA_AI:
            stop_all_camera_modes()
            ai_camera.start_gesture_camera(show_preview=False)
            camera_mode = CAMERA_AI
            dashboard.set_status(camera_mode="ai")

        autopilot.stop_servo_loop()
        autopilot.stop()
        manual_control.stop()

        dashboard.set_status(mode="search", follow_action="searching")
        print("Mode: search person")
        return MODE_SEARCH

    if command == "camera_ai":
        stop_all_camera_modes()
        ai_camera.start_gesture_camera(show_preview=False)
        camera_mode = CAMERA_AI
        dashboard.set_status(camera_mode="ai")
        return mode

    if command == "camera_stream":
        stop_all_camera_modes()
        camera_stream.start(open_browser=False)
        camera_mode = CAMERA_STREAM
        dashboard.set_status(camera_mode="stream")
        return mode

    if command == "camera_off":
        stop_all_camera_modes()
        camera_mode = CAMERA_OFF
        dashboard.set_status(camera_mode="off")
        return mode

    if command == "volume_up":
        audio.volume_up()
        return mode

    if command == "volume_down":
        audio.volume_down()
        return mode

    if command == "sound_fireball":
        audio.fireball()
        return mode

    if command == "sound_rain":
        audio.rain_over_me()
        return mode

    if command == "sound_mr":
        audio.mr_worldwide()
        return mode

    if command == "sound_speech":
        audio.speech()
        return mode

    if command == "sound_faaah":
        audio.faaah()
        return mode

    if command == "sound_honk":
        audio.honk()
        return mode

    if command == "sound_exit":
        audio.exit()
        return mode

    return mode



def toggle_live_mic():
    global live_mic_running

    if not live_mic_running:
        audio.start_pi_audio_receiver()
        live_mic_running = True
        print("Live mic receiver ON")
    else:
        audio.stop_pi_audio_receiver()
        live_mic_running = False
        print("Live mic receiver OFF")
      
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
        dashboard.set_status(camera_mode=CAMERA_AI)
        ai_camera.start_gesture_camera(show_preview=True)
        camera_mode = CAMERA_AI

    elif camera_mode == CAMERA_AI:
        print("Switching camera mode: normal browser stream")
        stop_all_camera_modes()
        dashboard.set_status(camera_mode=CAMERA_STREAM)
        camera_stream.start(open_browser=True)
        camera_mode = CAMERA_STREAM

    else:
        print("Switching camera mode: off")
        stop_all_camera_modes()
        dashboard.set_status(camera_mode=CAMERA_OFF)
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
    global camera_mode, live_mic_running
    mode = MODE_STOPPED
    print_controls()
    dashboard.start()
    autopilot.stop()
    manual_control.stop()

    try:
        while True:
            # Lesum bara mode-takkana hér.
            # Sjálf handstýringin er inni í manual_control.manual_step().
            pressed, dpad = get_pressed_buttons()
            dashboard_command = dashboard.get_pending_command()
            mode = handle_dashboard_command(dashboard_command, mode)
            manual_pressed = CROSS_BUTTON in pressed      # athugar set
            autopilot_pressed = TRIANGLE_BUTTON in pressed
            stop_pressed = CIRCLE_BUTTON in pressed
            camera_pressed = SQUARE_BUTTON in pressed
            follow_pressed = R1_BUTTON in pressed
            live_mic_pressed = L1_BUTTON in pressed
            volume_down_pressed = L3_BUTTON in pressed
            volume_up_pressed = R3_BUTTON in pressed
            honk_pressed = MENU_BUTTON in pressed
            rain_pressed = dpad == (0, 1)
            fireball_pressed = dpad == (0, -1)
            mr_pressed = dpad == (1, 0)
            speech_pressed = dpad == (-1, 0)

            tts_text = dashboard.get_pending_tts()
            if tts_text:
              audio.say(tts_text)

            if honk_pressed:
              audio.honk()

            if volume_down_pressed:
              audio.volume_down()

            if volume_up_pressed:
              audio.volume_up()

            if live_mic_pressed:
              toggle_live_mic()

            if camera_pressed:
              switch_camera_mode()
            

            if stop_pressed:
                print("Stop button pressed. Stopping robot.")
                audio.exit()
                dashboard.set_status(mode="stopped")
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

            if speech_pressed:
              audio.speech()

            

            if manual_pressed and mode != MODE_MANUAL:
                mode = MODE_MANUAL
                dashboard.set_status(mode="manual")
                autopilot.stop_servo_loop()
                autopilot.stop()
                manual_control.stop()
                print("Mode: manual / handstýring")

            elif autopilot_pressed and mode != MODE_AUTOPILOT:
              mode = MODE_AUTOPILOT
              dashboard.set_status(mode="autopilot")
              autopilot.start_servo_loop()
              autopilot.stop()
              manual_control.stop()
              print("Mode: autopilot")


            elif follow_pressed and mode != MODE_FOLLOW:
                mode = MODE_FOLLOW

                if camera_mode != CAMERA_AI:
                  stop_all_camera_modes()
                  ai_camera.start_gesture_camera(show_preview=True)
                  camera_mode = CAMERA_AI

                autopilot.stop_servo_loop()
                autopilot.stop()
                manual_control.stop()
                dashboard.set_status(mode="follow")
                dashboard.set_status(camera_mode=CAMERA_AI)
                print("Mode: follow person")

            if mode == MODE_MANUAL:
                keep_running = manual_control.manual_step()
                if keep_running is False:
                    print("Manual control requested stop.")
                    mode = MODE_STOPPED
                    break

            elif mode == MODE_AUTOPILOT:
                autopilot.autopilot_step()

            elif mode == MODE_FOLLOW:
                autopilot.follow_person_step()

            elif mode == MODE_SEARCH:
                found_person = autopilot.search_person_step()

                if found_person:
                    mode = MODE_FOLLOW
                    dashboard.set_status(mode="follow", follow_action="person found")
                    print("Search found person. Switching to follow mode.")

            else:
                autopilot.stop()
                manual_control.stop()

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping robot.")

    finally:
        stop_all_camera_modes()
        audio.stop_pi_audio_receiver()
        autopilot.stop_servo_loop()
        autopilot.stop()
        manual_control.stop()
        manual_control.close()
        dashboard.stop()
        pygame.quit()
        print("Robot stopped.")


if __name__ == "__main__":
    main()
