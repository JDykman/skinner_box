#!/usr/bin/env python3

from signal import pause
from openpyxl import Workbook
import pygame
from flask import Flask, Response, render_template, request, jsonify,  send_file, send_from_directory, url_for, redirect
from gpiozero import LED, Button, OutputDevice
import RPi.GPIO as GPIO
import json
import time
import threading
from picamera2 import Picamera2, Preview
from rpi_ws281x import Adafruit_NeoPixel, Color
import csv
import os
from werkzeug.utils import secure_filename, safe_join
import pandas as pd
import tempfile

app = Flask(__name__)
settings_path = 'config.json'
log_directory = '/home/jacob/Downloads/skinner_box-main/logs/'
# LED strip configuration:
LED_COUNT      = 60      # Number of LED pixels.
LED_PIN        = 12      # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)

# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)

try:
    strip.begin()
    print("Starting strip")
except:
    print("Error starting strip")
    pass

def list_log_files(_log_directory=log_directory):
    return [f for f in os.listdir(_log_directory) if os.path.isfile(os.path.join(_log_directory, f))]

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
lever = Button(lever_port, bounce_time=0.1)
poke = Button(nose_poke_port, pull_up=False, bounce_time=0.1)
water_primer = Button(water_primer_port, bounce_time=0.1)
manual_stimulus_button = Button(manual_stimulus_port, bounce_time=0.1)
manual_interaction = Button(manual_interaction_port, bounce_time=0.1)
manual_reward = Button(manual_reward_port, bounce_time=0.1)
start_trial_button = Button(start_trial_port, bounce_time=0.1)

#manual_stimulus_button.when_held
#manual_interaction.when_held()
#manual_reward.when_held()
#endregion


def start_motor():
    water_motor = OutputDevice(water_port, active_high=False, initial_value=False)
    print("Motor starting")  # Optional: for debugging
    water_motor.on()  # Start the motor
    water_primer.when_released = lambda: stop_motor(water_motor)

def stop_motor(motor):
    print("Motor stopping")  # Optional: for debugging
    motor.off()  # Stop the motor
    motor.close()


class TrialStateMachine:
    def __init__(self):
        self.state = 'Idle'
        self.lock = threading.Lock()
        self.currentIteration = 0
        self.settings = {}
        self.startTime = None
        self.interactable = True
        self.lastInteractTime = 0.0
        self.lastStimulusTime = 0.0
        self.stimulusCooldownThread = None
        self.log_path = '/home/jacob/Downloads/skinner_box-main/logs'
    def load_settings(self):
        # Implementation of loading settings from file
        try:
            with open('config.json', 'r') as file:
                self.settings = json.load(file)
        except FileNotFoundError:
            self.settings = {}
            
    def start_trial(self):
        with self.lock:
            if self.state == 'Idle':
                self.load_settings()
                goal = int(self.settings.get('goal', 0))
                duration = int(self.settings.get('duration', 0)) * 60
                self.timeRemaining = duration
                self.currentIteration = 0
                self.lastStimulusTime = time.time()  
                self.state = 'Running'
                # Format the current time to include date and time in the filename
                # YYYY_MM_DD_HH_MM_SS
                safe_time_str = time.strftime("%m_%d_%y_%H_%M_%S").replace(":", "_")
                # Update log_path to include the date and time
                self.log_path = f"/home/jacob/Downloads/skinner_box-main/logs/log_{safe_time_str}.csv"
                threading.Thread(target=self.run_trial, args=(goal, duration)).start()
                self.give_stimulus()
                return True
            return False

    def pause_trial(self):
        with self.lock:
            if self.state == 'Running':
                self.state = 'Paused'
                self.pause_trial_logic()
                return True
            return False

    def resume_trial(self):
        with self.lock:
            if self.state == 'Paused':
                self.state = 'Running'
                self.resume_trial_logic()
                return True
            return False

    def stop_trial(self):
        with self.lock:
            if self.state in ['Preparing', 'Running', 'Paused']:
                self.state = 'Idle'
                return True
            return False

    def run_trial(self, goal, duration):
        self.startTime = time.time()

        if(self.settings.get('interactionType') == 'lever'):
            lever.when_pressed = self.lever_press
        elif(self.settings.get('interactionType') == 'poke'):
            poke.when_pressed = self.nose_poke

        while self.state == 'Running':
            self.timeRemaining = (duration - (time.time() - self.startTime)).__round__(2)
            if (time.time() - self.lastStimulusTime) >= float(self.settings.get('cooldown', 0)) and self.interactable:
                print("No interaction in last 10s, Re-Stimming")
                self.give_stimulus()

            #Finish trial
            if self.currentIteration >= goal or self.timeRemaining <= 0:
                self.finish_trial()
                break
            time.sleep(.10)
            
    ## Interactions ##
    def lever_press(self):
        if self.state == 'Running':
            if self.interactable:
                self.interactable = False  # Disallow further interactions
                self.currentIteration += 1
                self.give_reward()
                log_interaction(self.log_path, round((time.time() - self.startTime), 2), "Lever Press", "Yes")
                return
        log_interaction(self.log_path, round((time.time() - self.startTime), 2), "Lever Press", "No")


    def nose_poke(self):
        print("Nose poke")
        if self.state == 'Running':
            if self.interactable == True:
                self.interactable = False
                self.currentIteration += 1
                self.lastInteractTime = time.time()
                self.give_reward()
                log_interaction(self.log_path, round((time.time() - self.startTime), 2), "Nose poke", "Yes")
                return
        log_interaction(self.log_path, round((time.time() - self.startTime), 2), "Nose poke", "No")

    ## Stimulus' ##
    def queue_stimulus(self): #give after cooldown
        if(self.settings.get('stimulusType') == 'light' and self.interactable == False):
            self.stimulusCooldownThread = threading.Timer(float(self.settings.get('cooldown', 0)), self.light_stimulus)
            self.stimulusCooldownThread.start()
        elif(self.settings.get('stimulusType') == 'tone' and self.interactable == False):
            self.stimulusCooldownThread = threading.Timer(float(self.settings.get('cooldown', 0)), self.noise_stimulus)
            self.stimulusCooldownThread.start()

    def give_stimulus(self): #Give Immedietly
        if(self.settings.get('stimulusType') == 'light'):
            self.light_stimulus()
        elif(self.settings.get('stimulusType') == 'tone'):
            self.noise_stimulus()
        self.lastStimulusTime = time.time()  # Reset the timer after delivering the stimulus

    def light_stimulus(self):
        if(strip):
            hex_color = self.settings.get('light-color') # Html uses hexadecimal colors
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:], 16) #So we convert it to rgb
            color = Color(r,g,b)
            flashLightStim(strip, color)
            self.interactable = True
            self.lastStimulusTime = time.time()

    def noise_stimulus(self):
        if(self.interactable == False):
            #TODO Make noise
            self.interactable = True

    ## Reward ##
    def give_reward(self):
        if(self.settings.get('rewardType') == 'water'):
            water()
        elif(self.settings.get('rewardType') == 'food'):
            feed()
        self.queue_stimulus()

    def finish_trial(self):
        with self.lock:
            if self.state == 'Running':
                self.state = 'Completed'
                print("Trial complete")
                return True
            return False
            
    def error(self):
        with self.lock:
            self.state = 'Error'
            self.handle_error()
            self.state = 'Idle'

    def pause_trial_logic(self):
        # TODO Code to pause trial
        pass

    def resume_trial_logic(self):
        # TODO Code to resume trial
        pass

    def handle_error(self):
        # TODO Code to handle errors
        pass


#region Action Functions
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
        time.sleep(.15) #TODO Adjust Water Time
        water_motor.off()
        water_motor.close()
    finally:
        return


def flashLightStim(strip, color, wait_ms=10):
    """Flash the light stimulus."""
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

def play_sound(pin, duration): #TODO
	print("Playing sound")
	#buzzer.on
	time.sleep(duration) # Wait a predetermained amount of time
	#buzzer.off

def lever_press():
    try:
        trial_state_machine.lever_press()
    except:
        pass
    feed()

def nose_poke():
    print("Nose poke")
    try:
        trial_state_machine.nose_poke()
    except:
        pass
    water()

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

def log_interaction(path, time, interaction_type, reward_given):
    """
    Logs an interaction to the CSV file.
    
    :param interaction_type: Type of interaction (Lever Press or Nose Poke).
    :param reward_given: Whether a reward was given (Yes or No).
    """
    # Determine the interaction number by reading the current file
    try:
        with open(path, mode='r', newline='') as file:
            reader = csv.reader(file)
            interaction_number = sum(1 for row in reader)  # Counts the existing rows for the next interaction number
    except FileNotFoundError:
        interaction_number = 1  # File doesn't exist, start from the first interaction

    # Data to log
    data = [interaction_number, time, interaction_type, reward_given]

    # Write data to the CSV file
    with open(path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)

def rename_log_files(_log_directory=log_directory):
    # Iterate over all files in the directory
    for filename in os.listdir(_log_directory):
        if ' ' in filename or ':' in filename:
            # Replace spaces and colons with underscores
            new_filename = filename.replace(' ', '_').replace(':', '_')
            # Construct the full old and new file paths
            old_file = os.path.join(_log_directory, filename)
            new_file = os.path.join(_log_directory, new_filename)
            # Rename the file
            os.rename(old_file, new_file)
            print(f'Renamed "{filename}" to "{new_filename}"')

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
		flashLightStim(strip, Color(255, 255, 255)) #TODO Change to settings

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
	if(trial_state_machine.state == 'running'):
		return render_template('runningtrialpage.html', settings=settings)
	
	else:
		settings = load_settings()  # Load settings
		# Perform operations based on settings...
		return render_template('trialpage.html', settings=settings)

@app.route('/start', methods=['POST'])
def start():
    global trial_state_machine
    settings = load_settings()  # Load settings
    if trial_state_machine.state == 'Running':
        return render_template('runningtrialpage.html', settings=settings)
    elif trial_state_machine.state == 'Idle':
        if trial_state_machine.start_trial():
            return render_template('runningtrialpage.html', settings=settings)
    elif trial_state_machine.state == 'Completed':
        trial_state_machine = TrialStateMachine()
        if trial_state_machine.start_trial():
            return render_template('runningtrialpage.html', settings=settings)
        return render_template('trialpage.html', settings=settings)

@app.route('/stop', methods=['POST'])
def stop():
    if trial_state_machine.stop_trial():
        return redirect(url_for('trial_settings'))
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
    global trial_state_machine
    try:
        # This should return the real-time values of countdown and current iteration
        trial_status = {
            'timeRemaining': trial_state_machine.timeRemaining,
            'currentIteration': trial_state_machine.currentIteration
        }
        return jsonify(trial_status)
    except:
        return
    
@app.route('/log-viewer', methods=['GET', 'POST'])
def log_viewer():
    log_files = list_log_files()  # Assume this function returns the list of log file names.
    return render_template('logpage.html', log_files=log_files)

@app.route('/download-raw-log/<filename>')
def download_raw_log_file(filename):
    filename = secure_filename(filename)  # Sanitize the filename
    try:
        return send_from_directory(directory=log_directory, path=filename, as_attachment=True, download_name=filename)
    except FileNotFoundError:
        return "Log file not found.", 404
@app.route('/download-excel-log/<filename>')
def download_excel_log_file(filename):
    secure_filename = safe_join(log_directory, filename)  # Ensure the path is secure
    try:
        # Initialize a workbook and select the active worksheet
        wb = Workbook()
        ws = wb.active
        
        # Define your column titles here
        column_titles = ['Entry', 'Time', 'Type', 'Reward']
        ws.append(column_titles)

        # Read the CSV file and append rows to the worksheet
        with open(secure_filename, mode='r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                ws.append(row)
        
        # Save the workbook to a temporary file
        temp_file = os.path.join('/home/jacob/Downloads/skinner_box-main/temp/', f'{filename.rsplit(".", 1)[0]}.xlsx')
        wb.save(temp_file)
        
        # Send the Excel file as an attachment
        return send_file(temp_file, as_attachment=True, download_name=f'{filename.rsplit(".", 1)[0]}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except FileNotFoundError:
        return "Log file not found.", 404
    
@app.route('/view-log/<filename>')
def view_log(filename):
    filename = secure_filename(filename)
    file_path = os.path.join(log_directory, filename)

    if os.path.isfile(file_path):
        with open(file_path, 'r') as file:
            log_content = file.readlines()

        # Create an HTML table with the log content
        rows = []
        for line in log_content:
            cells = line.strip().split(',')
            rows.append(cells)
            
        # Pass the rows to the template instead of directly returning HTML
        return render_template("t_logviewer.html", rows=rows)
    else:
        return "Log file not found.", 404
#endregion

# Run the app
if __name__ == '__main__':
    # Create a state machine
    trial_state_machine = TrialStateMachine()
    water_primer.when_pressed = start_motor
    start_trial_button.when_pressed = trial_state_machine.start_trial
    manual_interaction.when_pressed = water
    # Call the function to ensure naming is correct
    rename_log_files()
    # Start the Flask app
    app.run(debug=False, use_reloader=False, host='0.0.0.0')