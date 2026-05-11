import pygame

import subprocess
import signal
import os

live_mic_process = None


def start_pi_audio_receiver():
    global live_mic_process

    if live_mic_process is not None:
        print("Live mic receiver already running")
        return

    pygame.mixer.music.stop()

    command = (
        "nc -lk 5005 | "
        "aplay -D plughw:3,0 -f S16_LE -r 48000 -c 2 -"
    )

    live_mic_process = subprocess.Popen(
        command,
        shell=True,
        preexec_fn=os.setsid,
    )

    print("Live mic receiver started on port 5005")


def stop_pi_audio_receiver():
    global live_mic_process

    if live_mic_process is not None:
        try:
            os.killpg(os.getpgid(live_mic_process.pid), signal.SIGTERM)
        except Exception as e:
            print("Could not stop live mic receiver:", e)

        live_mic_process = None
        print("Live mic receiver stopped")
pygame.mixer.init()

def is_playing():
    return pygame.mixer.music.get_busy()

def fireball():
  pygame.mixer.music.load("fireball.mp3")
  pygame.mixer.music.play()

def rain_over_me():
  pygame.mixer.music.load("rain_over_me.mp3")
  pygame.mixer.music.play()

def mr_worldwide():
  pygame.mixer.music.load("mr_worldwide.mp3")
  pygame.mixer.music.play()
  
def right():
  pygame.mixer.music.load("right.mp3")
  pygame.mixer.music.play()

def left():
  pygame.mixer.music.load("left.mp3")
  pygame.mixer.music.play()

def faaah():
    pygame.mixer.music.load("faaah.mp3")
    pygame.mixer.music.play()

def stop_faaah():
    pygame.mixer.music.stop()

def speech():
  pygame.mixer.music.load("speech.mp3")
  pygame.mixer.music.play()
