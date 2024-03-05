from signal import pause
import pygame
from flask import Flask, render_template, request, jsonify, url_for, redirect
from gpiozero import LED, Button, Buzzer 
import RPi.GPIO as GPIO
import time
import threading
import board

app = Flask(__name__)
pygame.mixer.init()


#region Action Functions
def feed():
	flash_light(23, 1, 0.5)
	#TODO Add code to feed the animal
	return

def water():
	flash_light(25, 1, 0.5)
	#TODO Add code to water the animal
	return

def flash_light(pin, duration, interval):
	"""
	Flashes an LED light connected to a specified GPIO pin.

	:param pin: The GPIO pin number to which the LED is connected.
	:param duration: Total duration to flash the LED in seconds.
	:param interval: Interval between flashes in seconds.
	"""
	# Set up GPIO pin
	try: # Fixes issue with GPIO pin 'already being in use' causing a crash
		led = LED(pin)
		led.blink(interval, interval, duration)
	except:
		print("Error flashing light")
		return

def play_sound(pin, duration):
	print("Playing sound")
	buzzer = Buzzer(pin)

	buzzer.on
	time.sleep(duration)
	buzzer.off

def lever_press():
	print("Lever pressed")
	feed()

def nose_poke():
	print("Nose poke")
	water()

def check_buttons():
	while True:
		lever.when_pressed = lever_press
		poke.when_pressed = nose_poke
		time.sleep(0.1)  # Short delay to prevent CPU overload
#endregion

#region Routes
@app.route('/')
def homepage():
	return render_template('homepage.html')

@app.route('/testingpage')
def io_testing():
    return render_template('testingpage.html')

@app.route('/test_io', methods=['POST'])
def test_io():
	action = request.form.get('action')
	print(f"Button clicked: {action}")
	#TODO Add code to handle each action.
	if action == 'feed':
		feed()
	if action == 'water':
		water()
	if action == 'light':
		flash_light(24, 1, 0.5)
	if action == 'sound':
		play_sound(2, 1)
	if action == 'lever_press':
		lever_press()
	if action == 'nose_poke':
		nose_poke()

	return redirect(url_for('io_testing'))
#endregion

#region I/O

#Buttons
lever = Button(3)
poke = Button(6)
lever.when_pressed = lever_press
#LEDs

#endregion

# Run the app
if __name__ == '__main__':
	# Create and start the button checking thread
	# button_thread = threading.Thread(target=check_buttons, daemon=True)
	# button_thread.start()
		
	# Start the Flask app
	app.run(debug=True, use_reloader=False)

