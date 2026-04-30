import time
from adafruit_servokit import ServoKit
# Initialize for 8 channels
kit = ServoKit(channels=8)

def scan(sonic=True):
  kit.servo[0].angle = 0
  kit.servo[1].angle = 0
  while True:
    if sonic:
      time.sleep(0.5)
      kit.servo[0].angle = 45
      kit.servo[1].angle = 360-45
      time.sleep(0.5)
      kit.servo[0].angle = 360-30
      kit.servo[1].angle = 30
    else:
      break
    
  
scan()
