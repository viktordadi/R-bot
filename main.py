import time
import audio
import pygame
import manual_control
import autopilot
import ai_camera
import camera_stream
import dashboard
import led_control

# PS5 button mappings in pygame
# ------------------------
R1_BUTTON = 5          # R1 = follow person mode
MENU_BUTTON = 8        # Menu_BUTTON = honk
L3_BUTTON = 11         # L3 = volume down
R3_BUTTON = 12         # R3 = volume up
L1_BUTTON = 4          # L1 = start/stop live mic receiver
CROSS_BUTTON = 0       # X = manual / handstýring
CIRCLE_BUTTON = 1      # Circle = stoppa og hætta
TRIANGLE_BUTTON = 2    # Triangle = autopilot
SQUARE_BUTTON = 3      # switch camera mode
# ------------------------

# Settings
# ------------------------
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
# ------------------------

def handle_dashboard_command(command, mode):

    """
    Tekur við skipunum frá dashboardinu.

    command:
        Skipunin sem kemur frá dashboard, t.d. "manual", "stop", "follow".

    mode:
        Núverandi mode á róbotinum.

    Returns:
        Nýtt mode ef skipunin breytir mode.
        Annars sama mode og áður.
    """

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
        camera_stream.start()
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
    """
    Kveikir eða slekkur á live mic receiver.
    """

    global live_mic_running

    # Ef live mic er ekki í gangi, ræsa hann.
    if not live_mic_running:
        audio.start_pi_audio_receiver()
        live_mic_running = True
        print("Live mic receiver ON")

    # Ef live mic er nú þegar í gangi, stoppa hann.
    else:
        audio.stop_pi_audio_receiver()
        live_mic_running = False
        print("Live mic receiver OFF")
      
def stop_all_camera_modes():
    """
    Stoppar bæði AI myndavél og camera stream.
    """

    # Reyna að stoppa AI camera.
    try:
        ai_camera.stop_gesture_camera()
    except Exception as e:
        print("AI camera stop error:", e)

    # Reyna að stoppa venjulegt camera stream.
    try:
        camera_stream.stop()
    except Exception as e:
        print("Stream camera stop error:", e)

    time.sleep(1.0)


def switch_camera_mode():
    """
    Skiptir á milli camera modes:

        off -> AI camera -> browser stream -> off
    """

    global camera_mode

    # Ef myndavélin er slökkt, kveikja á AI camera.
    if camera_mode == CAMERA_OFF:
        print("Switching camera mode: AI camera")
        stop_all_camera_modes()
        dashboard.set_status(camera_mode=CAMERA_AI)
        ai_camera.start_gesture_camera(show_preview=True)
        camera_mode = CAMERA_AI

    # Ef AI camera er í gangi, skipta yfir í venjulegt browser stream.
    elif camera_mode == CAMERA_AI:
        print("Switching camera mode: normal browser stream")
        stop_all_camera_modes()
        dashboard.set_status(camera_mode=CAMERA_STREAM)
        camera_stream.start()
        camera_mode = CAMERA_STREAM

    # Annars slökkva á öllum camera modes.
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
    """
    Les hvaða takkar voru ýttir á í þessari lykkju.

    Returns:
        buttons:
            Set af tökkum sem voru ýttir.

        dpad:
            Staða á D-pad.
    """

    # Set heldur utan um takka án þess að tvítaka þá.
    buttons = set()

    # Sjálfgefið D-pad gildi.
    dpad = (0, 0)

    # Lesa pygame events.
    for event in pygame.event.get():

        # Ef ýtt var á takka, bæta honum í buttons settið.
        if event.type == pygame.JOYBUTTONDOWN:
            buttons.add(event.button)

        # Ef D-pad hreyfðist, vista nýja D-pad stöðu.
        if event.type == pygame.JOYHATMOTION:
            dpad = event.value

    return buttons, dpad

def handle_led_command(command):
    """
    Tekur við LED skipun frá dashboard og sendir hana áfram í led_control.
    """

    # Ná hvaða LED mode á að nota.
    mode = command.get("mode")

    # Slökkva á LED.
    if mode == "off":
        led_control.off()
        return

    # Nota brightness úr skipun, eða 0.15 ef ekkert er gefið.
    brightness = command.get("brightness", 0.15)

    # Setja fastan lit á LED.
    if mode == "color":
        led_control.set_color_with_brightness(
            command.get("r", 128),
            command.get("g", 0),
            command.get("b", 255),
            brightness,
        )
        return

    # Keyra rainbow effect.
    if mode == "rainbow":
        led_control.rainbow(brightness)
        return

    # Keyra blink.
    if mode == "blink":
        led_control.blink(
            command.get("r", 255),
            command.get("g", 0),
            command.get("b", 0),
            brightness,
        )
        return


def main():
    """
    Aðalforrit róbotsins.

    Sér um:
        - að lesa PS5 fjarstýringu
        - að skipta á milli modes
        - að keyra manual, autopilot, follow og search
        - að taka við dashboard skipunum
        - að stjórna hljóði, myndavél og LED
    """

    global camera_mode, live_mic_running

    # Róbotinn byrjar stoppaður.
    mode = MODE_STOPPED

    # Prenta takka leiðbeiningar.
    print_controls()

    # Ræsa dashboard.
    dashboard.start()

    # Stoppa mótora í byrjun til öryggis.
    autopilot.stop()
    manual_control.stop()

    try:
        # Aðallykkjan keyrir þar til notandi stoppar forritið.
        while True:

            # Lesa takka frá PS5 fjarstýringu.
            pressed, dpad = get_pressed_buttons()

            # Ná í skipun frá dashboard, ef einhver er til.
            dashboard_command = dashboard.get_pending_command()

            # Láta dashboard skipun breyta mode ef þarf.
            mode = handle_dashboard_command(dashboard_command, mode)

            # Athuga hvaða takkar voru ýttir.
            manual_pressed = CROSS_BUTTON in pressed
            autopilot_pressed = TRIANGLE_BUTTON in pressed
            stop_pressed = CIRCLE_BUTTON in pressed
            camera_pressed = SQUARE_BUTTON in pressed
            follow_pressed = R1_BUTTON in pressed
            live_mic_pressed = L1_BUTTON in pressed
            volume_down_pressed = L3_BUTTON in pressed
            volume_up_pressed = R3_BUTTON in pressed
            honk_pressed = MENU_BUTTON in pressed

            # D-pad er notað fyrir mismunandi hljóð.
            rain_pressed = dpad == (0, 1)
            fireball_pressed = dpad == (0, -1)
            mr_pressed = dpad == (1, 0)
            speech_pressed = dpad == (-1, 0)

            # Ná í texta frá dashboard sem á að lesa upp.
            tts_text = dashboard.get_pending_tts()

            # Ná í LED skipun frá dashboard.
            led_command = dashboard.get_pending_led_command()

            # Ef LED skipun kom, framkvæma hana.
            if led_command:
                handle_led_command(led_command)

            # Ef texti kom frá dashboard, lesa hann upp.
            if tts_text:
                audio.say(tts_text)

            # Spila honk ef ýtt var á Menu.
            if honk_pressed:
                audio.honk()

            # Lækka hljóðstyrk.
            if volume_down_pressed:
                audio.volume_down()

            # Hækka hljóðstyrk.
            if volume_up_pressed:
                audio.volume_up()

            # Kveikja eða slökkva á live mic.
            if live_mic_pressed:
                toggle_live_mic()

            # Skipta um camera mode.
            if camera_pressed:
                switch_camera_mode()

            # Ef ýtt er á Circle, stoppa róbotinn og hætta í forritinu.
            if stop_pressed:
                print("Stop button pressed. Stopping robot.")
                audio.exit()
                dashboard.set_status(mode="stopped")
                autopilot.stop_servo_loop()
                mode = MODE_STOPPED
                autopilot.stop()
                manual_control.stop()
                break

            # D-pad upp spilar rain hljóð.
            if rain_pressed:
                audio.rain_over_me()

            # D-pad niður spilar fireball hljóð.
            if fireball_pressed:
                audio.fireball()

            # D-pad hægri spilar mr worldwide.
            if mr_pressed:
                audio.mr_worldwide()

            # D-pad vinstri spilar speech.
            if speech_pressed:
                audio.speech()

            # Ef ýtt var á X og róbotinn er ekki þegar í manual mode.
            if manual_pressed and mode != MODE_MANUAL:
                mode = MODE_MANUAL
                dashboard.set_status(mode="manual")

                # Slökkva á servo loop þegar farið er í manual.
                autopilot.stop_servo_loop()

                # Stoppa áður en manual tekur við.
                autopilot.stop()
                manual_control.stop()

                print("Mode: manual / handstýring")

            # Ef ýtt var á Triangle og róbotinn er ekki þegar í autopilot.
            elif autopilot_pressed and mode != MODE_AUTOPILOT:
                mode = MODE_AUTOPILOT
                dashboard.set_status(mode="autopilot")

                # Autopilot notar servo loop.
                autopilot.start_servo_loop()

                # Stoppa mótora áður en autopilot tekur við.
                autopilot.stop()
                manual_control.stop()

                print("Mode: autopilot")

            # Ef ýtt var á R1 og róbotinn er ekki þegar í follow mode.
            elif follow_pressed and mode != MODE_FOLLOW:
                mode = MODE_FOLLOW

                # Follow mode þarf AI camera.
                if camera_mode != CAMERA_AI:
                    stop_all_camera_modes()
                    ai_camera.start_gesture_camera(show_preview=True)
                    camera_mode = CAMERA_AI

                # Follow notar ekki servo loop hér.
                autopilot.stop_servo_loop()

                # Stoppa mótora áður en follow tekur við.
                autopilot.stop()
                manual_control.stop()

                dashboard.set_status(mode="follow")
                dashboard.set_status(camera_mode=CAMERA_AI)

                print("Mode: follow person")
              
            if mode == MODE_MANUAL:

                # Manual step les stýringu og keyrir mótora.
                keep_running = manual_control.manual_step()

                # Ef manual_control biður um stopp, hætta.
                if keep_running is False:
                    print("Manual control requested stop.")
                    mode = MODE_STOPPED
                    break

            elif mode == MODE_AUTOPILOT:

                # Keyra eitt autopilot skref.
                autopilot.autopilot_step()

            elif mode == MODE_FOLLOW:

                # Keyra eitt follow skref.
                autopilot.follow_person_step()

            elif mode == MODE_SEARCH:

                # Leita að manneskju.
                found_person = autopilot.search_person_step()

                # Ef manneskja finnst, skipta sjálfkrafa í follow mode.
                if found_person:
                    mode = MODE_FOLLOW
                    dashboard.set_status(mode="follow", follow_action="person found")
                    print("Search found person. Switching to follow mode.")

            else:
                # Ef róbotinn er í stopped eða óþekktu mode,
                # passa að mótorar séu stoppaðir.
                autopilot.stop()
                manual_control.stop()

            # Lítil bið svo lykkjan keyri ekki of hratt.
            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping robot.")

    finally:
        # Hreinsa allt upp áður en forritið lokast.

        # Slökkva á öllum camera modes.
        stop_all_camera_modes()

        # Stoppa live mic ef hann er í gangi.
        audio.stop_pi_audio_receiver()

        # Stoppa servo loop.
        autopilot.stop_servo_loop()

        # Stoppa mótora frá autopilot og manual.
        autopilot.stop()
        manual_control.stop()

        # Loka manual controller.
        manual_control.close()

        # Stoppa dashboard.
        dashboard.stop()

        # Loka pygame.
        pygame.quit()

        print("Robot stopped.")


# Keyra main() bara ef þessi skrá er keyrð beint.
if __name__ == "__main__":
    main()
