from signal import pause
import pygame
from flask import Flask, Response, render_template, request, jsonify, url_for, redirect
from gpiozero import LED, Button, OutputDevice
import RPi.GPIO as GPIO
import json
import time
import threading
from picamera2 import Picamera2, Preview
from rpi_ws281x import Adafruit_NeoPixel, Color
import io 

app = Flask(__name__)
pygame.mixer.init()
settings_path = 'config.json'
trial_running = False
currentIteration = 0
timeRemaining = 0
# LED strip configuration:
LED_COUNT      = 60      # Number of LED pixels.
LED_PIN        = 12      # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)

# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
# Intialize the library (must be called once before other functions).
strip.begin()
#region I/O

#Input Ports
lever_port = 17
nose_poke_port = 4
start_trial_port = None
water_primer_port = None
manual_stimulus_port = None
manual_interaction_port = None
manual_reward_port = None

#Output Ports
feeder_port = 3
water_port = 18
speaker_port = 13

#Button Settup
lever = Button(lever_port, bounce_time=0.1)
poke = Button(nose_poke_port, pull_up=False, bounce_time=0.1)

#endregion

#region Action Functions
def feed():
	try:
		feeder_motor = OutputDevice(feeder_port, active_high=False, initial_value=False)
		feeder_motor.on()
		time.sleep(1) #TODO Feed Time
		feeder_motor.off()
		feeder_motor.close()
	finally:
		return

def water():
	try:
		water_motor = OutputDevice(water_port, active_high=False, initial_value=False)
		water_motor.on()
		time.sleep(1) #TODO Water Time
		water_motor.off()
		water_motor.close()
	finally:
		return


def colorWipe(strip, color, wait_ms=50):
	"""Wipe color across display a pixel at a time."""
	for i in range(strip.numPixels()):
		strip.setPixelColor(i, color)
		strip.show()
		time.sleep(wait_ms/1000.0)

	for i in range(strip.numPixels()):
		strip.setPixelColor(i, Color(0,0,0))
		strip.show()
		time.sleep(wait_ms/1000.0)

def play_sound(pin, duration):
	print("Playing sound")
	buzzer = Buzzer(pin) #TODO should be a speaker I think
	buzzer.on 
	time.sleep(duration) # Wait a predetermained amount of time
	buzzer.off

def lever_press():
	print("Lever pressed")
	global currentIteration # Get the global variable
	currentIteration += 1 # Increment the variable
	feed()

def nose_poke():
	print("Nose poke")
	global currentIteration # Get the global variable
	currentIteration += 1 # Increment the variable
	water()

def trialFunction():
	#Load Settings
	settings = load_settings()
	goal = int(settings['goal'])
	duration = int(settings['duration']) * 60
	# Get global variables
	global currentIteration 
	global timeRemaining
	global trial_running
	#Set Variables
	timeRemaining = duration
	currentIteration = 0
	lever.when_pressed = lever_press
	poke.when_pressed = nose_poke
	#Start Timer
	startTime = time.time()
	while trial_running:
		timeRemaining = (duration - (time.time() - startTime)).__round__(2)	#Update Variable and round to the neares .00
		#Activate inputs
		lever.is_active = True
		poke.is_active = True
		if currentIteration >= goal:
			endTrialFunction()
			break
		time.sleep(.10)
	#Disable inputs
	lever.is_active = False
	poke.is_active = False

def endTrialFunction():
	global trial_running
	trial_running = False
	print("Trial complete")
	trial_thread.join()
	return
#Settings and File Management
def load_settings():
    try:
        with open(settings_path, 'r') as file:
            settings = json.load(file)
    except FileNotFoundError:
        settings = {}
    return settings

def save_settings(settings):
	with open(settings_path, 'w') as file:
		json.dump(settings, file, indent=4)

#Video Feed
def gen_frames():
    picam2 = Picamera2()
    picam2.start_preview()
    jpeg_encoder = JpegEncoder()
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}, encoder=jpeg_encoder))
    picam2.start()
    
    while True:
        stream = io.BytesIO()
        picam2.capture_file(stream)
        stream.seek(0)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + stream.read() + b'\r\n')
        stream.seek(0)
        stream.truncate()
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
		colorWipe(strip, Color(255, 0, 0))  # Red wipe

	if action == 'sound':
		play_sound(speaker_port, 1)
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

@app.route('/end-trial', methods=['POST'])
def end_trial():
	endTrialFunction()
	return redirect(url_for('trial_settings'))

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

@app.route('/video-feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
#endregion


# Run the app
if __name__ == '__main__':
	# Create and start the button checking thread
	trial_thread = threading.Thread(target=trialFunction, daemon=True)
		
	# Start the Flask app
	app.run(debug=True, use_reloader=False, host='0.0.0.0')

