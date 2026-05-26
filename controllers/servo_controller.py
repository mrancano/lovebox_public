import RPi.GPIO as GPIO
import time

class ServoController:
    def __init__(self, pin=12, freq=50):
        self.pin = pin
        self.freq = freq
        self.period = 1 / freq
        
        # User-tested parameters
        self.pulse_max = 0.0024
        self.pulse_min = 0.0005
        self.max_deg = 180
        self.min_deg = 0

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, self.freq)
        self.pwm.start(0)

    def _degrees_to_duty(self, deg):
        # Calculate duty cycle: (Pulse Width / Period) * 100
        max_duty = (self.pulse_max / self.period) * 100
        min_duty = (self.pulse_min / self.period) * 100
        
        # Linear interpolation
        duty = min_duty + (deg / self.max_deg) * (max_duty - min_duty)
        return duty

    def go_to_degrees(self, deg):
        if not (self.min_deg <= deg <= self.max_deg):
            print(f"Angle {deg} out of range!")
            return

        duty = self._degrees_to_duty(deg)
        self.pwm.ChangeDutyCycle(duty)
        
        # Allow time for physical movement
        time.sleep(0.5) 
        
        # Set to 0 to stop sending pulses (releases the motor)
        self.pwm.ChangeDutyCycle(0)

    def cleanup(self):
        self.pwm.stop()
