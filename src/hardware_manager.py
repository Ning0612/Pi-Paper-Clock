# hardware_manager.py
from machine import ADC, Pin
from epaper import ICNT86, ICNT_Development, get_touch_state

class HardwareManager:
    def __init__(self):
        # ADC for light sensor
        self.adc = ADC(Pin(26))

        # Buttons
        self.button_1 = Pin(2, Pin.IN, Pin.PULL_UP)
        self.button_2 = Pin(3, Pin.IN, Pin.PULL_UP)
        self.button_3 = Pin(15, Pin.IN, Pin.PULL_UP)

        # Touch panel
        self.tp = ICNT86()
        self.icnt_dev = ICNT_Development()
        self.icnt_old = ICNT_Development()
        self.tp.ICNT_Init()

    def get_adc_value(self):
        return self.adc.read_u16()

    def get_button_states(self):
        return self.button_1.value(), self.button_2.value(), self.button_3.value()

    def get_touch_state(self):
        return get_touch_state(self.tp, self.icnt_dev, self.icnt_old)
