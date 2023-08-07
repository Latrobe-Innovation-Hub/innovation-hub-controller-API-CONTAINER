# Import the DeviceController class from pdu_class.py
from pdu_class import DeviceController

def main():
    master_username = input("Enter the master username: ")
    master_password = input("Enter the master password: ")

    devices = []

    while True:
        print("\nMain Menu:")
        print("1. Add new device")
        print("2. Connect to a device")
        print("3. Show available devices")
        print("4. Remove a device")
        print("5. Exit")

        main_choice = input("Enter your choice (1/2/3/4): ")

        if main_choice == "1":
            host_address = input("Enter the device address: ")
            new_device = DeviceController(host_address, master_username, master_password)
            devices.append(new_device)
            print("Device added successfully!")

        elif main_choice == "2":
            if not devices:
                print("No devices added yet. Please add a device first.")
            else:
                print("Available devices:")
                for index, device in enumerate(devices):
                    print(f"{index + 1}. {device.hostAddress}")

                device_choice = int(input("Enter the device number you want to connect to: "))
                selected_device = devices[device_choice - 1]
                selected_device.connect()
                print("Connected to the selected device.")

                while True:
                    print("\nDevice Menu:")
                    print("1. Disconnect from the current device")
                    print("2. View System Settings")
                    print("3. Change System Settings")
                    print("4. Change User Settings")
                    print("5. Change Ping Action Settings")
                    print("6. Change Outlet Settings")
                    print("7. Change PDU Settings")
                    print("8. Change Network Settings")
                    print("9. Back")

                    device_option = input("Enter your choice (1/2/3/4/5/6): ")

                    if device_option == "1":
                        selected_device.disconnect()
                        print("Disconnected from the current device.")
                        break

                    elif device_option == "2":
                        print("View System Settings.")
                        selected_device.print_all_info()
                    
                    elif device_option == "3":
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
                        
                    elif device_option == "4":
                        print("\nChange User Settings:")
                        new_username = input("Enter new username (leave blank to keep current): ")
                        new_password = input("Enter new password (leave blank to keep current): ")
                        driver = input("Enter new driver (leave blank to keep current): ")
                        selected_device.change_user_settings(new_username=new_username,
                                                             new_password=new_password,
                                                             driver=driver)
                        print("User settings updated successfully.")
                    
                    elif device_option == "5":
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
                    
                    elif device_option == "6":
                        print("\nChange Outlet Settings:")
                        selected_device.print_outlet_info()
                        outlet_name = input("Enter outlet name (A/B): ")
                        action = input("Enter new action (e.g., 'ON', 'OFF', 'OFF/ON'): ")
                        selected_device.change_power_action(outlet_name=outlet_name, action=action)
                        print("Outlet settings updated successfully.")
                        
                    elif device_option == "7":
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
                    
                    elif device_option == "8":
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

                    elif device_option == "9":
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
            print("Exiting the program.")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()