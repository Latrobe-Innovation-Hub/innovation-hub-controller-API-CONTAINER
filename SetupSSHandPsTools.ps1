<#
Before running script:
  1. Ensure you have administrative privileges on the computer. 
     Right-click on the script file and select "Run with PowerShell" or "Run as Administrator."
  
  2. If prompted by User Account Control (UAC), click "Yes" to allow the script to make changes to the system.
  
  3. The script will then execute the steps to install OpenSSH, start SSH services, open port 22,
     modify the registry, download and install PsTools, and finally, reboot the system.

NOTE:
  Please remember, Modifying system settings can have significant implications, so it's crucial to understand
  the changes the script makes and ensure you have the necessary permissions before running it.

  If you are unsure or uncomfortable with running the script, consider seeking help from your IT department or
  a knowledgeable system administrator.
#>

# Step 1: Install OpenSSH via add features settings
Add-WindowsFeature -Name OpenSSH-Server -IncludeAllSubFeature

# Step 2: Start authentication and SSH service via services
Start-Service ssh-agent
Start-Service sshd

# Step 3: Open port 22 for SSH via firewall
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22

# Step 4: Create a new registry key for LocalAccountTokenFilterPolicy
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -Value 1 -PropertyType DWord -Force

# Step 5: Disable UAC by setting EnableLUA to 0
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 0 -PropertyType DWord -Force

# Step 6: Download and install PsTools from Microsoft
$psToolsUrl = "https://download.sysinternals.com/files/PSTools.zip"
$downloadPath = "$env:TEMP\PSTools.zip"
$extractPath = "$env:TEMP\PSTools"
$destination = "C:\Windows\System32"

Invoke-WebRequest -Uri $psToolsUrl -OutFile $downloadPath
Expand-Archive -Path $downloadPath -DestinationPath $extractPath
Copy-Item "$extractPath\*" -Destination $destination

# Step 7: Reboot the system
Restart-Computer
