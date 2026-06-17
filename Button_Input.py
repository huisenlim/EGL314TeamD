import RPi.GPIO as GPIO
import time

# -------------------------------
# GPIO SETUP
# -------------------------------
button_pin = 27   # Button connected to GPIO27

GPIO.setmode(GPIO.BCM)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Ghost counter
ghost_number = 1
ghost_alive = True

try:
    print("Game Started!")
    print("Press the button to dispel ghosts!\n")

    while True:

        # Spawn new ghost if none exists
        if not ghost_alive:
            ghost_number += 1

            print(f"\nA new Ghost #{ghost_number} has appeared!")
            ghost_alive = True

            time.sleep(2)

        # -------------------------------
        # BUTTON PRESS DETECTED
        # -------------------------------
        if GPIO.input(button_pin) == False:

            if ghost_alive:

                print("\n=== BUTTON INPUT DETECTED ===")
                print(f"Dispelling Ghost #{ghost_number}...")
                
                time.sleep(1)

                print(f"Ghost #{ghost_number} Dispelled!")
                print("Area Cleared!")

                ghost_alive = False

            # Wait until button released
            while GPIO.input(button_pin) == False:
                time.sleep(0.1)

            # Debounce
            time.sleep(0.3)

        else:

            if ghost_alive:
                print(f"Ghost #{ghost_number} is haunting...")
            
            time.sleep(1)

except KeyboardInterrupt:
    print("\nProgram stopped")

finally:
    GPIO.cleanup()