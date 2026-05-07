import pygame

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

def sus():
  pygame.mixer.music.load("sus.mp3")
  pygame.mixer.music.play()
