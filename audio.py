import pygame

import subprocess
import signal
import os
import shlex

live_mic_process = None

# ffmpeg -f dshow -i audio="Microphone Array (Realtek(R) Audio)" -filter:a "volume=8" -ar 48000 -ac 2 -f s16le udp://10.100.38.59:5005

def say(text):
    if text is None:
        return

    text = str(text).strip()

    if text == "":
        return

    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

    try:
        subprocess.Popen(
            f'espeak {shlex.quote(text)} --stdout | pw-play -',
            shell=True,
        )
    except Exception as e:
        print("Text-to-speech error:", e)

def volume_up():
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"], check=False)
    print("Volume up")


def volume_down():
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"], check=False)
    print("Volume down")

def start_pi_audio_receiver():
    global live_mic_process

    if live_mic_process is not None:
        print("Live mic receiver already running")
        return

    pygame.mixer.music.stop()

    command = (
        "nc -lu 5005 | "
        "pw-cat --playback --raw --format s16 --rate 48000 --channels 2 -"
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

def honk():
    pygame.mixer.music.load("honk.mp3")
    pygame.mixer.music.play()

def exit():
    pygame.mixer.music.load("exit.mp3")
    pygame.mixer.music.play()
