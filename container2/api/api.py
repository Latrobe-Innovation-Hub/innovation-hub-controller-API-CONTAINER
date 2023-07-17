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


from flask import Flask, jsonify, request
import paramiko
import platform
import json
import re

import api_config as conf

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
def run_reboot_device(hostname, username, password, platformInput=None):
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


# send nircmd commands to remote pc - NEED TO TEST
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

            # build nircmd command
            command = f'nircmd {cmd}'

            # Send nircmd command
            _, stdout, stderr = client.exec_command(command)

            # capture exit status
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0: # THINK THIS WILL WORK???
                return f"nircmd command successful."
            else:
                return f"nircmd command failed with exit status {exit_status}."

        except Exception as e:
            return {'error': str(e)}

# =========================================================================
#  API - endpoints
# =========================================================================

# Init API application
app = Flask(__name__)

# home endpoint - displays a list of the current API endpoints
@app.route('/')
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


# mute/unmte remote windows pc endpoint
@app.route('/mute_device', methods=['POST'])
def mute_device():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password', 'mute']):
        return jsonify({'error': 'Missing required field(s)'}), 400 

    # Get the hostname, username, and password for the specified computer
    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    mute = data.get('mute')
    platformInput = data.get('platformInput')

    print("\n", hostname, username, password, mute, "\n")

    # Reboot the remote computer
    result = run_mute_device(hostname, username, password, mute, platformInput)

    if result is None:
        return jsonify({'error': 'backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


# reboot remote pc endpoint
@app.route('/reboot_device', methods=['POST'])
def reboot_windows():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password']):
        return jsonify({'error': 'Missing required field(s)'}), 400 

    # Get the hostname, username, and password for the specified computer
    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    platformInput = data.get('platformInput')

    print("\n", hostname, username, password, "\n")

    # Reboot the remote computer
    result = run_reboot_device(hostname, username, password, platformInput)

    if result is None:
        return jsonify({'error': 'backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


# open powerpoint in chrome on remote windows pc endpoint
@app.route('/open_powerpoint', methods=['POST'])
def open_powerpoint():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password', 'url']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    url = data.get('url')

    print("\n", hostname, username, password, url, "\n")

    # open powerpoint on chrome
    result = run_powerpoint(hostname, username, password, url)

    if result is None:
        return jsonify({'error': 'backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


# open powerpoint in chrome on remote windows pc endpoint
@app.route('/get_user_session_id', methods=['GET'])
def get_user_session_id():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password', 'target_username']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    target_username = data.get('target_username')

    print("\n", hostname, username, password, target_username, "\n")

    # check for target_username's session ID on remote host
    result = run_get_session_id(hostname, username, password, target_username)

    if result is None:
        return jsonify({'response': f"No user session ID found for {target_username}"}), 200
    else:
        return jsonify({'response': result}), 200


# kill running process on remote windows pc endpoint
@app.route('/close_process', methods=['POST'])
def close_process():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password', 'pid']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    pid = data.get('pid')

    print("\n", hostname, username, password, pid, "\n")

    # kill process
    result = kill_process(hostname, username, password, pid)

    if result is None:
        return jsonify({'error': 'backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


@app.route('/open_application', methods=['POST'])
def open_application_route():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password', 'application']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    application = data.get('application')
    arguments = data.get('arguments')

    print("\n", hostname, username, password, application, arguments, "\n")

    # open application
    result = run_application(hostname, username, password, application, arguments)

    if result is None:
        return jsonify({'error': 'backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


@app.route('/send_nircmd', methods=['POST'])
def send_nircmd():
    data = request.get_json()
    if not all(key in data for key in ['hostname', 'username', 'password', 'command']):
        return jsonify({'error': 'Missing required field(s)'}), 400

    hostname = data.get('hostname')
    username = data.get('username')
    password = data.get('password')
    command = data.get('command')

    print("\n", hostname, username, password, command, "\n")

    # run nircmd
    result = run_nircmd(hostname, username, password, application, arguments)

    if result is None:
        return jsonify({'error': 'backend function failed'}), 500
    else:
        return jsonify({'response': result}), 200


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


# =========================================================================
#  START API
# =========================================================================

## CONTAINER health-check
@app.route("/ping")
def ping():
    return "{status: ok}"


if __name__ == '__main__':
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=conf.APP_PORT, debug=True, use_reloader=True)
