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

	# Check if PsTools were installed
	if (Test-Path "C:\PSTools") {
		# Step 1: Remove PsTools
		$step1Success = $true
		try {
			Remove-Item "C:\PSTools" -Force -Recurse

			# Remove the PSTools directory from the system's PATH environment variable
			$pathEnv = [System.Environment]::GetEnvironmentVariable('PATH', [System.EnvironmentVariableTarget]::Machine)
			$newPath = $pathEnv -replace [regex]::Escape(";C:\PSTools"), ""
			[System.Environment]::SetEnvironmentVariable('PATH', $newPath, [System.EnvironmentVariableTarget]::Machine)
		} catch {
			$step1Success = $false
		}
		ConfirmStepSuccess "Remove PsTools" $step1Success
	} else {
		Write-Host "PsTools were not installed."
		$undoStepsStatus += [PSCustomObject]@{Step = "Remove PsTools"; Success = $true}
	}


	# Check if port 22 is open for SSH
	$port22Rule = Get-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue
	if ($port22Rule -ne $null) {
		# Step 2: Close port 22 for SSH via firewall
		$step2Success = $true
		try {
			Remove-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue
		} catch {
			$step2Success = $false
		}
		ConfirmStepSuccess "Close Port 22" $step2Success
	} else {
		Write-Host "Port 22 is already closed for SSH."
		$undoStepsStatus += [PSCustomObject]@{Step = "Close Port 22"; Success = $true}
	}

	# Check if SSH services are running
	$sshServiceStatus = Get-Service -Name ssh-agent, sshd -ErrorAction SilentlyContinue
	if ($sshServiceStatus -ne $null -and $sshServiceStatus.Status -contains 'Running') {
		# Step 3: Stop authentication and SSH services via services
		$step3Success = $true
		try {
			Stop-Service sshd
			Set-Service -Name sshd -StartupType Manual
		} catch {
			$step3Success = $false
		}
		ConfirmStepSuccess "Stop SSH Services" $step3Success
	} else {
		Write-Host "SSH services are already stopped."
		$undoStepsStatus += [PSCustomObject]@{Step = "Stop SSH Services"; Success = $true}
	}

	# Check if OpenSSH is installed
	if (Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Server*' }) {
		# Step 4: Remove OpenSSH via remove features settings
		$step4Success = $true
		try {
			Remove-WindowsCapability -Online -Name OpenSSH.Server
		} catch {
			$step4Success = $false
		}
		ConfirmStepSuccess "Remove OpenSSH" $step4Success
	} else {
		Write-Host "OpenSSH is not installed."
		$undoStepsStatus += [PSCustomObject]@{Step = "Remove OpenSSH"; Success = $true}
	}

	# Check if registry key exists for LocalAccountTokenFilterPolicy
	if (Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system\LocalAccountTokenFilterPolicy") {
		# Step 5: Remove the registry key for LocalAccountTokenFilterPolicy
		$step5Success = $true
		try {
			Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -Force
		} catch {
			$step5Success = $false
		}
		ConfirmStepSuccess "Remove Registry" $step5Success
	} else {
		Write-Host "Registry key for LocalAccountTokenFilterPolicy does not exist."
		$undoStepsStatus += [PSCustomObject]@{Step = "Remove Registry"; Success = $true}
	}

	# Check if registry key exists for EnableLUA
	if (Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\EnableLUA") {
		# Step 6: Re-enable UAC by setting EnableLUA to 1
		$step6Success = $true
		try {
			New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 1 -PropertyType DWord -Force
		} catch {
			$step6Success = $false
		}
		ConfirmStepSuccess "Re-enable UAC" $step6Success
	} else {
		Write-Host "Registry key for EnableLUA does not exist."
		$undoStepsStatus += [PSCustomObject]@{Step = "Re-enable UAC"; Success = $true}
	}

	# Display status of each undo step
	$undoStepsStatus | ForEach-Object { ConfirmStepSuccess $_.Step $_.Success }

	# If all undo steps were successful, ask the user if they want to reboot
	# else ask them before exiting
	$allUndoStepsSuccessful = ($undoStepsStatus | ForEach-Object { $_.Success }) -contains $false -eq $false

	if ($allUndoStepsSuccessful) {
		# Ask the user if they want to reboot
		$messageBoxTitle = "Undo Script Completed Successfully"
		$messageBoxContent = "All undo steps were completed successfully. Do you want to reboot now?"
		$result = [System.Windows.MessageBox]::Show($messageBoxContent, $messageBoxTitle, [System.Windows.MessageBoxButton]::YesNo)

		if ($result -eq [System.Windows.MessageBoxResult]::Yes) {
			Write-Host "Rebooting..."
			Restart-Computer
		}
	} else {
		# Ask the user before exiting
		$messageBoxTitle = "Undo Script Encountered Errors"
		$messageBoxContent = "Some undo steps encountered errors. Do you want to exit now?"
		$result = [System.Windows.MessageBox]::Show($messageBoxContent, $messageBoxTitle, [System.Windows.MessageBoxButton]::OK)
	}
} else {
	# Ask the user to press any key to exit
	Write-Host "Press any key to exit..."
	Read-Host > $null
}