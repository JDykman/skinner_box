# app/routes.py
import csv
import os
from flask import render_template, request, jsonify, redirect, send_file, send_from_directory, url_for
from app import app, config, gpio
from app.database import get_db_connection
from app.trial_state_machine import TrialStateMachine
from skinnerBox import list_log_files, load_settings, save_settings
from werkzeug.utils import secure_filename, safe_join
from openpyxl import Workbook

settings_path = config.settings_path
log_directory = config.log_directory
temp_directory = config.temp_directory
trial_state_machine = TrialStateMachine()

@app.route('/push_data', methods=['POST'])
def push_data():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO your_table (column1, column2)
            VALUES (%s, %s)
        """, (data['column1'], data['column2']))
        conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/pull_data', methods=['GET'])
def pull_data(table, condition):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM {table} WHERE {condition}")
        rows = cur.fetchall()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

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
        gpio.feed()
    if action == 'water':
        gpio.water()
    if action == 'light':
        gpio.flashLightStim((255, 255, 255)) #TODO Change to settings color
    if action == 'sound':
        gpio.play_sound(1)
    if action == 'lever_press':
        if trial_state_machine != None: gpio.lever_press(trial_state_machine)
        #TODO Put log interaction - manual
    if action == 'nose_poke':
        gpio.nose_poke()
    if action == 'nose_poke':
        if trial_state_machine != None: gpio.nose_poke(trial_state_machine)
        #TODO Put log interaction - manual
    return redirect(url_for('io_testing'))

@app.route('/trial', methods=['POST'])
def trial():
	settings = load_settings()  # Load settings
	if(trial_state_machine.state == 'running'):
		return render_template('runningtrialpage.html', settings=settings) #TODO change to trialpage
	else:
		settings = load_settings()  # Load settings
		# Perform operations based on settings...
		return render_template('trialsettingspage.html', settings=settings) #TODO change to trialsettings

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
        return render_template('trialsettingspage.html', settings=settings)

@app.route('/stop', methods=['POST'])
def stop(): # Stops the trial
    if trial_state_machine.stop_trial():
        return redirect(url_for('trial_settings'))
    return redirect(url_for('trial_settings'))

@app.route('/trial-settings', methods=['GET'])
def trial_settings(): # Displays the trial settings with the settings loaded from the file
    settings = load_settings()
    return render_template('trialsettingspage.html', settings=settings)

@app.route('/update-trial-settings', methods=['POST'])
def update_trial_settings(): # Updates the trial settings with the form data
    settings = load_settings()
    for key in request.form:
        settings[key] = request.form[key]
    save_settings(settings)
    return redirect(url_for('trial_settings'))

@app.route('/trial-status')
def trial_status(): # Returns the current status of the trial
    global trial_state_machine
    try:
        # This returns the real-time values of countdown and current iteration
        trial_status = {
            'timeRemaining': trial_state_machine.timeRemaining,
            'currentIteration': trial_state_machine.currentIteration
        }
        print (trial_state_machine.timeRemaining)
        return jsonify(trial_status)
    except:
        return

@app.route('/log-viewer', methods=['GET', 'POST'])
def log_viewer(): # Displays the log files in the log directory
    log_files = list_log_files()  # Assume this function returns the list of log file names.
    return render_template('logpage.html', log_files=log_files)

@app.route('/download-raw-log/<filename>')
def download_raw_log_file(filename): # Download the raw log file
    filename = secure_filename(filename)  # Sanitize the filename
    try:
        return send_from_directory(directory=log_directory, path=filename, as_attachment=True, download_name=filename)
    except FileNotFoundError:
        return "Log file not found.", 404

@app.route('/download-excel-log/<filename>')
def download_excel_log_file(filename): # Download the Excel log file
    # Use safe_join to ensure the filename is secure
    secure_filename = safe_join(log_directory, filename)
    try:
        # Initialize a workbook and select the active worksheet
        wb = Workbook()
        ws = wb.active
        if not os.path.exists(temp_directory):
            os.makedirs(temp_directory)
        
        # Define your column titles here
        column_titles = ['Date/Time', 'Total Time', 'Total Interactions', '', 'Entry', 'Interaction Time', 'Type', 'Reward', 'Interactions Between', 'Time Between']
        ws.append(column_titles)
        # Check if the file exists and is a CSV file
        if not os.path.isfile(secure_filename) or not filename.endswith('.csv'):
            print(f'CSV file not found or incorrect file type: {secure_filename}')
            return "Log file not found.", 404
        # Read the CSV file and append rows to the worksheet
        with open(secure_filename, mode='r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip the header of the CSV if it's already included
            for row in reader:
                ws.append(row)
        
        # Save the workbook to a temporary file
        temp_filename = f'{filename.rsplit(".", 1)[0]}.xlsx'
        temp_filepath = os.path.join(temp_directory, temp_filename)
        wb.save(temp_filepath)
        
        # Send the Excel file as an attachment
        return send_file(temp_filepath, as_attachment=True, download_name=temp_filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except FileNotFoundError:
        print(f'Excel file not found: {temp_filename}')
        return "Converted log file not found.", 404
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while processing the request.", 500

@app.route('/view-log/<filename>')
def view_log(filename): # View the log file in the browser
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
