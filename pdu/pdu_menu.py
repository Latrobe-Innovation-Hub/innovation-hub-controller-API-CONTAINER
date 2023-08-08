## Author: Andrew J. McDonald
## Date: 08.08.2023

# Import the DeviceController class from pdu_class.py
from pdu_class import DeviceController

import os
import sys
import shutil
import requests
import platform
from zipfile import ZipFile


PLATFORM_MAPPING = {
    'Linux': 'linux64',
    'Darwin': 'mac-x64',
    'Windows': 'win64' if platform.architecture()[0] == '64bit' else 'win32'
}

def download_chromedriver()
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

def download_chromedriver_old(version='114.0.5735.90'):
    extracted_file = None

    base_url = f'https://chromedriver.storage.googleapis.com/{version}/'
    download_links = {
        'chromedriver_linux64.zip': 'https://chromedriver.storage.googleapis.com/{}/chromedriver_linux64.zip'.format(version),
        'chromedriver_mac64.zip': 'https://chromedriver.storage.googleapis.com/{}/chromedriver_mac64.zip'.format(version),
        'chromedriver_mac_arm64.zip': 'https://chromedriver.storage.googleapis.com/{}/chromedriver_mac_arm64.zip'.format(version),
        'chromedriver_win32.zip': 'https://chromedriver.storage.googleapis.com/{}/chromedriver_win32.zip'.format(version),
    }
    
    #for link in download_links:
    #    print(download_links[link])

    os_name = platform.system()
    #print("platform", os_name)
    
    if os_name == 'Linux':
        os_arch = 'linux64'
        chromedriver_filename = 'chromedriver'
    elif os_name == 'Darwin':
        os_arch = 'mac64' if 'arm' not in platform.machine().lower() else 'mac_arm64'
        chromedriver_filename = 'chromedriver'
    elif os_name == 'Windows':
        os_arch = 'win32' if 'PROGRAMFILES(x86)' in os.environ else 'win64'
        chromedriver_filename = 'chromedriver.exe'
    else:
        print(f"Chromedriver for your operating system '{os_name}' is not available.")
        return None

    driver_url = download_links[f'chromedriver_{os_arch}.zip']
    chromedriver_zip = driver_url.split('/')[-1]

    print(f"Downloading ChromeDriver {version} for '{os_name}'...")
    response = requests.get(driver_url, stream=True)

    if response.status_code == 200:
        with open(chromedriver_zip, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

        with ZipFile(chromedriver_zip, 'r') as zip_ref:
            extracted_files = zip_ref.namelist()
            print("extracted_files", extracted_files)

            if chromedriver_filename in extracted_files:
                zip_ref.extract(chromedriver_filename)

        os.remove(chromedriver_zip)
        print("ChromeDriver downloaded and extracted successfully.")
        return chromedriver_filename
    else:
        print(f"Failed to download ChromeDriver: {response.status_code} - {response.reason}")
        return None

def view_outlet_settings_for_all_devices(devices):
    if not devices:
        print("No devices added yet. Please add a device first.")
    else:
        for index, device in enumerate(devices):
            print(f"\nDevice {index + 1} Outlet Settings:")
            device.print_outlet_info()

def main():
    chromedriver_path = download_chromedriver()
    if chromedriver_path is None:
        print(f"ChromeDriver file download failed... exiting.")

    master_username = input("Enter the master username: ")
    master_password = input("Enter the master password: ")

    devices = []

    while True:
        print("\nMain Menu:")
        print("1. Add new device")
        print("2. Connect to a device")
        print("3. Show available devices")
        print("4. Remove a device")
        print("5. View Outlet Settings for all Devices")
        print("6. Exit")

        main_choice = input("Enter your choice: ")

        if main_choice == "1":
            host_address = input("Enter the device address: ")
            print(chromedriver_path)
            new_device = DeviceController(host_address, master_username, master_password, chromedriver_path)
            devices.append(new_device)
            print("Device added successfully!")
            new_device.connect()  # Connect to the newly added device

        elif main_choice == "2":
            if not devices:
                print("No devices added yet. Please add a device first.")
            else:
                print("Available devices:")
                for index, device in enumerate(devices):
                    print(f"{index + 1}. {device.hostAddress}")

                device_choice = int(input("Enter the device number you want to connect to: "))
                selected_device = devices[device_choice - 1]
                #selected_device.connect()
                #print("Connected to the selected device.")
                print("\ndevice: ", selected_device.hostAddress)

                while True:
                    print("\nDevice Menu:")
                    print("1. View System Settings")
                    print("2. Change System Settings")
                    print("3. Change User Settings")
                    print("4. Change Ping Action Settings")
                    print("5. Change Outlet Settings")
                    print("6. Change PDU Settings")
                    print("7. Change Network Settings")
                    print("8. Back")

                    device_option = input("Enter your choice: ")

                    if device_option == "1":
                        print("View System Settings.")
                        selected_device.print_all_info()
                    
                    elif device_option == "2":
                        print("\nChange System Settings:")
                        selected_device.print_system_info()
                        system_name = input("Enter new system name (leave blank to keep current): ")
                        system_contact = input("Enter new system contact (leave blank to keep current): ")
                        location = input("Enter new location (leave blank to keep current): ")
                        driver = input("Enter new driver (leave blank to keep current): ")
                        selected_device.change_system_settings(system_name=system_name,
                                                               system_contact=system_contact,
                                                               location=location,
                                                               driver=driver)
                        print("System settings updated successfully.")
                        
                    elif device_option == "3":
                        print("\nChange User Settings:")
                        new_username = input("Enter new username (leave blank to keep current): ")
                        new_password = input("Enter new password (leave blank to keep current): ")
                        driver = input("Enter new driver (leave blank to keep current): ")
                        selected_device.change_user_settings(new_username=new_username,
                                                             new_password=new_password,
                                                             driver=driver)
                        print("User settings updated successfully.")
                    
                    elif device_option == "4":
                        print("\nChange Ping Action Settings:")
                        selected_device.print_ping_action_info()
                        outletA_IP = input("Enter new IP for outlet A (leave blank to keep current): ")
                        outletA_action = input("Enter new action for outlet A (leave blank to keep current): ")
                        outletA_active = input("Enter new active state for outlet A (leave blank to keep current): ")
                        outletB_IP = input("Enter new IP for outlet B (leave blank to keep current): ")
                        outletB_action = input("Enter new action for outlet B (leave blank to keep current): ")
                        outletB_active = input("Enter new active state for outlet B (leave blank to keep current): ")
                        selected_device.change_ping_action_settings(outletA_IP=outletA_IP,
                                                                    outletA_action=outletA_action,
                                                                    outletA_active=outletA_active,
                                                                    outletB_IP=outletB_IP,
                                                                    outletB_action=outletB_action,
                                                                    outletB_active=outletB_active)
                        print("Ping action settings updated successfully.")
                    
                    elif device_option == "5":
                        print("\nChange Outlet Settings:")
                        selected_device.print_outlet_info()
                        outlet_name = input("Enter outlet name (A/B): ")
                        action = input("Enter new action (e.g., 'ON', 'OFF', 'OFF/ON'): ")
                        selected_device.change_power_action(outlet_name=outlet_name, action=action)
                        print("Outlet settings updated successfully.")
                        
                    elif device_option == "6":
                        print("\nChange PDU Settings:")
                        selected_device.print_pdu_info()
                        outletA_name = input("Enter new name for Outlet A (leave blank to keep current): ")
                        outletA_onDelay = input("Enter new On Delay for Outlet A (leave blank to keep current): ")
                        outletA_offDelay = input("Enter new Off Delay for Outlet A (leave blank to keep current): ")
                        outletB_name = input("Enter new name for Outlet B (leave blank to keep current): ")
                        outletB_onDelay = input("Enter new On Delay for Outlet B (leave blank to keep current): ")
                        outletB_offDelay = input("Enter new Off Delay for Outlet B (leave blank to keep current): ")
                        selected_device.change_pdu_settings(outletA_name=outletA_name,
                                                            outletA_onDelay=outletA_onDelay,
                                                            outletA_offDelay=outletA_offDelay,
                                                            outletB_name=outletB_name,
                                                            outletB_onDelay=outletB_onDelay,
                                                            outletB_offDelay=outletB_offDelay)
                        print("PDU settings updated successfully.")
                    
                    elif device_option == "7":
                        print("\nChange Network Settings:")
                        selected_device.print_network_info()
                        dhcp = input("Enable DHCP? (True/False): ")
                        IP = input("Enter new IP address (leave blank to keep current): ")
                        subnet = input("Enter new subnet mask (leave blank to keep current): ")
                        gateway = input("Enter new gateway IP (leave blank to keep current): ")
                        DNS1 = input("Enter new primary DNS server (leave blank to keep current): ")
                        DNS2 = input("Enter new secondary DNS server (leave blank to keep current): ")

                        if dhcp.lower() == "true":
                            dhcp = True
                        else:
                            dhcp = False

                        selected_device.change_network_settings(dhcp=dhcp,
                                                                IP=IP,
                                                                subnet=subnet,
                                                                gateway=gateway,
                                                                DNS1=DNS1,
                                                                DNS2=DNS2)
                        print("Network settings updated successfully.")

                    elif device_option == "8":
                        print("Returning to Main Menu.")
                        break

                    else:
                        print("Invalid choice. Please try again.")

        elif main_choice == "3":
            if not devices:
                print("No devices added yet. Please add a device first.")
            else:
                print("Available devices:")
                for index, device in enumerate(devices):
                    print(f"{index + 1}. {device.hostAddress}")
                    
        elif main_choice == "4":
            if not devices:
                print("No devices added yet. Please add a device first.")
            else:
                print("Available devices:")
                for index, device in enumerate(devices):
                    print(f"{index + 1}. {device.hostAddress}")

                device_choice = int(input("Enter the device number you want to remove: "))

                if device_choice <= 0 or device_choice > len(devices):
                    print("Invalid device number. Please try again.")
                else:
                    # Get the device to be removed and disconnect it
                    device_to_remove = devices[device_choice - 1]
                    device_to_remove.disconnect()

                    # Remove the device from the list
                    devices.pop(device_choice - 1)
                    print("Device removed successfully.")
                    
        elif main_choice == "5":
            view_outlet_settings_for_all_devices(devices)

        elif main_choice == "6":
            print("Exiting the program.")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
