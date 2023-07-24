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

	# STEP 1 Check if PsTools were installed
	if (Test-Path "C:\PsTools") {
		# Step 1: Remove PsTools
		$step1Success = $true
		try {
			Remove-Item "C:\PsTools" -Force -Recurse

			# Remove the PSTools directory from the system's PATH environment variable
			$pathEnv = [System.Environment]::GetEnvironmentVariable('PATH', [System.EnvironmentVariableTarget]::Machine)
			$newPath = $pathEnv -replace [regex]::Escape(";C:\PsTools"), ""
			[System.Environment]::SetEnvironmentVariable('PATH', $newPath, [System.EnvironmentVariableTarget]::Machine)
		} catch {
			$step1Success = $false
		}
		#ConfirmStepSuccess "Remove PsTools" $step1Success
	} else {
		Write-Host "PsTools were not installed."
		$undoStepsStatus += [PSCustomObject]@{Step = "Remove PsTools"; Success = $true}
	}

	# Check if port 22 is open for SSH
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
		$undoStepsStatus += [PSCustomObject]@{Step = "Close Port 22"; Success = $true}
	}
	
	# Check if SSH services are running and set to manual startup
	$sshServiceStatus = Get-Service -Name sshd -ErrorAction SilentlyContinue

	# STEP 3 Stop and set sshd service to manual startup
	$step3SshdSuccess = $true
	if ($sshServiceStatus -ne $null -and $sshServiceStatus.ServiceName -contains 'sshd') {
		try {
			Stop-Service sshd
			Start-Sleep -Seconds 2
			Set-Service -Name sshd -StartupType Manual
		} catch {
			$step3SshdSuccess = $false
		}
		#ConfirmStepSuccess "Stop and Set sshd to Manual Startup" $step3SshdSuccess
	} else {
		Write-Host "sshd service is already stopped."
		$undoStepsStatus += [PSCustomObject]@{Step = "Stop and Set sshd to Manual Startup"; Success = $true}
	}

    # STEP 4 Check if OpenSSH is installed and remove it
	if (Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Client*' }) {
		# Step 4: Remove OpenSSH via remove features settings
		$step4Success = $true
		try {
			# Uninstall OpenSSH.Server feature
			Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Client*' } | Remove-WindowsCapability -Online
		} catch {
			$step4Success = $false
		}
		#ConfirmStepSuccess "Remove OpenSSH" $step4Success
	} else {
		Write-Host "OpenSSH is not installed."
		$undoStepsStatus += [PSCustomObject]@{Step = "Remove OpenSSH"; Success = $true}
	}

	# Step 5 Remove the registry key for LocalAccountTokenFilterPolicy
	$step5Success = $true
	try {
		Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -Force -ErrorAction Stop
	} catch {
		$step5Success = $false
	}
	#ConfirmStepSuccess "Remove Registry" $step7Success
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
	$undoStepsStatus | ForEach-Object { ConfirmStepSuccess $_.Step $_.Success }
}

Write-Host
Write-Host "Press any key to exit..."
