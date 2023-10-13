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


from flask import Flask, jsonify, request, render_template
from flask_cors import CORS, cross_origin
import paramiko
import platform
import json
import re

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


# open powerpoint slide file/url on remote windows pc in google chrome
def run_powerpoint(hostname, username, password, url=None):
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
            chrome = "c:\Program Files\Google\Chrome\Application\chrome.exe"

            # Execute the qwinsta command to retrieve session information for the target user
            session_id = get_session_id(client, username)

            if session_id:
                # Build psexec command string to open chrome in kiosk mode, at url
                command = f"psexec -accepteula -u {username} -p {password} -d -i {session_id} \"{chrome}\"  \"--kiosk\" \"{url}\""

                print("\n", command, "\n")
                
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

                # send powerpoint on chronme command
                #_, stdout, stderr = client.exec_command(command)
                
                # Capture the exit status and PID
                #exit_status = stdout.channel.recv_exit_status()
                #output = stdout.read().decode().strip()

                # Extract the PID from the output
                #pid_match = re.search(r"PID (\d+)", output)
                #pid = pid_match.group(1) if pid_match else None

                #if exit_status == 0:
                #    return {'pid': pid} if pid else {'error': 'Failed to retrieve PID'}
                #else:
                #    return {'error': f'PowerPoint failed with exit status: {exit_status}'}
                

                # capture exit status, on success exist status is PID for chrome
                # Need to check what exit status is when fails... does it ever fail?
                #exit_status = stdout.channel.recv_exit_status()
                #if exit_status == 0:
                #return int(exit_status)
            else:
                return f"No active session found for {username}."

            #else:
            #    return f"powerpoint failed with exit status: {exit_status}."

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


# run a program on remote windows pc - NEED TO TEST
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
            
                # Create the command to open the specified application with the given arguments
                command = f"psexec -accepteula -u {username} -p {password} -d -i {session_id} \"{application}\""

                if arguments is not None:
                    command += f' \"{arguments}\"'
                    
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

            # send command
            #stdin, stdout, stderr = client.exec_command(command)
            #print(stdin, stdout, stderr)

            # capture exit status
            #exit_status = stdout.channel.recv_exit_status()
            #if exit_status == 0:
            #return f"{exit_status}"
            #else:
            #    return f"command failed with exit status {exit_status}."

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

            # Specify the path to NirCmd and its executable file names
            nircmd_path = 'C:/NirCmd/'
            nircmd_executable = 'nircmd.exe'
            nircmdc_executable = 'nircmdc.exe'

            # Build the full nircmd command with the specified path
            command = f'{nircmd_path}{nircmd_executable} {cmd}'

            # Send the nircmd command
            _, stdout, stderr = client.exec_command(command)

            # Capture exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                return f"NirCmd command successful."
            else:
                return f"NirCmd command failed with exit status {exit_status}."

        except Exception as e:
            return {'error': str(e)}
            
# Initialize an empty list to store host data
app.config['host_data'] = []

# # Helper function to load PC host devices from the text file
# def load_pc_hosts():
    # with open('pc_hosts.txt', 'r') as file:
        # lines = file.readlines()
    # hosts = []
    # for line in lines:
        # host_address, username, password = line.strip().split(',')
        # hosts.append({
            # 'host_address': host_address,
            # 'username': username,
            # 'password': password
        # })  # Create a dictionary with host data
    # return hosts

# # Helper function to save PC host devices to the text file
# def save_pc_hosts(hosts):
    # with open('pc_hosts.txt', 'w') as file:
        # for host in hosts:
            # file.write(f"{host['host_address']},{host['username']},{host['password']}\n")

# # Load PC host devices when the Flask app starts
# @app.before_first_request
# def load_hosts():
    # app.config['host_data'] = load_pc_hosts()
    
# Initialize SQLite database
def init_db():
    # Initialize SQLite database for host data
    host_conn = sqlite3.connect('host_data.db')
    host_cursor = host_conn.cursor()

    # Create a table to store host data if it doesn't exist
    host_cursor.execute('''
        CREATE TABLE IF NOT EXISTS hosts (
            host_address TEXT PRIMARY KEY,
            username TEXT,
            password TEXT,
            platform TEXT NULL
        )
    ''')
    
    
    #host_cursor.execute('''
    #    CREATE TABLE IF NOT EXISTS hosts (
    #        id INTEGER PRIMARY KEY AUTOINCREMENT,
    #        host_address TEXT,
    #        username TEXT,
    #        password TEXT,
    #        platform TEXT NULL
    #    )
    #''')

    host_conn.commit()
    host_conn.close()

    # Initialize SQLite database for PDU devices
    pdu_conn = sqlite3.connect('pdu_devices.db')
    pdu_cursor = pdu_conn.cursor()

    # Create a table to store PDU device data if it doesn't exist
    #pdu_cursor.execute('''
    #    CREATE TABLE IF NOT EXISTS pdu_devices (
    #        host_address TEXT RIMARY KEY,
    #        username TEXT,
    #        password TEXT,
    #        driver_path TEXT
    #    )
    #''')
    
    pdu_cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdu_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_address TEXT,
            username TEXT,
            password TEXT,
            driver_path TEXT
        )
    ''')

    pdu_conn.commit()
    pdu_conn.close()

@app.before_first_request
def before_first_request():
    init_db()

def get_db_connection(database='host_data.db'):
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    return conn

# @app.route('/add_host', methods=['POST'])
# def add_host():
    # data = request.get_json()
    # host_address = data.get('host_address')
    # username = data.get('username')
    # password = data.get('password')

    # conn = get_db_connection()
    # cursor = conn.cursor()

    # # Check if the host address already exists in the database
    # cursor.execute('SELECT id FROM hosts WHERE host_address = ?', (host_address,))
    # existing_host = cursor.fetchone()

    # if existing_host:
        # conn.close()
        # return jsonify({'message': 'Host with the same address already exists'}), 200

    # # Insert the host data into the database
    # cursor.execute('INSERT INTO hosts (host_address, username, password) VALUES (?, ?, ?)',
                   # (host_address, username, password))
    # conn.commit()
    # conn.close()

    # return jsonify({'message': 'Host added successfully'}), 200
    
@app.route('/add_host', methods=['POST'])
def add_host():
    logger.info(f"Testing: /add_host")
    data = request.get_json()

    # Check if the required fields are present in the JSON data
    required_fields = ['host_address', 'username', 'password']
    if not all(key in data for key in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    host_address = data.get('host_address')
    logger.info(f"Testing: /add_host host_address: {host_address}")
    username = data.get('username')
    logger.info(f"Testing: /add_host username: {username}")
    password = data.get('password')
    logger.info(f"Testing: /add_host password: {password}")
    
    # Get the optional 'platform' field if it exists in the JSON data
    platform = data.get('platform')
    logger.info(f"Testing: /add_host platform: {platform}")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the host address already exists in the database
    cursor.execute('SELECT host_address FROM hosts WHERE host_address = ?', (host_address,))
    existing_host = cursor.fetchone()

    if existing_host:
        logger.info(f"Testing: /add_host existing_host: {existing_host}")
        conn.close()
        return jsonify({'message': 'Host with the same address already exists'}), 200

    # Insert the host data into the database, including the platform if provided
    if platform is not None:
        logger.info(f"Testing: /add_host if platform is not None is true: {platform}")
        cursor.execute('INSERT INTO hosts (host_address, username, password, platform) VALUES (?, ?, ?, ?)',
                       (host_address, username, password, platform))
    else:
        logger.info(f"Testing: /add_host if platform is not None is false: {platform}")
        cursor.execute('INSERT INTO hosts (host_address, username, password) VALUES (?, ?, ?)',
                       (host_address, username, password))

    conn.commit() 
    
    # Query the database to retrieve the added host
    cursor.execute('SELECT * FROM hosts WHERE host_address = ?', (host_address,))
    added_host = cursor.fetchone()
    logger.info(f"Added host in the database: {added_host}")
    
    # Log the actual values
    if added_host:
        logger.info(f"Added host: host_address={added_host[0]}, username={added_host[1]}, password={added_host[2]}, platform={added_host[3]}")

    # Check the database structure and platform data type
    try:
        # Check if the "hosts" table exists
        cursor.execute("PRAGMA table_info(hosts)")
        table_info = cursor.fetchall()

        # Log the table structure
        for column in table_info:
            column_name, data_type, _, _, _, _ = column
            logger.info(f"Column Name: {column_name}, Data Type: {data_type}")

        # Check the data type of the "platform" column
        for column in table_info:
            column_name, data_type, _, _, _, _ = column
            if column_name == 'platform':
                logger.info(f"Data Type of 'platform' Column: {data_type}")

    except sqlite3.Error as e:
        logger.error(f"Error: {e}")

    conn.close()

    return jsonify({'message': 'Host added successfully'}), 200

# @app.route('/remove_host/<int:host_id>', methods=['POST'])
# def remove_host(host_id):
    # conn = get_db_connection()
    # cursor = conn.cursor()

    # # Check if the host exists in the database
    # cursor.execute('SELECT id FROM hosts WHERE id = ?', (host_id,))
    # existing_host = cursor.fetchone()

    # if not existing_host:
        # conn.close()
        # return jsonify({'error': 'Host not found'}), 200

    # # Remove the host from the database
    # cursor.execute('DELETE FROM hosts WHERE id = ?', (host_id,))
    # conn.commit()
    # conn.close()

    # return jsonify({'success': 'Host removed successfully!'}), 200
    
@app.route('/remove_host/<string:host_address>', methods=['POST'])
def remove_host(host_address):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the host exists in the database
    cursor.execute('SELECT host_address FROM hosts WHERE host_address = ?', (host_address,))
    existing_host = cursor.fetchone()

    if not existing_host:
        conn.close()
        return jsonify({'error': 'Host not found'}), 200

    # Remove the host from the database
    cursor.execute('DELETE FROM hosts WHERE host_address = ?', (host_address,))
    conn.commit()
    conn.close()

    return jsonify({'success': 'Host removed successfully!'}), 200


@app.route('/remove_host_address', methods=['POST'])
def remove_host_address():
    data = request.get_json()

    # Check if the required 'host_address' field is present in the JSON data
    if 'host_address' not in data:
        return jsonify({'error': 'Missing required field(s)'}), 400

    host_address = data['host_address']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the host exists in the database based on 'host_address'
    cursor.execute('SELECT host_address FROM hosts WHERE host_address = ?', (host_address,))    
    existing_host = cursor.fetchone()

    if not existing_host:
        conn.close()
        return jsonify({'error': 'Host not found'}), 404

    # Remove the host from the database based on 'host_address'
    cursor.execute('DELETE FROM hosts WHERE host_address = ?', (host_address,))
    conn.commit()
    conn.close()

    return jsonify({'success': 'Host removed successfully!'}), 200


@app.route('/get_hosts', methods=['GET'])
def get_hosts():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM hosts')
    hosts = cursor.fetchall()
    conn.close()
    
    logger.info(f"testing.... in get_hosts, cursor.execute('SELECT * FROM hosts') is: {hosts}")
    
    if len(hosts) < 1:
        return jsonify({'message': 'No hosts added yet. Please add a host first.'}), 200

    host_list = []
    #for host in hosts:
    #    host_list.append({
    #        'host_id': host['id'],
    #        'host_address': host['host_address']
    #    })
    
    host_id = 1  # Initialize host_id to 0

    for host in hosts:
        host_list.append({
            'host_id': host_id,
            'host_address': host['host_address']
        })
        host_id += 1  # Increment host_id for the next host

    logger.info(f"testing.... in get_hosts, host_list is: {host_list}")
    
    return jsonify({'hosts': host_list}), 200

# =========================================================================
#  API - endpoints
# =========================================================================

# home endpoint - displays a list of the current API endpoints
@app.route('/home')
def home():
    endpoints = [
        {
            'url': '/mute_device',
            'method': 'POST',
            'description': 'Mute or unmute the volume on a remote computer.',
            'example_payload': {
                'hostname': 'remote-hostname.com',
                'username': 'remote-username',
                'password': 'remote-password',
                'mute': True
            }
        },
        {
            'url': '/reboot_device',
            'method': 'POST',
            'description': 'Reboot a remote computer.',
            'example_payload': {
                'hostname': 'remote-hostname.com',
                'username': 'remote-username',
                'password': 'remote-password'
            }
        },
        {
            'url': '/open_powerpoint',
            'method': 'POST',
            'description': 'Open a PowerPoint presentation on a remote computer.',
            'example_payload': {
                'hostname': 'remote-hostname.com',
                'username': 'remote-username',
                'password': 'remote-password',
                'url': 'presentation-url'
            }
        },
        {
            'url': '/close_process',
            'method': 'POST',
            'description': 'Close a process running on a remote computer.',
            'example_payload': {
                'hostname': 'remote-hostname.com',
                'username': 'remote-username',
                'password': 'remote-password',
                'pid': 'process-id'
            }
        },
        {
            'url': '/open_application',
            'method': 'POST',
            'description': 'Run an application on a remote computer.',
            'example_payload': {
                'hostname': 'remote-hostname.com',
                'username': 'remote-username',
                'password': 'remote-password',
                "application": "C:\\Program Files\\MyApp\\MyApp.exe",
                "arguments": "--arg1 value1 --arg2 value2"
            }
        },
        {
            'url': '/send_nircmd',
            'method': 'POST',
            'description': 'Run system tool nircmd commands on remote windows computer.',
            'example_payload': {
                'hostname': 'remote-hostname.com',
                'username': 'remote-username',
                'password': 'remote-password',
                "command": "screensaver",
            }
        }
    ]

    endpoint_info = ''
    for endpoint in endpoints:
        example_payload_str = json.dumps(endpoint['example_payload'], sort_keys=True, indent=4) #json.dumps(endpoint['example_payload'], indent=4).replace(',', ',\n')    

        endpoint_info += f"<h2>{endpoint['url']}</h2><p><strong>Method:</strong> {endpoint['method']}</p>"
        endpoint_info += f"<p><strong>Description:</strong> {endpoint['description']}</p>"
        endpoint_info += f"<p><strong>Example Payload:</strong> <pre>{example_payload_str}</pre></p><hr>"

    return f"<h1>Welcome to the office space management system!</h1><p>Here is a list of available endpoints:</p>{endpoint_info}"    

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
        cursor.execute('SELECT username, password FROM hosts WHERE host_address = ?', (hostname,))
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

### testing connect to SAMBA
### ========================

# # mute/unmte remote windows pc endpoint
# @app.route('/mute_device', methods=['POST'])
# def mute_device():
    # data = request.get_json()
    # if not all(key in data for key in ['hostname', 'username', 'password', 'mute']):
        # return jsonify({'error': 'Missing required field(s)'}), 400 

    # # Get the hostname, username, and password for the specified computer
    # hostname = data.get('hostname')
    # username = data.get('username')
    # password = data.get('password')
    # mute = data.get('mute')
    # platformInput = data.get('platformInput')

    # print("\n", hostname, username, password, mute, "\n")

    # # Reboot the remote computer
    # result = run_mute_device(hostname, username, password, mute, platformInput)

    # if result is None:
        # return jsonify({'error': 'backend function failed'}), 500
    # else:
        # return jsonify({'response': result}), 200

@app.route('/mute_device', methods=['POST'])
def mute_device():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'mute']):
        return jsonify({'error': 'Missing required field(s)'}), 400 

    # Get the hostname and mute status
    hostname = data.get('hostname')
    mute = data.get('mute')

    # Fetch the username, password, and platform from the database based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password, platform FROM hosts WHERE host_address = ?', (hostname,))
    host_info = cursor.fetchone()
    conn.close()

    if host_info is None:
        return jsonify({'error': 'Host not found'}), 404

    username, password, platform = host_info

    print("\n", hostname, username, password, mute, platform, "\n")

    # Reboot the remote computer
    result = run_mute_device(hostname, username, password, mute, platform)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

# reboot remote pc endpoint
@app.route('/reboot_device_by_platform', methods=['POST'])
def reboot_windows():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password']):
        return jsonify({'error': 'Missing required field(s)'}), 400 

    # Get the hostname, username, and password for the specified computer
    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    platform = data.get('platform')

    print("\n", hostname, username, password, "\n")

    # Reboot the remote computer
    result = run_reboot_device(hostname, username, password, platform)

    if result is None:
        return jsonify({'error': 'backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


@app.route('/reboot_device', methods=['POST'])
def reboot_device():
    logger.info("Testing: in reboot_device")
    data = request.get_json()
    if 'hostname' not in data:
        return jsonify({'error': 'Missing required field(s)'}), 400 

    # Get the hostname (host address) from the request
    hostname = data.get('hostname')
    logger.info(f"Testing: in reboot_device, hostname: {hostname}")

    # Query the database to retrieve the username and password based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password, platform FROM hosts WHERE host_address = ?', (hostname,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404
        
    # Log the actual values
    if host_data:
        try:
            logger.info(f"retrieved host: host_address={hostname}, username={host_data[0]}, password={host_data[1]}, platform={host_data[2]}")
        except:
            logger.info(f"retrieved host platform excepted...")
            logger.info(f"retrieved host: host_address={hostname}, username={host_data[0]}, password={host_data[1]}")
            pass
            
    platform = None

    # Extract the username, password, and platform from the retrieved data if available
    username = host_data[0]
    password = host_data[1]
    platform = host_data[2] if len(host_data) > 2 else None

    # Log the values
    logger.info(f"Testing: in reboot_device, username: {username}")
    logger.info(f"Testing: in reboot_device, password: {password}")
    logger.info(f"Testing: in reboot_device, platform: {platform}")

    # Reboot the remote computer using the retrieved credentials
    result = run_reboot_device(hostname, username, password, platform)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200

# # open powerpoint in chrome on remote windows pc endpoint
# @app.route('/open_powerpoint', methods=['POST'])
# def open_powerpoint():
    # data = request.get_json()
    # if not all(key in data for key in ['hostname', 'username', 'password', 'url']):
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # hostname = data.get('hostname')
    # username = data.get('username')
    # password = data.get('password')
    # url = data.get('url')

    # print("\n", hostname, username, password, url, "\n")

    # # open powerpoint on chrome
    # result = run_powerpoint(hostname, username, password, url)

    # if result is None:
        # return jsonify({'error': 'backend function failed'}), 500
    # else:
        # return jsonify({'response': result}), 200

@app.route('/open_powerpoint', methods=['POST'])
def open_powerpoint():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'url']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')

    # Query the database to retrieve the username and password based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = ?', (hostname,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username = host_data['username']
    password = host_data['password']
    url = data.get('url')

    print("\n", hostname, username, password, url, "\n")

    # Open PowerPoint on Chrome using the retrieved credentials
    result = run_powerpoint(hostname, username, password, url)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


# # open powerpoint in chrome on remote windows pc endpoint
# @app.route('/get_user_session_id', methods=['GET'])
# def get_user_session_id():
    # data = request.get_json()
    # if not all(key in data for key in ['hostname', 'username', 'password', 'target_username']):
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # hostname = data.get('hostname')
    # username = data.get('username')
    # password = data.get('password')
    # target_username = data.get('target_username')

    # print("\n", hostname, username, password, target_username, "\n")

    # # check for target_username's session ID on remote host
    # result = run_get_session_id(hostname, username, password, target_username)

    # if result is None:
        # return jsonify({'response': f"No user session ID found for {target_username}"}), 200
    # else:
        # return jsonify({'response': result}), 200


@app.route('/get_user_session_id', methods=['POST'])
def get_user_session_id():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'target_username']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')

    # Query the database to retrieve the username and password based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = ?', (hostname,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username = host_data['username']
    password = host_data['password']
    target_username = data.get('target_username')

    print("\n", hostname, username, password, target_username, "\n")

    # Check for target_username's session ID on the remote host using the retrieved credentials
    result = run_get_session_id(hostname, username, password, target_username)

    if result is None:
        return jsonify({'response': f"No user session ID found for {target_username}"}), 200
    else:
        return jsonify({'response': result}), 200


# # kill running process on remote windows pc endpoint
# @app.route('/close_process', methods=['POST'])
# def close_process():
    # data = request.get_json()
    # if not all(key in data for key in ['hostname', 'username', 'password', 'pid']):
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # hostname = data.get('hostname')
    # username = data.get('username')
    # password = data.get('password')
    # pid = data.get('pid')

    # print("\n", hostname, username, password, pid, "\n")

    # # kill process
    # result = kill_process(hostname, username, password, pid)

    # if result is None:
        # return jsonify({'error': 'backend function failed'}), 500
    # else:
        # return jsonify({'response': result}), 200


@app.route('/close_process', methods=['POST'])
def close_process():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'pid']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')

    # Query the database to retrieve the username and password based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = ?', (hostname,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username = host_data['username']
    password = host_data['password']
    pid = data.get('pid')

    print("\n", hostname, username, password, pid, "\n")

    # Kill the process on the remote host using the retrieved credentials
    result = kill_process(hostname, username, password, pid)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200



# @app.route('/open_application', methods=['POST'])
# def open_application_route():
    # data = request.get_json()
    # if not all(key in data for key in ['hostname', 'username', 'password', 'application']):
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # hostname = data.get('hostname')
    # username = data.get('username')
    # password = data.get('password')
    # application = data.get('application')
    # arguments = data.get('arguments')

    # print("\n", hostname, username, password, application, arguments, "\n")

    # # open application
    # result = run_application(hostname, username, password, application, arguments)

    # if result is None:
        # return jsonify({'error': 'backend function failed'}), 500
    # else:
        # return jsonify({'response': result}), 200


@app.route('/open_application', methods=['POST'])
def open_application_route():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'application']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')

    # Query the database to retrieve the username and password based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = ?', (hostname,))
    host_data = cursor.fetchone()
    conn.close()

    if host_data is None:
        return jsonify({'error': 'Host not found'}), 404

    # Extract the username and password from the retrieved data
    username = host_data['username']
    password = host_data['password']
    application = data.get('application')
    arguments = data.get('arguments')

    print("\n", hostname, username, password, application, arguments, "\n")

    # Open the application on the remote host using the retrieved credentials
    result = run_application(hostname, username, password, application, arguments)

    if result is None:
        return jsonify({'error': 'Backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


# @app.route('/send_nircmd', methods=['POST'])
# def send_nircmd():
    # data = request.get_json()
    # if not all(key in data for key in ['hostname', 'username', 'password', 'command']):
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # hostname = data.get('hostname')
    # username = data.get('username')
    # password = data.get('password')
    # command = data.get('command')

    # print("\n", hostname, username, password, command, "\n")

    # # run nircmd
    # result = run_nircmd(hostname, username, password, application, arguments)

    # if result is None:
        # return jsonify({'error': 'backend function failed'}), 500
    # else:
        # return jsonify({'response': result}), 200

@app.route('/send_nircmd', methods=['POST'])
def send_nircmd():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'command']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')
    command = data.get('command')

    # Fetch the username and password from the database based on the hostname
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM hosts WHERE host_address = ?', (hostname,))
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

# ====================================
# CHROMEDRIVER INSTALLATION
# ====================================
PLATFORM_MAPPING = {
    'Linux': 'linux64',
    'Darwin': 'mac-x64',
    'Windows': 'win64' if platform.architecture()[0] == '64bit' else 'win32'
}

def download_chromedriver():
    os_name = platform.system()

    if os_name in PLATFORM_MAPPING:
        os_arch = PLATFORM_MAPPING[os_name]
        chromedriver_filename = 'chromedriver.exe' if os_name == 'Windows' else 'chromedriver'
    else:
        print(f"Chromedriver for your operating system '{os_name}' is not available.")
        return None

    # Check if chromedriver file already exists
    if os.path.exists(chromedriver_filename):
        print("SUCCESS! Chromedriver found in current directory.")
        return chromedriver_filename
    
    json_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    
    response = requests.get(json_url)
    if response.status_code == 200:
        json_data = response.json()
    else:
        print(f"Failed to retrieve JSON data: {response.status_code} - {response.reason}")
        return None
    
    try:
        chromedriver_url = next(item['url'] for item in json_data['channels']['Stable']['downloads']['chromedriver'] if item['platform'] == os_arch)
    except StopIteration:
        print(f"Chromedriver for platform '{os_arch}' is not available in the JSON data.")
        return None
    
    chromedriver_zip = chromedriver_url.split('/')[-1]
    
    print(f"Downloading ChromeDriver for '{os_name}'...")
    response = requests.get(chromedriver_url, stream=True)
    
    if response.status_code == 200:
        with open(chromedriver_zip, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        
        with ZipFile(chromedriver_zip, 'r') as zip_ref:
            extracted_files = zip_ref.namelist()
            chromedriver_subpath = next((file for file in extracted_files if chromedriver_filename in file), None)
            
            if chromedriver_subpath:
                print(f"Extracting '{chromedriver_subpath}'...")
                zip_ref.extract(chromedriver_subpath)       
                shutil.move(chromedriver_subpath, '.')
                
                try:
                    # Get the subdirectory name from the extracted chromedriver subpath
                    zip_subdir = os.path.dirname(chromedriver_subpath)
                    print("SUCCESS! ChromeDriver downloaded and extracted successfully.")
                except:
                    print("ERROR! ChromeDriver downloaded and extracted FAILED.")
            else:
                print(f"'{chromedriver_filename}' not found in the zip archive.")
                
        # Remove zip file and subdirectory
        try:
            os.remove(chromedriver_zip)
            shutil.rmtree(zip_subdir)
            print("Zip and non-critical driver files removed.")
        except:
            pass
        
        return chromedriver_filename
    else:
        print(f"Failed to download ChromeDriver: {response.status_code} - {response.reason}")
        return None

# Set the path to the Chrome WebDriver file
#chrome_driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")
#chrome_driver_path = "/home/innovation-hub-api/api/chromedriver"

current_directory = os.path.dirname(os.path.abspath(__file__))
chrome_driver_path = os.path.join(current_directory, 'chromedriver')

master_username = "admin"
master_password = "admin"

# Initialize an empty list to store host data
app.config['pdu_data'] = None

from cachetools import TTLCache

object_cache = TTLCache(maxsize=100, ttl=86400)  # Adjust ttl and maxsize as needed, 86400 =24hrs

# Helper function to create and cache devices
def get_or_create_devices():
    pdu_data = app.config['pdu_data']
    
    if pdu_data is not None:
        return pdu_data

    #if 'pdu_data' in object_cache:
    #    return object_cache['pdu_data']
    
    conn = sqlite3.connect('pdu_devices.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pdu_devices')
    rows = cursor.fetchall()
    
    devices = []
    for row in rows:
        host_address = row[1]
        username = row[2]
        password = row[3]
        driver_path = row[4]
        
        new_pdu = DeviceController(host_address, username, password, driver_path)
        
        try:
            new_pdu.connect()
            devices.append(new_pdu)
        except Exception as e:
            pass
            
    conn.close()
    
    #object_cache['pdu_data'] = devices  # Cache the loaded devices
    app.config['pdu_data'] = devices
    return devices


# Helper function to load devices from the text file
# def load_pdu_devices():
    # with open('pdu_devices.txt', 'r') as file:
        # lines = file.readlines()
    # devices = []
    # for line in lines:
        # host_address, username, password, driver_path = line.strip().split(',')
        # new_pdu = DeviceController(host_address, master_username, master_password, chrome_driver_path)
        
        # try:
            # new_pdu.connect()
            # devices.append(new_pdu)
        # except Exception as e:
            # pass
            
    # return devices
    
def load_pdu_devices():
    conn = sqlite3.connect('pdu_devices.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM pdu_devices')
    rows = cursor.fetchall()
    
    logger.info(f"load_pdu_devices.... rows = cursor.fetchall() is: {rows}")
    
    devices = []
    for row in rows:
        host_address = row[1]
        username = row[2]
        password = row[3]
        driver_path = row[4]
        
        new_pdu = DeviceController(host_address, username, password, driver_path)
        
        try:
            new_pdu.connect()
            devices.append(new_pdu)
        except Exception as e:
            pass
            
    conn.close()
    
    logger.info(f"load_pdu_devices.... devices is: {devices}")
    
    return devices
	
# Load PC host devices when the Flask app starts
@app.before_first_request
def load_pdu():
    #app.config['pdu_data'] = load_pdu_devices()
    #logger.info(f"load_pdu.... app.config[pdu_data] is: {app.config['pdu_data']}")
    app.config['pdu_data'] = get_or_create_devices()
    #logger.info(f"load_pdu.... object_cache['pdu_data'] is: {object_cache['pdu_data']}")
    logger.info(f"load_pdu.... app.config[pdu_data] is: {app.config['pdu_data']}") 

# Helper function to load devices from the text file
def load_devices():
    with open('pdu_devices.txt', 'r') as file:
        lines = file.readlines()
    devices = []
    for line in lines:
        host_address, username, password, driver_path = line.strip().split(',')
        devices.append(DeviceController(host_address, username, password, driver_path))
    return devices

# Helper function to save devices to the text file
def save_devices(devices):
    with open('pdu_devices.txt', 'w') as file:
        for device in devices:
            file.write(device.hostAddress, device.username, device.password, device.chromedriver_path + '\n')

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

# Load devices when the app starts
#devices = load_devices()
#devices = []

# =============
# MAIN OPTIONS
# =============	
@app.route('/pdu/devices', methods=['GET'])
def list_devices():    
    logger.info("testing.... in list_devices")

    #pdus = None
    #pdus = app.config['pdu_data']
    #if 'pdu_data' in object_cache:
    #    pdus = object_cache['pdu_data']
    #    logger.info(f"testing.... got pdus = object_cache[pdu_data] <--- here!")
    #else:
        # If the cache doesn't exist, you might want to create it
    #    pdus = get_or_create_devices()
    #    logger.info(f"testing.... got pdus = get_or_create_devices() <--- here!")
        
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
    #devices = app.config['pdu_data']
    #devices = None
    #pdus = app.config['pdu_data']
    #if 'pdu_data' in object_cache:
    #    pdus = object_cache['pdu_data']
    #    logger.info(f"testing.... got pdus = object_cache[pdu_data] <--- here!")
    #else:
        # If the cache doesn't exist, you might want to create it
    #    pdus = get_or_create_devices()
    #    logger.info(f"testing.... got pdus = get_or_create_devices() <--- here!")
        
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

@app.route('/pdu/add_device', methods=['POST'])
def add_device():
    data = request.json
    host_address = data.get('host_address')
    logger.info(f"testing.... add_device {host_address}")
    logger.info(f"testing.... chrome_driver_path {chrome_driver_path}")

    if host_address is None:
        return jsonify({'error': 'Missing required field(s)'}), 400

    #devices = None        
    #if 'pdu_data' in object_cache:
    #    devices = object_cache['pdu_data']
    #    logger.info(f"testing.... got devices = object_cache[pdu_data] <--- here!")
    #else:
        # If the cache doesn't exist, you might want to create it
    #    devices = get_or_create_devices()
    #    logger.info(f"testing.... got devices = get_or_create_devices() <--- here!")
        
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")
        
    #if device_number <= 0 or device_number > len(devices):
    #    return jsonify({'error': 'Invalid device number. Please try again.'}), 200
    
    logger.info(f"testing.... load devices {devices}")

    # Check if a device already exists with the same host address
    for device in devices:
        if device.hostAddress == host_address:
            return jsonify({'error': f'Device with host address {host_address} already exists.'}), 200

    new_device = DeviceController(host_address, master_username, master_password, chrome_driver_path)

    try:
        new_device.connect()
        devices.append(new_device)  # Add the new device to the list

        # Save the devices to the database
        conn = sqlite3.connect('pdu_devices.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO pdu_devices (host_address, username, password, driver_path) VALUES (?, ?, ?, ?)',
            (new_device.hostAddress, new_device.username, new_device.password, new_device.chromedriver_path)
        )
        conn.commit()
        conn.close()

        # Cache the updated devices
        #object_cache['pdu_data'] = devices
        app.config['pdu_data'] = devices

        return jsonify({'success': 'Device added successfully!'})
    except Exception as e:
        return jsonify({'error': 'Device not reachable...'}), 200


# @app.route('/pdu/add_device', methods=['POST'])
# def add_device():
    # data = request.json
    # host_address = data.get('host_address')
    # logger.info(f"testing.... add_device {host_address}")
    # logger.info(f"testing.... chrome_driver_path {chrome_driver_path}")

    # if host_address is None:
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # devices = app.config['pdu_data']
    # logger.info(f"testing.... load devices {devices}")

    # # Check if a device already exists with the same host address
    # for device in devices:
        # if device.hostAddress == host_address:
            # return jsonify({'error': f'Device with host address {host_address} already exists.'}), 200

    # new_device = DeviceController(host_address, master_username, master_password, chrome_driver_path)

    # try:
        # new_device.connect()
        # #devices.append(new_device)
        # app.config['pdu_data'].append(new_device)

        # # Save the devices to the text file
        # with open('pdu_devices.txt', 'a') as file:
            # file.write(f"{host_address},{master_username},{master_password},{chrome_driver_path}\n")

        # return jsonify({'success': 'Device added successfully!'})
    # except Exception as e:
        # return jsonify({'error': 'Device not reachable...'}), 200
        
# @app.route('/pdu/add_device', methods=['POST'])
# def add_device():
    # data = request.json
    # host_address = data.get('host_address')
    # logger.info(f"testing.... add_device {host_address}")
    # logger.info(f"testing.... chrome_driver_path {chrome_driver_path}")

    # if host_address is None:
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # devices = get_or_create_devices()  # Use get_or_create_devices() to get devices
    # logger.info(f"testing.... load devices {devices}")

    # # Check if a device already exists with the same host address
    # for device in devices:
        # if device.hostAddress == host_address:
            # return jsonify({'error': f'Device with host address {host_address} already exists.'}), 200

    # new_device = DeviceController(host_address, master_username, master_password, chrome_driver_path)

    # try:
        # new_device.connect()
        # devices.append(new_device)  # Add the new device to the list

        # # Save the devices to the text file (if needed)
        # with open('pdu_devices.txt', 'a') as file:
            # file.write(f"{host_address},{master_username},{master_password},{chrome_driver_path}\n")

        # return jsonify({'success': 'Device added successfully!'})
    # except Exception as e:
        # return jsonify({'error': 'Device not reachable...'}), 200

# @app.route('/pdu/add_device', methods=['POST'])
# def add_device():
    # data = request.json
    # host_address = data.get('host_address')

    # if host_address is None:
        # return jsonify({'error': 'Missing required field(s)'}), 400

    # conn = get_db_connection('pdu_devices.db')
    # cursor = conn.cursor()

    # # Check if a device already exists with the same host address in the database
    # cursor.execute('SELECT id FROM pdu_devices WHERE host_address = ?', (host_address,))
    # existing_device = cursor.fetchone()

    # if existing_device:
        # conn.close()
        # return jsonify({'error': f'Device with host address {host_address} already exists.'}), 200

    # username = data.get('username')
    # password = data.get('password')
    # driver_path = data.get('driver_path')
    
    # new_device = DeviceController(host_address, master_username, master_password, chrome_driver_path)
    
    # logger.info(f"/pdu/add_device.... devices is: {host_address}")
    
    # try:
        # new_device.connect()
        # logger.info(f"/pdu/add_device.... new_device.connected")
        # app.config['pdu_data'].append(new_device)
        
        # logger.info(f"/pdu/add_device.... appending device to pdu_data app.config array: {app.config['pdu_data'].append(new_device)}")

        # # Insert the new device information into the database
        # cursor.execute('INSERT INTO pdu_devices (host_address, username, password, driver_path) VALUES (?, ?, ?, ?)',
                       # (host_address, username, password, driver_path))
        # conn.commit()
        # conn.close()
        
        # logger.info(f"added device to sql db: {host_address}")

        # return jsonify({'success': 'Device added successfully!'})
    # except Exception as e:
        # return jsonify({'error': 'Device not reachable...'}), 200


# @app.route('/pdu/remove_device/<int:device_choice>', methods=['POST'])
# def remove_device(device_choice):
    # logger.info(f"testing.... in remove_device, passed variable: {device_choice}")

    # if not app.config['pdu_data']:
        # return jsonify({'error': 'No devices added yet. Please add a device first.'}), 200

    # if device_choice <= 0 or device_choice > len(app.config['pdu_data']):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # device_to_remove = app.config['pdu_data'][device_choice - 1]
    # device_to_remove.disconnect()
    # app.config['pdu_data'].pop(device_choice - 1)

    # # Remove the device information from the database
    # conn = get_db_connection('pdu_devices.db')
    # cursor = conn.cursor()

    # host_address_to_remove = device_to_remove.hostAddress
    # cursor.execute('DELETE FROM pdu_devices WHERE host_address = ?', (host_address_to_remove,))
    # conn.commit()
    # conn.close()

    # return jsonify({'success': 'Device removed successfully!'})
    

# Function to remove a device from the cache
#def remove_device_from_cache(device):
#    logger.error(f"Removing {device} from the cache")
#    if 'pdu_data' in object_cache:
#        devices_cache = object_cache['pdu_data']
#        devices_cache.remove(device)
#        object_cache['pdu_data'] = devices_cache
#        logger.error(f" object_cache[pdu_data] {devices_cache}")

def remove_device_from_config(device):
    logger.error(f"Removing {device} from app.config['pdu_data']")
    pdu_data = app.config.get('pdu_data', [])
    
    if device in pdu_data:
        pdu_data.remove(device)
        app.config['pdu_data'] = pdu_data
        logger.error(f"app.config['pdu_data']: {pdu_data}")

# Modify your remove_device function to use the cache management functions
@app.route('/pdu/remove_device/<int:device_choice>', methods=['POST'])
def remove_device(device_choice):
    logger.info(f"testing.... in remove_device, device choice: {device_choice}")

    #devices = None
    #pdus = app.config['pdu_data']
    #if 'pdu_data' in object_cache:
    #    devices = object_cache['pdu_data']
    #    logger.info(f"testing.... in remove_device, devices = object_cache[pdu_data]")
    #else:
        # If the cache doesn't exist, you might want to create it
    #    devices = get_or_create_devices()
    #    logger.info(f"testing.... in remove_device, devices = get_or_create_devices()")
        
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    if not devices:
        return jsonify({'error': 'No devices added yet. Please add a device first.'}), 200

    if device_choice <= 0 or device_choice > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    device_to_remove = devices[device_choice - 1]
    logger.info(f"testing.... in remove_device, device_to_remove: {device_to_remove}")
    device_to_remove.disconnect()

    # Remove the device information from the database
    conn = sqlite3.connect('pdu_devices.db')
    cursor = conn.cursor()

    host_address_to_remove = device_to_remove.hostAddress
    logger.info(f"testing.... in remove_device, host_address_to_remove: {host_address_to_remove}")

    try:
        cursor.execute('DELETE FROM pdu_devices WHERE host_address = ?', (host_address_to_remove,))
        conn.commit()
        logger.info("Device removed from the database.")
    except sqlite3.Error as e:
        logger.error(f"Error removing device from the database: {str(e)}")
    finally:
        conn.close()

    # Remove the device from the cache
    remove_device_from_config(device_to_remove)

    return jsonify({'success': f"Device removed successfully!{device_to_remove} {host_address_to_remove}"})


@app.route('/pdu/remove_device_by_address/<string:host_address>', methods=['POST'])
def remove_device_by_address(host_address):
    logger.info(f"testing.... in remove_device, host_address: {host_address}")

    #devices = None
    #pdus = app.config['pdu_data']
    #if 'pdu_data' in object_cache:
    #    devices = object_cache['pdu_data']
    #else:
        # If the cache doesn't exist, you might want to create it
    #    devices = get_or_create_devices()
        
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    device_to_remove = None

    for device in devices:
        if device.hostAddress == host_address:
            device_to_remove = device
            break

    if device_to_remove is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

    device_to_remove.disconnect()
    devices.remove(device_to_remove)

    # Remove the device information from the database
    conn = sqlite3.connect('pdu_devices.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM pdu_devices WHERE host_address = ?', (host_address,))
        conn.commit()
        logger.info("Device removed from the database.")
    except sqlite3.Error as e:
        logger.error(f"Error removing device from the database: {str(e)}")
    finally:
        conn.close()

    # Remove the device from the cache
    remove_device_from_config(device_to_remove)

    return jsonify({'success': 'Device removed successfully!'})

@app.route('/pdu/view_outlet_settings_all', methods=['GET'])
def view_outlet_settings_all():
    #devices = app.config['pdu_data']
    #devices = None
    #pdus = app.config['pdu_data']
    #if 'pdu_data' in object_cache:
    #    devices = object_cache['pdu_data']
    #else:
        # If the cache doesn't exist, you might want to create it
    #    devices = get_or_create_devices()
        
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")
    
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

# =====================
# DEVICE LEVEL OPTIONS
# =====================
#@app.route('/pdu/devices/<int:device_number>/view_all_settings', methods=['GET'])
#def view_system_settings(device_number):
    #devices = app.config['pdu_data']
    #devices = None
    #pdus = app.config['pdu_data']
    #if 'pdu_data' in object_cache:
    #    devices = object_cache['pdu_data']
    #else:
        # If the cache doesn't exist, you might want to create it
    #    devices = get_or_create_devices()
    #if device_number <= 0 or device_number > len(devices):
    #    return jsonify({'error': 'Invalid device number. Please try again.'}), 200
        
#    devices = None
#    if 'pdu_data' in app.config:
#        devices = app.config['pdu_data']
#        logger.info("Testing: got pdus from app.config['pdu_data']")
#    else:
#        devices = get_or_create_devices()
#        logger.info("Testing: got pdus from get_or_create_devices()")

#    selected_device = devices[device_number - 1]
#    system_settings = selected_device.get_all_info()

#    return jsonify(system_settings)
    
@app.route('/pdu/devices/<string:host_address>/view_all_settings', methods=['GET'])
def view_system_settings(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200
        
    logger.info(f"Testing: in view_all_settings: device info: {device.hostAddress, device.username, device.password, device.chromedriver_path}")

    system_settings = selected_device.get_all_info()

    return jsonify(system_settings)
    


# @app.route('/pdu/devices/<int:device_number>/change_system_settings', methods=['PUT'])
# def change_system_settings(device_number):
    # devices = None
    # #pdus = app.config['pdu_data']
    # if 'pdu_data' in object_cache:
        # devices = object_cache['pdu_data']
    # else:
        # # If the cache doesn't exist, you might want to create it
        # devices = get_or_create_devices()
    # #devices = app.config['pdu_data']
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # new_system_settings = request.get_json()

    # # Explicitly extract parameters from the JSON data
    # system_name = new_system_settings.get('system_name', None)
    # system_contact = new_system_settings.get('system_contact', None)
    # location = new_system_settings.get('location', None)
    # driver = new_system_settings.get('driver', None)

    # selected_device.change_system_settings(
        # system_name=system_name,
        # system_contact=system_contact,
        # location=location,
        # driver=driver
    # )

    # return jsonify({'message': 'System settings updated successfully.'})
    
@app.route('/pdu/devices/<string:host_address>/change_system_settings', methods=['PUT'])
def change_system_settings(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

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

# @app.route('/pdu/devices/<int:device_number>/change_user_settings', methods=['PUT'])
# def change_user_settings(device_number):
    # #devices = app.config['pdu_data']
    # devices = None
    # #pdus = app.config['pdu_data']
    # if 'pdu_data' in object_cache:
        # devices = object_cache['pdu_data']
    # else:
        # # If the cache doesn't exist, you might want to create it
        # devices = get_or_create_devices()
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # new_user_settings = request.get_json()

    # # Explicitly extract parameters from the JSON data
    # new_username = new_user_settings.get('new_username', None)
    # new_password = new_user_settings.get('new_password', None)
    # driver = new_user_settings.get('driver', None)

    # selected_device.change_user_settings(
        # new_username=new_username,
        # new_password=new_password,
        # driver=driver
    # )

    # return jsonify({'message': 'User settings updated successfully.'})
    
@app.route('/pdu/devices/<string:host_address>/change_user_settings', methods=['PUT'])
def change_user_settings(host_address):
    # Check for required fields in the JSON data
    required_fields = ['new_username', 'new_password']
    if not request.is_json or not all(field in request.json for field in required_fields):
        return jsonify({'error': 'Missing required field(s)'}), 400

    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

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
        'UPDATE pdu_devices SET username=?, password=? WHERE host_address=?',
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

# @app.route('/pdu/devices/<int:device_number>/change_ping_action_settings', methods=['PUT'])
# def change_ping_action_settings(device_number):
    # #devices = app.config['pdu_data']
    # devices = None
    # #pdus = app.config['pdu_data']
    # if 'pdu_data' in object_cache:
        # devices = object_cache['pdu_data']
    # else:
        # # If the cache doesn't exist, you might want to create it
        # devices = get_or_create_devices()
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # new_ping_action_settings = request.get_json()

    # # Explicitly extract parameters from the JSON data
    # outletA_IP = new_ping_action_settings.get('outletA_IP', None)
    # outletA_action = new_ping_action_settings.get('outletA_action', None)
    # outletA_active = new_ping_action_settings.get('outletA_active', None)
    # outletB_IP = new_ping_action_settings.get('outletB_IP', None)
    # outletB_action = new_ping_action_settings.get('outletB_action', None)
    # outletB_active = new_ping_action_settings.get('outletB_active', None)

    # selected_device.change_ping_action_settings(
        # outletA_IP=outletA_IP,
        # outletA_action=outletA_action,
        # outletA_active=outletA_active,
        # outletB_IP=outletB_IP,
        # outletB_action=outletB_action,
        # outletB_active=outletB_active
    # )

    # return jsonify({'message': 'Ping action settings updated successfully.'})
    
@app.route('/pdu/devices/<string:host_address>/change_ping_action_settings', methods=['PUT'])
def change_ping_action_settings(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

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

### not tested
@app.route('/pdu/devices/<string:host_address>/change_ping_action_settings_dynamic', methods=['PUT'])
def change_ping_action_settings_dynamic(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

    new_ping_action_settings = request.get_json()

    # Extract the device's IP address from the JSON data
    device_IP = new_ping_action_settings.get('device_IP', None)

    if device_IP is None:
        return jsonify({'error': 'Device IP address is missing in the request.'}), 400

    # Iterate through the outlets list and update settings
    outlets = new_ping_action_settings.get('outlets', [])

    for outlet in outlets:
        outlet_name = outlet.get('outlet_name', None)
        outlet_action = outlet.get('outlet_action', None)
        outlet_active = outlet.get('outlet_active', None)

        # Perform actions for each outlet based on device_IP
        # Example: selected_device.change_ping_action_settings(device_IP, outlet_name, outlet_action, outlet_active)

    return jsonify({'message': 'Ping action settings updated successfully.'})

# @app.route('/pdu/devices/<int:device_number>/set_outlet_power_state', methods=['PUT'])
# def change_outlet_settings(device_number):
    # #devices = app.config['pdu_data']
    # #devices = None
    # #pdus = app.config['pdu_data']
    # #if 'pdu_data' in object_cache:
    # #    devices = object_cache['pdu_data']
    # #else:
        # # If the cache doesn't exist, you might want to create it
    # #    devices = get_or_create_devices()
    
    # devices = None
    # if 'pdu_data' in app.config:
        # devices = app.config['pdu_data']
        # logger.info("Testing: got pdus from app.config['pdu_data']")
    # else:
        # devices = get_or_create_devices()
        # logger.info("Testing: got pdus from get_or_create_devices()")
    
    # logger.info(f"testing change_outlet_settings... device_number): {device_number}")
    # logger.info(f"testing change_outlet_settings... len(devices): {len(devices)}")
    
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # new_outlet_settings = request.get_json()

    # # Explicitly extract parameters from the JSON data
    # outlet_name = new_outlet_settings.get('outlet_name', None)
    # action = new_outlet_settings.get('action', None)

    # selected_device.change_power_action(
        # outlet_name=outlet_name,
        # action=action
    # )

    # return jsonify({'message': 'Outlet settings updated successfully.'})
    
@app.route('/pdu/devices/<string:host_address>/set_outlet_power_state', methods=['PUT'])
def change_outlet_settings(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

    new_outlet_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    outlet_name = new_outlet_settings.get('outlet_name', None)
    action = new_outlet_settings.get('action', None)

    selected_device.change_power_action(
        outlet_name=outlet_name,
        action=action
    )

    return jsonify({'message': 'Outlet settings updated successfully.'})
	
# @app.route('/pdu/devices/<int:device_number>/change_pdu_settings', methods=['PUT'])
# def change_pdu_settings(device_number):
    # #devices = app.config['pdu_data']
    # devices = None
    # #pdus = app.config['pdu_data']
    # if 'pdu_data' in object_cache:
        # devices = object_cache['pdu_data']
    # else:
        # # If the cache doesn't exist, you might want to create it
        # devices = get_or_create_devices()
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # new_pdu_settings = request.get_json()

    # # Explicitly extract parameters from the JSON data
    # outletA_name = new_pdu_settings.get('outletA_name', None)
    # outletA_onDelay = new_pdu_settings.get('outletA_onDelay', None)
    # outletA_offDelay = new_pdu_settings.get('outletA_offDelay', None)
    # outletB_name = new_pdu_settings.get('outletB_name', None)
    # outletB_onDelay = new_pdu_settings.get('outletB_onDelay', None)
    # outletB_offDelay = new_pdu_settings.get('outletB_offDelay', None)

    # selected_device.change_pdu_settings(
        # outletA_name=outletA_name,
        # outletA_onDelay=outletA_onDelay,
        # outletA_offDelay=outletA_offDelay,
        # outletB_name=outletB_name,
        # outletB_onDelay=outletB_onDelay,
        # outletB_offDelay=outletB_offDelay
    # )

    # return jsonify({'message': 'PDU settings updated successfully.'})
    
@app.route('/pdu/devices/<string:host_address>/change_pdu_settings', methods=['PUT'])
def change_pdu_settings(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

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

# @app.route('/pdu/devices/<int:device_number>/change_network_settings', methods=['PUT'])
# def change_network_settings(device_number):
    # #devices = app.config['pdu_data']
    # devices = None
    # #pdus = app.config['pdu_data']
    # if 'pdu_data' in object_cache:
        # devices = object_cache['pdu_data']
    # else:
        # # If the cache doesn't exist, you might want to create it
        # devices = get_or_create_devices()
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # new_network_settings = request.get_json()

    # # Explicitly extract parameters from the JSON data
    # dhcp = new_network_settings.get('dhcp', None)
    # IP = new_network_settings.get('IP', None)
    # subnet = new_network_settings.get('subnet', None)
    # gateway = new_network_settings.get('gateway', None)
    # DNS1 = new_network_settings.get('DNS1', None)
    # DNS2 = new_network_settings.get('DNS2', None)

    # selected_device.change_network_settings(
        # dhcp=dhcp,
        # IP=IP,
        # subnet=subnet,
        # gateway=gateway,
        # DNS1=DNS1,
        # DNS2=DNS2
    # )

    # return jsonify({'message': 'Network settings updated successfully.'})
    
@app.route('/pdu/devices/<string:host_address>/change_network_settings', methods=['PUT'])
def change_network_settings(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

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
    
# @app.route('/pdu/devices/<int:device_number>/enable_disable_dhcp', methods=['PUT'])
# def enable_disable_dhcp(device_number):
    # #devices = app.config['pdu_data']
    # devices = None
    # #pdus = app.config['pdu_data']
    # if 'pdu_data' in object_cache:
        # devices = object_cache['pdu_data']
    # else:
        # # If the cache doesn't exist, you might want to create it
        # devices = get_or_create_devices()
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # dhcp_option = request.get_json().get('dhcp_option')

    # selected_device.change_dhcp_setting(dhcp=dhcp_option)
    # return jsonify({'message': 'DHCP settings updated successfully.'})
    
@app.route('/pdu/devices/<string:host_address>/enable_disable_dhcp', methods=['PUT'])
def enable_disable_dhcp(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None
    
    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

    dhcp_option = request.get_json().get('dhcp_option')

    selected_device.change_dhcp_setting(dhcp=dhcp_option)
    return jsonify({'message': 'DHCP settings updated successfully.'})
    
# @app.route('/pdu/devices/<int:device_number>/change_time_settings', methods=['PUT'])
# def change_time_settings(device_number):
    # #devices = app.config['pdu_data']
    # devices = None
    # #pdus = app.config['pdu_data']
    # if 'pdu_data' in object_cache:
        # devices = object_cache['pdu_data']
    # else:
        # # If the cache doesn't exist, you might want to create it
        # devices = get_or_create_devices()
    # if device_number <= 0 or device_number > len(devices):
        # return jsonify({'error': 'Invalid device number. Please try again.'}), 200

    # selected_device = devices[device_number - 1]
    # internet_time_option = request.get_json().get('internet_time_option')

    # selected_device.change_time_settings(internet_time=internet_time_option)
    # return jsonify({'message': 'Time settings updated successfully.'})

@app.route('/pdu/devices/<string:host_address>/change_time_settings', methods=['PUT'])
def change_time_settings(host_address):
    devices = None
    if 'pdu_data' in app.config:
        devices = app.config['pdu_data']
        logger.info("Testing: got pdus from app.config['pdu_data']")
    else:
        devices = get_or_create_devices()
        logger.info("Testing: got pdus from get_or_create_devices()")

    selected_device = None

    for device in devices:
        if device.hostAddress == host_address:
            selected_device = device
            break

    if selected_device is None:
        return jsonify({'error': f'Device with host address {host_address} not found.'}), 200

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
    #chrome_driver_path = download_chromedriver()
    
    #if chrome_driver_path is None:
    #    print(f"ChromeDriver file download failed... exiting.")
    #    exit()

    #app.run(debug=True)
    
    # Load PC host devices from the text file
    #pc_hosts = load_pc_hosts()
    #print(pc_hosts)
    
    # load device list from text file
    #devices = load_devices()
    #print(devices)
    
    # Iterate through the array and call the add_device function for each device
    # for device in devices:
        # result = initial_add_device(
            # device.hostAddress,
            # device.username,  # Use the correct attribute name for username
            # device.password,  # Use the correct attribute name for password
            # device.chromedriver_path,  # Use the correct attribute name for chromedriver_path
        # )

        # # Handle the result as needed
        # if 'error' in result:
            # print(f"Error: {result['error']}")
        # elif 'success' in result:
            # print(f"Success: {result['success']}")
        # else:
            # print("Unknown result")
    

    app.run(host="0.0.0.0", port=conf.APP_PORT, debug=True, use_reloader=True)
