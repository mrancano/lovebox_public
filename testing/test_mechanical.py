import RPi.GPIO as GPIO
import time

SERVO_PIN = 12

servo_freq = 50

pulse_width_max_rot = 0.0024
max_rot_degs = 180

pulse_width_min_rot = 0.0005
min_rot_degs = 0

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, servo_freq)
pwm.start(0)

def frange(start, stop, step):
    while start < stop:
        yield round(start, 10)  # Rounding prevents float precision errors
        start += step


def degrees_to_duty_cycle(
        deg,
        max_rot_degs=max_rot_degs,
        pulse_width_max_rot=pulse_width_max_rot,
        min_rot_degs=min_rot_degs,
        pulse_width_min_rot=pulse_width_min_rot,
        servo_freq=servo_freq):

    servo_period = 1 / servo_freq

    max_duty_cycle = (pulse_width_max_rot / servo_period) * 100
    min_duty_cycle = (pulse_width_min_rot / servo_period) * 100

    if deg > max_rot_degs:
        raise ValueError(f"deg exceeds maximum: {max_rot_degs}")

    if deg < min_rot_degs:
        raise ValueError(f"deg below minimum: {min_rot_degs}")

    deg_range = max_rot_degs - min_rot_degs
    duty_cycle_range = max_duty_cycle - min_duty_cycle

    duty_cycle = (
        ((deg - min_rot_degs) / deg_range) * duty_cycle_range
    ) + min_duty_cycle

    return duty_cycle


try:

#    for pulse_width in frange(0.0003,0.0015,0.0001):
#        print(f"Pulse Width:{pulse_width}")
#        duty_cycle = pulse_width*servo_freq*100
#        pwm.ChangeDutyCycle(duty_cycle)
#        time.sleep(5)

    while True:
        deg = float(input("Enter angle (0-180): "))

        duty = degrees_to_duty_cycle(deg)

        print(f"Duty cycle: {duty:.2f}%")

        pwm.ChangeDutyCycle(duty)

        time.sleep(5)

        # Stop sending signal to reduce jitter
        pwm.ChangeDutyCycle(0)

except KeyboardInterrupt:
    pass

finally:
    pwm.stop()
    GPIO.cleanup()
def frange(start, stop, step):
    while start < stop:
        yield round(start, 10)  # Rounding prevents float precision errors
        start += step
def frange(start, stop, step):
    while start < stop:
        yield round(start, 10)  # Rounding prevents float precision errors
        start += step
def frange(start, stop, step):
    while start < stop:
        yield round(start, 10)  # Rounding prevents float precision errors
        start += step

