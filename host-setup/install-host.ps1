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

===============================================================================

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
			Write-Host "Step $stepName encountered an error. Script execution cancelled."
		}
		$stepsStatus += [PSCustomObject]@{Step = $stepName; Success = $success}
	}

	# Array to store the status of each step
	$stepsStatus = @()

	# Check if OpenSSH is already installed
	if (!(Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Server*' })) {
		# Step 1: Install OpenSSH via add features settings
		$step1Success = $true
		try {
			Add-WindowsCapability -Online -Name OpenSSH.Server -IncludeAllSubFeature
		} catch {
			$step1Success = $false
		}
		ConfirmStepSuccess "Install OpenSSH" $step1Success
	} else {
		Write-Host "OpenSSH is already installed."
		$stepsStatus += [PSCustomObject]@{Step = "Install OpenSSH"; Success = $true}
	}

	# Check if SSH services are running
	$sshServiceStatus = Get-Service -Name ssh-agent, sshd -ErrorAction SilentlyContinue
	if ($sshServiceStatus -eq $null -or $sshServiceStatus.Status -contains 'Stopped') {
		# Step 2: Start authentication and SSH service via services
		$step2Success = $true
		try {
			Start-Service ssh-agent, sshd
		} catch {
			$step2Success = $false
		}
		ConfirmStepSuccess "Start SSH Services" $step2Success
	} else {
		Write-Host "SSH services are already running."
		$stepsStatus += [PSCustomObject]@{Step = "Start SSH Services"; Success = $true}
	}

	# Check if port 22 is open for SSH
	$port22Rule = Get-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue
	if ($port22Rule -eq $null) {
		# Step 3: Open port 22 for SSH via firewall
		$step3Success = $true
		try {
			New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
		} catch {
			$step3Success = $false
		}
		ConfirmStepSuccess "Open Port 22" $step3Success
	} else {
		Write-Host "Port 22 is already open for SSH."
		$stepsStatus += [PSCustomObject]@{Step = "Open Port 22"; Success = $true}
	}

	# Check if registry key exists for LocalAccountTokenFilterPolicy
	if (!(Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system\LocalAccountTokenFilterPolicy")) {
		# Step 4: Create a new registry key for LocalAccountTokenFilterPolicy
		$step4Success = $true
		try {
			New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -Value 1 -PropertyType DWord -Force
		} catch {
			$step4Success = $false
		}
		ConfirmStepSuccess "Modify Registry" $step4Success
	} else {
		Write-Host "Registry key for LocalAccountTokenFilterPolicy already exists."
		$stepsStatus += [PSCustomObject]@{Step = "Modify Registry"; Success = $true}
	}

	# Check if registry key exists for EnableLUA
	if (!(Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\EnableLUA")) {
		# Step 5: Disable UAC by setting EnableLUA to 0
		$step5Success = $true
		try {
			New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 0 -PropertyType DWord -Force
		} catch {
			$step5Success = $false
		}
		ConfirmStepSuccess "Disable UAC" $step5Success
	} else {
		Write-Host "Registry key for EnableLUA already exists."
		$stepsStatus += [PSCustomObject]@{Step = "Disable UAC"; Success = $true}
	}

	# Check if PsTools are already present
	if (!(Test-Path "C:\PSTools")) {
		# Step 6: Download and install PsTools from Microsoft
		$step6Success = $true
		try {
			$psToolsUrl = "https://download.sysinternals.com/files/PSTools.zip"
			
			# Set the download path to the local user's Downloads directory
			$downloadPath = [System.IO.Path]::Combine([Environment]::GetFolderPath('User'), 'Downloads\PSTools.zip')
			
			# Set the destination path for extraction
			$extractPath = "C:\PSTools"

			Invoke-WebRequest -Uri $psToolsUrl -OutFile $downloadPath
			Expand-Archive -Path $downloadPath -DestinationPath $extractPath

			# Add the PSTools directory to the system's PATH environment variable
			$pathEnv = [System.Environment]::GetEnvironmentVariable('PATH', [System.EnvironmentVariableTarget]::Machine)
			$newPath = "$pathEnv;$extractPath"
			[System.Environment]::SetEnvironmentVariable('PATH', $newPath, [System.EnvironmentVariableTarget]::Machine)
		} catch {
			$step6Success = $false
		}
		ConfirmStepSuccess "Download and Install PsTools" $step6Success
	} else {
		Write-Host "PsTools are already installed."
		$stepsStatus += [PSCustomObject]@{Step = "Download and Install PsTools"; Success = $true}
	}

	# Display status of each step
	$stepsStatus | ForEach-Object { ConfirmStepSuccess $_.Step $_.Success }

	# Check if all steps were successful
	$allStepsSuccessful = ($stepsStatus | ForEach-Object { $_.Success }) -contains $false -eq $false

	if ($allStepsSuccessful) {
		# Ask the user if they want to reboot
		$messageBoxTitle = "Script Completed Successfully"
		$messageBoxContent = "All steps were completed successfully. Do you want to reboot now?"
		$result = [System.Windows.MessageBox]::Show($messageBoxContent, $messageBoxTitle, [System.Windows.MessageBoxButton]::YesNo)

		if ($result -eq [System.Windows.MessageBoxResult]::Yes) {
			Write-Host "Rebooting..."
			Restart-Computer
		}
	} else {
		# Ask the user before exiting
		$messageBoxTitle = "Script Encountered Errors"
		$messageBoxContent = "Some steps encountered errors. Do you want to exit now?"
		$result = [System.Windows.MessageBox]::Show($messageBoxContent, $messageBoxTitle, [System.Windows.MessageBoxButton]::YesNo)

		if ($result -eq [System.Windows.MessageBoxResult]::Yes) {
			Write-Host "Exiting..."
		} else {
			# You may add additional code here to handle specific actions in case of errors.
			# For example, attempt to restart the script or perform recovery actions.
		}
	}
} else {
	# Ask the user to press any key to exit
	Write-Host "Press any key to exit..."
	Read-Host > $null
}