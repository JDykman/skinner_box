# app/state_machine.py
import csv
import threading
import json
import os
import time
from app import gpio
from app.config import log_directory

class TrialStateMachine:
    """
    A state machine to manage the trial process in a behavioral experiment.
    Attributes:
        state (str): The current state of the trial.
        lock (threading.Lock): A lock to ensure thread safety.
        currentIteration (int): The current iteration of the trial.
        settings (dict): The settings loaded from a configuration file.
        startTime (float): The start time of the trial.
        interactable (bool): Whether the system is currently interactable.
        lastSuccessfulInteractTime (float): The time of the last successful interaction.
        lastStimulusTime (float): The time of the last stimulus.
        stimulusCooldownThread (threading.Timer): The thread handling stimulus cooldown.
        log_path (str): The path to the log file.
        interactions_between (int): The number of interactions between successful interactions.
        time_between (float): The time between successful interactions.
        total_interactions (int): The total number of interactions.
        total_time (float): The total time of the trial.
        interactions (list): A list of interactions during the trial.
    Methods:
        load_settings(): Loads settings from a configuration file.
        start_trial(): Starts the trial.
        pause_trial(): Pauses the trial.
        resume_trial(): Resumes the trial.
        stop_trial(): Stops the trial.
        run_trial(goal, duration): Runs the trial logic.
        lever_press(): Handles a lever press interaction.
        nose_poke(): Handles a nose poke interaction.
        queue_stimulus(): Queues a stimulus after a cooldown period.
        give_stimulus(): Gives a stimulus immediately.
        light_stimulus(): Handles the light stimulus.
        noise_stimulus(): Handles the noise stimulus.
        give_reward(): Gives a reward based on the settings.
        add_interaction(interaction_type, reward_given, interactions_between=0, time_between=''): Logs an interaction.
        push_log(): Writes the log to a file.
        finish_trial(): Finishes the trial and logs the results.
        error(): Handles errors and sets the state to 'Error'.
        pause_trial_logic(): Logic to pause the trial.
        resume_trial_logic(): Logic to resume the trial.
        handle_error(): Logic to handle errors.
    """
    def __init__(self):
        self.state = 'Idle'
        self.lock = threading.Lock()
        self.currentIteration = 0
        self.settings = {}
        self.startTime = None
        self.interactable = True
        self.lastSuccessfulInteractTime = None
        self.lastStimulusTime = 0.0
        self.stimulusCooldownThread = None
        self.log_path = log_directory
        self.interactions_between = 0
        self.time_between = 0.0
        self.total_interactions = 0
        self.total_time = 0
        self.interactions = []
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
            gpio.lever.when_pressed = self.lever_press
        elif(self.settings.get('interactionType') == 'poke'):
            gpio.poke.when_pressed = self.nose_poke

        while self.state == 'Running':
            self.timeRemaining = (duration - (time.time() - self.startTime)).__round__(2) #TODO Not working
            if (time.time() - self.lastStimulusTime) >= float(self.settings.get('cooldown', 0)) and self.interactable:
                print("No interaction in last 10s, Re-Stimming")
                self.give_stimulus()

            #Finish trial
            if self.currentIteration >= goal or self.timeRemaining <= 0:
                self.total_time = (time.time() - self.startTime).__round__(2)
                if self.interactable: #This is here to make sure it records the last interaction
                    #TODO Find a better way to do this ^^
                    self.finish_trial()
                    break
            time.sleep(.10)
            
    ## Interactions ##
    def lever_press(self):
        current_time = time.time()
        self.total_interactions += 1

        if self.state == 'Running' and self.interactable:
            # Calculate time between only if the last interaction was when interactable was True
            if self.lastSuccessfulInteractTime is not None:
                self.time_between = (current_time - self.lastSuccessfulInteractTime).__round__(2)
            else:
                self.time_between = 0  # Default for the first successful interaction

            self.interactable = False  # Disallow further interactions until reset
            self.currentIteration += 1
            self.give_reward()
            self.add_interaction("Lever Press", "Yes", self.interactions_between, self.time_between)
            self.lastSuccessfulInteractTime = current_time  # Update only on successful interaction when interactable
            self.interactions_between = 0
        else:
            self.add_interaction("Lever Press", "No", self.interactions_between, 0)
            self.interactions_between += 1

    def nose_poke(self):
        current_time = time.time()
        self.total_interactions += 1

        if self.state == 'Running' and self.interactable:
            if self.lastSuccessfulInteractTime is not None:
                self.time_between = (current_time - self.lastSuccessfulInteractTime).__round__(2)
            else:
                self.time_between = 0  # Default for the first successful interaction

            self.interactable = False
            self.currentIteration += 1
            self.give_reward()
            self.add_interaction("Nose poke", "Yes", self.interactions_between, self.time_between)
            self.lastSuccessfulInteractTime = current_time  # Update only on successful interaction when interactable
            self.interactions_between = 0
        else:
            self.add_interaction("Nose poke", "No", self.interactions_between, 0)
            self.interactions_between += 1

    ## Stimulus' ##
    def queue_stimulus(self): # Give after cooldown
        if(self.settings.get('stimulusType') == 'light' and self.interactable == False):
            self.stimulusCooldownThread = threading.Timer(float(self.settings.get('cooldown', 0)), self.light_stimulus)
            self.stimulusCooldownThread.start()
        elif(self.settings.get('stimulusType') == 'tone' and self.interactable == False):
            self.stimulusCooldownThread = threading.Timer(float(self.settings.get('cooldown', 0)), self.noise_stimulus)
            self.stimulusCooldownThread.start()

    def give_stimulus(self): #Give immediately
        if(self.settings.get('stimulusType') == 'light'):
            self.light_stimulus()
        elif(self.settings.get('stimulusType') == 'tone'):
            self.noise_stimulus()
        self.lastStimulusTime = time.time()  # Reset the timer after delivering the stimulus

    def light_stimulus(self):
        hex_color = self.settings.get('light-color')  # Html uses hexadecimal colors
        gpio.flashLightStim(hex_color)
        self.interactable = True
        self.lastStimulusTime = time.time()

    def noise_stimulus(self):
        if(self.interactable == False):
            #TODO Make noise
            self.interactable = True

    ## Reward ##
    def give_reward(self):
        if(self.settings.get('rewardType') == 'water'):
            gpio.water()
        elif(self.settings.get('rewardType') == 'food'):
            gpio.feed()
        self.queue_stimulus()

    ## Logging ##
    def add_interaction(self, interaction_type, reward_given, interactions_between=0, time_between=''):
        entry = self.total_interactions
        interaction_time = (time.time() - self.startTime).__round__(2)
        
        # Log the interaction
        self.interactions.append([entry, interaction_time, interaction_type, reward_given, interactions_between, time_between])

    def push_log(self):
        #TODO create log file
        with open(self.log_path, 'w', newline='') as file:
            writer = csv.writer(file)
            headers = ['Date/Time', 'Total Time', 'Total Interactions', '', 'Entry', 'Interaction Time', 'Type', 'Reward', 'Interactions Between', 'Time Between']
            writer.writerow(headers)
            # Write the date and time of the trial under the 'Date/Time' column
            for interaction in self.interactions:
                if interaction == self.interactions[0]:
                    writer.writerow([time.strftime("%m/%d/%Y %H:%M:%S"), self.total_time, self.total_interactions, '', interaction[0], interaction[1], interaction[2], interaction[3], interaction[4], interaction[5]])
                else:
                    writer.writerow(['', '', '', '', interaction[0], interaction[1], interaction[2], interaction[3], interaction[4], interaction[5]])

    def finish_trial(self):
        with self.lock:
            if self.state == 'Running':
                self.state = 'Completed'
                self.push_log()
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
