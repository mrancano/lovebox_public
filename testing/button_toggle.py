import RPi.GPIO as GPIO
import time
from controllers.servo_controller import ServoController

BUTTON_PIN = 3
SERVO_PIN = 12

# Initialize hardware
servo = ServoController(pin=SERVO_PIN)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# State tracker
is_at_180 = False

print("Toggle Test Ready. Press button to flip the servo.")

try:
    while True:
        # Check for button press (LOW means pressed)
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            if not is_at_180:
                print("Moving to 180...")
                servo.go_to_degrees(180)
                is_at_180 = True
            else:
                print("Moving to 0...")
                servo.go_to_degrees(0)
                is_at_180 = False
            
            # Debounce: wait for release so it doesn't flicker states
            while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                time.sleep(0.1)
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nCleaning up...")
finally:
    servo.cleanup()
    GPIO.cleanup()
