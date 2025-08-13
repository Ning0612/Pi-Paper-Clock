# hardware_manager.py
import time
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
        
        # Button long press detection
        self.button_press_timestamps = {}
        self.long_press_threshold_ms = 3000

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
    
    def handle_button_long_press(self, callback=None):
        """Handle button long press detection with callback support.
        
        Args:
            callback: Function to call when long press is detected. 
                     Receives button index (0-2) as parameter.
                     
        Returns:
            True if long press was detected, False otherwise.
        """
        button_states = self.get_button_states()
        current_time_ms = time.ticks_ms()
        
        for i, state in enumerate(button_states):
            if state == 1:  # Button is pressed
                if i not in self.button_press_timestamps:
                    # Record the start of button press
                    self.button_press_timestamps[i] = current_time_ms
                else:
                    # Check if long press threshold is reached
                    press_duration = time.ticks_diff(current_time_ms, self.button_press_timestamps[i])
                    
                    if press_duration >= self.long_press_threshold_ms:
                        print(f"Button {i+1} long pressed for {press_duration} ms")
                        
                        # Call the callback if provided
                        if callback:
                            callback(i)
                            
                        # Clear the timestamp to prevent repeated calls
                        del self.button_press_timestamps[i]
                        return True
            else:
                # Button is released, clear timestamp
                if i in self.button_press_timestamps:
                    del self.button_press_timestamps[i]
        
        return False
