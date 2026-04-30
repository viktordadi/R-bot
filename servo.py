import time
from adafruit_servokit import ServoKit
# Initialize for 8 channels
kit = ServoKit(channels=8)

def scan(sonic=True):
  kit.servo[0].angle = 90
  kit.servo[1].angle = 90
  while sonic:
    time.sleep(0.5)
    kit.servo[0].angle = 135
    kit.servo[1].angle = 45
    time.sleep(0.5)
    kit.servo[0].angle = 15
    kit.servo[1].angle =  165
    
  
scan()
