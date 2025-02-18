<#
Author: Andrew McDonald
Date: 21.07.2023
Description: Potential host uninstall script to undo changes made for API access

Usage:
  Run locally on Windows host system in Powershell with Admin Rights

NOTE:
  This is just a test script, use at your own risk

Version History:
  0.1 - Testing 

#>

$comment = @"
=======================================================================================

Uninstall script to remove configurations made for Innovation Hub API controller access

Before running script:

  1. Ensure you have administrative privileges on the computer. 
     Right-click on the install-script.bat file and select "Run as Administrator."
  
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

=======================================================================================

"@

# Display the instruction comment
Write-Host $comment

# Prompt the user if they wish to continue
$response = Read-Host "Do you wish to continue? Type 'yes' to proceed."

if ($response -eq 'YES' -or $response -eq 'yes') {

	# Required for displaying message box
	Add-Type -AssemblyName PresentationFramework

	# Function to check if a step was successful
	function ConfirmStepSuccess {
		param([string]$stepName, [bool]$success)
		if ($success) {
			Write-Host "Step $stepName completed successfully."
		} else {
			Write-Host "Step $stepName encountered an error. Undo script execution cancelled."
		}
		$undoStepsStatus += [PSCustomObject]@{Step = $stepName; Success = $success}
	}

	# Array to store the status of each undo step
	$undoStepsStatus = @()

	# STEP 1 Remove PsTools if installed
	$step1Success = $true
	if (Test-Path "C:\PsTools") {
		try {
			Remove-Item "C:\PsTools" -Force -Recurse

			# Remove the PSTools directory from the system's PATH environment variable
			$pathEnv = [System.Environment]::GetEnvironmentVariable('PATH', [System.EnvironmentVariableTarget]::Machine)
			$newPath = $pathEnv -replace [regex]::Escape(";C:\PsTools"), ""
			[System.Environment]::SetEnvironmentVariable('PATH', $newPath, [System.EnvironmentVariableTarget]::Machine)
		} catch {
			$step1Success = $false
		}
	} else {
		Write-Host "PsTools were not installed."
	}
	$undoStepsStatus += [PSCustomObject]@{Step = "Remove PsTools"; Success = $step1Success}

	# Check if port 22 is open for SSH
	$step2Success = $true
	$port22Rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
	if ($port22Rule -ne $null) {
		# Step 2: Close port 22 for SSH via firewall
		$step2Success = $true
		try {
			Remove-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction Stop
		} catch {
			$step2Success = $false
		}
		#ConfirmStepSuccess "Close Port 22" $step2Success
	} else {
		Write-Host "Port 22 is already closed for SSH."
	}
	$undoStepsStatus += [PSCustomObject]@{Step = "Close Port 22"; Success = $step2Success}
	
	# Check if sshd service is running, stop and set to manual startup
	$sshdServiceStatus = Get-Service -Name sshd -ErrorAction SilentlyContinue

	# STEP 3A: Stop and set sshd service to manual startup
	$step3aSuccess = $true
	if ($sshdServiceStatus -ne $null -and $sshdServiceStatus.ServiceName -contains 'sshd') {
		try {
			Stop-Service sshd
			Start-Sleep -Seconds 2
			Set-Service -Name sshd -StartupType Manual
		} catch {
			$step3aSuccess = $false
		}
		#ConfirmStepSuccess "Stop and Set sshd to Manual Startup" $step3adSuccess
	} else {
		Write-Host "sshd service is already stopped."
	}
	$undoStepsStatus += [PSCustomObject]@{Step = "Stop and set sshd to Manual Startup"; Success = $step3aSuccess}

	# Check if ssh-agent service is running, stop and set to manual startup
	$sshagentServiceStatus = Get-Service -Name ssh-agent -ErrorAction SilentlyContinue

	# STEP 3B: Stop and set ssh-agent service to manual startup
	#$step3bSuccess = $true
	#if ($sshagentServiceStatus -ne $null -and $sshagentServiceStatus.ServiceName -contains 'ssh-agent') {
	#	try {
	#		Stop-Service sshd-agent
	#		Start-Sleep -Seconds 2
	#		Set-Service -Name ssh-agent -StartupType Manual
	#	} catch {
	#		$step3bSuccess = $false
	#	}
	#	#ConfirmStepSuccess "Stop and Set sshd to Manual Startup" $step3SshdSuccess
	#} else {
	#	Write-Host "sshd service is already stopped."
	#}
	#$undoStepsStatus += [PSCustomObject]@{Step = "Stop and set ssh-agent to Manual Startup"; Success = $step3bSuccess}

	# Step 4: Run the OpenSSH uninstall script
	$step4Success = $true
	try {
    		if ([Environment]::Is64BitOperatingSystem) {
        		$openSSHArch = "Win64"  # Use the Win64 architecture if the system is 64-bit
    		} else {
        		$openSSHArch = "Win32"  # Use the Win32 architecture if the system is 32-bit
    		}

    		$installPath = "C:\Program Files\OpenSSH\OpenSSH-$openSSHArch"
    		$uninstallScript = Join-Path $installPath "uninstall-sshd.ps1"

    		if (Test-Path $uninstallScript) {
        		Set-Location $installPath
        		.\uninstall-sshd.ps1
    		} else {
        		$step4Success = $false
    		}
	} catch {
    		$step4Success = $false
	}
	ConfirmStepSuccess "Run OpenSSH uninstall script" $step4Success
	$undoStepsStatus += [PSCustomObject]@{Step = "Run OpenSSH uninstall script"; Success = $step4Success}

	# Step 4: Remove OpenSSH via remove features settings
	#$step4Success = $true
	#try {
	#	# Uninstall the OpenSSH Client
	#	Remove-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0

	#	#Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Client' } | Remove-WindowsCapability -Online
	#} catch {
	#	$step4Success = $false
	#}
	#Write-Host "OpenSSH is not installed."
	#$undoStepsStatus += [PSCustomObject]@{Step = "Remove OpenSSH Client"; Success = $step4Success}

	# Step 4b: Remove OpenSSH via remove features settings
	#$step4bSuccess = $true
	#try {
	#	# Uninstall the OpenSSH Server
	#	Remove-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

	#	#Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Client' } | Remove-WindowsCapability -Online
	#} catch {
	#	$step4bSuccess = $false
	#}
	#Write-Host "OpenSSH is not installed."
	#$undoStepsStatus += [PSCustomObject]@{Step = "Remove OpenSSH Server"; Success = $step4bSuccess}

	# Step 5: Remove the registry key for LocalAccountTokenFilterPolicy
	$step5Success = $true
	try {
		if (Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system") {
        		$valueExists = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue
        		if ($null -ne $valueExists) {
            			Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -Force
        		}
    		}
	} catch {
        	$step5Success = $false
	}
	# Add the status to the undoStepsStatus list for the "Remove Registry" step
	$undoStepsStatus += [PSCustomObject]@{Step = "Remove Registry"; Success = $step5Success}

	# STEP 6 Set EnableLUA to 1 to enable UAC
	$step6Success = $true
	try {
		Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 1
	} catch {
		$step6Success = $false
	}
	#ConfirmStepSuccess "Enable UAC" $step6Success
	# Add the status to the undoStepsStatus list for the "Remove Registry" step
	$undoStepsStatus += [PSCustomObject]@{Step = "Enable UAC"; Success = $step6Success}
	
	# Display status of each undo step
        Write-Host
	Write-Host "RESULT"
	Write-Host "============================================"
	$undoStepsStatus | ForEach-Object { ConfirmStepSuccess $_.Step $_.Success }
	Write-Host "============================================"
}

Write-Host
Write-Host "Press any key to continue..."
