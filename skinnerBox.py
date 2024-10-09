# skinnerBox.py
import json
from app import app
from app import config
from app.trial_state_machine import TrialStateMachine
from app.config import log_directory
import os
try:
    from app.gpio import water_primer, start_trial_button, manual_interaction, start_motor, water
except:
    print("Error setting up buttons")
    pass


#region Helper Functions
# Ensure log path exists
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

def list_log_files(_log_directory=log_directory):
    return [f for f in os.listdir(_log_directory) if os.path.isfile(os.path.join(_log_directory, f))]
#Settings and File Management
def load_settings():
    try:
        with open(config.settings_path, 'r') as file:
            settings = json.load(file)
    except FileNotFoundError:
        settings = {}
    return settings
def save_settings(settings):
	with open(config.settings_path, 'w') as file:
		json.dump(settings, file, indent=4)
#endregion

# Run the app
if __name__ == '__main__':
    # Create a state machine
    trial_state_machine = TrialStateMachine() # Create an instance of the TrialStateMachine class
    water_primer.when_pressed = start_motor # Start the motor when the water primer is pressed
    start_trial_button.when_pressed = trial_state_machine.start_trial # Start the trial when the start button is pressed
    manual_interaction.when_pressed = water # Water when the manual interaction button is pressed

    # Start the Flask app
    #TODO Get the IP address of the Pi and send it to the db for remote access
    os.system('hostname -I')
    # Run the app on the local network
    app.run(debug=False, use_reloader=False, host='0.0.0.0')