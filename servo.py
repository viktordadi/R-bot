import time
from adafruit_servokit import ServoKit

kit = ServoKit(channels=8)

def scan(sonic=True):
    kit.servo[0].angle = 90
    kit.servo[1].angle = 90
    time.sleep(0.2)

    kit.servo[0].angle = 105
    kit.servo[1].angle = 75
    time.sleep(0.2)

    kit.servo[0].angle = 70
    kit.servo[1].angle = 110
    time.sleep(0.2)
