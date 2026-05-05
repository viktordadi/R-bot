import threading
import servo
import srf02
import smbus
import time
import random
import audio

scanning = True

i2c_lock = threading.Lock()

def servo_loop():
    global scanning

    while True:
        if scanning:
            with i2c_lock:
                servo.scan()
        time.sleep(0.05)


threading.Thread(target=servo_loop, daemon=True).start()


bus = smbus.SMBus(1) 

# addressa fyrir motor (hex yfir í decimal)
Motor_address = 0x50 

# upphafs skilirði:
motor_speed = 240



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

def turn_until_clear(direction):
    while True:
        with i2c_lock:
            command, dist_L, dist_R = srf02.get_front_status()

        if command == "C":
            stop()
            time.sleep(0.1)
            break

        if direction == "left":
            go_left_smooth()
        else:
            go_right_smooth()

        time.sleep(0.1)


def autopilot_step():
    global scanning

    with i2c_lock:
        command, dist_L, dist_R = srf02.get_front_status()

    if command == "C":
        print("Clear")
        scanning = True

        if min(dist_L, dist_R) < 60:
            go_forward_slow()
        else:
            go_forward()

    elif command == "B":
        print("Both")
        scanning = False

        with i2c_lock:
            servo.detect()
            time.sleep(0.1)

        go_backwards_slow()
        time.sleep(0.3)

        if dist_L > dist_R:
            turn_until_clear("left")
        else:
            turn_until_clear("right")

        scanning = True

    elif command == "R":
        print("Right")
        scanning = False

        with i2c_lock:
            servo.detect()
            time.sleep(0.1)

        turn_until_clear("left")
        scanning = True

    elif command == "L":
        print("Left")
        scanning = False

        with i2c_lock:
            servo.detect()
            time.sleep(0.1)

        turn_until_clear("right")
        scanning = True

    else:
        print("Error")
        stop()
        time.sleep(0.2)

if __name__ == "__main__":
    try:
        while True:
            autopilot_step()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping robot")

    finally:
        stop()

