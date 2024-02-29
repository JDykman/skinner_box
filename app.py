#from time import sleep
#import math
import csv
from flask import Flask, render_template, request, jsonify
from gpiozero import Button, LED, Buzzer
import RPi.GPIO as GPIO
from rpi_ws281x import ws, Color, Adafruit_NeoPixel
import board
import threading
import time
import datetime
import os
import pygame

app = Flask(__name__)
GPIO.setmode(GPIO.BCM)

pygame.mixer.init()

#region Classes
class NeoPixelController:
	def __init__(self, led_pin, led_count, pixel_order):
		if led_pin == 18:
			self.strip = Adafruit_NeoPixel(led_count, led_pin, 800000, 10, False, 255, 0, pixel_order)
			#self.strip = Adafruit_NeoPixel(LED_1_COUNT, LED_1_PIN, LED_1_FREQ_HZ,LED_1_DMA, LED_1_INVERT, LED_1_BRIGHTNESS,LED_1_CHANNEL, LED_1_STRIP)
			self.off_Color = Color(0,0,0)
		elif led_pin == 13:
			self.strip = Adafruit_NeoPixel(led_count, led_pin, 800000, 11, False, 255, 1, pixel_order)
			#self.strip = Adafruit_NeoPixel(LED_2_COUNT, LED_2_PIN, LED_2_FREQ_HZ,LED_2_DMA, LED_2_INVERT, LED_2_BRIGHTNESS,LED_2_CHANNEL, LED_2_STRIP)
			self.off_Color = Color(0,0,0,0)
		else:
			print("Invalid pin selected")
		self.count = led_count
		self.colors = [None] * led_count
		self.strip.begin()
		#self.off()

		
	def set_color(self, r, g, b, w=None):
		self.color = (r, g, b, w) if w is not None else (r, g, b)
		self.Color = Color(r, g, b, w) if w is not None else Color(r, g, b)
		
	def set_off_color(self, r, g, b, w=None):
		self.off_color = (r, g, b, w) if w is not None else (r, g, b)
		self.off_Color = Color(r, g, b, w) if w is not None else Color(r, g, b)

	def on(self, i=None, color=None):
		if color is None:
			color = self.Color
		#print(i)
		#print(type(i))
		#print(color)
		#print(type(color))
		if i is None:
			#print("I'm trying to fill")
			for j in range(self.count):
				self.strip.setPixelColor(j, color)
			self.colors = [color] * self.count
		else:
			#print("I'm trying to write a single color")
			self.strip.setPixelColor(i, color)
			self.colors[i] = color
		self.update()

	def off(self, i=None, color=None):
		if color is None:
			color = self.off_Color
		if i is None:
			for j in range(self.count):
				self.strip.setPixelColor(j, color)
			self.colors = [color] * self.count
		else:
			self.strip.setPixelColor(i, color)
			self.colors[i] = color
		self.update()
		
	def pulse_on(self, duration, i=None, color=None):
		self.on(i,color)
		threading.Timer(duration, self.off, [i]).start()

	def update(self):
		self.strip.show()
		time.sleep(0.01)
		
	def get_led_color(self, i):
		return self.colors[i]
		
class StepperMotorController:
	def __init__(self, step_pin, direction_pin=None, steps_per_rotation=200, default_direction=GPIO.HIGH, water_calibration=20, water_speed=20, water_amount=1):
		self.step_pin = step_pin
		self.direction_pin = direction_pin
		self.steps_per_rotation = steps_per_rotation
		self.default_direction = default_direction
		self.water_calibration = water_calibration
		self.water_amount = water_amount
		self.water_speed = water_speed
		self.is_motor_running = False  # Variable to track motor status
		self.setup_pins()
		self.set_direction(default_direction)  # Set default direction


	def setup_pins(self):
		GPIO.setup(self.step_pin, GPIO.OUT)
		if self.direction_pin is not None:
			GPIO.setup(self.direction_pin, GPIO.OUT)
	
	def set_default_direction(self, default_direction):
		self.default_direction = default_direction

	def set_water_calibration(self, water_calibration):
		self.water_calibration = water_calibration

	def set_water_speed(self, water_speed):
		self.water_speed = water_speed

	def set_water_amount(self, water_amount):
		self.water_amount = water_amount
		
	def set_direction(self, direction):
		if self.direction_pin is not None:
			GPIO.output(self.direction_pin, direction)

	def step(self, steps, delay):
		if steps < 0:
			self.set_direction(self.default_direction ^ 1)  # Toggle direction if steps < 0
			steps = -steps
		else:
			self.set_direction(self.default_direction)

		for _ in range(steps):
			GPIO.output(self.step_pin, GPIO.HIGH)
			time.sleep(delay)
			GPIO.output(self.step_pin, GPIO.LOW)
			time.sleep(delay)

	def move_degrees(self, degrees, rpm):
		steps = int(degrees * self.steps_per_rotation / 360)
		delay = 30.0 / (self.steps_per_rotation * rpm)
		self.step(steps, delay)
	
	def dispense_water(self,water_amount=None, water_speed=None):
		if water_amount is None:
			water_amount = self.water_amount
		if water_speed is None:
			water_speed = self.water_speed
		self.move_degrees(water_amount*self.water_calibration, water_speed)
		
	def on(self, water_speed=None):
		print("Motor Start")
		if water_speed is None:
			water_speed = self.water_speed
		if not self.is_motor_running:
			self.is_motor_running = True
			#while self.is_motor_running:
			#	GPIO.output(self.step_pin, GPIO.HIGH)
			#	time.sleep(30.0 / (self.steps_per_rotation * water_speed))
			#	GPIO.output(self.step_pin, GPIO.LOW)
			#	time.sleep(30.0 / (self.steps_per_rotation * water_speed))
			#	if not self.is_motor_running:
			#		break

	def off(self):
		print("Motor Stop")
		self.is_motor_running = False
		time.sleep(0.1)  # Delay to allow for the motor to stop gracefully
#endregion
	
#region I/O
#GPIO0(EEPROM Data)
#GPIO1(EEPROM Clock)

#GPIO2(I2C Data)  - Pin 3 (Fixed pullup)
#GPIO3(I2C Clock) - Pin 5 (Fixed pullup)
#GPIO14(TXD)	  - Pin 8
#GPIO15(RXD)	  - Pin 10 
#GPIO4			- Pin 7  *Used by water Motor
#GPIO17(CE11)	 - Pin 11
#GPIO18(CE01)~	- Pin 12 *Used by the Indicator Lights
#GPIO27		   - Pin 13 *Used by the Prime Water button
#GPIO22		   - Pin 15 *Used by the Trial button
#GPIO23		   - Pin 16 *Used by the Stimulus Button
#GPIO24		   - Pin 18 *Used by the Intereraction Button
#GPIO25		   - Pin 22 *Used by the Reward Button
#GPIO10(MOSI0)	- Pin 19 
#GPIO9(MISO0)	 - Pin 21
#GPIO11(SCLK0)	- Pin 23
#GPIO8(CE00)	  - Pin 24
#GPIO7(CE10)	  - Pin 26
#GPIO5			- Pin 29 *used by Lever
#GPIO6			- Pin 31 *used by Poke
#GPIO12~		  - Pin 32 *
#GPIO13~		  - Pin 33 *Used by the Stimulus Lights
#GPIO16(CE21)	 - Pin 36 *used by the old water motor
#GPIO19(MISO1)~   - Pin 35 * used by the old single stimulus light
#GPIO20(MOSI1)	- Pin 38
#GPIO21(SCLK1)	- Pin 40 *Used by Light Strips?

#GPIO26		   - Pin 37 ???? Not broken out by the shield ????

#buzzer = Buzzer(buzzer_pin)

old_water_motor_pin = 16

old_water_motor = LED(old_water_motor_pin)


SYSTEM_LIGHT = 15
LIGHT_LIGHT = 14
CAMERA_LIGHT = 13
TRIAL_LIGHT = 12
EXPERIMENT_LIGHT = 11
#EXPERIMENT_TWO_LIGHT = 10
LEFT_LED_STIMULUS_LIGHT = 10
RIGHT_LED_STIMULUS_LIGHT = 9
SOUND_STIMULUS_LIGHT = 8
LEVER_LIGHT = 7
NOSE_POKE_LIGHT = 6
LIGHT_BEAM_LIGHT = 5
WATER_REWARD_LIGHT = 4
FOOD_REWARD_LIGHT = 3

#STIMULUS_LIGHT = 10
#INTERACTION_LIGHT = 9
#REWARD_LIGHT = 8


LED_PIN0 = 18		# GPIO pin connected to the NeoPixels
LED_COUNT0 = 16	  # Number of NeoPixels
LED_PIXEL_ORDER0 = ws.WS2811_STRIP_GRB
indicatorStrip = NeoPixelController(LED_PIN0, LED_COUNT0, LED_PIXEL_ORDER0)
indicatorStrip.set_color(255,0,0)
indicatorStrip.set_off_color(0,0,0)
indicatorStrip.off()
indicatorStrip.on(SYSTEM_LIGHT)

LED_PIN1 = 13		# GPIO pin connected to the NeoPixels
LED_COUNT1 = 7	  # Number of NeoPixels
LED_PIXEL_ORDER1 = ws.SK6812_STRIP_GRBW
stimulusRing = NeoPixelController(LED_PIN1, LED_COUNT1, LED_PIXEL_ORDER1)
stimulusRing.set_color(0,255,255,255)
stimulusRing.set_off_color(0,0,0,0)
stimulusRing.off()


# LED_PIN2 = board.D21		# GPIO pin connected to the NeoPixels
# LED_COUNT2 = 16	  # Number of NeoPixels
# LED_PIXEL_ORDER2 = neopixel.GRBW
# lightStrip = NeoPixelController(LED_PIN2, LED_COUNT2, LED_PIXEL_ORDER2)
# lightStrip.set_color(255,0,0,0)
# lightStrip.set_off_color(0,0,0,0)
# lightStrip.off();

waterMotor = StepperMotorController(step_pin=4, direction_pin=None, steps_per_rotation=200)
#foodMotor = StepperMotorController(step_pin=STEP_PIN2, direction_pin=DIRECTION_PIN2, steps_per_rotation=200)
#waterMotor.start_motor(120)
#define the order of the indicator lights
# Define your pin numbers
lever_pin = 5
poke_pin = 6
#beam_pin = 
#buzzer_pin = 13
prime_water_button_pin = 27
start_trial_button_pin = 22
test_stimulus_button_pin = 23
test_interaction_button_pin = 24 
test_reward_button_pin = 25

lever = Button(lever_pin)
poke = Button(poke_pin)
#beam = Button(beam_pin)
prime_water_button = Button(prime_water_button_pin)
start_trial_button = Button(start_trial_button_pin, hold_time=5)
test_stimulus_button = Button(test_stimulus_button_pin)
test_interaction_button = Button(test_interaction_button_pin)
test_reward_button = Button(test_reward_button_pin)

#prime_water_button.when_pressed = waterMotor.on
#prime_water_button.when_released = waterMotor.off

prime_water_button.when_pressed = start_water
prime_water_button.when_released = stop_water

start_trial_button.when_pressed = start_trial
start_trial_button.when_held = end_trial

test_stimulus_button.when_pressed = test_stimulus_function
test_interaction_button.when_pressed = user_interaction_function
test_reward_button.when_pressed = test_reward_function

lever.when_pressed = lever_interaction_function
poke.when_pressed = poke_interaction_function
#beam.when_pressed = beam_interaction_function

#endregion
	
#region Filing
def find_config_file(file_name):
	config_file = None
	drives = []

	# Get all available drives
	if os.name == 'posix':
		drives = [os.path.join('/media', item) for item in os.listdir('/media') if os.path.ismount(os.path.join('/media', item))]
	elif os.name == 'nt':
		drives = [item for item in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f'{item}:')]

	# Search for the file in the root directory of each drive
	for drive in drives:
		search_path = os.path.join(drive, file_name)
		if os.path.isfile(search_path):
			config_file = search_path
			break

	return config_file

def read_config_file(file_path, default_config=None):
	config = {}
	# Read the config file
	with open(file_path, 'r') as csv_file:
		reader = csv.reader(csv_file)
		next(reader)  # Skip the header row
		# Iterate over each row in the file
		for row in reader:
			if len(row) >= 2:
				parameter = row[0].strip()
				value = row[1].strip()

				# Save the parameter and value to the config dictionary
				config[parameter] = value

	# Assign default values to missing parameters
	if default_config:
		for parameter, value in default_config.items():
			config.setdefault(parameter, value)

	return config
#endregion

#region Config
default_config = {
	'Tone': 'FALSE',
	'Tone Frequency': '100',
	'Light': 'FALSE',
	'Neopixel 1': 'FALSE',
	'Neopixel 1 Color': '(0, 0, 255)',
	'Neopixel 2': 'FALSE',
	'Neopixel 2 Color': '(0, 0, 255)',
	'Stimulus Duration': '0.5',
	'Poke': 'False',
	'Lever': 'False',
	'Light Beam': 'False',
	'Water': 'False',
	'Water Amount': '50',
	'Food': 'False',
	'Starting Goal': '1',
	'Goal Increment': '0',
	'Start Experiment End Delay': '5',
	'Experiment_End_Delay_Increment': '0',
	'Trial End Goal': '0',
	'Trial End Time': '0',
	'Trial End Water': '0',
	'Sound Address': '/home/pi/1000Hz_-6dBFS_1s.wav'
	# Add more default parameters and values as needed
}


# Define your variables
count = 0
lever_count = 0
poke_count = 0
beam_count = 0
count_goal = 0
first_count_time = 0
goal_time = 0
experiment = False
experiment_end_time = 0
experiment_end_delay = 0
total_water_amount = 0
trial = False
start_trial_time = 0
start_experiment_time = 0
experiment_number = 1
user_interactions = 0
is_second_experiment = False

# Define your functions

#Config Values:
starting_goal = 1
goal_increment = 0
trial_end_goal = 0
stimulus_duration = 1000
tone_frequency = 200
start_experiment_end_delay = 5
experiment_end_delay_increment = 0
trial_end_time = 0
water_amount = 0.035
trial_end_water = 0
second_experiment_bool = False
light_bool = False
tone_bool = True
neopixel1_bool = False
neopixel2_bool = False
poke_bool = True
lever_bool = False
beam_bool = False
water_bool = True
food_bool = False
light_bool2 = False
tone_bool2 = True
neopixel1_bool2 = False
neopixel2_bool2 = False
poke_bool2 = True
lever_bool2 = False
beam_bool2 = False
water_bool2 = True
food_bool2 = False
soundAddr = '/home/pi/1000Hz_-6dBFS_1s.wav'
sound = pygame.mixer.Sound(soundAddr) 

DEBUG = True

config = {}

def get_config_values_from_file():
	global starting_goal
	global goal_increment
	global trial_end_goal
	global stimulus_duration
	global tone_frequency
	global start_experiment_end_delay
	global experiment_end_delay_increment
	global trial_end_time
	global water_amount
	global trial_end_water
	global light_bool
	global tone_bool
	global neopixel1_bool
	global neopixel2_bool
	global poke_bool
	global lever_bool
	global beam_bool
	global water_bool
	global food_bool
	global config
	global soundAddr
	file_name = 'config.csv'  # Replace with the name of your config file
	config_file = find_config_file(file_name)
	default_config_file = '/home/pi/config.csv'
	if config_file:
		print(f"Config file found at: {config_file}")
		# Read the config file and process it further
		config = read_config_file(config_file, default_config)
	else:
		print("Using Default Config File")
		config = read_config_file(default_config_file, default_config)
	starting_goal = float(config['Starting Goal'])
	goal_increment = int(config['Goal Increment'])
	trial_end_goal = int(config['Trial End Goal'])
	stimulus_duration = float(config['Stimulus Duration'])
	tone_frequency = int(config['Tone Frequency'])
	start_experiment_end_delay = float(config['Start Experiment End Delay'])
	experiment_end_delay_increment = float(config['Experiment End Delay Increment'])
	trial_end_time = float(config['Trial End Time'])
	water_amount = float(config['Water Amount'])
	trial_end_water = float(config['Trial End Water'])
	light_value = config['Light']
	light_bool = light_value in ['TRUE', '1']

	tone_value = config['Tone']
	tone_bool = tone_value in ['TRUE', '1']

	neopixel1_value = config['Neopixel 1']
	neopixel1_bool = neopixel1_value in ['TRUE', '1']

	neopixel2_value = config['Neopixel 2']
	neopixel2_bool = neopixel2_value in ['TRUE', '1']

	poke_value = config['Poke']
	poke_bool = poke_value in ['TRUE', '1']

	lever_value = config['Lever']
	lever_bool = lever_value in ['TRUE', '1']
	
	beam_value = config['Light Beam']
	beam_bool = beam_value in ['TRUE', '1']
	
	water_value = config['Water']
	water_bool = water_value in ['TRUE', '1']
	
	food_value = config['Food']
	food_bool = food_value in ['TRUE', '1']
	
	soundAddr = config['Sound Address']

def save_config_to_csv(config, filepath):
	# Define the parameter names and values
	parameters = [
		('Tone', 'FALSE'),
		('Tone Frequency', '1000'),
		('Light', 'FALSE'),
		('Neopixel 1', 'TRUE'),
		('Neopixel 1 Color', '(0, 0, 255)'),
		('Neopixel 2', 'FALSE'),
		('Neopixel 2 Color', '(255, 0, 0)'),
		('Stimulus Duration', '0.5'),
		('Poke', 'FALSE'),
		('Lever', 'TRUE'),
		('Light Beam', 'FALSE'),
		('Water', 'TRUE'),
		('Water Amount', '50'),
		('Food', 'FALSE'),
		('Starting Goal', '1'),
		('Goal Increment', '0'),
		('Start Experiment End Delay', '20'),
		('Experiment End Delay Increment', '0'),
		('Trial End Goal', '0'),
		('Trial End Time', '0'),
		('Trial End Water', '0'),
		('Sound Address', '/home/pi/1000Hz_-6dBFS_1s.wav')
	]

	# Update the parameter values based on the provided config
	parameters_dict = dict(parameters)
	parameters_dict['Tone'] = str(config['Tone']).upper()
	parameters_dict['Tone Frequency'] = str(config['Tone Frequency'])
	parameters_dict['Light'] = str(config['Light']).upper()
	parameters_dict['Neopixel 1'] = str(config['Neopixel 1']).upper()
	parameters_dict['Neopixel 1 Color'] = str(config['Neopixel 1 Color'])
	parameters_dict['Neopixel 2'] = str(config['Neopixel 2']).upper()
	parameters_dict['Neopixel 2 Color'] = str(config['Neopixel 2 Color'])
	parameters_dict['Stimulus Duration'] = str(config['Stimulus Duration'])
	parameters_dict['Poke'] = str(config['Poke']).upper()
	parameters_dict['Lever'] = str(config['Lever']).upper()
	parameters_dict['Light Beam'] = str(config['Light Beam']).upper()
	parameters_dict['Water'] = str(config['Water']).upper()
	parameters_dict['Water Amount'] = str(config['Water Amount'])
	parameters_dict['Food'] = str(config['Food']).upper()
	parameters_dict['Starting Goal'] = str(config['Starting Goal'])
	parameters_dict['Goal Increment'] = str(config['Goal Increment'])
	parameters_dict['Start Experiment End Delay'] = str(config['Start Experiment End Delay'])
	parameters_dict['Experiment End Delay Increment'] = str(config['Experiment End Delay Increment'])
	parameters_dict['Trial End Goal'] = str(config['Trial End Goal'])
	parameters_dict['Trial End Time'] = str(config['Trial End Time'])
	parameters_dict['Trial End Water'] = str(config['Trial End Water'])
	parameters_dict['Sound Address'] = str(config['Sound Address'])

	# Save the parameters to the CSV file
	with open(filepath, 'w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(['Parameter', 'Parameter Value'])
		for parameter, value in parameters:
			writer.writerow([parameter, parameters_dict[parameter]])

def create_csv_if_not_exists(directory, header_row):
	filepath = os.path.join(directory, 'data.csv')
	if not os.path.exists(filepath):
		with open(filepath, 'w', newline='') as csvfile:
			writer = csv.writer(csvfile)
			writer.writerow(header_row)
		print(f"Created new CSV file at {filepath}")
	else:
		print(f"CSV file already exists at {filepath}")
		
data_header = ['Trial Start Time', 'Experiment Number', 'Experiment Start', 'Count Goal', 'Latency', 'Goal Time', 'User Interactions', 'Lever Count', 'Poke Count', 'Total Count', 'Total Experiment Time']

def append_row_to_csv(directory, data_row):
	filepath = os.path.join(directory, 'data.csv')
	if os.path.exists(filepath):
		with open(filepath, 'a', newline='') as csvfile:
			writer = csv.writer(csvfile)
			writer.writerow(data_row)
		print(f"Data appended to CSV file at {filepath}")
	else:
		print(f"CSV file does not exist at {filepath}")
#endregion

#region Functions
def start_trial(channel):
	global user_interactions
	global count_goal
	global starting_goal
	global total_water_amount
	global start_experiment_end_delay
	global experiment_end_delay
	global indicatorStrip
	#indicatorStrip.on(1)
	global TRIAL_LIGHT
	global trial
	global DEBUG
	global start_trial_time 
	global data_header
	global experiment_number
	global soundAddr
	global sound
	if DEBUG:
		if trial:
			print("Trial Already Started")
		else:
			print("Start Trial")
	if not trial:
		sound = pygame.mixer.Sound(soundAddr) 
		#get_config_values_from_file()
		create_csv_if_not_exists('/home/pi', data_header)
		#print(TRIAL_LIGHT)
		indicatorStrip.on(TRIAL_LIGHT)
		user_interactions = 0
		count_goal = starting_goal
		total_water_amount = 0
		start_trial_time = time.time()
		experiment_end_delay = start_experiment_end_delay
		experiment_number = 1
		trial = True
		start_experiment()

def start_experiment():
	global experiment
	global DEBUG
	global EXPERIMENT_LIGHT
	global indicatorStrip
	global count
	global start_experiment_time
	global user_interactions
	global is_second_experiment
	if DEBUG:
		if experiment:
			print("Experiment already Started")
		else:
			print("Start Experiment")
	if not experiment:
		start_experiment_time = time.time()
		experiment = True
		count = 0
		user_interactions=0
		if not is_second_experiment:
			indicatorStrip.on(EXPERIMENT_LIGHT)
		stimulus_function()


def test_stimulus_function(channel):
	global DEBUG
	if DEBUG:
		print("Test Stimulus")
		#print(channel)
	stimulus_function(True)

def stimulus_function(override=False):
	global DEBUG
	global experiment
	global STIMULUS_LIGHT
	global light_bool
	global old_stimulus_light
	global stimulus_duration
	global tone_bool
	global tone_bool2
	global light_bool2
	global sound
	global is_second_experiment
	if DEBUG:
		if experiment:
			print("Stimulus")
		elif override:
			print("Stimulus Override")
		else:
			print("No stimulus as no function")
	#indicatorStrip.pulse_on(0.5,STIMULUS_LIGHT)
	if (experiment or override) and not is_second_experiment:
		if light_bool:
			indicatorStrip.pulse_on(0.5,RIGHT_LED_STIMULUS_LIGHT)
			time.sleep(0.005)
			stimulusRing.pulse_on(1)
			time.sleep(0.005)
		if tone_bool:
			#print("Sound Stimulus")
			indicatorStrip.pulse_on(0.5,SOUND_STIMULUS_LIGHT)
			sound.play()
	if (experiment or override) and is_second_experiment:
		if light_bool2:
			indicatorStrip.pulse_on(0.5,RIGHT_LED_STIMULUS_LIGHT)
			time.sleep(0.005)
			stimulusRing.pulse_on(1)
			time.sleep(0.005)
		if tone_bool2:
			indicatorStrip.pulse_on(0.5,SOUND_STIMULUS_LIGHT)
			print("Sound Stimulus")
			sound.play()

def user_interaction_function(channel):
	global DEBUG
	global user_interactions
	if DEBUG:
		print("User Interaction")
		#print(channel)
	user_interactions += 1
	interaction_function(channel)

def lever_interaction_function(channel):
	global lever_bool
	global lever_count
	global lever_bool2
	global indicatorStrip
	global is_second_experiment
	lever_count += 1
	indicatorStrip.pulse_on(0.5,LEVER_LIGHT)
	if lever_bool and not is_second_experiment:
		interaction_function(channel)
	if lever_bool2 and is_second_experiment:
		interaction_function(channel)
		
def poke_interaction_function(channel):
	global poke_bool
	global poke_count
	global poke_bool2
	global indicatorStrip
	global is_second_experiment
	poke_count += 1
	indicatorStrip.pulse_on(0.5,NOSE_POKE_LIGHT)
	if poke_bool and not is_second_experiment:
		interaction_function(channel)
	if poke_bool2 and is_second_experiment:
		interaction_function(channel)
		
def beam_interaction_function(channel):
	global beam_bool
	global beam_count
	global beam_bool2
	global indicatorStrip
	global is_second_experiment
	beam_count += 1
	indicatorStrip.pulse_on(0.5,LIGHT_BEAM_LIGHT)
	if beam_bool and not is_second_experiment:
		interaction_function(channel)
	if beam_bool2 and is_second_experiment:
		interaction_function(channel)
		
		

def interaction_function(channel):
	global count
	global first_count_time
	global count_goal
	global goal_time
	global indicatorStrip
	global INTERACTION_LIGHT
	global DEBUG
	global experiment
	global start_experiment_time
	if DEBUG:
		if experiment:
			print("Interaction")
		else:
			print("Interaction but no Experiment")
	#indicatorStrip.pulse_on(0.5,INTERACTION_LIGHT)
	if experiment:
		count += 1
		print(f'Count: {count}')
		if count == 1:
			first_count_time = time.time() - start_experiment_time
		if count == count_goal:
			goal_time = time.time() - start_experiment_time
			print(f'Goal Time: {goal_time}')
			goal()
		
def goal():
	global goal_time
	global experiment_end_delay
	global experiment_end_delay_increment
	global DEBUG
	global experiment
	global start_experiment_time
	if DEBUG:
		if experiment:
			print("Goal")
		else:
			print("No Goal as No Experiment")
	if experiment:
		goal_time = time.time() - start_experiment_time
		threading.Timer(experiment_end_delay, end_experiment).start()
		reward_function(False)
#endregion 

#region Rewarding
def test_reward_function(channel):
	global DEBUG
	if DEBUG:
		print("Test Reward")
		#print(channel)
	reward_function(True)

def reward_function(override=False):
	global total_water_amount
	global indicatorStrip
	global REWARD_LIGHT
	global DEBUG
	global experiment
	global experiment_end_delay
	global water_bool
	global old_water_motor
	global water_amount
	if DEBUG:
		if experiment:
			print("Reward")
		elif override:
			print("Reward as no experiment condition is overridden")
		else: 
			print("No Reward")
	if experiment or override:
		#indicatorStrip.pulse_on(0.5,REWARD_LIGHT)
		total_water_amount += water_amount
		if water_bool:
			indicatorStrip.pulse_on(0.5,WATER_REWARD_LIGHT)
			old_water_motor.blink(on_time=water_amount, off_time=1, n=1, background=True)
		# Add your reward delivery code here
#endregion	

#region End Expiriment and Trial
def end_experiment():
	global experiment
	global count_goal
	global goal_increment
	global indicatorStrip
	global EXPERIMENT_LIGHT
	global experiment_end_delay
	global experiment_end_delay_increment
	global DEBUG
	global experiment_number
	global first_count_time
	global count
	global lever_count
	global poke_count
	global is_second_experiment
	if DEBUG:
		if experiment:
			print("End Experiment")
		else:
			print("Experiment not Running")
	if experiment:
		is_second_experiment = not is_second_experiment
		indicatorStrip.off(EXPERIMENT_LIGHT)
		data = [
		datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Trial Start Time
		experiment_number,  # Experiment Number
		start_experiment_time-start_trial_time,  # Experiment Start (mm:ss)
		count_goal,  # Count Goal
		first_count_time,  # Latency (Seconds)
		goal_time,  # Goal Time
		user_interactions,  # User Interactions
		lever_count,
		poke_count,
		count,  # Total Count
		time.time()-start_experiment_time  # Total Experiment Time
		]
		append_row_to_csv('/home/pi', data)
		experiment = False
		if trial:
			count_goal += goal_increment
			experiment_end_delay += experiment_end_delay_increment
			experiment_number += 1
			start_experiment()

def end_trial():
	global trial
	global DEBUG
	global TRIAL_LIGHT
	global config
	if DEBUG:
		if trial:
			print("End Trial")
		else:
			print("Trial not Running")
	if trial:
		save_config_to_csv(config, '/home/pi/current_config.csv')
		indicatorStrip.off(TRIAL_LIGHT)
		trial = False
		if experiment:
			end_experiment()
#endregion

#region Water
def start_water(channel):

	print("Start Water")
	old_water_motor.on()
	
def stop_water(channel):
	print("Stop Water")
	old_water_motor.off()
#endregion 

#region Lighting
def updateLights():
	#stimulusRing.update()
	indicatorStrip.update()
	threading.Timer(.5, updateLights).start()

threading.Timer(.5, updateLights).start()

#endregion

#GPIO.setup(prime_water_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#GPIO.add_event_detect(prime_water_button_pin, GPIO.FALLING, callback=waterMotor.start_motor, bouncetime=1000)
@app.route('/')
def index():
	return render_template('index.html')

# Define a route for the controller page
@app.route('/controller')
def controller():
	return render_template('controller.html')

@app.route('/update_led_colors', methods=['POST'])
def update_led_colors():
	led_colors = []
	for i in range(16):
		color = indicatorStrip.get_led_color(i)
		led_colors.append(color)

	# Return the LED colors as a JSON response
	return jsonify({'success': True, 'led_colors': led_colors})

@app.route('/debug_data')
def debug_data():
	poke_state = GPIO.input(poke_pin)
	lever_state = GPIO.input(lever_pin)
	beam_state = GPIO.input(beam_pin)
	data = {
		'poke_state': poke_state,
		'lever_state': lever_state,
		'beam_state': beam_state,
		'count': count,
		'count_goal': count_goal,
		'first_count_time': first_count_time,
		'goal_time': goal_time,
		'experiment_end_time': experiment_end_time,
		'experiment_end_delay': experiment_end_delay,
		'total_water_amount': total_water_amount
	}
	return jsonify(data)

# Define a route to execute server-side functions
@app.route('/execute_function', methods=['POST'])
def execute_function():
	data = request.json
	button_id = data['buttonId']
	action = data['action']

	# Perform the desired actions based on the button ID and action
	if button_id == 'start_trial':
		if action == 'press':
			start_trial()
			pass
		elif action == 'release':
			# Perform power button release action
			# ...
			pass
	elif button_id == 'prime_water':
		if action == 'press':
			# Perform prime water button press action
			# ...
			pass
		elif action == 'release':
			# Perform prime water button release action
			# ...
			pass
	# Handle other buttons and actions similarly

	# Return a success response
	return jsonify({'success': True})
	
	
@app.route('/test_output', methods=['POST'])
def test_output():
	output = request.form.get('output')
	# Add your code to test the specified output here
	return 'OK'

if __name__ == '__main__':
	#app.run(host='0.0.0.0', port=80, debug=True)
	app.run()
