from signal import pause
import pygame
from flask import Flask, render_template, request, jsonify, url_for, redirect
from gpiozero import LED, Button, Buzzer 
import RPi.GPIO as GPIO
import json
import time
import threading
import board

app = Flask(__name__)
pygame.mixer.init()
settings_path = 'config.json'
trial_running = False
currentIteration = 0
timeRemaining = 0


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
	global currentIteration
	currentIteration += 1
	feed()

def nose_poke():
	print("Nose poke")
	global currentIteration
	currentIteration += 1
	water()

def check_buttons():
	while True:
		lever.when_pressed = lever_press
		poke.when_pressed = nose_poke
		time.sleep(0.1)  # Short delay to prevent CPU overload

def trialFunction():
	settings = load_settings()
	goal = int(settings['goal'])
	duration = int(settings['duration']) * 60
	global currentIteration 
	currentIteration = 0
	global timeRemaining
	timeRemaining = duration
	global trial_running
	#Start Timer
	startTime = time.time()
	while trial_running:
		#Update Variables
		timeRemaining = (duration - (time.time() - startTime)).__round__(2)
		#Check for inputs
		lever.when_pressed = lever_press
		if currentIteration >= goal:
			trial_running = False
			print("Trial complete")
			break
		time.sleep(.10)
	lever.when_pressed = None


#Settings and File Management
def load_settings():
    try:
        with open(settings_path, 'r') as file:
            settings = json.load(file)  # Fixed from settings_file.load(file)
    except FileNotFoundError:
        settings = {}
    return settings

def save_settings(settings):
    with open(settings_path, 'w') as file:
        json.dump(settings, file, indent=4)  # Fixed from settings_file.dump(settings, file, indent=4)

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

@app.route('/trial', methods=['POST'])
def trial():
    settings = load_settings()  # Load settings
    # Perform operations based on settings...
    return render_template('trialpage.html', settings=settings)

@app.route('/start-trial', methods=['POST'])
def start_trial():
	#TODO run trial function of dedicated thread
	settings = load_settings()  # Load settings
	global trial_running
	trial_running = True
	try:
		trial_thread.start()
	except:	
		pass

	return render_template('runningtrialpage.html', settings=settings)

@app.route('/trial-settings', methods=['GET'])
def trial_settings():
    settings = load_settings()
    return render_template('trialpage.html', settings=settings)

@app.route('/update-trial-settings', methods=['POST'])
def update_trial_settings():
    settings = load_settings()
    for key in request.form:
        settings[key] = request.form[key]
    save_settings(settings)
    return redirect(url_for('trial_settings'))
@app.route('/trial-status')
def trial_status():
    # This should return the real-time values of countdown and current iteration
    trial_status = {
		'timeRemaining': timeRemaining,
		'currentIteration': currentIteration
	}
    return jsonify(trial_status)
#endregion

#region I/O

#Buttons
lever = Button(3)
poke = Button(6)
#LEDs

#endregion

# Run the app
if __name__ == '__main__':
	# Create and start the button checking thread
	trial_thread = threading.Thread(target=trialFunction, daemon=True)
		
	# Start the Flask app
	app.run(debug=True, use_reloader=False)

