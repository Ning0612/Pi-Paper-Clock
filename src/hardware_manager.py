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
        """
        Reads the raw button states and inverts them.
        Returns a tuple where 1 means 'pressed' and 0 means 'not pressed'.
        """
        # Read raw values: 0 when pressed, 1 when not pressed (due to PULL_UP)
        raw_state_1 = self.button_1.value()
        raw_state_2 = self.button_2.value()
        raw_state_3 = self.button_3.value()

        # Invert the states: 1 becomes 0, 0 becomes 1
        inverted_state_1 = 1 if raw_state_1 == 0 else 0
        inverted_state_2 = 1 if raw_state_2 == 0 else 0
        inverted_state_3 = 1 if raw_state_3 == 0 else 0
        
        return (inverted_state_1, inverted_state_2, inverted_state_3)

    def get_touch_state(self):
        return get_touch_state(self.tp, self.icnt_dev, self.icnt_old)
