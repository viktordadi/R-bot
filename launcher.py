import time
import subprocess
import pygame

ROBOT_DIR = "/home/viktor/R-bot"
MAIN_FILE = "/home/viktor/R-bot/main.py"

PS_BUTTON = 10

main_process = None
controller = None
controller_was_missing = True


def start_main():
    global main_process
    # Ef main.py er nú þegar í gangi, ekki ræsa annað eintak.
    if main_process is not None and main_process.poll() is None:
        print("main.py is already running")
        return

    print("Starting main.py...")
    main_process = subprocess.Popen(
        ["/usr/bin/python3", MAIN_FILE],
        cwd=ROBOT_DIR,
    )


def stop_main():
    global main_process
    # Ef main.py er ekki í gangi, þá þarf ekkert að stoppa.
    if main_process is None or main_process.poll() is not None:
        main_process = None
        return

    print("Stopping main.py...")
    main_process.terminate()

    try:
        main_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        main_process.kill()

    main_process = None


def connect_controller():
    pygame.joystick.quit()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        return None

    joy = pygame.joystick.Joystick(0)
    joy.init()
    return joy


def main():
    global controller, controller_was_missing

    # Ræsa pygame.
    pygame.init()

    # Ræsa joystick/fjarstýringar stuðning í pygame.
    pygame.joystick.init()

    print("Launcher running.")
    print("Waiting for controller...")

    try:
        # Aðallykkjan keyrir endalaust á meðan launcherinn er í gangi.
        while True:

            # Ef engin fjarstýring er vistuð, reyna að tengjast fjarstýringu.
            if controller is None:
                controller = connect_controller()

                # Ef engin fjarstýring finnst, bíða og reyna aftur.
                if controller is None:

                    # Prenta aftengingar skilaboð bara einu sinni
                    # þegar fjarstýringin hverfur.
                    if not controller_was_missing:
                        print("Controller disconnected. Waiting...")
                        controller_was_missing = True

                    time.sleep(1.0)
                    continue

                # Ef fjarstýring var áður ótengd en fannst núna,
                # prenta tengingar skilaboð.
                if controller_was_missing:
                    print("Controller connected:", controller.get_name())
                    print("Press PlayStation button to start main.py.")
                    controller_was_missing = False

            # Lesa öll pygame events, t.d. takka, tengingu og aftengingu.
            for event in pygame.event.get():

                # Ef fjarstýringin er aftengd.
                if event.type == pygame.JOYDEVICEREMOVED:
                    controller = None

                    # Setja þetta False svo skilaboðin
                    # "Controller disconnected" prentist næst.
                    controller_was_missing = False

                # Ef ný fjarstýring er tengd.
                elif event.type == pygame.JOYDEVICEADDED:
                    controller = connect_controller()

                    # Ef tenging tókst og fjarstýring var áður týnd,
                    # prenta að hún sé tengd.
                    if controller is not None and controller_was_missing:
                        print("Controller connected:", controller.get_name())
                        print("Press PlayStation button to start main.py.")
                        controller_was_missing = False

                # Ef ýtt er á takka á fjarstýringunni.
                elif event.type == pygame.JOYBUTTONDOWN:

                    # Ef ýtt er á PlayStation takkann,
                    # þá er main.py ræst.
                    if event.button == PS_BUTTON:
                        start_main()

            time.sleep(0.05)

    except KeyboardInterrupt:
        # Ef ýtt er á Ctrl+C í terminal, stoppar launcherinn.
        print("Launcher stopping.")

    finally:
        # Þegar launcherinn lokast, stoppa main.py ef það er í gangi.
        stop_main()

        # Loka pygame almennilega.
        pygame.quit()

if __name__ == "__main__":
    main()
