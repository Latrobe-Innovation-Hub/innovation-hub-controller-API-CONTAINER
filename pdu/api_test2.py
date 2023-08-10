from flask import Flask, request, jsonify
from pdu_class import DeviceController
import os

import sys
import shutil
import requests
import platform
from zipfile import ZipFile

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

app = Flask(__name__)

# Set the path to the Chrome WebDriver file
#chrome_driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")
chrome_driver_path = None

master_username = "admin"
master_password = "admin"
devices = []

# =============
# MAIN OPTIONS
# =============	
@app.route('/devices', methods=['GET'])
def list_devices():
    if not devices:
        return jsonify({'message': 'No devices added yet. Please add a device first.'}), 400

    device_list = []
    for index, device in enumerate(devices):
        device_list.append({
            'device_number': index + 1,
            'host_address': device.hostAddress
        })

    return jsonify({'devices': device_list})

@app.route('/devices/<int:device_number>', methods=['GET'])
def get_device(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
    # Here you can return information about the selected device if needed
    device_info = {
        'device_number': device_number,
        'host_address': selected_device.hostAddress,
        # Include other device information as needed
    }

    return jsonify(device_info)

@app.route('/add_device', methods=['POST'])
def add_device():
    data = request.json
    host_address = data.get('host_address')
    if host_address is None:
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Check if a device already exists with the same host address
    for device in devices:
        if device.hostAddress == host_address:
            return jsonify({'error': f'Device with host address {host_address} already exists.'}), 400

    new_device = DeviceController(host_address, master_username, master_password, chrome_driver_path)
    devices.append(new_device)
    
    try:
        new_device.connect()
        return jsonify({'success': 'Device added successfully!'})
    except Exception as e:
        return jsonify({'error: device not reachable...'}), 500

@app.route('/remove_device/<int:device_choice>', methods=['POST'])
def remove_device(device_choice):
    if not devices:
        return jsonify({'error': 'No devices added yet. Please add a device first.'}), 400

    if device_choice <= 0 or device_choice > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    device_to_remove = devices[device_choice - 1]
    device_to_remove.disconnect()
    devices.pop(device_choice - 1)

    return jsonify({'success': 'Device removed successfully!'})

@app.route('/view_outlet_settings_all', methods=['GET'])
def view_outlet_settings_all():
    if not devices:
        return jsonify({'message': 'No devices added yet. Please add a device first.'}), 400

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
@app.route('/devices/<int:device_number>/view_all_settings', methods=['GET'])
def view_system_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
    system_settings = selected_device.get_all_info()

    return jsonify(system_settings)

@app.route('/devices/<int:device_number>/change_system_settings', methods=['PUT'])
def change_system_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
    new_system_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    system_name = new_system_settings.get('system_name', None)
    system_contact = new_system_settings.get('system_contact', None)
    location = new_system_settings.get('location', None)
    driver = new_system_settings.get('driver', None)

    selected_device.change_system_settings(
        system_name=system_name,
        system_contact=system_contact,
        location=location,
        driver=driver
    )

    return jsonify({'message': 'System settings updated successfully.'})

@app.route('/devices/<int:device_number>/change_user_settings', methods=['PUT'])
def change_user_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
    new_user_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    new_username = new_user_settings.get('new_username', None)
    new_password = new_user_settings.get('new_password', None)
    driver = new_user_settings.get('driver', None)

    selected_device.change_user_settings(
        new_username=new_username,
        new_password=new_password,
        driver=driver
    )

    return jsonify({'message': 'User settings updated successfully.'})

@app.route('/devices/<int:device_number>/change_ping_action_settings', methods=['PUT'])
def change_ping_action_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
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

@app.route('/devices/<int:device_number>/set_outlet_power_state', methods=['PUT'])
def change_outlet_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
    new_outlet_settings = request.get_json()

    # Explicitly extract parameters from the JSON data
    outlet_name = new_outlet_settings.get('outlet_name', None)
    action = new_outlet_settings.get('action', None)

    selected_device.change_power_action(
        outlet_name=outlet_name,
        action=action
    )

    return jsonify({'message': 'Outlet settings updated successfully.'})
	
@app.route('/devices/<int:device_number>/change_pdu_settings', methods=['PUT'])
def change_pdu_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
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

@app.route('/devices/<int:device_number>/change_network_settings', methods=['PUT'])
def change_network_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
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
    
@app.route('/devices/<int:device_number>/enable_disable_dhcp', methods=['PUT'])
def enable_disable_dhcp(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
    dhcp_option = request.get_json().get('dhcp_option')

    selected_device.change_dhcp_setting(dhcp=dhcp_option)
    return jsonify({'message': 'DHCP settings updated successfully.'})
    
@app.route('/devices/<int:device_number>/change_time_settings', methods=['PUT'])
def change_time_settings(device_number):
    if device_number <= 0 or device_number > len(devices):
        return jsonify({'error': 'Invalid device number. Please try again.'}), 400

    selected_device = devices[device_number - 1]
    internet_time_option = request.get_json().get('internet_time_option')

    selected_device.change_time_settings(internet_time=internet_time_option)
    return jsonify({'message': 'Time settings updated successfully.'})
	
if __name__ == '__main__':
    #global chrome_driver_path
    chrome_driver_path = download_chromedriver()
    
    if chrome_driver_path is None:
        print(f"ChromeDriver file download failed... exiting.")
        exit()
    
    app.run(host="0.0.0.0", port="8050", debug=True, use_reloader=True)
