import threading
import servo
import srf02
import smbus
import time
import random



bus = smbus.SMBus(1) 

# addressa fyrir motor (hex yfir í decimal)
Motor_address = 0x50 

# upphafs skilirði:
motor_speed = 100



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
    send_to_motor(motor_speed*0.7, -motor_speed*0.2)

def go_left():
    send_to_motor(-motor_speed, -motor_speed)

def go_left_smooth():
    send_to_motor(motor_speed*0.2, -motor_speed*0.7)

def stop():
    send_to_motor(0,0)


def autopilot_step():
    command, dist_L, dist_R = srf02.get_front_status()

    if command == "C":
        print("Clear")
        if min(dist_L, dist_R) < 60:
            go_forward_slow()
        else:
            go_forward()

    elif command == "B":
        print("Both")
        go_backwards_slow()
        time.sleep(0.3)

        if dist_L > dist_R:
            go_left()
        else:
            go_right()

        time.sleep(0.4)
        stop()

    elif command == "R":
        print("Right")
        go_left_smooth()

    elif command == "L":
        print("Left")
        go_right_smooth()

    else:
        print("Error")
        stop()
        time.sleep(0.2)
        go_backwards_slow()
        time.sleep(0.3)
        stop()


if __name__ == "__main__":
    try:
        while True:
            autopilot_step()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping robot")

    finally:
        stop()
