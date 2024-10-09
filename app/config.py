# app/config.py
import os

# Get project folders directory
project_directory = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(project_directory, 'config.json')
log_directory = os.path.join(project_directory, 'logs/')
temp_directory = os.path.join(project_directory, 'temp/')

if not os.path.exists(log_directory):
    os.makedirs(log_directory)