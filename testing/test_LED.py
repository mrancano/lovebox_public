import time
import os
from gpiozero import LED

os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"

led = LED(4)
led.on()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    led.close()
