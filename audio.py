import pygame

import subprocess

live_mic_process = None


def start_live_mic():
    """
    Starts live PC microphone audio sent to the Pi speaker.

    This assumes the command is run from the PC, not from the Pi.
    So this function is only useful if audio.py runs on the PC.

    For your robot code running on the Pi, use start_pi_audio_receiver()
    instead.
    """
    print("Live mic should be started from the PC, not from the Pi.")


def start_pi_audio_receiver():
    """
    Starts a listener on the Pi using netcat + aplay.

    PC sends raw audio to this Pi.
    """
    global live_mic_process

    if live_mic_process is not None:
        print("Live mic receiver already running")
        return

    live_mic_process = subprocess.Popen(
        "nc -l -p 5005 | aplay -D plughw:3,0 -f S16_LE -r 48000 -c 2 -",
        shell=True,
    )

    print("Pi live mic receiver started on port 5005")


def stop_pi_audio_receiver():
    global live_mic_process

    if live_mic_process is not None:
        live_mic_process.terminate()
        live_mic_process = None
        print("Pi live mic receiver stopped")

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
