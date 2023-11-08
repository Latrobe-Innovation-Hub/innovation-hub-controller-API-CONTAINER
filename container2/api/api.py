# Author -----=============================================================
# name: Andrew J. McDonald
# initial: 23/05/23
# current: 17/07/23
# =========================================================================

# DESCRIPTION =============================================================
# Basic implementation of Flask RESTful API to manage La Trobe Innovation
# Hub space devices remotely. The API provides endpoints to control and
# monitor various devices including lights, power outlets, projectors, etc.
# =========================================================================

# NOTES ======================================================================================================================================================
#  Windows OpenSSH requires psexec to interact with the user deskspace.
#       Install openSSH additional feature in windows settings.
#           1. In services, turn on ssh server and authentication and set both to start automatically
#
#       To get psexec to work:
#           1. User must have admin rights
#           2. In regedit, create a new registry HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system\LocalAccountTokenFilterPolicy and set it to 1
#           3. In regedit, disable UAC - set HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\EnableLUA to 0 
#
#           NOTE: any changes to regedit require reboot to take effect
#
#       Then commands such as will work:  psexec -accepteula -u username -p password -d -i 1 cmd
#           cmd: opens cmd prompt
#           -i 1: sets the interactive env to use, defaults to 0 when not set, 1 is the active user?
#           -d: Don’t wait for process to terminate (non-interactive).
#           -p: Specifies optional password for user name. If you omit this you will be prompted to enter a hidden password.
#           -u: Specifies optional user name for login to computer.
#           -accepteula: This flag suppresses the display of the license dialog.
#
#           see more options: https://adamtheautomator.com/psexec/
#
#   NirCmd tool is used for Windows system level control of audio devices, screensavers, displays, etc...
#       Download NirCmd at the bottom of that page, and place nircmd.exe and nircmdc.exe in C:\Windows\System32 directory
#       NirCmd can be found here: https://www.nirsoft.net/utils/nircmd.html
# ======================================================================================================================================================

import gevent
import gevent.monkey

# patch all the standard library modules
gevent.monkey.patch_all()

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS, cross_origin
import paramiko
import platform
import json
import re
import os
from pathlib import Path
import time

import api_config as conf

import logging
import sqlite3

## =================
## Configure Logging 
## =================

# build logger
logger = logging.getLogger()

# set stdout and file log handlers
handler_stdout = logging.StreamHandler()
handler_file = logging.FileHandler('/home/innovation-hub-api/persistent/logs/container2/gunicorn.log')

# set log format
formatter = logging.Formatter('%(asctime)s [PYTHON] [%(levelname)s] %(filename)s: %(message)s')

# add formatters
handler_stdout.setFormatter(formatter)
handler_file.setFormatter(formatter)

# add handlers
logger.addHandler(handler_stdout)
logger.addHandler(handler_file)

# get logging level from system environment variable
log_level = 'INFO'

# set logging level from system environment variable
if log_level == 'DEBUG':
    logger.setLevel(logging.DEBUG)
elif log_level == 'INFO':
    logger.setLevel(logging.INFO)
elif log_level == 'WARNING':
    logger.setLevel(logging.WARNING)
elif log_level == 'ERROR':
    logger.setLevel(logging.ERROR)
elif log_level == 'CRITICAL':
    logger.setLevel(logging.CRITICAL)
else:
    logger.setLevel(logging.INFO)

# Init API application
app = Flask(__name__)

# Allow CORS for all routes
CORS(app, supports_credentials=True)

# Allow CORS for all routes under '/pdu/'
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# =========================================================================
#  Functions
# =========================================================================

# to display applications on the remote windows machine, we need to know the session
# id for the in view desktop to interact with it.  We use qwinsta to obtain this id
def get_session_id(client, username):
    # Execute the qwinsta command to retrieve session information for the target user
    _, stdout, _ = client.exec_command(f'qwinsta {username}')

    # Process the output to extract the session ID
    session_id = None
    for line in stdout:
        if line.strip().startswith('console') and username in line:
            session_id = line.split()[2]
            break

    if session_id:
        return session_id
    else:
        return None

def run_get_session_id(hostname, username, password, target_username):
   # Create a new SSH client object
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)

            # Execute the qwinsta command to retrieve session information for the target user
            _, stdout, _ = client.exec_command(f'qwinsta {username}')

            # Process the output to extract the session ID
            session_id = None
            for line in stdout:
                if line.strip().startswith('console') and target_username in line:
                    session_id = line.split()[2]
                    break

            if session_id:
                return session_id
            else:
                return None

        except Exception as e:
            return {'error': str(e)}

# mute/unmute windows pc using nircmd
def run_mute_device(hostname, username, password, mute, platformInput=None):
    # Create a new SSH client object
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)

            # set if mute/unmute
            mute = 1 if str(mute).lower() == "true" else 0

            # Determine the operating system of the remote computer
            if platformInput.lower().strip() == 'windows' or platformInput.lower().strip() == 'win':
                # Use the nircmd command to mute/unmute the system volume on Windows
                command = f'nircmd mutesysvolume {mute}'
            elif platformInput.lower().strip() == 'mac':
                # Use the osascript command to mute/unmute the system volume on macOS
                command = f"osascript -e 'set volume {1 - mute}'"
            else: # wing it!
                # Use the amixer command to mute/unmute the system volume on Linux/Unix
                command = f"amixer -D pulse sset Master 'mute' {mute}"

            # Send mute/unmute command
            _, stdout, stderr = client.exec_command(command)

            # capture exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0: # THINK THIS WILL WORK???
                if mute == 1:
                    return f"mute command successful."
                if mute == 0:
                    return f"unmute command successful."
            else:
                return f"{mute} command failed with exit status: {exit_status}"

        except Exception as e:
            return {'error': str(e)}

# reboot pc using via ssh
def run_reboot_device(hostname, username, password, platformInput="windows"):
    # Create a new SSH client object
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)
            
            # Determine the operating system of the remote computer
            if platformInput.lower().strip() == 'windows' or platformInput.lower().strip() == 'win':
                command = 'shutdown /r /t 0'
            elif platformInput.lower().strip() == 'mac' or platformInput.lower().strip() == 'unix':
                command = 'sudo reboot now'
                
            # Send the reboot command
            _, stdout, stderr = client.exec_command(command)

            # capture exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0: # THINK THIS WILL WORK???
                return "Reboot command successful."
            else:
                return f"Reboot command failed with exit status: {exit_status}"

        except Exception as e:
            return {'error': str(e)}


def run_shutdown_device(hostname, username, password, platformInput="windows"):
    # Create a new SSH client object
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)
            
            # Determine the operating system of the remote computer
            if platformInput.lower().strip() == 'windows' or platformInput.lower().strip() == 'win':
                command = 'shutdown /s /f /t 0'
            elif platformInput.lower().strip() == 'mac' or platformInput.lower().strip() == 'unix':
                command = 'sudo shutdown now'
                
            # Send the shutdown command
            _, stdout, stderr = client.exec_command(command)

            # capture exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0: # THINK THIS WILL WORK???
                return "Shutdown command successful."
            else:
                return f"Shutdown command failed with exit status: {exit_status}"

        except Exception as e:
            return {'error': str(e)}

import re

def run_youtube_script(hostname, username, password, youtube_url, loop=None, captions=None):
    # Create an SSH client
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)
            session_id = get_session_id(client, username)

            if session_id:
                command_arg = fr"cmd /c python C:\Users\{username}\Documents\browser-youtube.py"
                command_full = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} {command_arg} "{youtube_url}"'
                logger.info(f"testing =  run_youtube_script, command: {command_full}")

                if loop:
                    command_full += " --loop"
                    logger.info(f"testing =  run_youtube_script, command: {command_full}")
                    
                if captions:
                    command_full += " --captions"
                    logger.info(f"testing =  run_youtube_script, command: {command_full}")
                    
                command_full += fr" > C:\Users\{username}\Documents\youtube-pid.txt"

                _, stdout, stderr = client.exec_command(command_full)

                # Retrieve the output and error of the command
                output = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')

                # Extract the PID from the error output
                pid_match = re.search(r"process ID (\d+)", error)
                
                # Read the contents of the output file
                with client.open_sftp().file(fr"C:\Users\{username}\Documents\youtube-pid.txt") as output_file:
                    output = output_file.read().decode('utf-8')
                    logger.info("open youtube text file and get pid: ", output)

                if output:
                    return output
                else:
                    return f"youtube script failure: pid was not found..."
            else:
                return f"No active session found for {username}."
        except Exception as e:
            return {'error': str(e), 'pid': None}

def run_youtube_script2(hostname, username, password, youtube_url, loop=None, captions=None):
    # Create an SSH client
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)
            session_id = get_session_id(client, username)

            if session_id:
                command_arg = fr"cmd /c python C:\Users\{username}\Documents\browser-youtube.py"
                command_full = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} {command_arg} "{youtube_url}"'
                logger.info(f"testing =  run_youtube_script, command: {command_full}")

                if loop:
                    command_full += " --loop"
                    logger.info(f"testing =  run_youtube_script, command: {command_full}")
                    
                if captions:
                    command_full += " --captions"
                    logger.info(f"testing =  run_youtube_script, command: {command_full}")
                    
                command_full += fr" > C:\Users\{username}\Documents\youtube-pid.txt"

                _, stdout, stderr = client.exec_command(command_full)

                # Retrieve the output and error of the command
                output = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')

                ## Extract the PID from the error output
                #pid_match = re.search(r"process ID (\d+)", error)
                
                # Attempt to read the contents of the output file, retrying if necessary
                #pid = None

                #max_retries=3
                #retry_delay=10

                # Initialize the variable to store the number
                #pid = None

                #for retry in range(max_retries):
                #    time.sleep(retry_delay)
                #    try:
                #        stdin, stdout, stderr = client.exec_command(fr'type C:\Users\{username}\Documents\youtube-pid.txt')

                #        for line in iter(stdout.readline, ""):
                #            line = line.strip()
                #            if pid is None:
                #                pid = line
                #                break

                #        if pid:
                #            logger.info("The final 'pid' is:", pid)
                #            return pid
                #        else:
                #            logger.info("No number found in any line.")
                #            return f"youtube script failure: pid was not found..."
                        
                #    except:
                #        pass

                #    finally:
                        # Close the SFTP session and the SSH connection
                client.close()
                return "youtube script started"

                #return "Maximum retries exceeded: youtube script failure"
            else:
                return f"No active session found for {username}."
        except Exception as e:
            return {'error': str(e), 'pid': None}

@app.route('/open_youtube/<string:room_code>/<string:host_address>', methods=['POST'])
def open_youtube(room_code, host_address):
    data = request.get_json()
    if not all(key in data for key in ['url', 'loop', 'captions']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username, password = host_data

    url = data.get('url')
    loop = data.get('loop')
    captions = data.get('captions')

    # Call the function with explicit parameters
    result = run_youtube_script2(
    	hostname=host_address,
    	username=username,
    	password=password,
    	youtube_url=url,
    	loop=True if loop and loop.lower() == "true" else None,
    	captions=True if captions and captions.lower() == "true" else None
    )

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/chrome_off/<string:room_code>/<string:host_address>', methods=['GET'])
def chrome_off(room_code, host_address):
    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data

    # Kill the process on the remote host using the retrieved credentials and the 'pid' from the URL
    result = kill_chrome(host_address, username, password)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

# open powerpoint slide file/url on remote windows pc in google chrome
def run_browser(hostname, username, password, url=None):
    # Create an SSH client
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)

            # Set Chrome browser application path
            #edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
            logger.info(f"the chrome location is: {chrome}")

            # Execute the qwinsta command to retrieve session information for the target user
            session_id = get_session_id(client, username)

            if session_id:
                # Build psexec command string to open chrome in kiosk mode, at url
                #command = f"psexec -accepteula -u {username} -p {password} -d -i {session_id} \"{chrome}\"  \"--kiosk --disable-pinch --no-user-gesture-required\" \"{url}\""
                #command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} {edge} --kiosk --edge-kiosk-type=fullscreen "{url}\"'
                #command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} \"{chrome}\" \"--kiosk --no-user-gesture-required\" \"{url}\"'
                command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} "{chrome}" --kiosk "{url}"'

                logger.info(f"the command sent is: {command}")

                logger.info(f"testing.... in run_browser, command: {command}")
                
                _, stdout, stderr = client.exec_command(command)

                # Retrieve the output of the command
                output = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')

                # Extract the PID from the error output
                pid_match = re.search(r"process ID (\d+)", error)
                
                if pid_match:
                    pid = pid_match.group(1)
                    return pid
                else:
                    return f"{output}, {error}"
            else:
                return f"No active session found for {username}."
        except Exception as e:
            return {'error': str(e)}

# close process running on remote windows pc
def kill_process(hostname, username, password, pid):
    # Create an SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)

            # Find the window ID of the "powerpoint-slide" window
            _, stdout, stderr = client.exec_command(f'taskkill /PID {pid} /F')

            # capture exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0: # THINK THIS WILL WORK???
                return f"process ended successfully."
            else:
                return f"process ending failed with exit status {exit_status}."

        except Exception as e:
            return {'error': str(e)}

# close process running on remote windows pc
def kill_chrome(hostname, username, password):
    # Create an SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)

            # Find the window ID of the "powerpoint-slide" windows
            _, stdout, stderr = client.exec_command(f'taskkill /IM chrome.exe /F')

            # capture exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0: # THINK THIS WILL WORK???
                return f"process ended successfully."
            else:
                return f"process ending failed with exit status {exit_status}."

        except Exception as e:
            return {'error': str(e)}

# simulate mouse press  (hide taskbar)
# psexec -accepteula -u admin -p admin -d -i 1 "C:\NirCmd\nircmd.exe" "sendmouse click X Y"
import paramiko
import re
import logging

# Create a logger instance
logger = logging.getLogger(__name__)

def sim_mouse_press(hostname, username, password):
    # Create an SSH client
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)
            
            # Execute the qwinsta command to retrieve session information for the target user
            session_id = get_session_id(client, username)

            # Set the path to NirCmd on the remote machine
            nircmd_path = r'C:\NirCmd\nircmd.exe'

            # screen location of click
            X = 50
            Y = 50

            # Build the PsExec command to simulate a mouse click (hide taskbar)
            command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} "{nircmd_path}" sendmouse click {X} {Y}'

            logger.info(f"Sending mouse press command: {command}")

            _, stdout, stderr = client.exec_command(command)

            # Retrieve the output of the command
            #output = stdout.read().decode('utf-8')
            output = stderr.read().decode('utf-8')
            
            return output
        except Exception as e:
            return {'error': str(e)}


def run_application(hostname, username, password, application=None, arguments=None):
     # Create an SSH client
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

   # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)
            
            # Execute the qwinsta command to retrieve session information for the target user
            session_id = get_session_id(client, username)
            
            if session_id:
                logger.info(f"testing.... in run_application, application command sent by request: {application}")
                
                command = None
                if arguments and video:
                    # If both arguments and video are present
                    command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} "{application}" {arguments}'
                elif video:
                    # If only video is present
                    command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} "{application}"'          
                
                if command:
                    logger.info(f"testing.... in run_application, command created in runn_application: {command}")
                    _, stdout, stderr = client.exec_command(command)

                    # Retrieve the output of the command
                    output = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    # Extract the PID from the error output
                    pid_match = re.search(r"process ID (\d+)", error)
                
                    if pid_match:
                        pid = pid_match.group(1)
                        return pid
                    else:
                        return f"{output}, {error}"
                else:
                    return f"No command was constructed to send to {hostname}."        
            else:
                return f"No active session found for {username}."

        except Exception as e:
            return {'error': str(e)}

# run a program on remote windows pc - NEED TO TEST
def run_vlc_application(hostname, username, password, application=None, arguments=None, video=None):
    # Create an SSH client
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

   # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)
            
            # Execute the qwinsta command to retrieve session information for the target user
            session_id = get_session_id(client, username)
            
            if session_id:
                logger.info(f"testing.... in run_application, application command sent by request: {application}")
                
                # Construct the VLC command with appropriate quotes based on the video_path
                if video.startswith(('http://', 'https://', 'ftp://')):
                    # It's a URL, so no need to surround it with quotes
                    video = f'{video}'
                else:
                    # It's a local file path, surround it with quotes
                    video = f'"{video}"'
                
                command = None
                if arguments and video:
                    # If both arguments and video are present
                    command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} "{application}" {arguments} {video}'
                elif video:
                    # If only video is present
                    command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} "{application}" {video}'                
                
                if command:
                    logger.info(f"testing.... in run_application, command created in runn_application: {command}")
                    _, stdout, stderr = client.exec_command(command)

                    # Retrieve the output of the command
                    output = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')

                    # Extract the PID from the error output
                    pid_match = re.search(r"process ID (\d+)", error)
                
                    if pid_match:
                        pid = pid_match.group(1)
                        return pid
                    else:
                        return f"{output}, {error}"
                else:
                    return f"No command was constructed to send to {hostname}."        
            else:
                return f"No active session found for {username}."

        except Exception as e:
            return {'error': str(e)}

# send nircmd commands to a remote PC
def run_nircmd(hostname, username, password, cmd):
    # Create a new SSH client object
    client = paramiko.SSHClient()

    # Automatically add the remote host key (not recommended for production use)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Use a context manager to ensure the client is closed when the function finishes
    with client:
        try:
            # Connect to the remote host
            client.connect(hostname, username=username, password=password)

            # Execute the qwinsta command to retrieve session information for the target user
            session_id = get_session_id(client, username)

            # Set the path to NirCmd on the remote machine
            nircmd_path = r'C:\NirCmd\nircmd.exe'

            # Build the PsExec command to simulate a mouse click (hide taskbar)
            command = f'psexec -accepteula -u {username} -p {password} -d -i {session_id} "{nircmd_path}" {cmd}'

            logger.info(f"Sending mouse press command: {command}")

            _, stdout, stderr = client.exec_command(command)

            output = stderr.read().decode('utf-8')
            
            return output
        except Exception as e:
            return {'error': str(e)}  

# single database init - need to test and integrate
# def init_db():
    # print("initialising the database...")
    # logger.info("testing.... IN init_db function.")
    # conn = sqlite3.connect('/home/innovation-hub-api/persistent/db/container2/IH_device_database.db')
    # cursor = conn.cursor()

    # print("initialising table rooms...")
    # logger.info("testing.... init_db, initialising table rooms..")
    # # Create a table for rooms
    # cursor.execute('''
        # CREATE TABLE IF NOT EXISTS rooms (
            # room_code TEXT PRIMARY KEY,
            # description TEXT
        # )
    # ''')
    
    # print("initialising table hosts...")
    # logger.info("testing.... init_db, initialising table hosts..")
    # # Create a table for hosts
    # cursor.execute('''
        # CREATE TABLE IF NOT EXISTS hosts (
            # host_address TEXT PRIMARY KEY,
            # host_mac TEXT,       
            # host_name TEXT,
            # description TEXT,
            # username TEXT,
            # password TEXT,
            # platform TEXT,
            # room_code TEXT,
            
            # config_default TEXT,
            # config_cisco TEXT,
            # config_optus TEXT,
            # FOREIGN KEY (room_code) REFERENCES rooms (room_code)
        # )
    # ''')

    # print("initialising table displays...")
    # logger.info("testing.... init_db, initialising table displays..")
    # # Create a table for displays
    # cursor.execute('''
        # CREATE TABLE IF NOT EXISTS displays (
            # display_address TEXT PRIMARY KEY,
            # display_mac TEXT,       
            # display_name TEXT,
            # display_type TEXT,
            # username TEXT,
            # password TEXT,
            # room_code TEXT,
            # FOREIGN KEY (room_code) REFERENCES rooms (room_code)
        # )
    # ''')
    
    # print("initialising table pdus...")
    # logger.info("testing.... init_db, initialising table pdus..")
    # # Create a table for pdus
    # cursor.execute('''
        # CREATE TABLE IF NOT EXISTS pdus (
            # pdu_address TEXT PRIMARY KEY,
            # pdu_mac TEXT,
            # username TEXT,
            # password TEXT,
            # driver_path TEXT,
            # room_code TEXT,
            # FOREIGN KEY (room_code) REFERENCES rooms (room_code)
        # )
    # ''')

    # logger.info("testing.... init_db, committting tables..")
    # try:
        # conn.commit()
        # logger.info("testing.... init_db, committting successful!")
    # except:
        # logger.info("testing.... init_db, committting failed!")
    # finally:
        # conn.close()


import mysql.connector

def init_db():
    print("initializing the database...")
    logger.info("testing.... IN init_db function.")

    # Establish a connection to your MySQL server.
    #conn = mysql.connector.connect(
    #    host='mysql',
    #    user='root',  # Use 'root' for the root user
    #    password='digital2023',
    #    database='innovation-hub-api-db'  # Specify the database name you want to connect to
    #)
    
    conn = get_db_connection()
    
    cursor = conn.cursor()

    print("initializing table rooms...")
    logger.info("testing.... init_db, initializing table rooms..")
    # Create a table for rooms
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_code VARCHAR(255) PRIMARY KEY,
            description TEXT
        )
    ''')

    print("initializing table hosts...")
    logger.info("testing.... init_db, initializing table hosts..")
    # Create a table for hosts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hosts (
            host_address VARCHAR(255) PRIMARY KEY,
            host_mac VARCHAR(255),
            host_name TEXT,
            description TEXT,
            username VARCHAR(255),
            password VARCHAR(255),
            platform TEXT,
            room_code VARCHAR(255),
            config_default TEXT,
            config_cisco TEXT,
            config_optus TEXT,
            FOREIGN KEY (room_code) REFERENCES rooms (room_code)
        )
    ''')

    print("initializing table displays...")
    logger.info("testing.... init_db, initializing table displays..")
    # Create a table for displays
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS displays (
            display_address VARCHAR(255) PRIMARY KEY,
            display_mac VARCHAR(255),
            display_name TEXT,
            display_type TEXT,
            username VARCHAR(255),
            password VARCHAR(255),
            room_code VARCHAR(255),
            FOREIGN KEY (room_code) REFERENCES rooms (room_code)
        )
    ''')

    print("initializing table pdus...")
    logger.info("testing.... init_db, initializing table pdus..")
    # Create a table for pdus
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdus (
            pdu_address VARCHAR(255) PRIMARY KEY,
            pdu_mac VARCHAR(255),
            username VARCHAR(255),
            password VARCHAR(255),
            driver_path TEXT,
            room_code VARCHAR(255),
            FOREIGN KEY (room_code) REFERENCES rooms (room_code)
        )
    ''')

    logger.info("testing.... init_db, committing tables..")
    conn.commit()
    logger.info("testing.... init_db, committing successful!")

    cursor.close()
    conn.close()


def get_db_connection():
    conn = mysql.connector.connect(
        host='mysql',
        user='root',  # Use 'root' for the root user
        password='digital2023',
        database='innovation-hub-api-db'  # Specify the database name you want to connect to
    )
    return conn

# # Route to get all hosts
@app.route('/get_hosts', methods=['GET'])
def get_hosts():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT host_address, host_mac, host_name, description, username, password, platform, room_code, config_default, config_cisco, config_optus FROM hosts WHERE room_code = %s", (room_code,))
    hosts = cursor.fetchall()
    conn.close()
    
    if len(hosts) < 1:
        return jsonify({'message': 'No hosts added yet. Please add a host first.'}), 200

    host_list = []
    for host in hosts:
        host_list.append({
            'host_id':          host[0], # host['host_address'],
            'host_mac' :        host[1], #host['host_mac'],
            'host_name':        host[2], #host['host_name'],
            'description':      host[3], #host['description'],
            'username':         host[4], #host['username'],
            'password':         host[5], #host['password'],
            'platform':         host[6], #host['platform'],
            'room_code':        host[7], #host['room_code']
            'config_default':   host[8],
            'config_cisco':     host[9],
            'config_optus':     host[10],
        })

    return jsonify({'hosts': host_list}), 200

@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT room_code, description FROM rooms')
    rooms = cursor.fetchall()
    conn.close()
    
    if len(rooms) < 1:
        return jsonify({'message': 'No rooms added yet. Please add a room first.'}), 200

    room_list = []
    for room in rooms:
        room_list.append({
            'room_code':    room[0],
            'description':  room[1],
        })

    return jsonify({'rooms': room_list}), 200

@app.route('/get_hosts/<string:room_code>', methods=['GET'])
def get_hosts_for_room(room_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT host_address, host_mac, host_name, description, username, password, platform, room_code, config_default, config_cisco, config_optus FROM hosts WHERE room_code = %s", (room_code,))
    hosts = cursor.fetchall()
    conn.close()

    if len(hosts) < 1:
        return jsonify({'message': 'No hosts found for room {}'.format(room_code)}), 200

    host_list = []
    for host in hosts:
        host_list.append({
            'host_id':          host[0], # host['host_address'],
            'host_mac' :        host[1], # host['host_mac'],
            'host_name':        host[2], # host['host_name'],
            'description':      host[3], # host['description'],
            'username':         host[4], # host['username'],
            'password':         host[5], # host['password'],
            'platform':         host[6], # host['platform'],
            'room_code':        host[7], # host['room_code']
            'config_default':   host[8], # host['config_default'],
            'config_cisco':     host[9], # host['config_cisco'],
            'config_optus':     host[10], # host['config_optus']
        })

    return jsonify({'hosts': host_list}), 200

# Route to get all displays
@app.route('/get_displays', methods=['GET'])
def get_displays():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT display_address, display_mac, display_name, display_type, username, password, room_code FROM displays WHERE room_code = %s", (room_code,))
    displays = cursor.fetchall()
    conn.close()
    
    if len(displays) < 1:
        return jsonify({'message': 'No displays added yet. Please add a display first.'}), 200

    display_list = []
    for display in displays:
        display_list.append({
            'display_address':  display[0], #display['display_address'],
            'display_mac' :     display[1], #display['display_mac'],
            'display_name':     display[2], #display['display_name'],
            'display_type':     display[3], #display['display_type'],
            'username':         display[4], #display['username'],
            'password':         display[5], #display['password'],
            'room_code':        display[6], #display['room_code']
        })

    return jsonify({'displays': display_list}), 200

@app.route('/get_displays/<string:room_code>', methods=['GET'])
def get_displays_for_room(room_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT display_address, display_mac, display_name, display_type, username, password, room_code FROM displays WHERE room_code = %s", (room_code,))
    displays = cursor.fetchall()
    conn.close()

    if len(displays) < 1:
        return jsonify({'message': 'No displays found for room {}'.format(room_code)}), 200

    display_list = []
    for display in displays:
        display_list.append({
            'display_address':  display[0], #display['display_address'],
            'display_mac' :     display[1], #display['display_mac'],
            'display_name':     display[2], #display['display_name'],
            'display_type':     display[3], #display['display_type'],
            'username':         display[4], #display['username'],
            'password':         display[5], #display['password'],
            'room_code':        display[6], #display['room_code']
        })

    return jsonify({'displays': display_list}), 200

# Route to get all PDUs
@app.route('/get_pdus', methods=['GET'])
def get_pdus():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT pdu_address, pdu_mac, username, password, room_code FROM pdus")
    pdus = cursor.fetchall()
    conn.close()
    
    if len(pdus) < 1:
        return jsonify({'message': 'No PDUs added yet. Please add a PDU first.'}), 200

    pdu_list = []
    for pdu in pdus:
        pdu_list.append({
            'pdu_address':  pdu[0], # pdu['pdu_address'],
            'pdu_mac' :     pdu[1], # pdu['pdu_mac'],
            'username':     pdu[2], # pdu['username'],
            'password':     pdu[3], # pdu['password'],
            'room_code':    pdu[4], # pdu['room_code']
        })

    return jsonify({'pdus': pdu_list}), 200

@app.route('/get_pdus/<string:room_code>', methods=['GET'])
def get_pdus_for_room(room_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT pdu_address, pdu_mac, username, password, room_code FROM pdus WHERE room_code = %s", (room_code,))
    pdus = cursor.fetchall()  
    conn.close()

    if len(pdus) < 1:
        return jsonify({'message': 'No PDUs found for room {}'.format(room_code)}), 200

    pdu_list = []
    for pdu in pdus:
        pdu_list.append({
            'pdu_address':  pdu[0], # pdu['pdu_address'],
            'pdu_mac' :     pdu[1], # pdu['pdu_mac'],
            'username':     pdu[2], # pdu['username'],
            'password':     pdu[3], # pdu['password'],
            'room_code':    pdu[4], # pdu['room_code']
        })

    return jsonify({'pdus': pdu_list}), 200

@app.route('/get_room/<room_code>', methods=['GET'])
def get_room(room_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT room_code, description FROM rooms WHERE room_code = %s", (room_code,))
    room = cursor.fetchone()

    if room is None:
        conn.close()
        return jsonify({'message': f'Room with room_code {room_code} not found.'}), 404

    cursor.execute("SELECT host_address, host_mac, host_name, description, username, password, platform, room_code, config_default, config_cisco, config_optus FROM hosts WHERE room_code = %s", (room_code,))
    hosts = cursor.fetchall()
    
    host_list = []
    for host in hosts:
        host_list.append({
            'host_id':          host[0], # host['host_address'],
            'host_mac' :        host[1], # host['host_mac'],
            'host_name':        host[2], # host['host_name'],
            'description':      host[3], # host['description'],
            'username':         host[4], # host['username'],
            'password':         host[5], # host['password'],
            'platform':         host[6], # host['platform'],
            'room_code':        host[7], # host['room_code']
            'config_default':   host[8], # host['config_default'],
            'config_cisco':     host[9], # host['config_cisco'],
            'config_optus':     host[10], # host['config_optus']
        })

    cursor.execute("SELECT display_address, display_mac, display_name, display_type, username, password, room_code FROM displays WHERE room_code = %s", (room_code,))
    displays = cursor.fetchall()
    
    display_list = []
    for display in displays:
        display_list.append({
            'display_address':  display[0], #display['display_address'],
            'display_mac' :     display[1], #display['display_mac'],
            'display_name':     display[2], #display['display_name'],
            'display_type':     display[3], #display['display_type'],
            'username':         display[4], #display['username'],
            'password':         display[5], #display['password'],
            'room_code':        display[6], #display['room_code']
        })

    #cursor.execute("SELECT * FROM pdus WHERE room_code = %s", (room_code,))
    cursor.execute("SELECT pdu_address, pdu_mac, username, password, room_code FROM pdus WHERE room_code = %s", (room_code,))
    pdus = cursor.fetchall()  
    
    pdu_list = []
    for pdu in pdus:
        pdu_list.append({
            'pdu_address':  pdu[0],  # Use index to access the column values
            'pdu_mac' :     pdu[1],
            'username':     pdu[2],
            'password':     pdu[3],
            'room_code':    pdu[4]
        })

    conn.close()
    
    room_info = {
        'room_code':    room[0], # room['room_code'],
        'description':  room[1], #room['description'],
        'hosts':        host_list,
        'displays':     display_list,
        'pdus':         pdu_list
    }

    return jsonify({'room_info': room_info}), 200

# Route to add a new room
@app.route('/add_room', methods=['POST'])
def add_room():
    data = request.get_json()

    # Check if the required fields are present in the JSON data
    required_fields = ['room_code', 'description']
    if not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    room_code = data.get('room_code')
    description = data.get('description')
    
    logger.info(f"testing.... in add_room, room_code: {room_code}")
    logger.info(f"testing.... in add_room, description: {description}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Show tables in the database
    # cursor.execute('SHOW TABLES')
    # tables = [table[0] for table in cursor.fetchall()]

    # # Log the list of tables
    # logger.info('List of tables in the database:')
    # for table in tables:
        # logger.info(f'Table: {table}')

    # # Describe each table
    # for table in tables:
        # cursor.execute(f'DESCRIBE {table}')
        # columns = [column[0] for column in cursor.fetchall()]

        # # Log the table name and its columns
        # logger.info(f'Table: {table}')
        # logger.info('Columns:')
        # for column in columns:
            # logger.info(f'  {column}')
    
    logger.info(f"testing.... in add_room, database SELECT exec...")
    try:
        #cursor.execute('SELECT room_code FROM rooms WHERE room_code = ?', (room_code,))
        cursor.execute("SELECT room_code FROM rooms WHERE room_code = %s", (room_code,))
        existing_room = cursor.fetchone()
        #cursor.close()
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        conn.close()
        return jsonify({'error': 'Database error'}), 500  # Return a 500 Internal Server Error response

    # Check if the room with the provided room_code already exists
    #cursor.execute('SELECT room_code FROM rooms WHERE room_code = ?', (room_code,))
    #existing_room = cursor.fetchone()
    
    logger.info(f"testing.... in add_room, existing_room: {existing_room}")

    if existing_room:
        conn.close()
        return jsonify({'error': 'Room with the same room_code already exists'}), 400
    
    logger.info(f"testing.... in add_room, database INSERT INTO exec...")
    try:
        #cursor.execute('INSERT INTO rooms (room_code, description) VALUES (?, ?)', (room_code, description))
        cursor.execute("INSERT INTO rooms (room_code, description) VALUES (%s, %s)", (room_code, description))
        conn.commit()
        #conn.close()
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return jsonify({'error': 'Database error'}), 500  # Return a 500 Internal Server Error response
    finally:
        cursor.close()
        conn.close()


    # Insert the room data into the database
    #cursor.execute('INSERT INTO rooms (room_code, description) VALUES (?, ?)', (room_code, description))

    #conn.commit()
    #conn.close()

    return jsonify({'message': 'Room added successfully'}), 200

@app.route('/remove_room/<string:room_code>', methods=['DELETE'])
def remove_room(room_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    cursor.execute("SELECT room_code FROM rooms WHERE room_code = %s", (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        return jsonify({'error': 'Room not found'}), 404

    # Delete the room from the database
    #cursor.execute('DELETE FROM rooms WHERE room_code = ?', (room_code,))
    #cursor.execute('DELETE FROM rooms WHERE room_code = %s', (room_code,))

    
    # Delete associated PDUs, displays, and hosts from the database
    #cursor.execute('DELETE FROM pdus WHERE room_code = ?', (room_code,))
    #cursor.execute('DELETE FROM displays WHERE room_code = ?', (room_code,))
    #cursor.execute('DELETE FROM hosts WHERE room_code = ?', (room_code,))
    cursor.execute('DELETE FROM pdus WHERE room_code = %s', (room_code,))
    cursor.execute('DELETE FROM displays WHERE room_code = %s', (room_code,))
    cursor.execute('DELETE FROM hosts WHERE room_code = %s', (room_code,))
    cursor.execute('DELETE FROM rooms WHERE room_code = %s', (room_code,))
    
    conn.commit()
    conn.close()

    # Now, remove the devices from app.config
    devices = app.config.get('pdu_data', [])

    for device in devices:
        if device.room_code == room_code:
            device.disconnect()
            devices.remove(device)

    app.config['pdu_data'] = devices

    return jsonify({'message': 'Room and associated devices removed successfully'}), 200

#Route to add a new host
#@app.route('/add_host', methods=['POST'])
@app.route('/add_host/<string:room_code>', methods=['POST'])
def add_host(room_code):
    data = request.get_json()

    # Check if the required fields are present in the JSON data
    required_fields = ['host_address', 'host_name', 'description', 'username', 'password', 'platform']
    if not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    host_address = data.get('host_address')
    host_name = data.get('host_name')
    host_mac = data.get('host_mac')
    description = data.get('description')
    username = data.get('username')
    password = data.get('password')
    platform = data.get('platform')
    
    print("display_name: ", host_name)
    print("display_type: ", platform)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    cursor.execute("SELECT room_code FROM rooms WHERE room_code = %s", (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        return jsonify({'error': 'Room with the provided room_code does not exist'}), 400

    # Check if the host address already exists in the database for the given room
    #cursor.execute('SELECT host_address FROM hosts WHERE host_address = ? AND room_code = ?', (host_address, room_code))
    cursor.execute('SELECT host_address FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    existing_host = cursor.fetchone()

    if existing_host:
        conn.close()
        return jsonify({'message': 'Host with the same address already exists in the room'}), 200

    # Insert the host data into the database
    #cursor.execute('INSERT INTO hosts (host_address, host_mac, host_name, description, username, password, platform, room_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
    #                   (host_address, host_mac, host_name, description, username, password, platform, room_code))
    cursor.execute('INSERT INTO hosts (host_address, host_mac, host_name, description, username, password, platform, room_code) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
               (host_address, host_mac, host_name, description, username, password, platform, room_code))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Host added successfully'}), 200
    
@app.route('/remove_host/<string:room_code>/<string:host_address>', methods=['DELETE'])
def remove_host(room_code, host_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    #cursor.execute('SELECT room_code FROM rooms WHERE room_code = ?', (room_code,))
    cursor.execute("SELECT room_code FROM rooms WHERE room_code = %s", (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        return jsonify({'error': 'Room not found'}), 404

    # Check if the host with the provided host_address exists
    cursor.execute('SELECT host_address FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    existing_host = cursor.fetchone()

    if not existing_host:
        conn.close()
        return jsonify({'error': 'Host not found in the specified room'}), 404

    # Delete the host from the database
    cursor.execute('DELETE FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Host removed successfully'}), 200

@app.route('/update_host_config/<string:room_code>/<string:host_address>', methods=['PUT'])
def update_host_config(room_code, host_address):
    data = request.get_json()

    # Check if the required fields are present in the JSON data
    required_fields = ['config_default', 'config_cisco', 'config_optus']
    if not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    config_default = data.get('config_default')
    config_cisco = data.get('config_cisco')
    config_optus = data.get('config_optus')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the host with the provided `host_address` exists in the database for the given `room_code`
    cursor.execute('SELECT host_address FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    existing_host = cursor.fetchone()

    if not existing_host:
        conn.close()
        return jsonify({'error': 'Host not found in the specified room'}), 404

    # Update the configuration attributes in the database
    cursor.execute(
        'UPDATE hosts SET config_default=%s, config_cisco=%s, config_optus=%s WHERE host_address=%s AND room_code=%s',
        (config_default, config_cisco, config_optus, host_address, room_code)
    )

    conn.commit()
    conn.close()

    return jsonify({'message': 'Host configuration attributes updated successfully'}), 200

@app.route('/get_host_config/<string:room_code>/<string:host_address>', methods=['GET'])
def get_host_config(room_code, host_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the host with the provided `host_address` exists in the database for the given `room_code`    
    cursor.execute('SELECT config_default, config_cisco, config_optus FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host = cursor.fetchone()
    conn.close()

    if not host:
        return jsonify({'error': 'Host not found in the specified room'}), 404

    # Access tuple elements using indices with comments specifying the column names
    host_config = {
        'config_default':   host[0],    # Assuming 'config_default' is the first column in the SELECT query
        'config_cisco':     host[1],    # Assuming 'config_cisco' is the second column in the SELECT query
        'config_optus':     host[2]     # Assuming 'config_optus' is the third column in the SELECT query
    }

    return jsonify({'host_config': host_config}), 200

@app.route('/set_host_config/<string:room_code>/<string:host_address>/<string:attribute_name>', methods=['PUT'])
def set_host_config_attribute(room_code, host_address, attribute_name):
    data = request.get_json()

    # Check if the attribute name is valid
    valid_attribute_names = ['config_default', 'config_cisco', 'config_optus']
    if attribute_name not in valid_attribute_names:
        return jsonify({'error': f'Invalid attribute name.  Must be one of: {valid_attribute_names}'}), 400

    # Check if the required field is present in the JSON data
    if attribute_name not in data:
        return jsonify({'error': f'Missing {attribute_name} field. Must be one of: {valid_attribute_names}'}), 400

    attribute_value = data[attribute_name]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the host with the provided `host_address` exists in the database for the given `room_code`
    cursor.execute('SELECT host_address FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    existing_host = cursor.fetchone()

    if not existing_host:
        conn.close()
        return jsonify({'error': 'Host not found in the specified room'}), 404
    
    # Assuming attribute_name, attribute_value, host_address, and room_code are properly defined
    # Construct the SQL query as a string with placeholders
    query = f'UPDATE hosts SET {attribute_name} = %s WHERE host_address = %s AND room_code = %s'

    # Pass the values separately as a tuple
    values = (attribute_value, host_address, room_code)
    
    try:
        # Execute the query and commit the changes to the database
        cursor.execute(query, values)
        conn.commit()
    except Exception as e:
        # Handle any database-related errors here
        conn.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

    return jsonify({'message': f'{attribute_name} attribute updated successfully'}), 200
    
@app.route('/get_host_config/<string:room_code>/<string:host_address>/<string:attribute_name>', methods=['GET'])
def get_host_config_attribute(room_code, host_address, attribute_name):
    # Check if the requested attribute name is valid
    valid_attribute_names = ['config_default', 'config_cisco', 'config_optus']
    if attribute_name not in valid_attribute_names:
        conn.close()
        return jsonify({'error': f'Invalid attribute name.  Must be one of: {valid_attribute_names}'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the host with the provided `host_address` exists in the database for the given `room_code`
    cursor.execute('SELECT * FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host = cursor.fetchone()

    if not host:
        conn.close()
        return jsonify({'error': 'Host not found in the specified room'}), 404
        
        
    # Check if the host with the provided `host_address` exists in the database for the given `room_code`
    cursor.execute(f'SELECT {attribute_name} FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_attribute = cursor.fetchone()

    if not host_attribute:
        conn.close()
        return jsonify({'error': f'{attribute_name} not found in the specified room'}), 404

    # Construct a dictionary containing the requested configuration attribute
    host_config = {
        attribute_name: host_attribute[0]
    }

    conn.close()

    return jsonify({'host_config': host_config}), 200
    
#@app.route('/add_display', methods=['POST'])
@app.route('/add_display/<string:room_code>', methods=['POST'])
def add_display(room_code):
    data = request.get_json()

    # Check if the required fields are present in the JSON data
    required_fields = ['display_address', 'display_name', 'display_type', 'username', 'password']
    if not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    display_address = data.get('display_address')
    display_mac = data.get('display_mac')
    display_name = data.get('display_name')
    display_type = data.get('display_type')
    username = data.get('username')
    password = data.get('password')
    #room_code = data.get('room_code')
    
    print("display_name: ", display_name)
    print("display_type: ", display_type)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    cursor.execute('SELECT room_code FROM rooms WHERE room_code = %s', (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        return jsonify({'error': 'Room with the provided room_code does not exist'}), 400

    # Check if the display address already exists in the database for the given room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if existing_display:
        conn.close()
        return jsonify({'message': 'Display with the same address already exists in the room'}), 200

    # Insert the display data into the database
    #cursor.execute('INSERT INTO displays (display_address, display_mac, display_name, display_type, username, password, room_code) VALUES (?, ?, ?, ?, ?, ?, ?)',
    #               (display_address, display_mac, display_name, display_type, username, password, room_code))
    cursor.execute('INSERT INTO displays (display_address, display_mac, display_name, display_type, username, password, room_code) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  (display_address, display_mac, display_name, display_type, username, password, room_code))    
               
    conn.commit()
    conn.close()

    return jsonify({'message': 'Display added successfully'}), 200

@app.route('/remove_display/<string:room_code>/<string:display_address>', methods=['DELETE'])
def remove_display(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    cursor.execute('SELECT room_code FROM rooms WHERE room_code = %s', (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        return jsonify({'error': 'Room not found'}), 404

    # Check if the display with the provided display_address exists
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Delete the display from the database
    cursor.execute('DELETE FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Display removed successfully'}), 200

import aiohttp
#import asyncio
from epson_projector.main_non_async import Projector 

from flask import jsonify

import urllib3

# Disable SSL certificate verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


### this is the pj solution using digest auth for epson projects!
### SEE BELOW LIST FOR MORE COMMANDS
# Select source:
# PUT https://192.168.128.18/lighting/api/v01/pj/source
# {
#   "source": "HDMI", "SD Player","LAN","Spotlight",
# }
@app.route('/select_projector_source/<string:room_code>/<string:display_address>', methods=['PUT'])
def select_projector_source(room_code, display_address):   
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()
    
    data = request.get_json()
    source = data.get("source")
    
    ## maybe check if source is in display sources?

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/source'
    
    # Build the payload as a dictionary
    payload = {
        "source": source
    }

    try:
        # Send a GET request with the payload
        response = requests.put(url, data=json.dumps(payload), auth=HTTPDigestAuth(username, password), verify=False, headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# get current source:
# GET https://192.168.128.18/lighting/api/v01/pj/source
# response: {
#     "source": "HDMI", "SD Player","LAN","Spotlight",
# }
@app.route('/get_projector_source/<string:room_code>/<string:display_address>', methods=['GET'])
def get_projector_source(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close() 

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/source'

    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get sources:
# GET https://192.168.128.18/lighting/api/v01/pj/sources
# response: {
#     "sources": [
#         "SD Player",
#         "HDMI",
#         "LAN",
#         "Spotlight"
#     ],
#     "signageSource": "SD Player"
# }
@app.route('/get_projector_sources/<string:room_code>/<string:display_address>', methods=['GET'])
def get_projector_sources(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close() 

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/sources'

    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# # Turn on/off
# PUT https://192.168.128.18/lighting/api/v01/pj/power
# {
#     "power": "ON","OFF"
# }
@app.route('/set_projector_power/<string:room_code>/<string:display_address>', methods=['PUT'])
def set_projector_power(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()
    
    data = request.get_json()
    power = data.get("power")

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/power'

    # Build the payload as a dictionary
    payload = {
        "power": power
    }

    try:
        # Send a GET request with the payload
        response = requests.put(url, data=json.dumps(payload), auth=HTTPDigestAuth(username, password), verify=False, headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# # get current power state
# GET https://192.168.128.18/lighting/api/v01/pj/power
# response: {
#     "power": "OFF"
# }
@app.route('/get_projector_power/<string:room_code>/<string:display_address>', methods=['GET'])
def get_projector_power(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close() 

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/power'

    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ## returns the current state of mute?
# GET https://192.168.128.18/lighting/api/v01/pj/mute
# response: {
#   "mute": "ON","OFF"
# }
@app.route('/get_projector_mute/<string:room_code>/<string:display_address>', methods=['GET'])
def get_projector_mute(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close() 

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/mute'

    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# # select state of mute
# PUT https://192.168.128.18/lighting/api/v01/pj/mute
# {
#   "mute": "ON","OFF"
# }
@app.route('/set_projector_mute/<string:room_code>/<string:display_address>', methods=['PUT'])
def set_projector_mute(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()
    
    data = request.get_json()
    mute = data.get("mute")
    
    logger.info(f'set_projector_mute, mute: {mute}')

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/mute'
    logger.info(f'set_projector_mute, url: {url}')

    # Build the payload as a dictionary
    payload = {
        "mute": mute
    }

    try:
        # Send a GET request with the payload
        response = requests.put(url, data=json.dumps(payload), auth=HTTPDigestAuth(username, password), verify=False, headers={'Content-Type': 'application/json'})
        logger.info(f'set_projector_mute, response: {response}')

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': f'Failed {response.text}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# up/down volume
# PUT https://192.168.128.18/lighting/api/v01/pj/volume
# {
#   "volume": "INC","DEC"
# }
@app.route('/change_projector_volume/<string:room_code>/<string:display_address>', methods=['PUT'])
def change_projector_volume(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()
    
    data = request.get_json()
    volume = data.get("volume")

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/volume'

    # Build the payload as a dictionary
    payload = {
        "volume": volume
    }

    try:
        # Send a GET request with the payload
        response = requests.put(url, data=json.dumps(payload), auth=HTTPDigestAuth(username, password), verify=False, headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/set_projector_volume/<string:room_code>/<string:display_address>', methods=['PUT'])
def set_projector_volume(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()
    
    data = request.get_json()
    desired_volume_level = data.get("volume_level")
    if desired_volume_level > 20:
        desired_volume_level = 20
    elif desired_volume_level < 0:
        desired_volume_level = 20
    
    # get current volume
    current_volume = None
    url = f'http://{display_address}/lighting/api/v01/pj/volume'
    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)
        if response.status_code == 200:
            # Parse the JSON response
            response_data = json.loads(response.text)

            # Extract the value of the "volume" field
            current_volume = response_data.get("volume")
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    # Step 1: Calculate the difference between `desired_volume_level` and `current_volume`
    volume_difference = desired_volume_level - current_volume
    logger.info(f'set_projector_volume, volume_difference = {volume_difference}')
    
    if volume_difference == 0:
        return jsonify({'message': 'Volume already at that equivalent level'}), 200

    # Define a function to send volume control commands
    def send_volume_command(command, volume_difference, max_consecutive_uppers=20):
        # Build URL
        url = f'http://{display_address}/lighting/api/v01/pj/volume'

        # Build the payload as a dictionary
        payload = {
            "volume": command
        }

        # Send a PUT request with the payload
        for _ in range(volume_difference):
            #time.sleep(sleep_duration)
            try:
                response = requests.put(url, data=json.dumps(payload), auth=HTTPDigestAuth(username, password), verify=False, headers={'Content-Type': 'application/json'})
            except Exception as e:
                logger.info(f'send_volume_command, Exception: {e}')
                return False

            logger.info(f'send_volume_command, response: {response.text}')
            
            # If the response is 200 but contains {"limit":"upper"}, adjust sleep duration
            if '{"limit":"upper"}' in response.text:
                return True

        return True

    # Apply the volume control commands
    if volume_difference > 0:
        logger.info(f'set_projector_volume, volume_difference > 0 = {volume_difference > 0}')
        # Increase volume
        if not send_volume_command("INC", volume_difference):
            return jsonify({'error': 'Failed to increase volume'}), 500
    elif volume_difference < 0:
        logger.info(f'set_projector_volume, volume_difference < 0 = {volume_difference < 0}')
        # Decrease volume
        if not send_volume_command("DEC", -volume_difference):
            return jsonify({'error': 'Failed to decrease volume'}), 500

    # Step 3: Confirm `current_volume` is equal to `desired_volume_level`
    # Get the updated current volume
    url = f'http://{display_address}/lighting/api/v01/pj/volume'
    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            current_volume = response_data.get("volume")
            logger.info(f'set_projector_volume, after loop current_volume = {current_volume}')
        else:
            return jsonify({'error': 'Failed to confirm volume change'}), 500
    except Exception as e:
        return jsonify({'error': 'Failed to confirm volume change'}), 500

    # Check if the current volume matches the desired volume
    logger.info(f'set_projector_volume, current_volume = {current_volume}')
    logger.info(f'set_projector_volume, desired_volume_level = {desired_volume_level}')
    if current_volume == desired_volume_level:
        return jsonify({'message': 'Volume changed successfully'}), 200
    else:
        return jsonify({'error': 'Volume change confirmation failed'}), 500


# # get current volume
# GET https://192.168.128.18/lighting/api/v01/pj/volume
# response: 
#     "volume": 15
# }
@app.route('/get_projector_volume/<string:room_code>/<string:display_address>', methods=['GET'])
def get_projector_volume(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close() 

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/volume'

    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# # get current power state
# GET https://192.168.128.18/lighting/api/v01/pj/power
# response: {
#     "power": "OFF"
# }
@app.route('/get_projector_state/<string:room_code>/<string:display_address>', methods=['GET'])
def get_projector_state(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close() 

    # build url
    url = f'http://{display_address}/lighting/api/v01/pj/power'

    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), verify=False)

        if response.status_code == 200:
            return response.text, 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# @app.route('/turn_on_projector/<string:room_code>/<string:display_address>', methods=['post'])
# async def turn_on_projector(room_code, display_address):
#     # define constants for power states
#     power_on = "01"
#     power_init = "02"
#     power_off = "04"
#     power_err = "err"  
    
#     projector_state = none
    
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # check if the display exists in the specified room
#     cursor.execute('select display_address from displays where display_address = %s and room_code = %s', (display_address, room_code))
#     existing_display = cursor.fetchone()

#     if not existing_display:
#         conn.close()
#         logger.info('display not found in the specified room')
#         return jsonify({'error': 'display not found in the specified room'}), 404

#     # fetch the projector details from the database, including host_address, username, and password
#     cursor.execute('select username, password from displays where display_address = %s', (display_address,))
#     display_details = cursor.fetchone()

#     if not display_details:
#         conn.close()
#         logger.info('display details not found')
#         return jsonify({'error': 'display details not found'}), 404

#     username, password = display_details

#     conn.close()

#     logger.info('debugging line...')
    
#     power_state = power_init

#     # initialize aiohttp client session
#     async with aiohttp.clientsession() as session:
#         host = display_address
#         websession = session
#         projector = projector(host, websession)

#         try:
#             # get the current power state
#             power_state = await projector.get_property("pwr")
        
#             if power_state == power_err:
#                 # retry initialization if the response is "err"
#                 max_retries = 1
#                 for retry in range(1, max_retries + 1):                
#                     # wait before retrying (you can adjust the duration)
#                     await asyncio.sleep(1)
                
#                     # retry initialization
#                     power_state = await projector.get_property("pwr")
#                     if str(power_state) != power_err:
#                         break
#                 else:
#                     logger.info('initialization failed after all retries.')
#                     return jsonify({'error': "initialization failed after all retries."}), 500

        
#             if power_state == power_off:
#                 logger.info(f"projector at: {host} is off, so turning on..")
  
#                 # the projector is currently off, so we can turn it on
#                 await projector.send_command("pwr on")
                
#                 # wait for the projector to power on
#                 await asyncio.sleep(1)
                
#                 # check the current power state to confirm it's on
#                 max_retries = 1
#                 for retry in range(1, max_retries + 1):
#                     power_state = await projector.get_property("pwr")
			
#                     if power_state == power_on:
#                         logger.info('projector turned on successfully')
#                         return jsonify({'message': power_state}), 200
			    
#                     # wait before retrying (you can adjust the duration)
#                     await asyncio.sleep(1)	
#                 else:
#                     logger.info('failed to turn on the projector')
#                     #return jsonify({'error': 'failed to turn on the projector'}), 500
#                     return jsonify({'message': power_state}), 200
#             else:
#                 logger.info('projector is already on')
#                 return jsonify({'message': power_state}), 200

#         except exception as e:
#             logger.exception('an error occurred during projector control')
#             return jsonify({'error': str(e)}), 500
            
# @app.route('/turn_off_projector/<string:room_code>/<string:display_address>', methods=['post'])
# async def turn_off_projector(room_code, display_address):
#     # define constants for power states
#     power_on = "01"
#     power_init = "02"
#     power_off = "04"
#     power_err = "err"    

#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # check if the display exists in the specified room
#     cursor.execute('select display_address from displays where display_address = %s and room_code = %s', (display_address, room_code))
#     existing_display = cursor.fetchone()

#     if not existing_display:
#         conn.close()
#         return jsonify({'error': 'display not found in the specified room'}), 404

#     # fetch the projector details from the database, including host_address, username, and password
#     cursor.execute('select username, password from displays where display_address = %s', (display_address,))
#     display_details = cursor.fetchone()

#     if not display_details:
#         conn.close()
#         return jsonify({'error': 'display details not found'}), 404

#     username, password = display_details

#     conn.close()

#     # initialize aiohttp client session
#     async with aiohttp.clientsession() as session:
#         host = display_address
#         websession = session
#         projector = projector(host, websession)

#         try:
#             # get the current power state
#             power_state = await projector.get_property("pwr")
        
#             if power_state == power_err:
#                 # retry initialization if the response is "err"
#                 max_retries = 15
#                 for retry in range(1, max_retries + 1):                
#                     # wait before retrying (you can adjust the duration)
#                     await asyncio.sleep(5)
                
#                     # retry initialization
#                     power_state = await projector.get_property("pwr")
#                     if str(power_state) != power_err:
#                         break
#                 else:
#                     return jsonify({'error': "initialization failed after all retries."}), 500
     

#             while power_state != power_off:
#                 if power_state == power_on:
#                     # the projector is currently on, so we can turn it off
#                     await projector.send_command("pwr off")
                
#                     # wait for the projector to power off
#                     await asyncio.sleep(5)

# 		    # check the current power state to confirm it's off
#                     max_retries = 15
#                     for retry in range(1, max_retries + 1):
#                         # check the current power state to confirm it's off
#                         power_state = await projector.get_property("pwr")

#                         if power_state == power_off:
#                             return jsonify({'message': 'projector turned off successfully'}), 200

# 		        # wait before retrying (you can adjust the duration)
#                         await asyncio.sleep(5)
#                     else:
#                         return jsonify({'error': 'failed to turn off the projector'}), 500
#                 elif power_state == power_off:
#                     return jsonify({'message': 'projector is already off'}), 200
#         except exception as e:
#             return jsonify({'error': str(e)}), 500


import requests
from requests.auth import HTTPDigestAuth

@app.route('/turn_off_projector/<string:room_code>/<string:display_address>', methods=['POST'])
def turn_off_projector(room_code, display_address):
    logger.info(f"turn_off_projector, room_code, display_address: {room_code} {display_address}" )

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()
    
    logger.info(f"turn_off_projector, username, password: {username} {password}")

    # build request with display credentials
    url = f'http://{display_address}/api/v01/contentmgr/remote/power/off'
    
    logger.info(f"turn_off_projector, url: {url} ")

    try:
        #response = requests.get(url, auth=(username, password))
        response = requests.get(url, auth=HTTPDigestAuth(username, password))

        if response.status_code == 200:
            return jsonify({'message': 'Projector turned off successfully'}), 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed to turn off the projector'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/turn_on_projector/<string:room_code>/<string:display_address>', methods=['POST'])
def turn_on_projector(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()    

    # build request with display credentials
    url = f'http://{display_address}/api/v01/contentmgr/remote/power/on'

    try:
        #response = requests.get(url, auth=(username, password))
        response = requests.get(url, auth=HTTPDigestAuth(username, password))

        if response.status_code == 200:
            return jsonify({'message': 'Projector turned on successfully'}), 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'Failed to turn on the projector'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


## v02 api test function route... for 2x PU1008B and 2x EV-110 projectors in TC level2
## projectors in library dih are ev105/100, and only api v01
api_v02 = {
    "power_control": {
        "endpoint_url": "/api/v02/contentmgr/remote/power",
        "request_type": "PUT",
        "request_body": {
            "power": None  # To be set by the user
        },
        "request_body_options": {"power": ["on", "off"]}
    },
    "switch_source": {
        "endpoint_url": "/api/v02/contentmgr/remote/source",
        "request_type": "PUT",
        "request_body": {
            "source": None  # To be set by the user
        },
        "request_body_options": {"source": ["is an int"]}
    },
    "mute": {
        "endpoint_url": "/api/v02/contentmgr/remote/mute",
        "request_type": "PUT",
        "request_body": {
            "mute": None  # To be set by the user
        },
        "request_body_options": {"mute": ["on", "off"]}
    },
    "content_playback": {
        "endpoint_url": "/api/v02/contentmgr/playlists/playback",
        "request_type": "PUT",
        "request_body": {
            "playback": None,  # To be set by the user
            "mode": "normal",
            "playlist_id": None  # To be set by the user
        },
        "request_body_options": {
            "playback": ["start", "stop"],
            "mode": ["normal", "timetable"],
            "playlist_id": ["is an int"]
        }
    }
}

@app.route('/projector_api/<string:room_code>/<string:display_address>', methods=['POST'])
def projector_api(room_code, display_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the display exists in the specified room
    cursor.execute('SELECT display_address FROM displays WHERE display_address = %s AND room_code = %s', (display_address, room_code))
    existing_display = cursor.fetchone()

    if not existing_display:
        conn.close()
        return jsonify({'error': 'Display not found in the specified room'}), 404

    # Fetch the projector details from the database, including host_address, username, and password
    cursor.execute('SELECT username, password FROM displays WHERE display_address = %s', (display_address,))
    display_details = cursor.fetchone()

    if not display_details:
        conn.close()
        return jsonify({'error': 'Display details not found'}), 404

    username, password = display_details
    conn.close()  

    try:
        data = request.get_json()
        command = data.get("command")

        details = api_v02.get(command)
        if not details:
            raise ValueError(f"Invalid command: {command}")

        request_body = details["request_body"]
        validation_options = details["request_body_options"]

        # Remove "command" from user_input if it exists
        user_input = {key: value for key, value in data.items() if key != "command"}

        for param, value in user_input.items():
            if param in request_body:
                valid_values = validation_options.get(param)
                if valid_values is not None and value not in valid_values:
                    raise ValueError(f"Invalid value for {param}: {value}. Valid values are: {', '.join(valid_values)}")
            else:
                raise ValueError(f"Invalid parameter: {param}")
    except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    # Now you can proceed with building and making the API call with the validated data
    request_type = details.get("request_type")  # Default to GET if request type not specified
    endpoint_url = details["endpoint_url"]
        
    # Build the JSON payload based on command and user input
    payload = {}
    payload.update(user_input)  # Merge with user input
        
    # build request with display credentials
    url = f'http://{display_address}{endpoint_url}'
    
    try:
        if request_type == "GET":
            response = requests.get(url, auth=HTTPDigestAuth(username, password))
        elif request_type == "POST":
            # Make a POST request with the payload as data
            response = requests.post(url, json=payload, auth=HTTPDigestAuth(username, password))
        elif request_type == "PUT":
            # Make a PUT request with the payload as data
            response = requests.put(url, json=payload, auth=HTTPDigestAuth(username, password))
        elif request_type == "DELETE":
            # Make a DELETE request
            response = requests.delete(url, auth=HTTPDigestAuth(username, password))
        else:
            return jsonify({'error': 'Invalid request type'}), 400

        if response.status_code == 200:
            return jsonify({"message": "API call successful"}), 200
        elif response.status_code == 401:
            return jsonify({'error': 'Authentication failed'}), 401
        else:
            return jsonify({'error': 'API call failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500




current_directory = os.path.dirname(os.path.abspath(__file__))
chrome_driver_path = os.path.join(current_directory, 'chromedriver')

# Initialize an empty list to store host data
app.config['pdu_data'] = None

# Helper function to create and cache devices
def get_or_create_devices():
    pdu_data = app.config.get('pdu_data')

    if pdu_data is not None and len(pdu_data) > 0:
        return pdu_data

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT pdu_address, username, password, room_code FROM pdus')
    pdus = cursor.fetchall()  
    
    pdu_list = []
    for pdu in pdus:
        pdu_list.append({
            'pdu_address':  pdu[0],  # Use index to access the column values
            'username':     pdu[1],
            'password':     pdu[2],
            'room_code':    pdu[3]
        })

    conn.close()

    if not pdus:
        # The database is empty; no need to continue
        conn.close()
        return []

    print("here!!!")
    print(pdus)
    for row in pdus:
        print(len(row))
        for r in row:
            print(r)
    print("and here!!!")

    devices = []
    for row in pdus:
        print(len(row))
        logger.info(f"getting/adding pdu pdu_address row[0]: {row[0]}") 
        logger.info(f"getting/adding pdu username row[1]: {row[1]}")
        logger.info(f"getting/adding pdu password row[2]: {row[2]}")  
        logger.info(f"getting/adding pdu room_code row[3]: {row[3]}")

        pdu_address = row[0]
        username = row[1]
        password = row[2]
        room_code = row[3]
        print(pdu_address, username, password, room_code)

        new_pdu = DeviceController(pdu_address, username, password, chrome_driver_path, room_code)

        try:
            new_pdu.connect()
            devices.append(new_pdu)
        except Exception as e:
            pass

    conn.close()

    app.config['pdu_data'] = devices
    return devices

	

@app.before_first_request
def before_first_request():
    print("on first run...")
    logger.info("testing.... on first run, init db..")
    init_db()
    
    # load and init any pdus form db
    logger.info("testing.... on first run, load init pdus...")
    app.config['pdu_data'] = get_or_create_devices()
    logger.info(f"load_pdu.... app.config[pdu_data] is: {app.config['pdu_data']}") 

#def get_db_connection(database='/home/innovation-hub-api/persistent/db/container2/IH_device_database.db'):                    
#    conn = sqlite3.connect(database)
#    conn.row_factory = sqlite3.Row
#    return conn

def create_app():
    app = Flask(__name__)

    # Initialize the app and perform any desired actions here
    print("Performing actions at application startup...")

    return app

# =========================================================================
#  API - endpoints
# =========================================================================

### testing connect to SAMBA
### ========================
def connect_and_map_samba_share(ssh_conn, samba_username, samba_password, share_path):
    try:
        # Check for available drive letters
        used_drive_letters = set()
        for line in ssh_conn.exec_command('net use')[1].readlines():
            line = line.strip()
            if line and line[0].isalpha():
                used_drive_letters.add(line[0])

        # Find an available drive letter (A to Z)
        drive_letter = 'A'
        while drive_letter <= 'Z':
            if drive_letter not in used_drive_letters:
                # Build the net use command for Samba with the selected drive letter
                net_use_command = f'net use {drive_letter}: {share_path} /user:{samba_username} {samba_password} /persistent:yes'

                # Execute the net use command remotely
                stdin, stdout, stderr = ssh_conn.exec_command(net_use_command)

                # Check the exit status of the command
                exit_status = stdout.channel.recv_exit_status()

                if exit_status == 0:
                    return {
                        'message': f"Successfully connected {drive_letter} to {share_path}.",
                        'drive_letter': drive_letter
                    }
                else:
                    return {
                        'error': f"Failed to connect {drive_letter} to {share_path}. Error: {stderr.read().decode()}",
                        'drive_letter': None
                    }

            drive_letter = chr(ord(drive_letter) + 1)

        # If no available drive letter was found
        return {
            'error': 'No available drive letters to map.',
            'drive_letter': None
        }

    except Exception as e:
        return {
            'error': str(e),
            'drive_letter': None
        }
    finally:
        # Close the SSH connection when done
        ssh_conn.close()
        
@app.route('/connect_samba_share', methods=['POST'])
def connect_samba_share_route():
    try:
        # Get parameters from the JSON request
        data = request.get_json()
        if not all(key in data for key in ['hostname', 'samba_username', 'samba_password', 'share_path']):
            return jsonify({'error': 'Missing required field(s)'}), 400 

        hostname = data['hostname']
        samba_username = data['samba_username']
        samba_password = data['samba_password']
        share_path = data['share_path']

        # Retrieve SSH username and password from the SQLite3 database based on hostname
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s', (hostname,))
        host_data = cursor.fetchone()
        conn.close()

        if host_data is None:
            return jsonify({'error': 'Host not found'}), 404

        ssh_username, ssh_password = host_data

        # Create a new SSH client object
        client = paramiko.SSHClient()

        # Automatically add the remote host key (not recommended for production use)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the remote host using SSH
        client.connect(hostname, username=ssh_username, password=ssh_password)

        # Call the connect_and_map_samba_share function with the SSH client object
        # NOTE: connect_and_map_samba_share function handles closing of client object
        result = connect_and_map_samba_share(
            client, samba_username, samba_password, share_path
        )

        # Check if the mapping was successful
        if 'drive_letter' in result:
            if result['drive_letter'] is not None:
                return jsonify({'message': result['message'], 'drive_letter': result['drive_letter']}), 200
            else:
                return jsonify({'error': result['error']}), 500
        else:
            return jsonify({'error': 'Unexpected response from connect_and_map_samba_share'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

import socket
from ipaddress import IPv4Network

def is_valid_mac_address(mac_address):
    # A simple validation function for MAC addresses
    if not mac_address:
        logger.info(f"testing.... in is_valid_mac_address, mac_address is {mac_address}")
        return False

    mac_address = mac_address.replace('-', '').replace(':', '')
    
    if len(mac_address) != 12:
        logger.info(f"testing.... in is_valid_mac_address, length of mac_address is not 12")
        return False

    if not all(c in '0123456789ABCDEF' for c in mac_address.upper()):
        logger.info(f"testing.... in is_valid_mac_address, something wrong with mac_address....")
        return False

    logger.info(f"testing.... in is_valid_mac_address, mac_address OK.")
    return True

def send_magic_packet(mac_address, broadcast_address):
    logger.info(f"testing.... in send_magic_packet, mac_address: {mac_address}")
    logger.info(f"testing.... in send_magic_packet, broadcast_address: {broadcast_address}")

    # Create a Magic Packet
    mac_bytes = bytes.fromhex(mac_address.replace(':', '').replace('-', ''))
    magic_packet = b'\xFF' * 6 + mac_bytes * 16
    
    logger.info(f"testing.... in send_magic_packet, mac_bytes: {mac_bytes}")
    logger.info(f"testing.... in send_magic_packet, magic_packet: {magic_packet}")
    
    # Send the Magic Packet to the broadcast address
    try:
        logger.info(f"testing.... in send_magic_packet, sending1...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            logger.info(f"testing.... in send_magic_packet, sending2...")
            s.sendto(magic_packet, (broadcast_address, 9))  # Replace with the actual broadcast address
            logger.info(f"testing.... in send_magic_packet, sending3...")
        return True
    except Exception as e:
        #print(f"Error sending Magic Packet: {str(e)}")
        logger.info(f"Error sending Magic Packet: {str(e)}")
        return False
    

from ipaddress import IPv4Network

@app.route('/wake-on-lan/<string:room_code>/<string:host_address>', methods=['GET'])
def wake_on_lan(room_code, host_address):
    # Check if the room, host, and host_mac exist in a single query
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.room_code, h.host_mac, h.host_name
        FROM rooms r
        LEFT JOIN hosts h ON r.room_code = h.room_code AND h.host_address = %s
        WHERE r.room_code = %s
    ''', (host_address, room_code))
    result = cursor.fetchone()
    conn.close()
    
    logger.info(f"wake-on-lan")

    if result is None:
        logger.info(f"wake-on-lan result is {result}")
        return jsonify({'error': 'Room not found or host not found in the specified room'}), 404

    room_code_result, host_mac, host_name = result

    # replace hyphens
    host_mac = host_mac.replace('-', ':')

    # Convert to lowercase
    host_mac = host_mac.lower()

    if room_code_result is None:
        logger.info(f"wake-on-lan room_code_result is {room_code_result}")
        return jsonify({'error': 'Room not found'}), 404

    if host_mac is None:
        logger.info(f"wake-on-lan host_mac is {host_mac}")
        return jsonify({'error': f'Mac not found for {host_name} in the room {room_code})'}), 404
        
    logger.info(f"wake-on-lan host_mac is {host_mac}")

    #broadcast_address = '192.168.3.255'
    
    # Validate the MAC address
    if not is_valid_mac_address(host_mac):
        logger.info(f"wake-on-lan is_valid_mac_address is {is_valid_mac_address}")
        return jsonify({'error': f'Invalid MAC address: {host_mac}'}), 400
        
    # Calculate the broadcast address based on the host_address
    try:
        logger.info(f"wake-on-lan trying to send {host_address} a wake up packet")
        host_ip = IPv4Network(f'{host_address}/24', strict=False)
        logger.info(f"wake-on-lan host_ip {host_ip}")
        broadcast_address = str(host_ip.broadcast_address)
        logger.info(f"wake-on-lan broadcast_address {broadcast_address}")
        logger.info(f"testing.... in wake_on_lan, broadcast_address: {broadcast_address}")
    except ValueError:
        return jsonify({'error': 'Invalid host address'}), 400

    # Send the Magic Packet
    if send_magic_packet(host_mac, broadcast_address):
        return jsonify({'status': 'Magic Packet sent successfully'}), 200
    else:
        return jsonify({'error': 'Failed to send Magic Packet'}), 500

@app.route('/reboot/<string:room_code>/<string:host_address>', methods=['GET'])
def reboot_device(room_code, host_address):
    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password, platform FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password, platform = host_data

    # Reboot the remote device based on the retrieved information
    result = run_reboot_device(host_address, username, password, platform)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200
        
@app.route('/shutdown/<string:room_code>/<string:host_address>', methods=['GET'])
def shutdown_device(room_code, host_address):
    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password, platform FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password, platform = host_data

    # Reboot the remote device based on the retrieved information
    result = run_shutdown_device(host_address, username, password, platform)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/open_browser/<string:room_code>/<string:host_address>', methods=['POST'])
def open_browser(room_code, host_address):
    data = request.get_json()
    if not all(key in data for key in ['url']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username, password = host_data
    #username = host_data['username']
    #password = host_data['password']
    url = data.get('url')

    # Open PowerPoint on the remote device using the retrieved credentials and URL
    result = run_browser(host_address, username, password, url)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200
        
@app.route('/sim_mouse_click/<string:room_code>/<string:host_address>', methods=['GET'])
def sim_mouse_click(room_code, host_address):
    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username, password = host_data

    # simulate mouse click
    result = sim_mouse_press(host_address, username, password)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/get_user_session_id', methods=['POST'])
def get_user_session_id_old():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'target_username']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    host_address = data.get('hostname')
    
    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s', (host_address,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data
    target_username = data.get('username')
    
    if target_username:
        # Check for target_username's session ID on the remote host using the retrieved credentials
        result = run_get_session_id(host_address, username, password, target_username)
    else:
        result = run_get_session_id(host_address, username, password, username)
    
    if result is None:
        return jsonify({'response': f"No user session ID found for {target_username}"}), 200
    else:
        return jsonify({'response': result}), 200

@app.route('/get_user_session_id/<string:room_code>/<string:host_address>', methods=['GET'])
def get_user_session_id(room_code, host_address):
    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username, password = host_data
    
    result = run_get_session_id(host_address, username, password, username)

    if result is None:
        return jsonify({'response': f"No user session ID found for {target_username}"}), 200
    else:
        return jsonify({'response': result}), 200

@app.route('/close_process', methods=['POST'])
def close_process_old():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'pid']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    host_address = data.get('hostname')

    # Query the database to retrieve the username and password based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s', (host_address,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data
    pid = data.get('pid')

    print("\n", host_address, username, password, pid, "\n")

    # Kill the process on the remote host using the retrieved credentials
    result = kill_process(host_address, username, password, pid)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200
        
@app.route('/close_process/<string:room_code>/<string:host_address>', methods=['POST'])
def close_process(room_code, host_address):
    data = request.get_json()
    if not all(key in data for key in ['pid']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Query the database to retrieve the username and password based on the host_address and room_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data
    pid = data.get('pid')

    # Kill the process on the remote host using the retrieved credentials
    result = kill_process(host_address, username, password, pid)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/close_process/<string:room_code>/<string:host_address>/<string:pid>', methods=['POST'])
def close_process2(room_code, host_address, pid):
    # Ensure the 'pid' is present in the URL
    if not pid:
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data

    # Kill the process on the remote host using the retrieved credentials and the 'pid' from the URL
    result = kill_process(host_address, username, password, pid)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/open_application', methods=['POST'])
def open_application_route_old():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'application']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')

    # Query the database to retrieve the username and password based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s', (hostname,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data
    application = data.get('application')
    arguments = data.get('arguments')

    print("\n", hostname, username, password, application, arguments, "\n")

    # Open the application on the remote host using the retrieved credentials
    result = run_application(hostname, username, password, application, arguments)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/open_application/<string:room_code>/<string:host_address>', methods=['POST'])
def open_application(room_code, host_address):
    data = request.get_json()
    if not all(key in data for key in ['application']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data
    application = data.get('application')
    arguments = data.get('arguments')

    # Open the application on the remote host using the retrieved credentials
    result = run_application(host_address, username, password, application, arguments)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200
    
from pathlib import Path

def normalize_windows_path(path):
    # Replace common path separators with a single backslash for Windows
    return path.replace('/', '\\').replace('//', '\\').replace('\\\\', '\\')

@app.route('/open_vlc_video/<string:room_code>/<string:host_address>', methods=['POST'])
def open_vlc_video(room_code, host_address):
    data = request.get_json()
    logger.info(f"testing.... in open_vlc_video, request.get_json(): {data}")

    if not all(key in data for key in ['application', 'video_path']):
        return jsonify({'error': 'Missing required field(s)'}), 400
    
    logger.info(f"testing.... in open_vlc_video, room_code: {room_code}")
    logger.info(f"testing.... in open_vlc_video, host_address: {host_address}")

    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    #username = host_data['username']
    #password = host_data['password']
    username, password = host_data
    application = data['application']
    
    logger.info(f"testing.... in open_vlc_video, username: {username}")
    logger.info(f"testing.... in open_vlc_video, password: {password}")
    logger.info(f"testing.... in open_vlc_video, application: {application}")

    # Check if the 'video_path' is a complete path or just a filename
    #if os.path.isabs(data['video_path']):
    #    video_path = normalize_windows_path(data['video_path'])
    #    logger.info(f"testing.... in open_vlc_video, path provided is absolute")
    #    logger.info(f"testing.... in open_vlc_video, video_path: {video_path}")
    #else:
    #    video_path = normalize_windows_path(f'C:/Users/{username}/Videos/{data["video_path"]}')
    #    logger.info(f"testing.... in open_vlc_video, path provided is just a filename")
    #    logger.info(f"testing.... in open_vlc_video, video_path: {video_path}")
        
    # Check if the 'video_path' is a URL or a local file path
    if data['video_path'].startswith(('http://', 'https://', 'ftp://')):
        # It's a URL
        video_path = data['video_path']
        logger.info(f"URL provided: {video_path}")
    else:
        # It's a local file path
        if os.path.isabs(data['video_path']):
            video_path = normalize_windows_path(data['video_path'])
            logger.info(f"Absolute file path provided: {video_path}")
        else:
            video_path = normalize_windows_path(f'C:/Users/{username}/Videos/{data["video_path"]}')
            logger.info(f"Relative file path provided: {video_path}")

    # Convert the path to a string if needed
    video_path = str(video_path)
    logger.info(f"testing.... in open_vlc_video, Convert the path to a string if needed: {video_path}")

    # Open VLC media player in fullscreen and play the specified video
    if application.lower() == 'vlc':
        # Specify the full path to the VLC executable
        vlc_executable = 'C:\\Program Files (x86)\\VideoLan\\VLC\\vlc.exe'

        arguments = '--fullscreen'

        if data.get('loop', False):
            arguments += ' --loop'

        logger.info(f"testing.... in open_vlc_video, arguments: {arguments}")
        result = run_vlc_application(host_address, username, password, vlc_executable, arguments=arguments,video=video_path)
        
        if result is None:
            return jsonify({'error': 'Failed to open VLC or play video'}), 500
        else:
            return jsonify({'response': result}), 200
    else:
        return jsonify({'error': 'Unsupported application'}), 400

@app.route('/send_nircmd', methods=['POST'])
def send_nircmd_old():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'command']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')
    command = data.get('command')

    # Fetch the username and password from the database based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s', (hostname,))
    host_info = cursor.fetchone()
    conn.close()

    if host_info is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password = host_info

    print("\n", hostname, username, password, command, "\n")

    # Run nircmd
    result = run_nircmd(hostname, username, password, command)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/send_nircmd/<string:room_code>/<string:host_address>', methods=['POST'])
def send_nircmd(room_code, host_address):
    data = request.get_json()
    if not all(key in data for key in ['command']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_info = cursor.fetchone()
    conn.close()

    if host_info is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password = host_info
    command = data.get('command')

    # Run nircmd on the remote host using the retrieved credentials
    result = run_nircmd(host_address, username, password, command)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

@app.route('/monitor_off/<string:room_code>/<string:host_address>', methods=['GET'])
def monitor_off(room_code, host_address):
    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_info = cursor.fetchone()
    conn.close()

    if host_info is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password = host_info

    command = "monitor off"

    # Run nircmd on the remote host using the retrieved credentials
    result = run_nircmd(host_address, username, password, command)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200
    

@app.route('/monitor_on/<string:room_code>/<string:host_address>', methods=['GET'])
def monitor_on(room_code, host_address):
    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_info = cursor.fetchone()
    conn.close()

    if host_info is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password = host_info

    command = "monitor on"

    # Run nircmd on the remote host using the retrieved credentials
    result = run_nircmd(host_address, username, password, command)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500

    # Simulate mouse clicks to keep the monitor on
    time.sleep(3)
    result = sim_mouse_press(host_address, username, password)
    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500

    return jsonify({'response': "Monitor should be back on"}), 200

@app.route('/hide_taskbar/<string:room_code>/<string:host_address>', methods=['GET'])
def hide_taskbar(room_code, host_address):
    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_info = cursor.fetchone()
    conn.close()

    if host_info is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password = host_info

    command = "win hide class Shell_TrayWnd"

    # Run nircmd on the remote host using the retrieved credentials
    result = run_nircmd(host_address, username, password, command)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


@app.route('/show_taskbar/<string:room_code>/<string:host_address>', methods=['GET'])
def show_taskbar(room_code, host_address):
    # Query the database to retrieve the username and password based on the 'host_address' and 'room_code'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = %s AND room_code = %s', (host_address, room_code))
    host_info = cursor.fetchone()
    conn.close()

    if host_info is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password = host_info

    command = "win show class Shell_TrayWnd"

    # Run nircmd on the remote host using the retrieved credentials
    result = run_nircmd(host_address, username, password, command)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200
# =========================================================================
#  PDU SECTION
# =========================================================================

from flask import Flask, request, jsonify
from pdu_class import DeviceController
import os
import sys
import shutil
import requests
import platform
from zipfile import ZipFile
from flask import Flask

# =============
# MAIN OPTIONS
# =============	
@app.route('/pdu/devices', methods=['GET'])
def list_devices():    
    logger.info("testing.... in list_devices")

    pdus = None
    if 'pdu_data' in app.config:
        pdus = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        pdus = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")
        
    logger.info(f"testing.... devices is: {pdus}")
    
    if len(pdus) < 1:
        return jsonify({'message': 'No devices added yet. Please add a device first.'}), 200
    logger.info(f"testing.... past len(devices) < 1!")
    
    pdu_list = []
    for index, device in enumerate(pdus):
        pdu_list.append({
            'device_number': index + 1,
            'host_address': device.hostAddress
        })
        
    logger.info(f"testing.... device_list is: {pdu_list}")
    return jsonify({'devices': pdu_list})

@app.route('/pdu/devices/<int:device_number>', methods=['GET'])
def get_device(device_number):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")
        
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    selected_device = devices[device_number - 1]
    # Here you can return information about the selected device if needed
    device_info = {
        'device_number': device_number,
        'host_address': selected_device.hostAddress,
        # Include other device information as needed
    }

    return jsonify(device_info)

# # Route to add a new PDU
#### ====================================================
#### ====================================================
####  NEW DATABASE PDU ADD ROUTE - TESTING?
@app.route('/add_pdu/<string:room_code>', methods=['POST'])
def add_pdu(room_code):
    data = request.get_json()

    # Check if the required fields are present in the JSON data
    required_fields = ['pdu_address', 'username', 'password']
    if not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    pdu_address = data.get('pdu_address')
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    cursor.execute('SELECT room_code FROM rooms WHERE room_code = %s', (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        return jsonify({'error': 'Room with the provided room_code does not exist'}), 400

    # Check if the PDU address already exists in the database for the given room
    cursor.execute('SELECT pdu_address FROM pdus WHERE pdu_address = %s AND room_code = %s', (pdu_address, room_code))
    existing_pdu = cursor.fetchone()

    if existing_pdu:
        conn.close()
        return jsonify({'message': 'PDU with the same address already exists in the room'}), 200

    # Check if the PDU address already exists in app.config['pdu_data']
    pdu_data = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        pdu_data = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        pdu_data = get_or_create_devices()   

    #pdu_data = app.config.get('pdu_data', [])
    for existing_pdu in pdu_data:
        if existing_pdu.hostAddress == pdu_address:
            return jsonify({'message': 'PDU with the same address already exists in app.config'}), 200

    # Additional code to instantiate DeviceController objects and store them
    new_pdu = DeviceController(pdu_address, username, password, chrome_driver_path, room_code)
    try:
        logger.info(f"testing --- in add pdu, pdu_address = {pdu_address}")
        logger.info(f"testing --- in add pdu, username = {username}") 
        logger.info(f"testing --- in add pdu, password = {password}") 
        logger.info(f"testing --- in add pdu, driver_path = {chrome_driver_path}") 
        logger.info(f"testing --- in add pdu, room_code = {room_code}") 
    
        new_pdu.connect()

        # Insert the PDU data into the database after a successful connection
        cursor.execute('INSERT INTO pdus (pdu_address, username, password, driver_path, room_code) VALUES (%s, %s, %s, %s, %s)',
                       (pdu_address, username, password, chrome_driver_path, room_code))
        conn.commit()

        # Add the new PDU object to the app.config list
        pdu_data.append(new_pdu)
        app.config['pdu_data'] = pdu_data

        return jsonify({'message': 'PDU added successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'PDU not reachable...'}), 200
    finally:
        conn.close()


@app.route('/remove_pdu/<string:room_code>/<string:pdu_address>', methods=['DELETE'])
def remove_device(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()    

    print("Received DELETE request for room_code:", room_code, "and pdu_address:", pdu_address)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    cursor.execute('SELECT room_code FROM rooms WHERE room_code = %s', (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        print("Room not found.")
        return jsonify({'error': 'Room not found'}), 404

    # Check if the PDU with the provided pdu_address exists in the specified room
    cursor.execute('SELECT pdu_address FROM pdus WHERE pdu_address = %s AND room_code = %s', (pdu_address, room_code))
    existing_host = cursor.fetchone()

    if not existing_host:
        conn.close()
        print("Host not found in the specified room.")
        return jsonify({'error': 'Host not found in the specified room'}), 404

    # Remove the host from the database
    cursor.execute('DELETE FROM pdus WHERE pdu_address = %s AND room_code = %s', (pdu_address, room_code))
    conn.commit()
    conn.close()
    
    print("Host removed from the database.")

    for device in devices:
        if device.hostAddress == pdu_address:
            device.disconnect()
            devices.remove(device)
            app.config['pdu_data'] = devices
            print("Device removed from app.config.")

    return jsonify({'message': 'PDU removed successfully'}), 200


@app.route('/pdu/remove_device_by_address/<string:pdu_address>', methods=['POST'])
def remove_device_by_address(pdu_address):
    logger.info(f"testing.... in remove_device, pdu_address: {pdu_address}")
        
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    device_to_remove = None

    for device in devices:
        if device.hostAddress == pdu_address:
            device_to_remove = device
            break

    if device_to_remove is None:
        return jsonify({'error': f'Device with host address {pdu_address} not found.'}), 404

    device_to_remove.disconnect()
    devices.remove(device_to_remove)

    # Remove the device information from the database
    conn = sqlite3.connect('pdu_devices.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM pdu_devices WHERE host_address = %s', (pdu_address,))
        conn.commit()
        logger.info("Device removed from the database.")
    except sqlite3.Error as e:
        logger.error(f"Error removing device from the database: {str(e)}")
    finally:
        conn.close()

    # Now, remove the device from the app.config
    devices = app.config.get('pdu_data', [])

    for device in devices:
        if device.hostAddress == pdu_address:
            device.disconnect()
            devices.remove(device)
            app.config['pdu_data'] = devices
            print("Device removed from app.config.")

    return jsonify({'success': 'Device removed successfully!'})

@app.route('/view_pdu_outlet_settings_all/<string:room_code>', methods=['GET'])
def view_outlet_settings(room_code):
    pdus = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        pdus = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        pdus = get_or_create_devices()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the room with the provided room_code exists
    cursor.execute('SELECT room_code FROM rooms WHERE room_code = %s', (room_code,))
    existing_room = cursor.fetchone()

    if not existing_room:
        conn.close()
        return jsonify({'message': f'No room found with room code: {room_code}.'}), 404

    # Fetch the devices (PDUs) for the specified room_code from the pdus table
    #cursor.execute('SELECT * FROM pdus WHERE room_code = %s', (room_code,))
    #pdus_indb = cursor.fetchall()
    
    cursor.execute('SELECT pdu_address FROM pdus WHERE room_code = %s', (room_code,))
    pdus_indb = cursor.fetchall()
    conn.close()
    
    if len(pdus_indb) < 1:
        return jsonify({'message': 'No PDUs added yet. Please add a PDU first.'}), 200
    
    # Create a dictionary to index the PDUs by pdu_address
    pdus_by_address = {pdu.hostAddress: pdu for pdu in pdus}

    # Cross-reference and fetch outlet info
    pdu_outlet_settings_all = []
    for index, pdu_db in enumerate(pdus_indb):
        pdu_address = pdu_db[0]  # Assume pdu_address is the first element
        if pdu_address in pdus_by_address:
            pdu_in_config = pdus_by_address[pdu_address]
            # Fetch outlet settings or other information about the device if needed
            pdu_outlet_info = pdu_in_config.get_outlet_info()
            pdu_outlet_settings = {
                'device_number': index + 1,
                'pdu_address': pdu_address,
                'outlet_settings': pdu_outlet_info
            }
            pdu_outlet_settings_all.append(pdu_outlet_settings)
            
    return jsonify(pdu_outlet_settings_all)

@app.route('/view_pdu_outlet_settings_all/', methods=['GET'])
def view_outlet_settings_all():        
    pdus = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        pdus = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        pdus = get_or_create_devices()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get a list of all room codes from the database
    cursor.execute('SELECT room_code FROM rooms')
    room_codes = [row['room_code'] for row in cursor.fetchall()]

    pdu_outlet_settings_all = []

    for room_code in room_codes:
        room_pdus = [pdu for pdu in pdus if pdu.room_code == room_code]
        
        # Check if there are any PDUs for this room
        if not room_pdus:
            # Skip rooms with no PDUs
            continue

        room_outlet_settings = []
        
        for pdu in room_pdus:
            pdu_address = pdu.hostAddress
            # Fetch outlet settings or other information about the device if needed
            # Replace the following line with your actual implementation
            pdu_outlet_info = pdu.get_outlet_info()
            pdu_outlet_settings = {
                'pdu_address': pdu_address,
                'outlet_settings': pdu_outlet_info
            }
            room_outlet_settings.append(pdu_outlet_settings)

        # Add room outlet settings to the main list
        pdu_outlet_settings_all.append({
            'room_code': room_code,
            'pdus': room_outlet_settings
        })

    conn.close()
    
    return jsonify(pdu_outlet_settings_all)

@app.route('/pdu/view_outlet_settings_all', methods=['GET'])
def view_outlet_settings_all_old():        
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()
    
    if len(devices) < 1:
        return jsonify({'message': 'No devices added yet. Please add a device first.'}), 200
        
    logger.info("testing.... in view_outlet_settings_all")
    logger.info(f"testing.... devices is: {devices}")

    outlet_settings_all = []
    for index, device in enumerate(devices):
        device_outlet_info = device.get_outlet_info()
        device_outlet_settings = {
            'device_number': index + 1,
            'host_address': device.hostAddress,
            'outlet_settings': device_outlet_info
        }
        outlet_settings_all.append(device_outlet_settings)

    return jsonify(outlet_settings_all)


@app.route('/view_all_pdu_settings/<string:room_code>/<string:pdu_address>', methods=['GET'])
def view_all_pdu_settings(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    # You can use the selected_device to retrieve system settings or other information
    # Here you can customize the response based on your requirements
    system_settings = selected_device.get_all_info()

    return jsonify(system_settings)

#@app.route('/pdu/devices/<string:host_address>/change_system_settings', methods=['PUT'])
@app.route('/change_pdu_system_settings/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def change_system_settings(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()
        
    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    new_system_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    system_name = new_system_settings.get('system_name', None)
    system_contact = new_system_settings.get('system_contact', None)
    location = new_system_settings.get('location', None)
    #driver = new_system_settings.get('driver', None)
    
    logger.info(f"in change_system_settings: {system_name}, {system_contact}, {location}")

    selected_device.change_system_settings(
        system_name=system_name,
        system_contact=system_contact,
        location=location,
        #driver=driver
    )

    return jsonify({'message': 'System settings updated successfully.'})
    
#@app.route('/pdu/devices/<string:host_address>/change_user_settings', methods=['PUT'])
@app.route('/change_pdu_user_settings/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def change_user_settings(room_code, pdu_address):
    # Check for required fields in the JSON data
    required_fields = ['new_username', 'new_password']
    if not request.is_json or not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    new_user_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    new_username = new_user_settings.get('new_username')
    new_password = new_user_settings.get('new_password')
    # driver = new_user_settings.get('driver', None)

    # Update the selected device's settings
    selected_device.change_user_settings(
        new_username=new_username,
        new_password=new_password,
        # driver=driver
    )

    # Update the device settings in the SQLite database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE pdus SET username=%s, password=%s WHERE pdu_address=%s AND room_code=%s',
        (new_username, new_password, pdu_address, room_code)
    )
    conn.commit()
    conn.close()

    # Update the device in the app.config['pdu_data']
    for index, device in enumerate(devices):
        if device.hostAddress == pdu_address:
            devices[index] = selected_device
            break

    # Update the cached devices in app.config
    app.config['pdu_data'] = devices

    return jsonify({'message': 'User settings updated successfully.'})

@app.route('/pdu/devices/<string:host_address>/change_user_settings', methods=['PUT'])
def change_user_settings_old(host_address):
    # Check for required fields in the JSON data
    required_fields = ['new_username', 'new_password']
    if not request.is_json or not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

    new_user_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    new_username = new_user_settings.get('new_username', None)
    new_password = new_user_settings.get('new_password', None)
    # driver = new_user_settings.get('driver', None)

    # Update the selected device's settings
    selected_device.change_user_settings(
        new_username=new_username,
        new_password=new_password,
        # driver=driver
    )

    # Update the device settings in the SQLite database
    conn = sqlite3.connect('pdu_devices.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE pdu_devices SET username=?, password=%s WHERE host_address=%s',
        (new_username, new_password, host_address)
    )
    conn.commit()
    conn.close()

    # Update the device in the app.config['pdu_data']
    for index, device in enumerate(devices):
        if device.hostAddress == host_address:
            devices[index] = selected_device
            break

    # Update the cached devices in app.config
    app.config['pdu_data'] = devices

    return jsonify({'message': 'User settings updated successfully.'})

#@app.route('/pdu/devices/<string:host_address>/change_ping_action_settings', methods=['PUT'])
@app.route('/change_pdu_ping_action_settings/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def change_ping_action_settings(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    new_ping_action_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    outletA_IP = new_ping_action_settings.get('outletA_IP', None)
    outletA_action = new_ping_action_settings.get('outletA_action', None)
    outletA_active = new_ping_action_settings.get('outletA_active', None)
    outletB_IP = new_ping_action_settings.get('outletB_IP', None)
    outletB_action = new_ping_action_settings.get('outletB_action', None)
    outletB_active = new_ping_action_settings.get('outletB_active', None)

    selected_device.change_ping_action_settings(
        outletA_IP=outletA_IP,
        outletA_action=outletA_action,
        outletA_active=outletA_active,
        outletB_IP=outletB_IP,
        outletB_action=outletB_action,
        outletB_active=outletB_active
    )

    return jsonify({'message': 'Ping action settings updated successfully.'})

#@app.route('/pdu/devices/<string:host_address>/set_outlet_power_state', methods=['PUT'])
@app.route('/change_pdu_outlet_power_state/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def change_outlet_settings(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    new_outlet_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    outlet_name = new_outlet_settings.get('outlet_name')
    action = new_outlet_settings.get('action')

    selected_device.change_power_action(
        outlet_name=outlet_name,
        action=action
    )

    return jsonify({'message': 'Outlet settings updated successfully.'})
	    
#@app.route('/pdu/devices/<string:host_address>/change_pdu_settings', methods=['PUT'])
@app.route('/change_pdu_pdu_settings/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def change_pdu_settings(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    new_pdu_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    outletA_name = new_pdu_settings.get('outletA_name', None)
    outletA_onDelay = new_pdu_settings.get('outletA_onDelay', None)
    outletA_offDelay = new_pdu_settings.get('outletA_offDelay', None)
    outletB_name = new_pdu_settings.get('outletB_name', None)
    outletB_onDelay = new_pdu_settings.get('outletB_onDelay', None)
    outletB_offDelay = new_pdu_settings.get('outletB_offDelay', None)

    selected_device.change_pdu_settings(
        outletA_name=outletA_name,
        outletA_onDelay=outletA_onDelay,
        outletA_offDelay=outletA_offDelay,
        outletB_name=outletB_name,
        outletB_onDelay=outletB_onDelay,
        outletB_offDelay=outletB_offDelay
    )

    return jsonify({'message': 'PDU settings updated successfully.'})
    
#@app.route('/pdu/devices/<string:host_address>/change_network_settings', methods=['PUT'])
@app.route('/change_pdu_network_settings/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def change_network_settings(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    new_network_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    dhcp = new_network_settings.get('dhcp', None)
    IP = new_network_settings.get('IP', None)
    subnet = new_network_settings.get('subnet', None)
    gateway = new_network_settings.get('gateway', None)
    DNS1 = new_network_settings.get('DNS1', None)
    DNS2 = new_network_settings.get('DNS2', None)

    selected_device.change_network_settings(
        dhcp=dhcp,
        IP=IP,
        subnet=subnet,
        gateway=gateway,
        DNS1=DNS1,
        DNS2=DNS2
    )

    return jsonify({'message': 'Network settings updated successfully.'})
    
#@app.route('/pdu/devices/<string:host_address>/enable_disable_dhcp', methods=['PUT'])
@app.route('/change_pdu_dhcp_setting/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def enable_disable_dhcp(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    dhcp_option = request.get_json().get('dhcp_option')

    selected_device.change_dhcp_setting(dhcp=dhcp_option)
    return jsonify({'message': 'DHCP settings updated successfully.'})

#@app.route('/pdu/devices/<string:host_address>/change_time_settings', methods=['PUT'])
@app.route('/change_pdu_time_setting/<string:room_code>/<string:pdu_address>', methods=['PUT'])
def change_time_settings(room_code, pdu_address):
    devices = None        
    if app.config['pdu_data'] is not None:
        # There is data in app.config['pdu_data']
        devices = app.config['pdu_data']
    else:
        # app.config['pdu_data'] is None, so it's not populated with data
        devices = get_or_create_devices()

    selected_device = None

    for device in devices:
        if device.room_code == room_code and device.hostAddress == pdu_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {pdu_address} in room {room_code} not found.'}), 200

    internet_time_option = request.get_json().get('internet_time_option')

    selected_device.change_time_settings(internet_time=internet_time_option)
    return jsonify({'message': 'Time settings updated successfully.'})

# =========================================================================
#  UNTESTED - endpoints
# =========================================================================

# upload images to a directory on a remote windows pc - delete any images already in that dir path
#
# To send image files to the API endpoint, you can use the multipart/form-data encoding type in the request. This encoding type allows you to send binary data, such as image files, as part of the HTTP request body.
# Here's an example of how you can send image files to the API endpoint using multipart/form-data encoding type: 

## =========================================================================
# import requests
# url = 'http://example.com/upload_images'
# data = {
#     'hostname': 'remote-server',
#     'username': 'remote-username',
#     'password': 'remote-password',
#     'directory': '/path/to/remote/directory',
# }
# files = [
#     ('images', ('image1.jpg', open('image1.jpg', 'rb'), 'image/jpeg')),
#     ('images', ('image2.png', open('image2.png', 'rb'), 'image/png')),
# ]
#
# response = requests.post(url, data=data, files=files)
# print(response.json())
## =========================================================================

# In this example, we're using the requests library to send a POST request to the API endpoint at http://example.com/upload_images. The request includes the following data:
# hostname: The hostname or IP address of the remote server.
# username: The username to use for the SSH connection.
# password: The password to use for the SSH connection.
# directory: The directory path on the remote server where the image files should be uploaded.
# The request also includes a list of files to be uploaded. Each file is represented by a tuple in the files list:
#
# The first element of the tuple is the name of the parameter to use for the file in the request body. In this case, we're using images as the parameter name.
# The second element of the tuple is a tuple representing the file itself. The first element of this tuple is the filename of the file (e.g. 'image1.jpg'), the second element is an open file handle to the file (e.g. open('image1.jpg', 'rb')), and the third element is the content type of the file (e.g. 'image/jpeg').
# When the server receives this request, it will receive the hostname, username, password, and directory values as JSON-encoded data in the request body, and the image files will be included as binary data in the multipart/form-data encoded request body.
#
# You can adjust the files list to include as many files as you need to upload, and you can adjust the filenames and content types to match the actual filenames and content types of the files you're uploading.
from pathlib import Path
@app.route('/upload_images', methods=['POST'])
def upload_images():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password', 'directory']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Extract the list of image files from the request.
    files = request.files.getlist('images')

    # SSH into the Windows PC using Paramiko.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(data['hostname'], username=data['username'], password=data['password'])

    # Upload the image files to the specified directory path.
    sftp = ssh.open_sftp()
    for file in files:
        remote_path = Path(data['directory']) / file.filename
        sftp.put(file, str(remote_path))

    sftp.close()
    ssh.close()

    return jsonify({'message': 'Images uploaded successfully.'}), 200

# turn down volume using paramiko
def turn_down_volume(hostname, username, password):
    # Create an SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the remote Windows computer
        client.connect(hostname, username=username, password=password)

        # Send the command to turn down the volume
        command = "nircmd.exe changesysvolume -2000"
        stdin, stdout, stderr = client.exec_command(command)

        # Print the output of the command
        print(stdout.read().decode())

    except paramiko.AuthenticationException:
        print("Authentication failed, please verify your credentials.")
    except paramiko.SSHException as sshException:
        print(f"Unable to establish SSH connection: {sshException}")
    except paramiko.Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        # Close the SSH connection
        client.close()

# set/change volume using paramiko
# to use: change_volume('hostname', 'username', 'password', 'mute')
def change_volume(hostname, username, password, action, step=2000):
    # Create an SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the remote Windows computer
        client.connect(hostname, username=username, password=password)

        # Send the command to change the volume
        if action == 'down':
            command = f"nircmd.exe changesysvolume -{step}"
        elif action == 'up':
            command = f"nircmd.exe changesysvolume +{step}"
        elif action == 'mute':
            command = "nircmd.exe mutesysvolume 1"
        elif action == 'unmute':
            command = "nircmd.exe mutesysvolume 0"
        else:
            return {'error': 'Invalid action provided'}

        stdin, stdout, stderr = client.exec_command(command)

        # Print the output of the command
        print(stdout.read().decode())

        return {'success': f"Volume {action}ed successfully"}
    except paramiko.AuthenticationException:
        return {'error': "Authentication failed, please verify your credentials."}
    except paramiko.SSHException as sshException:
        return {'error': f"Unable to establish SSH connection: {sshException}"}
    except paramiko.Exception as e:
        return {'error': f"Exception occurred: {e}"}
    finally:
        # Close the SSH connection
        client.close()

# To use this API route, you can send a POST request to http://your-server-url/change_volume with
# a JSON body containing the hostname, username, password, action, and step parameters.
# For example:
# {
#     "hostname": "192.168.1.100",
#     "username": "user",
#     "password": "pass",
#     "action": "up",
#     "step": 1000
# }
@app.route('/change_volume', methods=['POST'])
def change_volume_api():
    # Get the hostname, username, password, action, and step from the request body
    data = request.get_json()
    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    action = data.get('action')
    step = data.get('step', 2000)

    # Call the change_volume function
    result = change_volume(hostname, username, password, action, step)

    # Return the result as a JSON response
    return jsonify(result)

# add device function for init
def initial_add_device(host_address, master_username, master_password, chrome_driver_path):
    #current_directory = os.path.dirname(os.path.abspath(__file__))
    #chrome_driver_path = os.path.join(current_directory, 'chromedriver')

    new_device = DeviceController(host_address, master_username, master_password, chrome_driver_path)

    try:
        new_device.connect()
        return {'success': 'Device added successfully!'}
    except Exception as e:
        return {'error': 'Device not reachable...'}

## CONTAINER health-check
@app.route("/ping")
def ping():
    return "{status: ok}"

# =========================================================================
#  START API
# =========================================================================
if __name__ == '__main__':    
    app.run(host="0.0.0.0", port=conf.APP_PORT, debug=True, use_reloader=True)
