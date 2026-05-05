import time
from adafruit_servokit import ServoKit

kit = ServoKit(channels=8)

def center():
    kit.servo[0].angle = 90
    kit.servo[1].angle = 90

def look_right():
    kit.servo[0].angle = 105
    kit.servo[1].angle = 75

def look_left():
    kit.servo[0].angle = 70
    kit.servo[1].angle = 110

def move_and_wait(position):
    if position == "center":
        center()
    elif position == "right":
        look_right()
    elif position == "left":
        look_left()

    time.sleep(0.15)
