# run.py
import os
from app import app

if __name__ == '__main__':
    #Get the localhost and send it to the db for remote access
    os.system('hostname -I')
    

    # Run the app on the local network
    app.run(debug=False, use_reloader=False, host='0.0.0.0')