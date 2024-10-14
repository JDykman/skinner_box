import time
import os

#TODO Overhaul this file. It's a mess.

# Detect if running on Raspberry Pi
try:
    from gpiozero import LED, Button, OutputDevice
    from rpi_ws281x import Adafruit_NeoPixel, Color
    IS_PI = True
except (ImportError, RuntimeError):
    print("Error importing GPIO libraries. Mocking GPIO for testing.")
    IS_PI = False

# LED strip configuration
LED_COUNT = 6      # Number of LED pixels.
LED_PIN = 12        # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800kHz)
LED_DMA = 10        # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)

# If running on Raspberry Pi, initialize the real components
if IS_PI:
    try:
        strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
        strip.begin()
        print("Starting LED strip")
    except Exception as e:
        print(f"Error starting LED strip: {e}")
        strip = None
else:
    # Mock GPIO for non-Raspberry Pi environments
    class MockDevice:
        def __init__(self):
            self.status = False

        def on(self):
            print("Mock device on")
            self.status = True

        def off(self):
            print("Mock device off")
            self.status = False

        def close(self):
            print("Mock device closed")
    class MockNeoPixel:
        def is_active(self):
            # Simulate LED strip status
            import random
            return random.choice([True, False])
        
        def numPixels(self):
            return LED_COUNT

        def setPixelColor(self, i, color):
            pass

        def show(self):
            print("Mock LED strip updated")
        

#region I/O
# Input Ports
lever_port = 14
nose_poke_port = 17
start_trial_port = 23
water_primer_port = 22
manual_stimulus_port = 24
manual_interaction_port = 25
manual_reward_port = 26

# Output Ports
feeder_port = 3
water_port = 18
speaker_port = 13

# Button Setup
if IS_PI:
    try:
        lever = Button(lever_port, bounce_time=0.1)
        poke = Button(nose_poke_port, pull_up=False, bounce_time=0.1)
        water_primer = Button(water_primer_port, bounce_time=0.1)
        manual_stimulus_button = Button(manual_stimulus_port, bounce_time=0.1)
        manual_interaction = Button(manual_interaction_port, bounce_time=0.1)
        manual_reward = Button(manual_reward_port, bounce_time=0.1)
        start_trial_button = Button(start_trial_port, bounce_time=0.1)
        feeder_motor = OutputDevice(feeder_port, active_high=False, initial_value=False)
        water_motor = OutputDevice(water_port, active_high=False, initial_value=False)
    except Exception as e:
        print(f"Error setting up buttons: {e}") 
else:
    # Mock GPIO for non-Raspberry Pi environments
    lever = MockDevice()
    poke = MockDevice()
    water_primer = MockDevice()
    manual_stimulus_button = MockDevice()
    manual_interaction = MockDevice()
    manual_reward = MockDevice()
    start_trial_button = MockDevice()
    feeder_motor = MockDevice()
    water_motor = MockDevice()
    buzzer = MockDevice()
    strip = MockNeoPixel()
#endregion

#region Action Functions
# Rewards
def feed():
    try:
        feeder_motor.on()
        time.sleep(1)  # TODO Adjust Feed Time
        feeder_motor.off()
        feeder_motor.close()
    finally:
        return

def water():
    try:
        water_motor.on()
        time.sleep(0.15)  # TODO Adjust Water Time
        water_motor.off()
        water_motor.close()
    finally:
        return

def start_motor():
    try:
        print("Motor starting")
        water_motor.on()
        if water_primer is not None:
            water_primer.when_released = lambda: stop_motor(water_motor)
    except Exception as e:
        print(f"An error occurred while starting the motor: {e}")
    finally:
        return

def stop_motor(motor):
    try:
        print("Motor stopping")
        motor.off()
        motor.close()
    except Exception as e:
        print(f"An error occurred while stopping the motor: {e}")
    finally:
        return

# Stims
def flashLightStim(color, wait_ms=10):
    """Flash the light stimulus."""
    try:
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:], 16)  # Convert to RGB
        if IS_PI: color = Color(r, g, b)
        else: color = (r, g, b)
        # Turn lights on
        print(f"Flashing light with color {color}")
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
        # Turn lights off
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
            strip.show()
            time.sleep(wait_ms / 1000.0)
    except Exception as e:
        print(f"An error occurred in flashLightStim: {e}")

def play_sound(duration):  # TODO
    try:
        print("Playing sound")
        time.sleep(duration)  # Wait for a predetermined amount of time
    except Exception as e:
        print(f"An error occurred while playing sound: {e}")
    finally:
        pass

# Interactions
def lever_press(state_machine = None):
    try:
        if state_machine != None:
            state_machine.lever_press()
        else:
            lever.on()
            print("Lever pressed")
            time.sleep(0.1) #TODO Get rid of this
            lever.off()
    except Exception as e:
        print(f"An error occurred during lever press: {e}")
    feed()

def nose_poke(state_machine = None):
    try:
        print("Nose poke")
        if state_machine != None:
            state_machine.nose_poke()
        else:
            poke.on()
            time.sleep(0.1)
            poke.off()
    except Exception as e:
        print(f"An error occurred during nose poke: {e}")
    water()
#endregion
