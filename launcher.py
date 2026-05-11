#!/usr/bin/env python3

import os
import time
import subprocess
import pygame
import signal

ROBOT_DIR = "/home/viktor/R-bot"
MAIN_FILE = "/home/viktor/R-bot/main.py"

# Prófaðu fyrst 12. Ef það virkar ekki, sjáðu debug print í terminal.
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
        print("main.py is not running")
        main_process = None
        return

    print("Stopping main.py...")
    main_process.terminate()

    try:
        main_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("main.py did not stop, killing it...")
        main_process.kill()

    main_process = None


def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller found.")
        print("Connect the PS5 controller and restart launcher.py.")
        return

    controller = pygame.joystick.Joystick(0)
    controller.init()

    print("Launcher running.")
    print("Controller:", controller.get_name())
    print("Press PlayStation button to start main.py.")
    print("Press Ctrl+C to quit launcher.")
    print()
    

    try:
        while True:
            for event in pygame.event.get():
                
                    if event.button == PS_BUTTON:
                        start_main()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nLauncher stopping.")

    finally:
        stop_main()
        pygame.quit()


if __name__ == "__main__":
    main()
