import smbus
import time
import random
from srf02.py import get_front_status    
bus = smbus.SMBus(1) 

# addressa fyrir motor (hex yfir í decimal)
Motor_address = 0x50 

# upphafs skilirði:
motor_speed = 70


# ýmis gildi (mögulega )
sensor_distance_stop = 200
sensor_distance_continue = 300



#-------------------------------------------
# senda upplysingar yfir yfir i I2C/motor
def send_to_motor(m1, m2):
# breytir gildum sem eru fyrir utan (-240 og 240)
    m1 = max(-240, min(240, int(m1)))
    m2 = max(-240, min(240, int(m2))) 
# splitar hrada + stefnu 
    m1_speed = abs(m1)
    m1_sign = 0 if m1 >= 0 else 1
    m2_speed = abs(m2)
    m2_sign = 0 if m2 >= 0 else 1
    data = [m1_speed, m1_sign, m2_speed, m2_sign]
  
  # senda gogn yfir a T2C med smbus pakkanum
    bus.write_i2c_block_data(Motor_address,0x00,data)
#------------------------------------------------------


  

# skilgreina skipanir
def go_forward():
    send_to_motor(motor_speed, -motor_speed)

def go_forward_slow():
    send_to_motor(motor_speed*0.6, -motor_speed*0.6)

def go_backwards():
    send_to_motor(-motor_speed, motor_speed)

def go_backwards_slow():
    send_to_motor(-motor_speed*0.6, motor_speed*0.6)

def go_right():
    send_to_motor(motor_speed, motor_speed)

def go_right_smooth():
    send_to_motor(motor_speed*0.8, motor_speed*0.6)

def go_left():
    send_to_motor(-motor_speed, -motor_speed)

def go_left_smooth():
    send_to_motor(-motor_speed*0.6, motor_speed*0.8)

def stop():
    send_to_motor(0,0)


while True:
    command, dist_L, dist_R = get_front_status()

    if command == "C":
        go_forward()
        """
    elif get_front_status() [0] == "B":
        time.sleep(0.1)
        if get_front_status() [0] == "L" or [1] > [2]:
            go_right()
        elif get_front_status() [0] == "R" or [1] < [2]:
            go_left() 
        else:
        """
    elif command == "B":
        x = random.randint(0, 1)
        if x == 1:
            go_left()
        if x == 0:
            go_right()
    elif command == "R":
        go_left()
    elif command == "L":
        go_right()
    time.sleep(0.05)


    


