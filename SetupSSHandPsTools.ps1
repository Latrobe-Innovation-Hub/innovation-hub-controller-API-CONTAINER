<#
Author: Andrew McDonald
Date: 21.07.2023
Description: Potential host setup script for Innovation Hub API Windows devices

Usage:
  Run locally on Windows host system in Powershell with Admin Rights

NOTE:
  This is just a test script, use at your own risk

Version History:
  0.1 - Testing 

#>

$comment = @"
===============================================================================

Before running script:

  1. Ensure you have administrative privileges on the computer. 
     Right-click on the script file and select "Run with PowerShell" 
     or "Run as Administrator."
  
  2. If prompted by User Account Control (UAC), click "Yes" to allow 
     the script to make changes to the system.
  
  3. The script will then execute the steps to install OpenSSH, 
     start SSH services, open port 22, modify the registry, download 
     and install PsTools, and finally, reboot the system.

NOTE:

  Please remember, Modifying system settings can have significant 
  implications, so it's crucial to understand the changes the script 
  makes and ensure you have the necessary permissions before running it.

  If you are unsure or uncomfortable with running the script, consider 
  seeking help from your IT department or a knowledgeable system administrator.

===============================================================================

"@

# Display the instruction comment
Write-Host $comment

# Prompt the user if they wish to continue
$response = Read-Host "Do you wish to continue? Type 'yes' to proceed."

if ($response -eq 'YES' -or $response -eq 'yes') {
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
}
else {
    Write-Host "Script execution cancelled. No changes have been made to the system."
    Read-Host "Press any key to exit..."
    exit
}
