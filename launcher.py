
import time
import subprocess
import pygame

ROBOT_DIR = "/home/viktor/R-bot"
MAIN_FILE = "/home/viktor/R-bot/main.py"


PS_BUTTON = 10

main_process = None


def start_main():
    global main_process

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


def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller found.")
        return

    controller = pygame.joystick.Joystick(0)
    controller.init()

    print("Launcher running.")
    print("Press PlayStation button to start main.py.")

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == PS_BUTTON:
                        start_main()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Launcher stopping.")

    finally:
        stop_main()
        pygame.quit()


if __name__ == "__main__":
    main()
