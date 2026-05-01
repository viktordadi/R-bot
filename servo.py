import time
from adafruit_servokit import ServoKit
# Initialize for 8 channels
kit = ServoKit(channels=8)

def scan(sonic=True):
  kit.servo[0].angle = 105
  kit.servo[1].angle = 75
  time.sleep(0.5)
  kit.servo[0].angle = 70
  kit.servo[1].angle = 110
