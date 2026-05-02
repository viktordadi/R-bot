import pygame
import time

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("Engin fjarstýring fannst.")
    exit()

js = pygame.joystick.Joystick(0)
js.init()

print("Fjarstýring fannst:")
print(js.get_name())
print()
print("Hreyfðu pinnum, ýttu á takka og prófaðu L2/R2.")
print("Ctrl+C til að hætta.")
print()

last_axes = {}
last_buttons = {}
last_hats = {}

try:
    while True:
        pygame.event.pump()

        # Axes: pinnar og triggers
        for i in range(js.get_numaxes()):
            value = round(js.get_axis(i), 3)

            if i not in last_axes or abs(value - last_axes[i]) > 0.05:
                print(f"AXIS {i}: {value}")
                last_axes[i] = value

        # Buttons
        for i in range(js.get_numbuttons()):
            value = js.get_button(i)

            if i not in last_buttons or value != last_buttons[i]:
                if value == 1:
                    print(f"BUTTON {i}: pressed")
                else:
                    print(f"BUTTON {i}: released")
                last_buttons[i] = value

        # D-pad / hats
        for i in range(js.get_numhats()):
            value = js.get_hat(i)

            if i not in last_hats or value != last_hats[i]:
                print(f"HAT {i}: {value}")
                last_hats[i] = value

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nHætt.")
finally:
    pygame.quit()
