import time
from adafruit_servokit import ServoKit
# Initialize for 8 channels
kit = ServoKit(channels=8)
while True:
  print("Moving to 180")
  kit.servo[0].angle = 180
  time.sleep(1)
  print("Moving to 0")
  kit.servo[0].angle = 0
  time.sleep(1)
