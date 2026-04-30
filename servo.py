import time
from adafruit_servokit import ServoKit
# Initialize for 8 channels
kit = ServoKit(channels=8)

def scan(sonic=True):
  kit.servo[0].angle = 90
  kit.servo[1].angle = 90
    while sonic:
    time.sleep(0.5)
    kit.servo[0].angle = 110
    kit.servo[1].angle = 70
    time.sleep(0.5)
    kit.servo[0].angle = 45
    kit.servo[1].angle = 135
    
  
scan()
