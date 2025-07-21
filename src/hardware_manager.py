# hardware_manager.py
from machine import ADC, Pin
from epaper import ICNT86, ICNT_Development, get_touch_state

class HardwareManager:
    """Manages hardware components like ADC, buttons, and touch panel."""
    def __init__(self):
        """Initializes hardware components."""
        self.adc = ADC(Pin(26))

        self.button_1 = Pin(2, Pin.IN, Pin.PULL_UP)
        self.button_2 = Pin(3, Pin.IN, Pin.PULL_UP)
        self.button_3 = Pin(15, Pin.IN, Pin.PULL_UP)

        self.tp = ICNT86()
        self.icnt_dev = ICNT_Development()
        self.icnt_old = ICNT_Development()
        self.tp.ICNT_Init()

    def get_adc_value(self):
        """Reads the ADC value from the light sensor."""
        return self.adc.read_u16()

    def get_button_states(self):
        """Reads the raw button states and inverts them."""
        raw_state_1 = self.button_1.value()
        raw_state_2 = self.button_2.value()
        raw_state_3 = self.button_3.value()

        inverted_state_1 = 1 if raw_state_1 == 0 else 0
        inverted_state_2 = 1 if raw_state_2 == 0 else 0
        inverted_state_3 = 1 if raw_state_3 == 0 else 0
        
        return (inverted_state_1, inverted_state_2, inverted_state_3)

    def get_touch_state(self):
        """Gets the current touch state from the touch panel."""
        return get_touch_state(self.tp, self.icnt_dev, self.icnt_old)
