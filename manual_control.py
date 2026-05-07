import threading
import servo
import srf02
import smbus
import controller
import pygame
import time
import random
bus = smbus.SMBus(1)
i2c_lock = threading.Lock()
ctrl, l2_idle, r2_idle = controller.setup_controller()



# addressa fyrir motor (hex yfir í decimal)
Motor_address = 0x50 

# upphafs skilirði:
motor_speed = 255



#-------------------------------------------
# senda upplysingar yfir yfir i I2C/motor
def send_to_motor(m1, m2):
# breytir gildum sem eru fyrir utan (-255 og 255)
    m1 = max(-255, min(255, int(m1)))
    m2 = max(-255, min(255, int(m2))) 
    
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
    send_to_motor(motor_speed*0.7, -motor_speed*0.2)

def go_left():
    send_to_motor(-motor_speed, -motor_speed)

def go_left_smooth():
    send_to_motor(motor_speed*0.2, -motor_speed*0.7)

def stop():
    send_to_motor(0,0)

def close():
    controller.close_controller()


def manual_step():
    # les skynjar og stjórnar 
    # with I2c_lock tryggir að aðeins eitt fall talar við I2C
    with i2c_lock:
        command, dist_L, dist_R = srf02.get_front_status(25)

    throttle, steering, quit_pressed = controller.read_controller(ctrl, l2_idle, r2_idle)

    if quit_pressed:
        with i2c_lock:
            stop()
        return False

    if command == "B":
        print("Hindrun")
        with i2c_lock:
            go_backwards_slow()
        time.sleep(0.3)
    
    else: 
        m1 = throttle*motor_speed + steering*motor_speed*0.6
        m2 = -throttle*motor_speed + steering*motor_speed*0.6   
        with i2c_lock:
            send_to_motor(m1, m2)
    return True

# aðallykkja sem kallar á fallið ef það er kallað á hana
if __name__ == "__main__":
    try:
        while True:
            if not manual_step():
                break
    finally:                      
        controller.close_controller()
