## Author: Andrew J. McDonald
## Date: 08.08.2023

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import argparse
import re
import time

import logging

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

class DeviceController:
    def __init__(self, hostAddress, username, password, chromedriver_path, room_code):   
        # device credentials
        self.username = username
        self.password = password
        
        # device address
        self.hostAddress = hostAddress
        device_url = f'http://{hostAddress}'
        logger.info(f"device_url: {device_url}")
        parsed_url = urlparse(device_url)
        logger.info(f"parsed_url: {parsed_url}")
        self.base_url = f"{parsed_url.scheme}://{username}:{password}@{parsed_url.netloc}"  # Assign base_url
        logger.info(f"self.base_url: {self.base_url}")
            
        
        #self.base_url = None
        
        ### ==========================
        ###  ADD ROOM CODE FOR REFERENCING LOCATION
        ###  CAN USE THIS TO IDENTIFY WHERE THE PDU
        ###  IS ASSOCIATED TO. WOULD NEED TO UPDATE INIT PARAMS
        ###
        ###  AND ALSO WHERE PDUS ARE BEING ADDED IN API.PY
        self.room_code = room_code
        
        # system info
        self.model_num = None
        self.Firmware_ver = None
        self.MAC = None
        self.system_name = None
        self.system_contact = None
        self.system_location = None
        
        # outlet info
        ## NOTE: see the dynamic fetch for more than 2 outlets...
        self.outlet_states = {}
        
        # ping action info
        self.outlet_ping_addresses = {}
        self.outlet_ping_action = {}
        self.outlet_ping_active = {}
        
        # pdu info
        self.outlet_names = {} 
        self.outlet_onDelays = {}
        self.outlet_oFFDelays = {}
        
        # network info
        self.hostname = None
        self.ip_address = None
        self.subnet = None
        self.gateway = None
        self.dhcp_enabled = None
        self.dns1 = None
        self.dns2 = None
        
        # webdriver
        self.driver = None

        # Need to downlaod and store browser driver...
        #self.chromedriver_path = r'C:\Program Files (x86)\chromedriver\chromedriver.exe'
        self.chromedriver_path = chromedriver_path
        
        logger.info(f"in pdu class.... chromedriver_path: {self.chromedriver_path}")
        
        # Webdriver settings
        self.service = Service(executable_path=self.chromedriver_path)
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--window-position=0,0")
        self.chrome_options.add_argument("--window-size=1840,1080")

        # Init webdriver
        self.driver = webdriver.Chrome(service=Service(executable_path=self.chromedriver_path), options=self.chrome_options)
        
    # ===================================================
    # Webdriver Connectors
    # ===================================================
    def connect(self):
        if self.driver is not None:
            #print("connecting webdriver... ", end='')
            logger.info(f"connecting webdriver...")
            
            try:
                device_url = f'http://{self.hostAddress}'
                logger.info(f"device_url: {device_url}")
                parsed_url = urlparse(device_url)
                logger.info(f"parsed_url: {parsed_url}")
                self.base_url = f"{parsed_url.scheme}://{self.username}:{self.password}@{parsed_url.netloc}"  # Assign base_url
                logger.info(f"self.base_url: {self.base_url}")
                self.driver.get(self.base_url)
            except Exception as e:
                raise e  # Raise the exception instead of returning it
            
            #print(" done!")
            logger.info(f"connecting webdriver... done")
            return True
            #self.print_info()
 
    def disconnect(self):
        if self.driver is not None:
            #print("disconnecting webdriver...", end='')
            logger.info(f"disconnecting webdriver...")
            self.driver.quit()
            self.driver = None
            logger.info(f"disconnecting webdriver... done")
            #print(" done!")
            
    # ===================================================
    # Class Attribute Printers
    # ===================================================  
    def print_all_info(self):
        if self.driver is not None:
            #print("updating device info... ", end='')
            logger.info(f"updating device info...")
                
            # Fetch and store the system info after establishing the connection
            self._fetch_system_settings()
    
            # Fetch and store the outlet states after establishing the connection
            self._fetch_outlet_states()
            
            # Fetch and store the network info after establishing the connection
            self._fetch_network_settings()
            
            # Fetch and store the ping action info after establishing the connection
            self._fetch_ping_action_settings()
            
            # Fetch and store the pdu info after establishing the connection
            self._fetch_pdu_settings()
            
            print("done!")
        
            print("Device Credentials:")
            print(f"\tUsername: {self.username}")
            print(f"\tPassword: {self.password}\n")
    
            print("System Info:")
            print(f"\tModel Number: {self.model_num}")
            print(f"\tFirmware Version: {self.Firmware_ver}")
            print(f"\tMAC Address: {self.MAC}")
            print(f"\tSystem Name: {self.system_name}")
            print(f"\tSystem Contact: {self.system_contact}")
            print(f"\tSystem Location: {self.system_location}\n")
    
            print("Outlet Info:")
            for outlet, state in self.outlet_states.items():
                print(f"\tOutlet {outlet}: {state}")
            print()
            
            print("Ping Action Info:")
            for outlet, address in self.outlet_ping_addresses.items():
                print(f"\tOutlet {outlet}:")
                print(f"\t\taddress: {address}")
                print(f"\t\taction: {self.outlet_ping_action.get(outlet, 'Not Available')}")
                print(f"\t\tactive: {self.outlet_ping_active.get(outlet, 'Not Available')}")
            print()
    
            print("PDU Info:")
            for outlet, name in self.outlet_names.items():
                on_delay = self.outlet_onDelays.get(outlet, 'Not Available')
                off_delay = self.outlet_oFFDelays.get(outlet, 'Not Available')
                print(f"\tOutlet {outlet}:")
                print(f"\t\tname: {name}")
                print(f"\t\ton delay: {on_delay}")
                print(f"\t\toff delay: {off_delay}")
            print()
    
            print("Network Info:")
            print(f"\tHostname: {self.hostname}")
            print(f"\tIP Address: {self.ip_address}")
            print(f"\tSubnet: {self.subnet}")
            print(f"\tGateway: {self.gateway}")
            print(f"\tDHCP Enabled: {self.dhcp_enabled}")
            print(f"\tDNS1: {self.dns1}")
            print(f"\tDNS2: {self.dns2}")
            
    def get_all_info(self):
        if self.driver is not None:
            self._fetch_system_settings()
            self._fetch_outlet_states()
            self._fetch_network_settings()
            self._fetch_ping_action_settings()
            self._fetch_pdu_settings()
            
            info = {
                'device_credentials': {
                    'username': self.username,
                    'password': self.password
                },
                'system_info': {
                    'model_number': self.model_num,
                    'firmware_version': self.Firmware_ver,
                    'mac_address': self.MAC,
                    'system_name': self.system_name,
                    'system_contact': self.system_contact,
                    'system_location': self.system_location
                },
                'outlet_info': [
                    {'outlet': outlet, 'state': state}
                    for outlet, state in self.outlet_states.items()
                ],
                'ping_action_info': [
                    {
                        'outlet': outlet,
                        'address': self.outlet_ping_addresses.get(outlet, 'Not Available'),
                        'action': self.outlet_ping_action.get(outlet, 'Not Available'),
                        'active': self.outlet_ping_active.get(outlet, 'Not Available')
                    }
                    for outlet in self.outlet_states
                ],
                'pdu_info': [
                    {
                        'outlet': outlet,
                        'name': name,
                        'on_delay': self.outlet_onDelays.get(outlet, 'Not Available'),
                        'off_delay': self.outlet_oFFDelays.get(outlet, 'Not Available')
                    }
                    for outlet, name in self.outlet_names.items()
                ],
                'network_info': {
                    'hostname': self.hostname,
                    'ip_address': self.ip_address,
                    'subnet': self.subnet,
                    'gateway': self.gateway,
                    'dhcp_enabled': self.dhcp_enabled,
                    'dns1': self.dns1,
                    'dns2': self.dns2
                }
            }
            
            return info

    def print_system_info(self):
        if self.driver is not None:
            self._fetch_system_settings()
            print("System Info:")
            print(f"\tModel Number: {self.model_num}")
            print(f"\tFirmware Version: {self.Firmware_ver}")
            print(f"\tMAC Address: {self.MAC}")
            print(f"\tSystem Name: {self.system_name}")
            print(f"\tSystem Contact: {self.system_contact}")
            print(f"\tSystem Location: {self.system_location}\n")
            
    def get_system_info(self):
        if self.driver is not None:
            self._fetch_system_settings()
            system_info = {
                'model_number': self.model_num,
                'firmware_version': self.Firmware_ver,
                'mac_address': self.MAC,
                'system_name': self.system_name,
                'system_contact': self.system_contact,
                'system_location': self.system_location
            }
            return system_info

    def print_outlet_info(self):
        if self.driver is not None:
            self._fetch_outlet_states()
            print("Outlet Info:")
            for outlet, state in self.outlet_states.items():
                print(f"\tOutlet {outlet}: {state}")
            print()
    
    def get_outlet_info(self):
        if self.driver is not None:
            self._fetch_outlet_states()
            outlet_info = {}
            for outlet, state in self.outlet_states.items():
                outlet_info[outlet] = state
            return outlet_info
        
    def print_ping_action_info(self):
        if self.driver is not None:
            self._fetch_ping_action_settings()
            print("Ping Action Info:")
            for outlet, address in self.outlet_ping_addresses.items():
                print(f"\tOutlet {outlet}:")
                print(f"\t\taddress: {address}")
                print(f"\t\taction: {self.outlet_ping_action.get(outlet, 'Not Available')}")
                print(f"\t\tactive: {self.outlet_ping_active.get(outlet, 'Not Available')}")
            print()
            
    def get_ping_action_info(self):
        if self.driver is not None:
            self._fetch_ping_action_settings()
            ping_action_info = [
                {
                    'outlet': outlet,
                    'address': self.outlet_ping_addresses.get(outlet, 'Not Available'),
                    'action': self.outlet_ping_action.get(outlet, 'Not Available'),
                    'active': self.outlet_ping_active.get(outlet, 'Not Available')
                }
                for outlet in self.outlet_states
            ]
            return ping_action_info

    def print_pdu_info(self):
        if self.driver is not None:
            self._fetch_pdu_settings()
            print("PDU Info:")
            for outlet, name in self.outlet_names.items():
                on_delay = self.outlet_onDelays.get(outlet, 'Not Available')
                off_delay = self.outlet_oFFDelays.get(outlet, 'Not Available')
                print(f"\tOutlet {outlet}:")
                print(f"\t\tname: {name}")
                print(f"\t\ton delay: {on_delay}")
                print(f"\t\toff delay: {off_delay}")
            print()
            
    def get_pdu_info(self):
        if self.driver is not None:
            self._fetch_pdu_settings()
            pdu_info = [
                {
                    'outlet': outlet,
                    'name': name,
                    'on_delay': self.outlet_onDelays.get(outlet, 'Not Available'),
                    'off_delay': self.outlet_oFFDelays.get(outlet, 'Not Available')
                }
                for outlet, name in self.outlet_names.items()
            ]
            return pdu_info

    def print_network_info(self):
        if self.driver is not None:
            self._fetch_network_settings()
            print("Network Info:")
            print(f"\tHostname: {self.hostname}")
            print(f"\tIP Address: {self.ip_address}")
            print(f"\tSubnet: {self.subnet}")
            print(f"\tGateway: {self.gateway}")
            print(f"\tDHCP Enabled: {self.dhcp_enabled}")
            print(f"\tDNS1: {self.dns1}")
            print(f"\tDNS2: {self.dns2}")
            
    def get_network_info(self):
        if self.driver is not None:
            self._fetch_network_settings()
            network_info = {
                'hostname': self.hostname,
                'ip_address': self.ip_address,
                'subnet': self.subnet,
                'gateway': self.gateway,
                'dhcp_enabled': self.dhcp_enabled,
                'dns1': self.dns1,
                'dns2': self.dns2
            }
            return network_info
    
    # ===================================================
    # Class Attribute Updaters  
    # ===================================================    
    def update_all_attrs(self):
        if self.driver is not None:
            print("updating device info...", end='')
        
            # Fetch and store the system info after establishing the connection
            self._fetch_system_settings()
    
            # Fetch and store the outlet states after establishing the connection
            self._fetch_outlet_states()
            
            # Fetch and store the network info after establishing the connection
            self._fetch_network_settings()
            
            # Fetch and store the ping action info after establishing the connection
            self._fetch_ping_action_settings()
            
            # Fetch and store the pdu info after establishing the connection
            self._fetch_pdu_settings()
            
            print(" done!")
    
    def get_outlet_states(self):
        if not hasattr(self, 'outlet_states'):
            if self.driver is not None:
                self._fetch_outlet_states()
        return self.outlet_states
    
    # Getter methods for individual outlet states
    def get_outlet_state_A(self):
        if not hasattr(self, 'outlet_states'):
            if self.driver is not None:
                self._fetch_outlet_states()
        return self.outlet_states.get('A')

    def get_outlet_state_B(self):
        if not hasattr(self, 'outlet_states'):
            if self.driver is not None:
                self._fetch_outlet_states()
        return self.outlet_states.get('B')
    
    def _fetch_outlet_states(self):
        if self.driver is not None:
            # Get the status page URL
            status_url = f"{self.base_url}/status.xml"
            logger.info(f"in pdu class _fetch_outlet_states.... status_url: {status_url}")
    
            # Load the status page
            self.driver.get(status_url)
    
            # Get the page source and parse it with BeautifulSoup
            html_doc = self.driver.page_source
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
    
            # Store the outlet states as instance attributes
            self.outlet_states = {
                "A": outlet_a_status,
                "B": outlet_b_status,
            }
            
            # After fetching the outlet states, navigate back to the main device URL
            self.driver.back()
            time.sleep(1)  # Adjust the sleep duration as needed
    
    ### ================ ###
    ### TESTING FOR DYNAMIC NUMBER OF OUTLETS
    ### ================ ###
    def _fetch_outlet_states_many(self):
        if self.driver is not None:
            # Get the status page URL
            status_url = f"{self.base_url}/status.xml"
            logger.info(f"in pdu class _fetch_outlet_states.... status_url: {status_url}")

            # Load the status page
            self.driver.get(status_url)

            # Get the page source and parse it with BeautifulSoup
            html_doc = self.driver.page_source
            html_doc = BeautifulSoup(html_doc, features='lxml')
        
            # Find all elements that match the pattern for outlets (e.g., pot0, pot1, pot2, etc.)
            outlet_elements = html_doc.find_all(text=re.compile(r'pot\d+'))

            outlet_states = {}

            # Iterate through the outlet elements and extract their states
            for outlet_element in outlet_elements:
                outlet_name = outlet_element.strip()  # Extract the outlet name, e.g., "pot0"
                outlet_status = "ON" if int(outlet_element.find_next('state').text) == 1 else "OFF"
                outlet_states[outlet_name] = outlet_status

            # Store the outlet states as instance attribute
            self.outlet_states = outlet_states

            # After fetching the outlet states, navigate back to the main device URL
            self.driver.back()
            time.sleep(1)  # Adjust the sleep duration as needed
        
    def _fetch_dhcp_settings(self):
        if self.driver is not None:
            # Construct the URL for the "Network" page
            network_url = self.base_url + "/confignet.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(network_url)
    
            # Wait to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            # Fetch DHCP status
            checkbox = self.driver.find_element(By.NAME, "dhcpenabled")
            self.dhcp_enabled = checkbox.is_selected()
            
            # returns True or False
            return checkbox.is_selected()
        
    def _fetch_pdu_settings(self):
        if self.driver is not None:
            # Construct the URL for the "Network" page
            network_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(network_url)
    
            # Wait to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            # Fetch outlet ping addressess
            input_element = self.driver.find_element(By.NAME, "B00")
            outletA_name = input_element.get_attribute("value")
            
            input_element = self.driver.find_element(By.NAME, "B01")
            outletB_name = input_element.get_attribute("value")
            
            # Store the outlet ping addresses as instance attributes
            self.outlet_names = {
                "A": outletA_name,
                "B": outletB_name,
            }
    
            # Fetch outlet Ping action
            input_element = self.driver.find_element(By.NAME, "O00")
            outletA_onDelay = input_element.get_attribute("value")
            
            input_element = self.driver.find_element(By.NAME, "O01")
            outletB_onDelay = input_element.get_attribute("value")
            
            # Store the outlet states as instance attributes
            self.outlet_onDelays = {
                "A": outletA_onDelay,
                "B": outletB_onDelay,
            }
            
            # Fetch outlet Ping action
            input_element = self.driver.find_element(By.NAME, "F00")
            outletA_offDelay = input_element.get_attribute("value")
            
            input_element = self.driver.find_element(By.NAME, "F01")
            outletB_offDelay = input_element.get_attribute("value")
            
            # Store the outlet states as instance attributes
            self.outlet_oFFDelays = {
                "A": outletA_offDelay,
                "B": outletB_offDelay,
            }
        
    def _fetch_ping_action_settings(self):
        if self.driver is not None:
            # Construct the URL for the "Network" page
            network_url = self.base_url + "/POMeventaction.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(network_url)
    
            # Wait to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            # Fetch outlet ping addressess
            input_element = self.driver.find_element(By.NAME, "A00")
            outletA_ping_address = input_element.get_attribute("value")
            
            input_element = self.driver.find_element(By.NAME, "A01")
            outletB_ping_address = input_element.get_attribute("value")
            
            # Store the outlet ping addresses as instance attributes
            self.outlet_ping_addresses = {
                "A": outletA_ping_address,
                "B": outletB_ping_address,
            }
    
            # Fetch outlet Ping action
            input_element = self.driver.find_element(By.NAME, "C00")
            outletA_ping_action = input_element.get_attribute("value")
            
            input_element = self.driver.find_element(By.NAME, "C01")
            outletB_ping_action = input_element.get_attribute("value")
            
            # Store the outlet states as instance attributes
            self.outlet_ping_action = {
                "A": outletA_ping_action,
                "B": outletB_ping_action,
            }
            
            # Fetch outlet Ping active state
            checkbox = self.driver.find_element(By.NAME, "D00")
            outletA_ping_active = checkbox.is_selected()
            
            checkbox = self.driver.find_element(By.NAME, "D01")
            outletB_ping_active = checkbox.is_selected()
            
            # Store the outlet states as instance attributes
            self.outlet_ping_active = {
                "A": outletA_ping_active,
                "B": outletB_ping_active,
            }
        
    def _fetch_network_settings(self):
        if self.driver is not None:
            # Construct the URL for the "Network" page
            network_url = self.base_url + "/confignet.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(network_url)
    
            # Wait to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            # Fetch DHCP status
            checkbox = self.driver.find_element(By.NAME, "dhcpenabled")
            self.dhcp_enabled = checkbox.is_selected()
    
            # Fetch hostname
            input_element = self.driver.find_element(By.NAME, "host")
            self.hostname = input_element.get_attribute("value")
    
            # Fetch IP address
            input_element = self.driver.find_element(By.NAME, "ip")
            self.ip_address = input_element.get_attribute("value")
    
            # Fetch subnet mask
            input_element = self.driver.find_element(By.NAME, "subnet")
            self.subnet = input_element.get_attribute("value")
    
            # Fetch gateway
            input_element = self.driver.find_element(By.NAME, "gw")
            self.gateway = input_element.get_attribute("value")
    
            # Fetch primary DNS
            input_element = self.driver.find_element(By.NAME, "dns1")
            self.dns1 = input_element.get_attribute("value")
    
            # Fetch secondary DNS
            input_element = self.driver.find_element(By.NAME, "dns2")
            self.dns2 = input_element.get_attribute("value")
        
    def _fetch_system_settings(self):
        if self.driver is not None:
            # Construct the URL for the "Network" page
            system_url = self.base_url + "/index.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(system_url)
        
            # Wait to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            # Get the page source using Selenium
            page_source = self.driver.page_source
    
            # Use Beautiful Soup to parse the page source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find the tbody element containing the desired information
            tbody_element = soup.find('tbody')
            
            # Extracting model number
            model_element = tbody_element.find('td', text="Model No.")
            model = model_element.find_next('td').text.strip() if model_element else "Not Available"
            self.model_num = model
            
            # Extracting firmware version
            firmware_element = soup.find('td', text=re.compile(r"Firmware\s+Version"))
            firmware = firmware_element.find_next('td').text.strip() if firmware_element else "Not Available"
            self.Firmware_ver=firmware
    
            # Extracting MAC address
            mac_element = tbody_element.find('td', text="MAC Address")
            mac = mac_element.find_next('td').font.text.strip() if mac_element else "Not Available"
            self.MAC=mac
        
            # Fetch system name
            input_element = self.driver.find_element(By.NAME, "T0")
            self.system_name = input_element.get_attribute("value")
            
            # Fetch system contact
            input_element = self.driver.find_element(By.NAME, "T1")
            self.system_contact = input_element.get_attribute("value")
            
            # Fetch system location
            input_element = self.driver.find_element(By.NAME, "T2")
            self.system_location = input_element.get_attribute("value")
        
    # ===================================================
    # System Settings
    # ===================================================
    def change_system_settings(self, system_name=None, system_contact=None, location=None, driver=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            logger.info(f"PDU CLASS, change_system_settings")
            logger.info(f"PDU CLASS, change_system_settings, self.base_url: {self.base_url}")
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply=False
            
            if system_name is not None and system_name.strip():
                # Perform action to change the hostname
                print(f"Changing system name to: {system_name}")
                logger.info(f"PDU CLASS, change_system_settings, Changing system name to: {system_name}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "T0")
    
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = system_name	   # Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply=True
                sn = True
                
            if system_contact is not None and system_contact.strip():
                # Perform action to change the hostname
                print(f"Changing system contact to: {system_contact}")
                logger.info(f"PDU CLASS, change_system_settings, Changing system contact to: {system_contact}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "T1")
    
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = system_contact	  # Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply=True
                sc = True
                
            if location is not None and location.strip():
                # Perform action to change the hostname
                print(f"Changing location to: {location}")
                logger.info(f"PDU CLASS, change_system_settings, Changing location to: {location}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "T2")
    
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = location	# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply=True
                ln = True
            
            if apply:
                try: 
                    logger.info(f"PDU CLASS, change_system_settings in apply {apply}")
                    # Wait for the "Apply" button to be clickable and then click it
                    apply_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Apply'][@type='button']")))
                    apply_button.click()
                    logger.info(f"PDU CLASS, change_system_settings, after apply_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable...")
                
                    # Wait for the "Alert" to appear
                    wait = WebDriverWait(self.driver, 10)
                    alert = wait.until(EC.alert_is_present())
                    print("DEBUG: Alert Text:", alert.text)
                    logger.info(f"PDU CLASS, change_system_settings, DEBUG: Alert Text {alert.text}")
    
                    # Accept the alert using the Alert object's accept() method
                    alert.accept()
                    print("DEBUG: Alert Accepted")
                    logger.info(f"PDU CLASS, change_system_settings, DEBUG: Alert accepted")
    
                    # Add a wait here to ensure the page has settled after the action
                    time.sleep(1)  # Adjust the sleep duration as needed
                    
                    # Update class attributes only if the apply button worked
                    if sn:
                        self.set_system_name(system_name)
                    if sc:
                        self.set_system_contact(system_contact)
                    if ln:
                        self.set_location(location)
                        
                    logger.info(f"PDU CLASS, change_system_settings, apply try passed")
                except Exception as e:
                    print(f"An error occurred while applying the changes: {e}")
                    
                    # Handle the error as needed, e.g., log the error, display a message, etc.
            
            return self.driver
   
    # ===================================================
    # User Settings
    # ===================================================
        # Setter method for username
    def set_username(self, new_username):
        if new_username is not None:
            self._username = new_username

    # Setter method for password
    def set_password(self, new_password):
        if new_password is not None:
            self._password = new_password
    
    # ===================================================
    # User Settings
    # ===================================================
    def change_user_settings(self, new_username=None, new_password=None, driver=None):
        if self.driver is not None:
            # Ensure the connection is established
            #self.connect(self.driver)
        
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "User" page
            user_url = self.base_url + "/configID.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(user_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply = False
            
            if new_username is not None and new_username.strip() and new_password is not None and new_password.strip():
                # Perform action to change the hostname
                #print(f"Changing username to: {new_username}")
                logger.info(f"PDU CLASS, change_user_settings, {new_username} {new_password}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "T0")
                logger.info(f"PDU CLASS, change_user_settings, Locate the input element by its name attribute")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                input_element.send_keys(self.username)
                logger.info(f"PDU CLASS, Change the value of the input element {self.username}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "T2")
                logger.info(f"PDU CLASS,  Locate the input element by its name attribute")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = new_username	# Replace this with the value you want to set
                input_element.send_keys(new_value)     
                logger.info(f"PDU CLASS,  Locate the input element by its name attribute {new_value}")
                
                # Perform action to change the password
                #print(f"Changing password to: {new_password}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "T1")
                logger.info(f"PDU CLASS,  Locate the input element by its name attribute")  
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                input_element.send_keys(self.password)
                logger.info(f"PDU CLASS,  Change the value of the input element {self.password}")  
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "T3")
                logger.info(f"PDU CLASS, Locate the input element by its name attribute")  
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = new_password	# Replace this with the value you want to set
                input_element.send_keys(new_value)
                logger.info(f"PDU CLASS,  Change the value of the input element {new_value}")  
                
                apply = True
            
            if apply:
                try:
                    # click Apply button to submit changes
                    apply_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Apply'][@type='submit']")))
                    apply_button.click()
                    logger.info(f"PDU CLASS,  click Apply button to submit changes")  
    
                    # Add a wait here to ensure the page has settled after the action
                    time.sleep(1)  # Adjust the sleep duration as needed
    
                    # Update class attributes using setter methods only if the apply button worked
                    self.set_username(new_username)
                    self.set_password(new_password)
                    
                    # device address
                    device_url = f'http://{self.hostAddress}'
                    logger.info(f"device_url: {device_url}")
                    parsed_url = urlparse(device_url)
                    logger.info(f"parsed_url: {parsed_url}")
                    self.base_url = f"{parsed_url.scheme}://{self.username}:{self.password}@{parsed_url.netloc}"  # Assign base_url
                    logger.info(f"self.base_url: {self.base_url}")
                    
                    logger.info(f"PDU CLASS, Update class attributes only if the apply button worked")
    
                except Exception as e:
                    print(f"An error occurred while applying the changes: {e}")
                    # Handle the error as needed, e.g., log the error, display a message, etc.
            
            return self.driver

    # ===================================================
    # Time Settings
    # ===================================================
    def change_time_settings(self, internet_time=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            time_setting_url = self.base_url + "/configtime.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(time_setting_url)
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(2)  # Adjust the sleep duration as needed
            
            apply = False
            
            if internet_time is not None and internet_time.strip():
                action_dropdown_outletB = Select(self.driver.find_element(By.NAME, "t0"))

                if internet_time.strip().lower() == "on":
                    action_dropdown_outletB.select_by_visible_text("10 minutes")
                elif internet_time.strip().lower() == "off":
                    action_dropdown_outletB.select_by_visible_text("NO")
                 
                time.sleep(.5)	# Adjust the sleep duration as needed
                
                # Find the buttons based on their onclick attribute
                apply_button_name = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='Gett1()']"))
                )
                
                # click Apply but to submit changes to names
                apply_button_name.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                time.sleep(.5)  # Adjust the sleep duration as needed
                
                # Refresh the page to handle the "Please refresh this page" alert
                self.driver.refresh()
                
                # Wait for the element to be present and extract its text
                system_time_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "t5"))
                )
                system_time_text = system_time_element.text

                # Print or use the extracted text
                print("System Time:", system_time_text)
                
            return self.driver
    
    # ===================================================
    # Ping Action Settings
    # ===================================================
    def change_ping_action_settings(self, outletA_IP=None, outletA_action=None, outletA_active=None, outletB_IP=None, outletB_action=None, outletB_active=None):
        if self.driver is not None:
            # Ensure the connection is established
            self.connect(self.driver)
    
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            ping_action_url = self.base_url + "/POMeventaction.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(ping_action_url)
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(2)  # Adjust the sleep duration as needed
            
            apply = False
            
            # Check the state of checkbox_outletA
            checkbox_outletA = self.driver.find_element(By.NAME, "D00")
            checkbox_state_outletA = checkbox_outletA.is_selected()
    
            # If outletA_IP or outletA_action is not None and checkbox_outletA is enabled, disable it
            if ((outletA_IP is not None and outletA_IP.strip()) or (outletA_action is not None and outletA_action.strip())) and checkbox_state_outletA:
                checkbox_outletA.click()
                apply = True
    
            if apply:
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                apply = False
            
            # make changes
            if outletA_IP is not None and outletA_IP.strip():
                ip_field_outletA = self.driver.find_element(By.NAME, "A00")
                ip_field_outletA.clear()
                ip_field_outletA.send_keys(outletA_IP)
                time.sleep(.5)	# Adjust the sleep duration as needed
                
            if outletA_action is not None and outletA_action.strip():
                action_dropdown_outletA = Select(self.driver.find_element(By.NAME, "C00"))
                action_dropdown_outletA.select_by_visible_text(outletA_action)
                time.sleep(.5)	# Adjust the sleep duration as needed
    
            # make changes
            if outletA_active is not None and outletA_active.strip():
                checkbox_outletA = self.driver.find_element(By.NAME, "D00")
                checkbox_state_outletA = checkbox_outletA.is_selected()
                if (outletA_active.lower() == "enable" and not checkbox_state_outletA) or (outletA_active.lower() == "disable" and checkbox_state_outletA):
                    checkbox_outletA.click()
                    apply = True
                    
                if outletA_active.lower() == "disable":
                    print("changes made to outletA IP and Action will not be saved as active state is set to disabled")
    
            if apply:
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # Update class attributes only if the apply button worked
                self.set_username(new_username)
                self.set_password(new_password)
                
                apply = False
                
            # Check the state of checkbox_outletB
            checkbox_outletB = self.driver.find_element(By.NAME, "D01")
            checkbox_state_outletB = checkbox_outletB.is_selected()
    
            # If outletB_IP or outletB_action is not None and checkbox_state_outletB is enabled, disable it
            if ((outletB_IP is not None and outletB_IP.strip()) or (outletB_action is not None and outletB_action.strip())) and checkbox_state_outletB:
                checkbox_outletB.click()
                apply = True
    
            if apply:
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                apply = False
            
            # make changes
            if outletB_IP is not None and outletB_IP.strip():
                ip_field_outletB = self.driver.find_element(By.NAME, "A01")
                ip_field_outletB.clear()
                ip_field_outletB.send_keys(outletB_IP)
                time.sleep(2)  # Adjust the sleep duration as needed
            
            if outletB_action is not None and outletB_action.strip():
                action_dropdown_outletB = Select(self.driver.find_element(By.NAME, "C01"))
                action_dropdown_outletB.select_by_visible_text(outletB_action)
                time.sleep(.5)	# Adjust the sleep duration as needed
    
            # make changes
            if outletB_active is not None and outletB_active.strip():
                checkbox_outletB = self.driver.find_element(By.NAME, "D01")
                checkbox_state_outletB = checkbox_outletB.is_selected()
                if (outletB_active.lower() == "enable" and not checkbox_state_outletB) or (outletB_active.lower() == "disable" and checkbox_state_outletB):
                    checkbox_outletB.click()
                    apply = True
                
                if outletB_active.lower() == "disable":
                    print("changes made to outletB IP and Action will not be saved as active state is set to disabled")
    
            if apply:
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            # update ping action attributes
            self._fetch_ping_action_settings(self)
    
            return self.driver
    
    # ===================================================
    # Outlet Settings
    # ===================================================
    def perform_outlet_actions(self, outlet_name, checkbox_name, button_name):
        if self.driver is not None:
            try:
                # Find and click the checkbox for the specified outlet
                checkbox = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.NAME, checkbox_name)))
                print(f"DEBUG: Found Checkbox Element for {outlet_name}: {checkbox_name}")
                checkbox.click()
                print(f"DEBUG: Checkbox '{checkbox_name}' Clicked for {outlet_name}")
    
                # Find and click the button for the specified action
                button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, button_name)))
                print(f"DEBUG: Found Button Element for {outlet_name}: {button_name}")
                button.click()
                print(f"DEBUG: Button '{button_name}' Clicked for {outlet_name}")
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method  
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(2)  # Adjust the sleep duration as needed
                
                # update ping action attributes
                self._fetch_outlet_states()
    
                # Return a success message
                return f"Outlet {outlet_name} action '{button_name}' completed successfully."
    
            except Exception as e:
                # Handle any exceptions that occurred during the action
                error_message = f"Error performing outlet {outlet_name} action: {str(e)}"
                print(error_message)
                return error_message

    def change_power_action(self, outlet_name=None, action=None):
        if self.driver is not None:
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
    
            # Update outlet states
            self._fetch_outlet_states()
    
            # Get the current state of outlets (on or off)
            current_state = self.get_outlet_states()
    
            # Construct the URL for the "Outlet" page
            outlet_url = self.base_url + "/outlet.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(outlet_url)
            
            time.sleep(1)  # Adjust the sleep duration as needed
            
            if current_state[outlet_name] == "OFF" and action == "ON":
                # Perform TURN ON action on outlet
                self.perform_outlet_actions(outlet_name, outlet_check_boxes.get(outlet_name), outlet_actions.get(action))
            elif current_state[outlet_name] == "ON" and action == "OFF":
                # Perform TURN OFF action on outlet
                self.perform_outlet_actions(outlet_name, outlet_check_boxes.get(outlet_name), outlet_actions.get(action))
            elif action == "OFF/ON":
                # Perform TURN OFF/ON action on outlet
                self.perform_outlet_actions(outlet_name, outlet_check_boxes.get(outlet_name), outlet_actions.get(action))
            else:
                if current_state[outlet_name] == "ON" and action == "ON":
                    print(f"Power is already ON for outlet {outlet_name}")
                elif current_state[outlet_name] == "OFF" and action == "OFF":
                    print(f"Power is already OFF for outlet {outlet_name}")
                else:
                    print(f"Outlet {outlet_name} is currently {current_state[outlet_name]}, tried to change to {action}")
                    
            time.sleep(1)  # Adjust the sleep duration as needed
    
            return self.driver  # Return the driver instance instead of closing it
    
    # ===================================================
    # PDU Settings
    # ===================================================
    def change_ouletA_name(self, outletA_name=None):
        if self.driver is not None:
            # Ensure the connection is established
            ####self.connect(self.driver)
    
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            pdu_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(pdu_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply_name = False
        
            if outletA_name is not None and outletA_name.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA name to: {outletA_name}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "B00")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletA_name	# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_name = True
                
            if apply_name:
                # Find the buttons based on their onclick attribute
                apply_button_name = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetGroupName(0)']"))
                )
            
                # click Apply but to submit changes to names
                apply_button_name.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_pdu_settings()
                
            return self.driver
        
    def change_ouletA_onDelay(self, outletA_onDelay=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            pdu_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(pdu_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply_on_delay = False
            
            if outletA_onDelay is not None and outletA_onDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA ON delay to: {outletA_onDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "O00")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletA_onDelay				# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_on_delay = True
            
            if apply_on_delay:
                # Find the buttons based on their onclick attribute
                apply_button_on_delay = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTime(0)']"))
                )
            
                # click Apply but to submit changes to on delay
                apply_button_on_delay.click()
                
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_pdu_settings()
                
            return self.driver
    
    def change_ouletA_offDelay(self, outletA_offDelay=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            pdu_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(pdu_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply_off_delay = False
            
            if outletA_offDelay is not None and outletA_offDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA OFF delay to: {outletA_offDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "F00")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletA_offDelay			 # Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_off_delay = True
            
            if apply_off_delay:
                # Find the buttons based on their onclick attribute
                apply_button_off_delay = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTimef(0)']"))
                )
            
                ## click Apply but to submit changes to off delay
                apply_button_off_delay.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_pdu_settings()
    
            return self.driver
    
    def change_ouletB_name(self, outletB_name=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            pdu_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(pdu_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply_name = False
        
            if outletB_name is not None and outletB_name.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA name to: {outletB_name}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "B01")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletB_name	# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_name = True
                
            if apply_name:
                # Find the buttons based on their onclick attribute
                apply_button_name = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetGroupName(0)']"))
                )
            
                # click Apply but to submit changes to names
                apply_button_name.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_pdu_settings()
                
            return self.driver
        
    def change_ouletB_onDelay(self, outletB_onDelay=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            pdu_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(pdu_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply_on_delay = False
            
            if outletB_onDelay is not None and outletB_onDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA ON delay to: {outletB_onDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "O01")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletB_onDelay				# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_on_delay = True
            
            if apply_on_delay:
                # Find the buttons based on their onclick attribute
                apply_button_on_delay = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTime(0)']"))
                )
            
                # click Apply but to submit changes to on delay
                apply_button_on_delay.click()
                
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_pdu_settings()
                
            return self.driver
    
    def change_ouletB_offDelay(self, outletB_offDelay=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            pdu_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(pdu_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply_off_delay = False
            
            if outletB_offDelay is not None and outletB_offDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA OFF delay to: {outletB_offDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "F01")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletB_offDelay			 # Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_off_delay = True
            
            if apply_off_delay:
                # Find the buttons based on their onclick attribute
                apply_button_off_delay = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTimef(0)']"))
                )
            
                ## click Apply but to submit changes to off delay
                apply_button_off_delay.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_pdu_settings()
    
            return self.driver
    
    def change_pdu_settings(self, outletA_name=None, outletA_onDelay=None, outletA_offDelay=None, outletB_name=None, outletB_onDelay=None, outletB_offDelay=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
            
            # Construct the URL for the "Ping Action" page
            pdu_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Ping Action" page
            self.driver.get(pdu_url)
            
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
            
            apply_name = False
            apply_on_delay = False
            apply_off_delay = False
            
            if outletA_name is not None and outletA_name.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA name to: {outletA_name}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "B00")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletA_name	# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_name = True
            
            if outletA_onDelay is not None and outletA_onDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA ON delay to: {outletA_onDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "O00")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletA_onDelay				# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_on_delay = True
            
            if outletA_offDelay is not None and outletA_offDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA OFF delay to: {outletA_offDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "F00")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletA_offDelay			 # Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_off_delay = True
            
            if outletB_name is not None and outletB_name.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA name to: {outletB_name}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "B01")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletB_name	# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_name = True
            
            if outletB_onDelay is not None and outletB_onDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA ON delay to: {outletB_onDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "O01")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletB_onDelay				# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_on_delay = True
            
            if outletB_offDelay is not None and outletB_offDelay.strip():
                # Perform action to change the primary DNS
                print(f"Changing outletA OFF delay to: {outletB_offDelay} secs")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "F01")
                
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = outletB_offDelay			 # Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply_off_delay = True
                
            if apply_name:
                # Find the buttons based on their onclick attribute
                apply_button_name = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetGroupName(0)']"))
                )
            
                # click Apply but to submit changes to names
                apply_button_name.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
            
            if apply_on_delay:
                # Find the buttons based on their onclick attribute
                apply_button_on_delay = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTime(0)']"))
                )
            
                # click Apply but to submit changes to on delay
                apply_button_on_delay.click()
                
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
            
            if apply_off_delay:
                # Find the buttons based on their onclick attribute
                apply_button_off_delay = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTimef(0)']"))
                )
            
                ## click Apply but to submit changes to off delay
                apply_button_off_delay.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
                
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
            # update attributes
            self._fetch_pdu_settings()
    
            return self.driver
        
    def change_pdu_settings(self, outletA_name=None, outletA_onDelay=None, outletA_offDelay=None, outletB_name=None, outletB_onDelay=None, outletB_offDelay=None):
        if self.driver is not None:
            if outletA_name or outletA_onDelay or outletA_offDelay:
                # Call function to change Outlet A settings
                self.change_outletA_settings(name=outletA_name, on_delay=outletA_onDelay, off_delay=outletA_offDelay)
    
            if outletB_name or outletB_onDelay or outletB_offDelay:
                # Call function to change Outlet B settings
                self.change_outletB_settings(name=outletB_name, on_delay=outletB_onDelay, off_delay=outletB_offDelay)
                
    def change_outletA_settings(self, name=None, on_delay=None, off_delay=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
    
            # Construct the URL for the "Outlet A" page
            outletA_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Outlet A" page
            self.driver.get(outletA_url)
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            apply_name = False
            apply_on_delay = False
            apply_off_delay = False
    
            if name is not None and name.strip():
                # Perform action to change the outlet A name
                print(f"Changing Outlet A name to: {name}")
    
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "B00")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = name	        # Replace this with the value you want to set
                input_element.send_keys(new_value)
    
                apply_name = True
    
            if on_delay is not None and on_delay.strip():
                # Perform action to change the outlet A ON delay
                print(f"Changing Outlet A ON delay to: {on_delay} secs")
    
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "O00")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = on_delay		# Replace this with the value you want to set
                input_element.send_keys(new_value)
    
                apply_on_delay = True
    
            if off_delay is not None and off_delay.strip():
                # Perform action to change the outlet A OFF delay
                print(f"Changing Outlet A OFF delay to: {off_delay} secs")
    
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "F00")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = off_delay		# Replace this with the value you want to set
                input_element.send_keys(new_value)
    
                apply_off_delay = True
    
            if apply_name:
                # Find the buttons based on their onclick attribute
                apply_button_outletA = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetGroupName(0)']"))
                )
    
                # click Apply button to submit changes to Outlet A settings
                apply_button_outletA.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
            
            if apply_on_delay:
                # Find the buttons based on their onclick attribute
                apply_button_outletA = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTime(0)']"))
                )
    
                # click Apply button to submit changes to Outlet A settings
                apply_button_outletA.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
            if apply_off_delay:
                # Find the buttons based on their onclick attribute
                apply_button_outletA = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTimef(0)']"))
                )
    
                # click Apply button to submit changes to Outlet A settings
                apply_button_outletA.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
            
            return self.driver
    
    def change_outletB_settings(self, name=None, on_delay=None, off_delay=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
    
            # Construct the URL for the "Outlet B" page
            outletB_url = self.base_url + "/configpdu.htm"
    
            # Navigate to the "Outlet B" page
            self.driver.get(outletB_url)
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            apply_name = False
            apply_on_delay = False
            apply_off_delay = False
    
            if name is not None and name.strip():
                # Perform action to change the outlet B name
                print(f"Changing Outlet B name to: {name}")
    
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "B01")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = name	# Replace this with the value you want to set
                input_element.send_keys(new_value)
    
                apply_name = True
    
            if on_delay is not None and on_delay.strip():
                # Perform action to change the outlet B ON delay
                print(f"Changing Outlet B ON delay to: {on_delay} secs")
    
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "O01")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = on_delay		# Replace this with the value you want to set
                input_element.send_keys(new_value)
    
                apply_on_delay = True
    
            if off_delay is not None and off_delay.strip():
                # Perform action to change the outlet B OFF delay
                print(f"Changing Outlet B OFF delay to: {off_delay} secs")
    
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "F01")
    
                # Change the value of the input element
                input_element.clear()		# Clear the existing value (optional, if needed)
                new_value = off_delay		# Replace this with the value you want to set
                input_element.send_keys(new_value)
    
                apply_off_delay = True
                
            if apply_name:
                # Find the buttons based on their onclick attribute
                apply_button_outletB = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetGroupName(0)']"))
                )
    
                # click Apply button to submit changes to Outlet A settings
                apply_button_outletB.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
            
            if apply_on_delay:
                # Find the buttons based on their onclick attribute
                apply_button_outletB = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTime(0)']"))
                )
    
                # click Apply button to submit changes to Outlet A settings
                apply_button_outletB.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
            if apply_off_delay:
                # Find the buttons based on their onclick attribute
                apply_button_outletB = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@onclick='GetTimef(0)']"))
                )
    
                # click Apply button to submit changes to Outlet A settings
                apply_button_outletB.click()
    
                # Wait for the confirmation alert to appear
                wait = WebDriverWait(self.driver, 10)
                alert = wait.until(EC.alert_is_present())
                print("DEBUG: Alert Text:", alert.text)
    
                # Accept the alert using the Alert object's accept() method
                alert.accept()
                print("DEBUG: Alert Accepted")
    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
    
            return self.driver

    # ===========================================
    # Network Settings
    # ===========================================
    # dhcp can be either yes/on/enable or no/off/disable
    def change_dhcp_setting(self, dhcp=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
    
            # Construct the URL for the "Outlet B" page
            network_url = self.base_url + "/confignet.htm"
    
            # Navigate to the "Outlet B" page
            self.driver.get(network_url)
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            apply = False
            
            # Find the checkbox element by its name attribute
            checkbox = self.driver.find_element(By.NAME, "dhcpenabled")
            
            # Remove spaces and convert to uppercase for case-insensitive comparison
            dhcp_lower = dhcp.strip().lower()
            
            if dhcp_lower == "enable" or dhcp_lower == "on" or dhcp_lower == "yes":
                dhcp_state = True       
            elif dhcp_lower == "disable" or dhcp_lower == "off" or dhcp_lower == "no":
                dhcp_state = False
            else:
                dhcp = None
                
            if dhcp is not None and dhcp_lower:
                # Perform action to enable/disable dhcp 
                print(f"Changing dhcp to: {dhcp_state}")
    
                # Check the checkbox if it's not already checked
                if not checkbox.is_selected() and dhcp_state: #dhcp.strip().lower() == "enable":
                    checkbox.click()
                    apply = True
                elif checkbox.is_selected() and not dhcp_state: #dhcp.strip().lower() == "disable":
                    checkbox.click()
                    apply = True
                else:
                    if not checkbox.is_selected() and not dhcp_state: #dhcp.strip().lower() == "disable":
                        print("dhcp is already disabled")
                    elif checkbox.is_selected() and dhcp_state: #dhcp.strip().lower() == "enable":
                        print("dhcp is already enabled")
            
            if apply:
                try:
                    # After changing the value, you can click the "Apply" button to save the changes
                    apply_button = self.driver.find_element(By.NAME, "submit")
                    apply_button.click()
                        
                    # Add a wait here to ensure the page has settled after the action
                    time.sleep(1)  # Adjust the sleep duration as needed
                    
                    # Update Class dhcp attribute
                    self._fetch_dhcp_settings()
                    
                    print("dhcp updated!")
                except Exception as e:
                    print(f"An error occurred while applying the changes: {e}")
                    # Handle the error as needed, e.g., log the error, display a message, etc.
            
            return self.driver
    
    def change_hostname_settings(self, hostname=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
    
            # Construct the URL for the "Outlet B" page
            outletB_url = self.base_url + "/confignet.htm"
    
            # Navigate to the "Outlet B" page
            self.driver.get(outletB_url)
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            apply = False
            
            if hostname is not None and hostname.strip():
                # Perform action to change the hostname
                print(f"Changing hostname to: {hostname}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "host")
    
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = hostname	# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply = True
                
            if apply:
                # After changing the value, you can click the "Apply" button to save the changes
                apply_button = self.driver.find_element(By.NAME, "submit")
                apply_button.click()
                    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_network_settings()
            
            return self.driver
        
    def is_valid_ip(ip):
        # Regular expression pattern for a valid IP address
        ip_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        return re.match(ip_pattern, ip) is not None
    
    def is_valid_subnet(subnet):
        # Regular expression pattern for a valid subnet in the format "xxx.xxx.xxx.xxx"
        subnet_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        return re.match(subnet_pattern, subnet) is not None
    
    def change_network_settings(self, IP=None, subnet=None, gateway=None, DNS1=None, DNS2=None):
        if self.driver is not None:
            # Navigate to the URL
            alert = self.driver.get(self.base_url)
    
            # Construct the URL for the "Outlet B" page
            network_url = self.base_url + "/confignet.htm"
    
            # Navigate to the "Outlet B" page
            self.driver.get(network_url)
    
            # Add a wait here to ensure the page has settled after the action
            time.sleep(1)  # Adjust the sleep duration as needed
    
            apply = False
            
            # Find the checkbox element by its name attribute
            checkbox = self.driver.find_element(By.NAME, "dhcpenabled")
            
            # Check the checkbox if it's not already checked
            if not checkbox.is_selected():
                print("dhcp is already disabled")
            elif checkbox.is_selected():
                checkbox.click()
                apply = True
            
            if IP is not None and IP.strip() and is_valid_ip(IP.strip()):
                # Perform action to change the IP address
                print(f"Changing IP address to: {IP}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "ip")
                
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = IP			# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply = True
            else:
                print("Invalid IP address. Please provide a valid IP.")
    
            if subnet is not None and subnet.strip() and is_valid_subnet(subnet.strip()):
                # Perform action to change the netmask
                print(f"Changing subnet to: {subnet}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "subnet")
                
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = subnet		# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply = True
            else:
                print("Invalid subnet. Please provide a valid subnet in the format 'xxx.xxx.xxx.xxx'.")
    
            if gateway is not None and gateway.strip() and is_valid_ip(gateway.strip()):
                # Perform action to change the gateway
                print(f"Changing gateway to: {gateway}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "gw")
                
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = gateway		# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply = True
            else:
                print("Invalid gateway address. Please provide a valid IP.")
    
            if DNS1 is not None and DNS1.strip() and is_valid_dns(DNS1.strip()):
                # Perform action to change the primary DNS
                print(f"Changing primary DNS to: {DNS1}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "dns1")
                
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = DNS1		# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply = True
            else:
                print("Invalid primary DNS. Please provide a valid DNS in the format 'xxx.xxx.xxx.xxx'.")
    
            if DNS2 is not None and DNS2.strip() and is_valid_dns(DNS2.strip()):
                # Perform action to change the secondary DNS
                print(f"Changing secondary DNS to: {DNS2}")
                
                # Locate the input element by its name attribute
                input_element = self.driver.find_element(By.NAME, "dns2")
                
                # Change the value of the input element
                input_element.clear()	# Clear the existing value (optional, if needed)
                new_value = DNS2		# Replace this with the value you want to set
                input_element.send_keys(new_value)
                
                apply = True
            else:
                print("Invalid secondary DNS. Please provide a valid DNS in the format 'xxx.xxx.xxx.xxx'.")
            
            if apply:
                # After changing the value, you can click the "Apply" button to save the changes
                apply_button = self.driver.find_element(By.NAME, "submit")
                apply_button.click()
                    
                # Add a wait here to ensure the page has settled after the action
                time.sleep(1)  # Adjust the sleep duration as needed
                
                # update attributes
                self._fetch_network_settings()
            
            return self.driver
    
    # Getters for the attributes
    @property
    def host_address(self):
        return self.hostAddress

    @property
    def user_name(self):
        return self.username

    @property
    def passwd(self):
        return self.password

    @property
    def dns_1(self):
        return self.dns1

    @property
    def dns_2(self):
        return self.dns2
        
    # Getters for DNS attributes
    def get_dns1(self):
        return self.dns1

    def get_dns2(self):
        return self.dns2

    @property
    def is_dhcp_enabled(self):
        return self.dhcp_enabled

    @property
    def host_name(self):
        return self.hostname

    @property
    def ip(self):
        return self.ip_address

    @property
    def netmask(self):
        return self.subnet

    @property
    def gateway_address(self):
        return self.gateway
        
    def set_username(self, new_username):
        print(f"Changing username to: {new_username}")
        self.username = new_username

    def set_password(self, new_password):
        print(f"Changing password to: {new_password}")
        self.password = new_password
    
    def set_system_name(self, new_system_name):
        print(f"Changing system name to: {new_system_name}")
        self.system_name = new_system_name

    def set_system_contact(self, new_system_contact):
        print(f"Changing password to: {new_system_contact}")
        self.system_contact = new_system_contact
        
    def set_location(self, new_location):
        print(f"Changing password to: {new_location}")
        self.location = new_location
        
    def set_dhcp(self, new_dhcp_status):
        print(f"Changing dhcp to: {new_dhcp_status}")
        self.dhcp = new_dhcp_status
        
    def set_hostname(self, new_hostname):
        print(f"Changing dhcp to: {new_hostname}")
        self.hostname = new_hostname
