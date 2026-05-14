import threading
import smbus
import controller
import pygame
import time
import random

# Opna I2C bus 1 á Raspberry Pi.
bus = smbus.SMBus(1)

# Lock fyrir I2C samskipti.
i2c_lock = threading.Lock()

# Setja upp PS5 fjarstýringuna.
# ctrl er fjarstýringin sjálf.
# l2_idle og r2_idle eru upphafsgildi fyrir L2/R2 triggera.
ctrl, l2_idle, r2_idle = controller.setup_controller()


# Addressa mótorstýringarinnar á I2C.
Motor_address = 0x50

# Hámarkshraði mótoranna.
motor_speed = 255


# -------------------------------------------
# Senda upplýsingar yfir I2C til mótorstýringar.
# -------------------------------------------
def send_to_motor(m1, m2):
    # Passa að mótorhraði fari ekki út fyrir -255 til 255.
    m1 = max(-255, min(255, int(m1)))
    m2 = max(-255, min(255, int(m2)))

    # Skipta mótor 1 í hraða og stefnu.
    # Hraði er alltaf jákvæð tala.
    # Sign segir hvort mótorinn fari áfram eða afturábak.
    m1_speed = abs(m1)
    m1_sign = 0 if m1 >= 0 else 1

    # Skipta mótor 2 í hraða og stefnu.
    m2_speed = abs(m2)
    m2_sign = 0 if m2 >= 0 else 1

    # Gögnin sem eru send til mótorstýringar:
    data = [m1_speed, m1_sign, m2_speed, m2_sign]

    # Senda gögnin yfir I2C til mótorstýringar.
    bus.write_i2c_block_data(Motor_address, 0x00, data)


# -------------------------------------------
# Stoppa mótora.
# -------------------------------------------
def stop():
    # Læsa I2C áður en sent er á mótorstýringu.
    with i2c_lock:
        send_to_motor(0, 0)


def close():
    # Loka pygame/controller tengingu.
    controller.close_controller()


def manual_step():
    """
    Les PS5 fjarstýringuna einu sinni og sendir hraða á mótorana.

    Returns:
        True  = halda áfram í manual mode
        False = hætta/stopp ef ýtt er á Circle
    """

    # Lesa throttle, steering og quit frá controller.py.
    # throttle kemur frá R2/L2.
    # steering kemur frá vinstri stýripinna.
    throttle, steering, quit_pressed = controller.read_controller(ctrl, l2_idle, r2_idle)

    # Ef ýtt var á Circle, stoppa mótora og biðja main um að hætta.
    if quit_pressed:
        stop()
        return False

    # Reikna hraða fyrir mótor 1.
    m1 = throttle * motor_speed + steering * motor_speed * 0.6

    # Reikna hraða fyrir mótor 2.
    # 0.95 minnkar aðeins kraftinn á öðrum mótornum til að róbotinn keyri beinna.
    m2 = (-throttle * motor_speed + steering * motor_speed * 0.6) * 0.95

    # Senda mótorhraða yfir I2C.
    with i2c_lock:
        send_to_motor(m1, m2)

    # Skila True svo manual mode haldi áfram.
    return True



if __name__ == "__main__":
    try:
        # Keyra manual_step aftur og aftur.
        while True:
            # Ef manual_step skilar False, hætta í lykkjunni.
            if not manual_step():
                break

    finally:
        # Loka controller þegar forritið hættir.
        controller.close_controller()
