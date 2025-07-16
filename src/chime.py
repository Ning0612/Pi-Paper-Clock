import time
from machine import Pin, PWM

class Chime:
    def __init__(self, pin_num=20):
        self.pin = Pin(pin_num, Pin.OUT)
        self.pwm = PWM(self.pin)
        self.pwm.duty_u16(0)

    def play(self, frequency, duration_ms, volume):
        if volume > 0:
            self.pwm.freq(frequency)
            duty_cycle = int((volume / 100) * 65535)
            self.pwm.duty_u16(duty_cycle)
            time.sleep_ms(duration_ms)
        self.pwm.duty_u16(0)

    def do_chime(self, pitch=880, volume=80):
        """Play two short beeps."""
        self.play(pitch, 100, volume)
        time.sleep_ms(50)
        self.play(pitch, 100, volume)

    def deinit(self):
        self.pwm.deinit()

def test_chime():
    """Function to test the chime sound."""
    print("Testing chime...")
    chime = Chime(20)
    chime.do_chime(pitch=440, volume=50)
    chime.deinit()
    print("Test complete.")

if __name__ == '__main__':
    test_chime()
