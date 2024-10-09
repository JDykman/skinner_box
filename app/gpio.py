# app/gpio.py
import time

try:
    from gpiozero import LED, Button, OutputDevice
    from rpi_ws281x import Adafruit_NeoPixel, Color
except:
    print("Error importing GPIO libraries")
    pass

# LED strip configuration:
LED_COUNT      = 60      # Number of LED pixels.
LED_PIN        = 12      # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
# Create NeoPixel object with appropriate configuration.
try:
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
    strip.begin()
    print("Starting strip")
except:
    print("Error starting strip")
    pass
#endregion

#region I/O

#Input Ports
lever_port = 14
nose_poke_port = 17 #Port 17 no work
start_trial_port = 23
water_primer_port = 22
manual_stimulus_port = 24
manual_interaction_port = 25
manual_reward_port = 26

#Output Ports
feeder_port = 3
water_port = 18
speaker_port = 13

#Button Settup
try:
    lever = Button(lever_port, bounce_time=0.1)
    poke = Button(nose_poke_port, pull_up=False, bounce_time=0.1)
    water_primer = Button(water_primer_port, bounce_time=0.1)
    manual_stimulus_button = Button(manual_stimulus_port, bounce_time=0.1)
    manual_interaction = Button(manual_interaction_port, bounce_time=0.1)
    manual_reward = Button(manual_reward_port, bounce_time=0.1)
    start_trial_button = Button(start_trial_port, bounce_time=0.1)
except:
    print("Error setting up buttons")
    pass
#manual_stimulus_button.when_held
#manual_interaction.when_held()
#manual_reward.when_held()
#endregion

#region Action Functions
#Rewards
def feed():
	try:
		feeder_motor = OutputDevice(feeder_port, active_high=False, initial_value=False)
		feeder_motor.on()
		time.sleep(1) #TODO Adjust Feed Time
		feeder_motor.off()
		feeder_motor.close()
	finally:
		return

def water():
    try:
        water_motor = OutputDevice(water_port, active_high=False, initial_value=False)
        water_motor.on()
        time.sleep(.15) #TODO Adjust Water Time with settings
        water_motor.off()
        water_motor.close()
    finally:
        return

def start_motor():
    try:
        water_motor = OutputDevice(water_port, active_high=False, initial_value=False)
        print("Motor starting")  # Optional: for debugging
        water_motor.on()  # Start the motor
        if(water_primer!=None):water_primer.when_released = lambda: stop_motor(water_motor)
    except Exception as e:
        print(f"An error occurred while starting the motor: {e}")
        stop_motor(water_motor)
    finally:
        return
    
def stop_motor(motor):
    try:
        print("Motor stopping")  # Optional: for debugging
        motor.off()  # Stop the motor
        motor.close()
    except Exception as e:
        print(f"An error occurred while stopping the motor: {e}")
    finally:
        return

#Stims
def flashLightStim(color, wait_ms=10):
    """Flash the light stimulus."""
    try:
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:], 16)  # Convert to RGB
        color = Color(r, g, b)
        if (strip):
            # Turn lights on
            print(color)
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, color)
                strip.show()
                time.sleep(wait_ms/1000.0)
            # Turn lights off
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, Color(0,0,0))
                strip.show()
                time.sleep(wait_ms/1000.0)
    except Exception as e:
        # Log the exception or handle it as needed
        print(f"An error occurred in light_stimulus: {e}")

def play_sound(duration): #TODO 
    try:
        print("Playing sound")
        #buzzer.on
        time.sleep(duration) # Wait a predetermained amount of time
        #buzzer.off
    except Exception as e:
        print(f"An error occurred while playing sound: {e}")
    finally:
        pass

#Interactions
def lever_press(state_machine):
    try:
        state_machine.lever_press()
    except:
        pass
    feed()

def nose_poke(state_machine):
    print("Nose poke")
    try:
        state_machine.nose_poke()
    except:
        pass
    water()
