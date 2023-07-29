# Script Name: pdu-testing.py
# Description: serveredge PDU web interaction and control test script
# Author: Andrew J. McDonald 

import re
import time

from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select


## ====================================================================
## script to download chromedriver and set to PATH in debian - untested
## ====================================================================
#
# import platform
# import os
# import zipfile
# import requests

# def download_chromedriver():
    # # Check the architecture of the system
    # architecture = platform.machine()
    # if '64' in architecture:
        # bit_version = '64'
    # else:
        # bit_version = '32'
    
    # # Check the latest version of ChromeDriver from the official site
    # version_url = f'https://sites.google.com/chromium.org/driver/downloads?authuser=0'
    # response = requests.get(version_url)
    # response.raise_for_status()
    # latest_version = None
    # for line in response.text.splitlines():
        # if 'Latest Stable Release' in line:
            # latest_version = line.split()[-1]
            # break
    
    # if not latest_version:
        # raise ValueError("Failed to fetch the latest ChromeDriver version.")
    
    # # Create the download URL based on the version and architecture
    # chromedriver_url = f'https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_linux{bit_version}.zip'
    
    # # Download the chromedriver zip file
    # response = requests.get(chromedriver_url)
    # response.raise_for_status()
    
    # # Save the zip file
    # chromedriver_zip_path = 'chromedriver.zip'
    # with open(chromedriver_zip_path, 'wb') as f:
        # f.write(response.content)
    
    # # Extract the chromedriver binary from the zip file
    # with zipfile.ZipFile(chromedriver_zip_path, 'r') as zip_ref:
        # zip_ref.extractall('.')
    
    # # Set permissions to allow execution
    # os.chmod('chromedriver', 0o755)
    
    # # Remove the downloaded zip file
    # os.remove(chromedriver_zip_path)

# def setup_chromedriver():
    # try:
        # # Check if the OS is Debian
        # if platform.linux_distribution()[0].lower() == 'debian':
            # print("Detected Debian system.")
            # download_chromedriver()
            # print("Chromedriver setup completed successfully.")
        # else:
            # print("Not running on a Debian system. Chromedriver setup not needed.")
    # except Exception as e:
        # print(f"Error occurred during Chromedriver setup: {e}")

# if __name__ == "__main__":
    # setup_chromedriver()
## ====================================================================


# Set up the ChromeDriver service with the executable path
chromedriver_path = r'C:\Program Files (x86)\chromedriver\chromedriver.exe'
service = Service(executable_path=chromedriver_path)

# Create the WebDriver instance (without headless mode, so you can see the browser)
driver = webdriver.Chrome(service=service)


def get_outlet_states(hostAddress, username, password, driver, http_proto="http"):
    if http_proto == "http":
        port_no = "80"
    else:
        port_no = "443"
    
    parsed_url = urlparse(f'http://{hostAddress}')
    base_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"
    
    # Get the status page URL
    status_url = f"{base_url}/status.xml"

    # Load the status page
    driver.get(status_url)
    
    # Get the page source and parse it with BeautifulSoup
    html_doc = driver.page_source
    html_doc = BeautifulSoup(html_doc, features='lxml')
    html_string = str(html_doc)
    html_lines = html_string.split("\n")
    
    outlet_a_status = None
    outlet_b_status = None
    
    # Search for outlet A and B in the HTML lines
    for html_line in html_lines:
        if re.search("pot0", html_line):
            values = html_line.split(",")
            outlet_a_status = "ON" if int(values[10]) == 1 else "OFF"
            outlet_b_status = "ON" if int(values[11]) == 1 else "OFF"
            break

    # Print the status of outlets A and B
    #print(f"Outlet A: {outlet_a_status}")
    #print(f"Outlet B: {outlet_b_status}")
    
    outlet_state = {
        "A":outlet_a_status,
        "B":outlet_b_status,
    }
    
    return outlet_state

# Function to perform actions on outlets
def perform_outlet_actions(outlet_name, checkbox_name, button_name):
    # Find and click the checkbox for the specified outlet
    print(checkbox_name)
    checkbox = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, checkbox_name)))
    print(f"DEBUG: Found Checkbox Element for {outlet_name}: {checkbox_name}")
    checkbox.click()
    print(f"DEBUG: Checkbox '{checkbox_name}' Clicked for {outlet_name}")

    # Find and click the button for the specified action
    button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, button_name)))
    print(f"DEBUG: Found Button Element for {outlet_name}: {button_name}")
    button.click()
    print(f"DEBUG: Button '{button_name}' Clicked for {outlet_name}")
    
    # Wait for the confirmation alert to appear
    wait = WebDriverWait(driver, 10)
    alert = wait.until(EC.alert_is_present())
    print("DEBUG: Alert Text:", alert.text)

    # Accept the alert using the Alert object's accept() method
    alert.accept()
    print("DEBUG: Alert Accepted")

    # Add a wait here to ensure the page has settled after the action
    time.sleep(1)  # Adjust the sleep duration as needed


def power_action(hostAddress, username, password, outlet_name=None, action=None):
    # check parameters exist
    if outlet_name is None or action is None:
        return None

    outlet_check_boxes = {
        "A": "C11",
        "B": "C12",
    }

    outlet_actions = {
        "ON": "T18",
        "OFF": "T19",
        "OFF/ON": "T21",
    }
    
    # get the current state of outlets (on or off)
    current_state = get_outlet_states(hostAddress,  username, password, driver)
    
    device_url = f'http://{hostAddress}'
    parsed_url = urlparse(device_url)

    # Add username and password to the URL
    full_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"

    # Navigate to the URL
    alert = driver.get(full_url)
    
    # Click the "Outlet" link to go to the outlet settings page
    section = "Outlet"
    link = driver.find_element(By.LINK_TEXT, section)
    link.click()
    
    if current_state[outlet_name] == "OFF" and action == "ON":
        # Perform TURN ON action on outlet
        perform_outlet_actions(outlet_name, outlet_check_boxes.get(outlet_name), outlet_actions.get(action))
    elif current_state[outlet_name] == "ON" and action == "OFF":
        # Perform TURN OFF action on outlet
        perform_outlet_actions(outlet_name, outlet_check_boxes.get(outlet_name), outlet_actions.get(action))
    elif action == "OFF/ON":
        # Perform TURN OFF/ON action on outlet
        perform_outlet_actions(outlet_name, outlet_check_boxes.get(outlet_name), outlet_actions.get(action))
    else:
        if current_state[outlet_name] == "ON" and action == "ON":
            print(f"Power is already ON for outlet{outlet_name}")
        elif current_state[outlet_name] == "OFF" and action == "OFF":
            print(f"Power is already OFF for outlet{outlet_name}")
        else:
            print(f"Outlet={outlet_name} is currently{current_state[outlet_name]}, tried to change to {action}")


def change_system_settings(hostAddress, username, password, system_name=None, system_contact=None, location=None):
    device_url = f'http://{hostAddress}'
    parsed_url = urlparse(device_url)

    # Add username and password to the URL
    full_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"

    # Navigate to the URL
    alert = driver.get(full_url)
    
    # Click the "Sytem" link to go to the sytem settings page
    #section = "System"
    #link = driver.find_element(By.PARTIAL_LINK_TEXT, section)
    #link.click()
    
    # Add a wait here to ensure the page has settled after the action
    time.sleep(1)  # Adjust the sleep duration as needed
    
    apply=False
    
    if system_name is not None:
        # Perform action to change the hostname
        print(f"Changing system name to: {system_name}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "T0")

        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = system_name    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply=True
        
    if system_contact is not None:
        # Perform action to change the hostname
        print(f"Changing system contact to: {system_contact}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "T1")

        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = system_contact    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply=True
        
    if location is not None:
        # Perform action to change the hostname
        print(f"Changing location to: {location}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "T2")

        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = location    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply=True
        
    if apply:
        # Wait for the "Apply" button to be clickable and then click it
        apply_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Apply'][@type='button']")))
        apply_button.click()
    
        # Wait for the "Alert" to appear
        wait = WebDriverWait(driver, 10)
        alert = wait.until(EC.alert_is_present())
        print("DEBUG: Alert Text:", alert.text)

        # Accept the alert using the Alert object's accept() method
        alert.accept()
        print("DEBUG: Alert Accepted")

        # Add a wait here to ensure the page has settled after the action
        time.sleep(1)  # Adjust the sleep duration as needed
    

def change_user_settings(hostAddress, username, password, new_username=None, new_password=None):
    device_url = f'http://{hostAddress}'
    parsed_url = urlparse(device_url)

    # Add username and password to the URL
    full_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"

    # Navigate to the URL
    alert = driver.get(full_url)
    
    # Click the "User" link to go to the user settings page
    section = "User"
    link = driver.find_element(By.LINK_TEXT, section)
    link.click()
    
    # Add a wait here to ensure the page has settled after the action
    time.sleep(1)  # Adjust the sleep duration as needed
    
    apply = False
    
    if new_username is not None and new_password is not None:
        # Perform action to change the hostname
        print(f"Changing username to: {new_username}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "T0")

        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        input_element.send_keys(username)
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "T2")

        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = new_username    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        
        # Perform action to change the password
        print(f"Changing password to: {new_password}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "T1")

        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        input_element.send_keys(password)
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "T3")

        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = new_password    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply = True
    
    if apply:
        # click Apply but to submit changes
        apply_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Apply'][@type='submit']")))
        apply_button.click()
        
        # Add a wait here to ensure the page has settled after the action
        time.sleep(1)  # Adjust the sleep duration as needed


def change_ping_action_settings(hostAddress, username, password, outletA_IP=None, outletA_action=None, outletA_active=None, outletB_IP=None, outletB_action=None, outletB_active=None):     
    try:
        device_url = f'http://{hostAddress}'
        parsed_url = urlparse(device_url)

        # Add username and password to the URL
        full_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"

        # Navigate to the URL
        alert = driver.get(full_url)

        # Click the "Network" link to go to the network settings page
        section = "Ping Action"
        link = driver.find_element(By.LINK_TEXT, section)
        link.click()

        # Add a wait here to ensure the page has settled after the action
        time.sleep(2)  # Adjust the sleep duration as needed
        
        apply = False
        
        # Check the state of checkbox_outletA
        checkbox_outletA = driver.find_element(By.NAME, "D00")
        checkbox_state_outletA = checkbox_outletA.is_selected()

        # If outletA_IP or outletA_action is not None and checkbox_outletA is enabled, disable it
        if (outletA_IP is not None or outletA_action is not None) and checkbox_state_outletA:
            checkbox_outletA.click()
            apply = True

        if apply:
            # Wait for the confirmation alert to appear
            wait = WebDriverWait(driver, 10)
            alert = wait.until(EC.alert_is_present())
            print("DEBUG: Alert Text:", alert.text)

            # Accept the alert using the Alert object's accept() method
            alert.accept()
            print("DEBUG: Alert Accepted")
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply = False
        
        # make changes
        if outletA_IP is not None:
            ip_field_outletA = driver.find_element(By.NAME, "A00")
            ip_field_outletA.clear()
            ip_field_outletA.send_keys(outletA_IP)
            time.sleep(.5)  # Adjust the sleep duration as needed
            
        if outletA_action is not None:
            action_dropdown_outletA = Select(driver.find_element(By.NAME, "C00"))
            action_dropdown_outletA.select_by_visible_text(outletA_action)
            time.sleep(.5)  # Adjust the sleep duration as needed

        # make changes
        if outletA_active is not None:
            checkbox_outletA = driver.find_element(By.NAME, "D00")
            checkbox_state_outletA = checkbox_outletA.is_selected()
            if (outletA_active.lower() == "enable" and not checkbox_state_outletA) or (outletA_active.lower() == "disable" and checkbox_state_outletA):
                checkbox_outletA.click()
                apply = True
                
            if outletA_active.lower() == "disable":
                print("changes made to outletA IP and Action will not be saved as active state is set to disabled")

        if apply:
            # Wait for the confirmation alert to appear
            wait = WebDriverWait(driver, 10)
            alert = wait.until(EC.alert_is_present())
            print("DEBUG: Alert Text:", alert.text)

            # Accept the alert using the Alert object's accept() method
            alert.accept()
            print("DEBUG: Alert Accepted")

            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply = False
            
        # Check the state of checkbox_outletB
        checkbox_outletB = driver.find_element(By.NAME, "D01")
        checkbox_state_outletB = checkbox_outletB.is_selected()

        # If outletB_IP or outletB_action is not None and checkbox_state_outletB is enabled, disable it
        if (outletB_IP is not None or outletB_action is not None) and checkbox_state_outletB:
            checkbox_outletB.click()
            apply = True

        if apply:
            # Wait for the confirmation alert to appear
            wait = WebDriverWait(driver, 10)
            alert = wait.until(EC.alert_is_present())
            print("DEBUG: Alert Text:", alert.text)

            # Accept the alert using the Alert object's accept() method
            alert.accept()
            print("DEBUG: Alert Accepted")
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply = False
        
        # make changes
        if outletB_IP is not None:
            ip_field_outletB = driver.find_element(By.NAME, "A01")
            ip_field_outletB.clear()
            ip_field_outletB.send_keys(outletB_IP)
            time.sleep(2)  # Adjust the sleep duration as needed
                
        # Find the dropdown element by its name or other suitable locator
        #dropdown_element = driver.find_element(By.NAME, "C01")

        # Find all the options within the dropdown
        #options = dropdown_element.find_elements(By.TAG_NAME, "option")

        # Print the text of each option
        #for option in options:
        #    print(option.text)
           
        # make changes
        #if outletB_action is not None:
        
        if outletB_action is not None:
            action_dropdown_outletB = Select(driver.find_element(By.NAME, "C01"))
            action_dropdown_outletB.select_by_visible_text(outletB_action)
            time.sleep(.5)  # Adjust the sleep duration as needed

        # make changes
        if outletB_active is not None:
            checkbox_outletB = driver.find_element(By.NAME, "D01")
            checkbox_state_outletB = checkbox_outletB.is_selected()
            if (outletB_active.lower() == "enable" and not checkbox_state_outletB) or (outletB_active.lower() == "disable" and checkbox_state_outletB):
                checkbox_outletB.click()
                apply = True
            
            if outletB_active.lower() == "disable":
                print("changes made to outletB IP and Action will not be saved as active state is set to disabled")

        if apply:
            # Wait for the confirmation alert to appear
            wait = WebDriverWait(driver, 10)
            alert = wait.until(EC.alert_is_present())
            print("DEBUG: Alert Text:", alert.text)

            # Accept the alert using the Alert object's accept() method
            alert.accept()
            print("DEBUG: Alert Accepted")

        # Add a wait here to ensure the page has settled after the action
        time.sleep(1)  # Adjust the sleep duration as needed

    finally:
        # Close the browser window after the script execution
        driver.quit()    


def change_network_settings(hostAddress, username, password, hostname=None, dhcp=None, IP=None, subnet=None, gateway=None, DNS1=None, DNS2=None):
    
    device_url = f'http://{hostAddress}'
    parsed_url = urlparse(device_url)

    # Add username and password to the URL
    full_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"

    # Navigate to the URL
    alert = driver.get(full_url)
    
    # Click the "Network" link to go to the networkd settings page
    section = "Network"
    link = driver.find_element(By.LINK_TEXT, section)
    link.click()
    
    # Add a wait here to ensure the page has settled after the action
    time.sleep(1)  # Adjust the sleep duration as needed
    
    apply = False
    
    if dhcp is not None:
        # Perform action to enable/disable dhcp 
        print(f"Changing dhcp to: {dhcp}")
    
        # Find the checkbox element by its name attribute
        checkbox = driver.find_element(By.NAME, "dhcpenabled")

        # Check the checkbox if it's not already checked
        if not checkbox.is_selected() and dhcp == "enable":
            checkbox.click()
            apply = True
        elif checkbox.is_selected() and dhcp == "disable":
            checkbox.click()
            apply = True
        else:
            if not checkbox.is_selected() and dhcp == "disable":
                print("dhcp is already disabled")
            elif checkbox.is_selected() and dhcp == "enable":
                print("dhcp is already enabled")   
    
    if hostname is not None:
        # Perform action to change the hostname
        print(f"Changing hostname to: {hostname}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "host")

        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = hostname    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply = True

    if IP is not None:
        # Perform action to change the IP address
        print(f"Changing IP address to: {IP}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "ip")
        
        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = IP          # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply = True

    if subnet is not None:
        # Perform action to change the netmask
        print(f"Changing subnet to: {subnet}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "subnet")
        
        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = subnet      # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply = True

    if gateway is not None:
        # Perform action to change the gateway
        print(f"Changing gateway to: {gateway}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "gw")
        
        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = gateway     # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply = True

    if DNS1 is not None:
        # Perform action to change the primary DNS
        print(f"Changing primary DNS to: {DNS1}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "dns1")
        
        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = DNS1        # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply = True

    if DNS2 is not None:
        # Perform action to change the secondary DNS
        print(f"Changing secondary DNS to: {DNS2}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "dns2")
        
        # Change the value of the input element
        input_element.clear()   # Clear the existing value (optional, if needed)
        new_value = DNS2        # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply = True
    
    if apply:
        # After changing the value, you can click the "Apply" button to save the changes
        apply_button = driver.find_element(By.NAME, "submit")
        apply_button.click()
            
        # Add a wait here to ensure the page has settled after the action
        time.sleep(1)  # Adjust the sleep duration as needed


def change_pdu_settings(hostAddress, username, password, outletA_name=None, outletA_onDelay=None, outletA_offDelay=None, outletB_name=None, outletB_onDelay=None, outletB_offDelay=None):
    
    device_url = f'http://{hostAddress}'
    parsed_url = urlparse(device_url)

    # Add username and password to the URL
    full_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"

    # Navigate to the URL
    alert = driver.get(full_url)
    
    # Click the "Network" link to go to the networkd settings page
    section = "PDU"
    link = driver.find_element(By.LINK_TEXT, section)
    link.click()
    
    # Add a wait here to ensure the page has settled after the action
    time.sleep(1)  # Adjust the sleep duration as needed
    
    apply_name = False
    apply_on_delay = False
    apply_off_delay = False
    
    if outletA_name is not None:
        # Perform action to change the primary DNS
        print(f"Changing outletA name to: {outletA_name}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "B00")
        
        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = outletA_name    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply_name = True
    
    if outletA_onDelay is not None:
        # Perform action to change the primary DNS
        print(f"Changing outletA ON delay to: {outletA_onDelay} secs")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "O00")
        
        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = outletA_onDelay             # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply_on_delay = True
    
    if outletA_offDelay is not None:
        # Perform action to change the primary DNS
        print(f"Changing outletA OFF delay to: {outletA_offDelay} secs")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "F00")
        
        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = outletA_offDelay             # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply_off_delay = True
    
    if outletB_name is not None:
        # Perform action to change the primary DNS
        print(f"Changing outletA name to: {outletB_name}")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "B01")
        
        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = outletB_name    # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply_name = True
    
    if outletB_onDelay is not None:
        # Perform action to change the primary DNS
        print(f"Changing outletA ON delay to: {outletB_onDelay} secs")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "O01")
        
        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = outletB_onDelay             # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply_on_delay = True
    
    if outletB_offDelay is not None:
        # Perform action to change the primary DNS
        print(f"Changing outletA OFF delay to: {outletB_offDelay} secs")
        
        # Locate the input element by its name attribute
        input_element = driver.find_element(By.NAME, "F01")
        
        # Change the value of the input element
        input_element.clear()       # Clear the existing value (optional, if needed)
        new_value = outletB_offDelay             # Replace this with the value you want to set
        input_element.send_keys(new_value)
        
        apply_off_delay = True
        
    if apply_name:
        # Find the buttons based on their onclick attribute
        apply_button_name = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetGroupName(0)']"))
        )
    
        # click Apply but to submit changes to names
        apply_button_name.click()

        # Wait for the confirmation alert to appear
        wait = WebDriverWait(driver, 10)
        alert = wait.until(EC.alert_is_present())
        print("DEBUG: Alert Text:", alert.text)

        # Accept the alert using the Alert object's accept() method
        alert.accept()
        print("DEBUG: Alert Accepted")
        
        # Add a wait here to ensure the page has settled after the action
        time.sleep(1)  # Adjust the sleep duration as needed
    
    if apply_on_delay:
        # Find the buttons based on their onclick attribute
        apply_button_on_delay = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTime(0)']"))
        )
    
        # click Apply but to submit changes to on delay
        apply_button_on_delay.click()
        
        # Wait for the confirmation alert to appear
        wait = WebDriverWait(driver, 10)
        alert = wait.until(EC.alert_is_present())
        print("DEBUG: Alert Text:", alert.text)

        # Accept the alert using the Alert object's accept() method
        alert.accept()
        print("DEBUG: Alert Accepted")
        
        # Add a wait here to ensure the page has settled after the action
        time.sleep(1)  # Adjust the sleep duration as needed
    
    if apply_off_delay:
        # Find the buttons based on their onclick attribute
        apply_button_off_delay = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTimef(0)']"))
        )
    
        ## click Apply but to submit changes to off delay
        apply_button_off_delay.click()

        # Wait for the confirmation alert to appear
        wait = WebDriverWait(driver, 10)
        alert = wait.until(EC.alert_is_present())
        print("DEBUG: Alert Text:", alert.text)

        # Accept the alert using the Alert object's accept() method
        alert.accept()
        print("DEBUG: Alert Accepted")
        
        # Add a wait here to ensure the page has settled after the action
        time.sleep(1)  # Adjust the sleep duration as needed

#print(get_outlet_states('192.168.0.200', 'snmp', '1234', driver))

## Outlet page - working
#power_action('192.168.0.200', 'snmp', '1234', "A", "OFF/ON")
#power_action('192.168.0.200', 'snmp', '1234', "A", "ON")
#power_action('192.168.0.200', 'snmp', '1234', "A", "OFF")
#power_action('192.168.0.200', 'snmp', '1234', "B", "OFF")

## Network page - working
#change_network_settings(hostAddress, username, password, hostname=None, dhcp=None, IP=None, subnet=None, gateway=None, DNS1=None, DNS2=None):
#change_network_settings('192.168.0.200', 'snmp', '1234', dhcp="enable")
#change_network_settings('192.168.0.200', 'snmp', '1234', hostname="frank", dhcp="disable", IP="192.168.0.5", subnet="255.255.255.0", gateway="192.168.0.1", DNS1="8.8.8.8", DNS2="8.8.4.4")

## User page - working
# change_user_settings(hostAddress, username, password, new_username=None, new_password=None):
#change_user_settings('192.168.0.5', 'admin', 'admin', new_username='snmp', new_password='1234')
#change_user_settings('192.168.0.5', 'snmp', '1234', new_username='admin', new_password='admin')

## System page - working
# change_system_settings('192.168.0.5', 'snmp', '1234', system_name=None, system_contact=None, location=None)
#change_system_settings('192.168.0.5', 'snmp', '1234', system_name="PDU-TEST", system_contact="Andrew", location="Melbourne")

## Ping Action page - working
#change_ping_action_settings('192.168.0.5', 'snmp', '1234', outletA_IP="192.168.0.100", outletA_action="OFF", outletA_active="enable", outletB_IP="192.168.0.101", outletB_action="OFF/ON", outletB_active="enable")
#change_ping_action_settings('192.168.0.5', 'snmp', '1234', outletB_IP="192.168.0.13", outletB_action="OFF", outletB_active="enable")
#change_ping_action_settings('192.168.0.5', 'snmp', '1234', outletA_IP="192.168.0.12", outletA_action="OFF", outletA_active="enable")

## PDU page - working
#change_pdu_settings('192.168.0.5', 'snmp', '1234', outletA_name="outletA", outletA_onDelay="1", outletA_offDelay="1", outletB_name="outletB", outletB_onDelay="2", outletB_offDelay="2")
