import time
from machine import Pin, PWM

class Chime:
    """Controls the chime functionality using PWM on a specified pin."""
    def __init__(self, pin_num=20):
        """Initializes the Chime object."""
        self.pin = Pin(pin_num, Pin.OUT)
        self.pwm = PWM(self.pin)
        self.pwm.duty_u16(0)

    def play(self, frequency, duration_ms, volume):
        """Plays a tone at a given frequency, duration, and volume."""
        if volume > 0:
            self.pwm.freq(frequency)
            duty_cycle = int((volume / 100 / 2) * 65535)
            self.pwm.duty_u16(duty_cycle)
            time.sleep_ms(duration_ms)
        self.pwm.duty_u16(0)

    def do_chime(self, pitch=880, volume=80):
        """Plays two short beeps."""
        self.play(pitch, 100, volume)
        time.sleep_ms(200)
        self.play(pitch, 100, volume)

    def deinit(self):
        """Deinitializes the PWM to release the pin."""
        self.pwm.deinit()


