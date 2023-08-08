# Network Power Delivery Unit (PDU)
```
Main Menu:
1. Add new device
2. Connect to a device
3. Show available devices
4. Remove a device
5. View Outlet Settings for all Devices
6. Exit
Enter option number:
```
```
device:  192.168.20.205
Device Menu:
1. View System Settings
2. Change System Settings
3. Change User Settings
4. Change Ping Action Settings
5. Change Outlet Settings
6. Change PDU Settings
7. Change Network Settings
8. Change Time Settings
8. Back
Enter your choice:
```

PDU Class functions, variables:
System:
system Name = String
System Contact = String
Location = String

Outlet:
options: ON,OFF, OFF/ON

Ping Action:
Ping IP Address = String (IP)
Action: OFF,OFF/ON
Active: enabled, disabled

PDU:
Name: String
ON Delay(sec) = Int
OFF Delay(sec) = Int

User:
old ID = String
old Password = String
new ID = String
new Password = String

Network:
Host Name = String
IP Address =  String (IP)
Subnet Mask = String (IP)
Gateway = String(IP)
DHCP = String(enable,disable)
Primary DNS IP = String(IP)
Secondary DNS IP = String(IP)

Time:
Time between updates (NTP)= String(on,off)
