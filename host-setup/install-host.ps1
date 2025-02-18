# Save the current working directory
$originalWorkingDirectory = $args[0]

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

Function Enable-AutoHideTaskBar {
    #This will configure the Windows taskbar to auto-hide
    [cmdletbinding(SupportsShouldProcess)]
    [Alias("Hide-TaskBar")]
    [OutputType("None")]
    Param()

    Begin {
        Write-Verbose "[$((Get-Date).TimeofDay) BEGIN  ] Starting $($myinvocation.mycommand)"
        $RegPath = 'HKCU:SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3'
    } #begin
    Process {
        if (Test-Path $regpath) {
            Write-Verbose "[$((Get-Date).TimeofDay) PROCESS] Auto Hiding Windows 10 TaskBar"
            $RegValues = (Get-ItemProperty -Path $RegPath).Settings
            $RegValues[8] = 3

            Set-ItemProperty -Path $RegPath -Name Settings -Value $RegValues

            if ($PSCmdlet.ShouldProcess("Explorer", "Restart")) {
                #Kill the Explorer process to force the change
                Stop-Process -Name explorer -Force
            }
        }
        else {
            Write-Warning "Can't find registry location $regpath."
        }
    } #process
    End {
        Write-Verbose "[$((Get-Date).TimeofDay) END    ] Ending $($myinvocation.mycommand)"
    } #end
}

# Display the instruction comment
Write-Host $comment

# Display the CWD pass in bia batch script
Write-Host $originalWorkingDirectory

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
	
    # Step 1: Download and Install OpenSSH server
    $step1bSuccess = $true
    try {
        # Check if sshd service is running and stop it if it is
        $sshdService = Get-Service -Name sshd -ErrorAction SilentlyContinue
        if ($sshdService -ne $null -and $sshdService.Status -eq 'Running') {
            Stop-Service -Name sshd
        }

        # Check if ssh-agent service is running and stop it if it is
        $sshAgentService = Get-Service -Name ssh-agent -ErrorAction SilentlyContinue
        if ($sshAgentService -ne $null -and $sshAgentService.Status -eq 'Running') {
            Stop-Service -Name ssh-agent
        }

        # Fetch the latest release information from GitHub API
        Write-Host "Fetching the latest release information from GitHub API..."
        $repoApiUrl = "https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/latest"
        $latestRelease = Invoke-RestMethod -Uri $repoApiUrl
		
        # Extract the latest release version and use it to construct the download URLs
        $latestVersion = $latestRelease.tag_name
        Write-Host "Latest Version: $latestVersion"
        $openSSHServerUrl64 = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/$latestVersion/OpenSSH-Win64.zip"
        $openSSHServerUrl32 = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/$latestVersion/OpenSSH-Win32.zip"
		
        # Choose the correct URL based on system architecture and download
        Write-Host "Downloading the appropriate release based on system architecture..."
        $downloadPath = "$env:TEMP\OpenSSH.zip"
        if ([Environment]::Is64BitOperatingSystem) {
            Write-Host "Downloading from URL: $openSSHServerUrl64"
            Invoke-WebRequest -Uri $openSSHServerUrl64 -OutFile $downloadPath
        } else {
            Write-Host "Downloading from URL: $openSSHServerUrl32"
            Invoke-WebRequest -Uri $openSSHServerUrl32 -OutFile $downloadPath
        }
		
        # Extract downloaded files
        Write-Host "Extracting downloaded files..."
        $extractPath = "C:\Program Files\OpenSSH\"  # Change this path to the desired installation location
        Write-Host "Extraction Path: $extractPath"
        Expand-Archive -Path $downloadPath -DestinationPath $extractPath -Force
		
        # Set OpenSSH install path based on the system architecture
        Write-Host "Running OpenSSH install script..."
        if ([Environment]::Is64BitOperatingSystem) {
            Set-Location "$extractPath\OpenSSH-Win64"
        } else {
            Set-Location "$extractPath\OpenSSH-Win32"
        }

        # Run OpenSSH install script
        Write-Host "Installing openSSH..."
        .\install-sshd.ps1

        # Remove OpenSSH release archive
        Remove-Item -Path $downloadPath -Force
    } catch {
        $step1bSuccess = $false
    }
    ConfirmStepSuccess "Install OpenSSH Server" $step1bSuccess
    $stepsStatus += [PSCustomObject]@{Step = "Install OpenSSH Server"; Success = $step1bSuccess}

    # Step 2A: Set the sshd service to Automatic startup
    $step2aSuccess = $true
    try {
        Set-Service -Name sshd -StartupType 'Automatic'
    } catch {
        $step2aSuccess = $false
    }
    ConfirmStepSuccess "Set sshd service to Automatic startup" $step2aSuccess
    $stepsStatus += [PSCustomObject]@{Step = "Set sshd service to Automatic startup"; Success = $step2aSuccess}

    # Step 2B: Set the ssh-agent service to Automatic startup
    $step2bSuccess = $true
    try {
        Set-Service -Name ssh-agent -StartupType 'Automatic'
    } catch {
        $step2bSuccess = $false
    }
    ConfirmStepSuccess "Set the ssh-agent service to Automatic startup" $step2bSuccess
    $stepsStatus += [PSCustomObject]@{Step = "Set the ssh-agent service to Automatic startup"; Success = $step2bSuccess}

    # Step 3A: Start the sshd service
    $step3aSuccess = $true
    try {
        Start-Service sshd
    } catch {
        $step3aSuccess = $false
    }
    ConfirmStepSuccess "Start sshd service" $step3aSuccess
    $stepsStatus += [PSCustomObject]@{Step = "Start sshd service"; Success = $step3aSuccess}
	
    # Step 3B: Start the ssh-agent service
    $step3bSuccess = $true
    try {
        Start-Service ssh-agent
    } catch {
        $step3bSuccess = $false
    }
    ConfirmStepSuccess "Start sshd service" $step3bSuccess
    $stepsStatus += [PSCustomObject]@{Step = "Start ssh-agent service"; Success = $step3bSuccess}
	
    # Step 4: Confirm the Firewall rule is configured. It should be created automatically by setup. Run the following to verify
    if (!(Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue | Select-Object Name, Enabled)) {
        Write-Output "Firewall Rule 'OpenSSH-Server-In-TCP' does not exist, creating it..."
        try {
            New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
            $stepsStatus += [PSCustomObject]@{Step = "Firewall rule 'OpenSSH-Server-In-TCP' has been created and exists."; Success = $true}
        } catch {
            $stepsStatus += [PSCustomObject]@{Step = "Failed to create firewall rule 'OpenSSH-Server-In-TCP'."; Success = $false}
        }
    } else {
        Write-Output "Firewall rule 'OpenSSH-Server-In-TCP' has been created and exists."
        $stepsStatus += [PSCustomObject]@{Step = "Firewall rule 'OpenSSH-Server-In-TCP' has been created and exists."; Success = $true}
    }

    # Check if registry key exists for LocalAccountTokenFilterPolicy
    if (!(Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system\LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue)) {
        # Step 4: Create a new registry key for LocalAccountTokenFilterPolicy
        $step5Success = $true
        try {
            New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -Value 1 -PropertyType DWord -Force
        } catch {
            $step5Success = $false
        }
    #ConfirmStepSuccess "Modify Registry" $step5Success
    } else {
        $currentValue = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" | Select-Object -ExpandProperty LocalAccountTokenFilterPolicy
        if ($currentValue -ne 1) {
            Write-Host "Updating registry key for LocalAccountTokenFilterPolicy to the correct value (1)..."
            $step5Success = $true
            try {
                Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -Value 1 -Type DWord
            } catch {
                $step5Success = $false
            }
        #ConfirmStepSuccess "Modify Registry" $step5Success
        } else {
            Write-Host "Registry key for LocalAccountTokenFilterPolicy already exists and is set to the correct value (1)."
            $stepsStatus += [PSCustomObject]@{Step = "Modify Registry"; Success = $true}
        }
    }

    # Step 5: Check if registry key exists for EnableLUA
    if (!(Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\EnableLUA")) {
        # Step 5: Disable UAC by setting EnableLUA to 0
        $step6Success = $true
        try {
            New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 0 -PropertyType DWord -Force
        } catch {
            $step6Success = $false
        }
        ConfirmStepSuccess "Disable UAC" $step6Success
    } else {
        $currentValue = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" | Select-Object -ExpandProperty EnableLUA
        if ($currentValue -ne 0) {
            Write-Host "Updating registry key for EnableLUA to the correct value (0)..."
            $step6Success = $true
            try {
                Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 0 -Type DWord
            } catch {
                $step6Success = $false
            }
            ConfirmStepSuccess "Disable UAC" $step6Success
        } else {
            Write-Host "Registry key for EnableLUA already exists and is set to the correct value (0)."
            $stepsStatus += [PSCustomObject]@{Step = "Disable UAC"; Success = $true}
        }
    }
	
    # Step 6: Check if PsTools are already present
    if (!(Test-Path "C:\PSTools")) {
        # Step 6: Download and install PsTools from Microsoft
        $step7Success = $true
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
            $step7Success = $false
        }
        #ConfirmStepSuccess "Download and Install PsTools" $step7Success
    } elseif (!(Get-ChildItem -Path "C:\PSTools" -Force)) {
        # Step 6: Re-download and re-install PsTools since the directory exists but is empty
        $step7Success = $true
        try {
            $psToolsUrl = "https://download.sysinternals.com/files/PSTools.zip"
			
            # Set the download path to the local user's Downloads directory
            $downloadPath = [System.IO.Path]::Combine([Environment]::GetFolderPath('User'), 'Downloads\PSTools.zip')
			
            # Download the PSTools zip again
            Invoke-WebRequest -Uri $psToolsUrl -OutFile $downloadPath
			
            # Extract the new PSTools contents
            Expand-Archive -Path $downloadPath -DestinationPath "C:\PSTools" -Force

            # Add the PSTools directory to the system's PATH environment variable
            $pathEnv = [System.Environment]::GetEnvironmentVariable('PATH', [System.EnvironmentVariableTarget]::Machine)
            $newPath = "$pathEnv;C:\PSTools"
            [System.Environment]::SetEnvironmentVariable('PATH', $newPath, [System.EnvironmentVariableTarget]::Machine)
        } catch {
            $step7Success = $false
        }
        #ConfirmStepSuccess "Download and Install PsTools" $step7Success
    } else {
        #Write-Host "PsTools are already installed."
        $stepsStatus += [PSCustomObject]@{Step = "Download and Install PsTools"; Success = $true}
    }

    # Step 7: Set up Auto-Login
    $autoLoginSuccess = $true
    try {
        # Get the full domain-qualified username
        $FullUsername = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
	
        # Split the username to extract the part after the backslash (domain\username format)
        $UsernameParts = $FullUsername -split '\\'
        $AutoLoginUsername = $UsernameParts[1]
	
        # Prompt the user for their password
        $AutoLoginPassword = Read-Host "Enter your password for $AutoLoginUsername" -AsSecureString
	
        # Output to verify the username and password
        Write-Host "Username: $AutoLoginUsername"
        Write-Host "Password: $AutoLoginPassword"
	
        # Set the auto-login registry values
        function Set-AutoLogin {
            param(
                [string]$Username,
                [securestring]$Password
            )
	    
            $RegistryPath = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
            Set-ItemProperty $RegistryPath 'AutoAdminLogon' -Value "1" -Type String 
            Set-ItemProperty $RegistryPath 'DefaultUsername' -Value $Username -Type String 
	
            # Convert the secure string to a plain text password
            $PasswordPlainText = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))
	
            Set-ItemProperty $RegistryPath 'DefaultPassword' -Value $PasswordPlainText -Type String
        }
	
	Set-AutoLogin -Username $AutoLoginUsername -Password $AutoLoginPassword
    } catch {
	$autoLoginSuccess = $false
	Write-Host "Error setting Auto-Login registry values: $_"
    }
	
    ConfirmStepSuccess "Set up Auto-Login" $autoLoginSuccess
    $stepsStatus += [PSCustomObject]@{Step = "Set up Auto-Login"; Success = $autoLoginSuccess}
	
    # Output to verify the status of Auto-Login
    Write-Host "Auto-Login status: $autoLoginSuccess"

    # Step 8: Download and Install NirCmd
    $step8Success = $true
    try {
	# Define the download URL for NirCmd
	$nircmdUrl = "http://www.nirsoft.net/utils/nircmd-x64.zip"
	
	# Set the download path to a temporary directory
	$downloadPath = Join-Path $env:TEMP "nircmd.zip"
	
	# Set the destination path for extraction
	$extractPath = "C:\NirCmd"  # Change this path to the desired installation location
	
	# Download NirCmd
	Invoke-WebRequest -Uri $nircmdUrl -OutFile $downloadPath
	
	# Check if the destination directory exists, and create it if not
	if (-not (Test-Path -Path $extractPath -PathType Container)) {
	    New-Item -ItemType Directory -Path $extractPath
	}
	
	# Extract NirCmd to the destination path
	Expand-Archive -Path $downloadPath -DestinationPath $extractPath -Force
	
	# Check if the NirCmd directory is already in the system's PATH
	$existingPath = [System.Environment]::GetEnvironmentVariable('PATH', [System.EnvironmentVariableTarget]::Machine)

	if ($existingPath -notlike "*$extractPath*") {
	    # The directory is not in the PATH, so add it
	    $newPath = "$existingPath;$extractPath"
	    [System.Environment]::SetEnvironmentVariable('PATH', $newPath, [System.EnvironmentVariableTarget]::Machine)
	}
    } catch {
	$step8Success = $false
    }
    ConfirmStepSuccess "Download and Install NirCmd" $step8Success
    $stepsStatus += [PSCustomObject]@{Step = "Download and Install NirCmd"; Success = $step8Success}

    # Step 9: Set Windows Power, Sleep, Taskbar, and Desktop Settings - Need to test!
    $step9Success = $true
    try {
	# Set the screen turn off time to "Never" when plugged in
	powercfg -x -monitor-timeout-ac 0
	Write-Host "Windows power and sleep settings updated: Screen turns off after 'Never' when plugged in."
	
	# Set the computer to never enter sleep mode when on battery
	powercfg -x -standby-timeout-ac 0
	Write-Host "Windows power and sleep settings updated: Standby set to 'Never' when plugged in."
	
	# Set the taskbar to auto-hide - need to confirm works>?
	Enable-AutoHideTaskBar

	# Disable show icons on Desktop - need to confirm works>?
	$Path="HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
	Set-ItemProperty -Path $Path -Name "HideIcons" -Value 1
	Get-Process "explorer"| Stop-Process
	Write-Host "Windows desktop: Disabled show icons."
    } catch {
	$step9Success = $false
    }
    ConfirmStepSuccess "Set Windows Power, Sleep, and Taskbar Settings" $step9Success
    $stepsStatus += [PSCustomObject]@{Step = "Set Windows Power, Sleep, Taskbar, and Desktop Settings"; Success = $step9Success}

    # Step 9.5: Enable Windows Remote Desktop
    $step9_5Success = $true
    try {
	# Enable RDP for all users (0) and allow connections
	Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name "fDenyTSConnections" -Value 0
	Write-Host "RDP has been enabled."
    } catch {
	$step9_5Success = $false
    }
    ConfirmStepSuccess "Enable Windows Remote Desktop" $step9_5Success
    $stepsStatus += [PSCustomObject]@{Step = "Enable Windows Remote Desktop"; Success = $step9_5Success}

    # Step 9.6: Allow RDP through Windows Firewall
    $step9_6Success = $true
    try {
	# Enable the Windows Firewall rule for Remote Desktop
	Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
	Write-Host "Remote Desktop rule enabled in Windows Firewall."
    } catch {
	$step9_6Success = $false
    }
    ConfirmStepSuccess "Allow RDP through Windows Firewall" $step9_6Success
    $stepsStatus += [PSCustomObject]@{Step = "Allow RDP through Windows Firewall"; Success = $step9_6Success}

    # Enable "Do not show the lock screen" Group Policy setting
    $step9_7Success = $true

    try {
        # Define the Group Policy registry path
        $gpPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization"

        # Check if the registry key exists, and create it if it doesn't
        if (-not (Test-Path -Path $gpPath)) {
            New-Item -Path $gpPath -Force
        }

        # Set the "NoLockScreen" registry value to 1 to enable the setting
        Set-ItemProperty -Path $gpPath -Name "NoLockScreen" -Value 1

        Write-Host "Enabled 'Do not show the lock screen' setting."

    } catch {
        $step9_7Success = $false
    }

    # Confirm whether the step was successful
    ConfirmStepSuccess "Enable 'Do not show the lock screen' setting" $step9_7Success

    # Add the step's status to the stepsStatus array
    $step9_7Success += [PSCustomObject]@{Step = "Enable 'Do not show the lock screen' setting"; Success = $step9_7Success}

    # Step 10: Install Google Chrome
    $step10Success = $true
    try {
	# Define the URL for the Google Chrome offline installer
	$chromeInstallerUrl = "https://dl.google.com/tag/s/appguid%3D%7B8A69D345-D564-463C-AFF1-A69D9E530F96%7D%26iid%3D%7BCD63C8A9-CE05-2063-361D-1A77FFBBB7F2%7D%26lang%3Den%26browser%3D3%26usagestats%3D0%26appname%3DGoogle%2520Chrome%26needsadmin%3Dtrue%26ap%3Dx64-stable-statsdef_0_0_1%26installdataindex%3Ddefaultbrowser/chrome/install/ChromeStandaloneSetup64.exe"
		
	# Set the download path to a temporary directory
	$downloadPath = Join-Path $env:TEMP "ChromeStandaloneSetup64.exe"
		
	# Download the Chrome installer
	Invoke-WebRequest -Uri $chromeInstallerUrl -OutFile $downloadPath
		
	# Install Chrome silently
	Start-Process -FilePath $downloadPath -ArgumentList "/silent", "/install" -Wait
    } catch {
	$step10Success = $false
    }
    ConfirmStepSuccess "Install Google Chrome" $step10Success
    $stepsStatus += [PSCustomObject]@{Step = "Install Google Chrome"; Success = $step10Success}

    # Step 11: Install Python 3.7 and Add to PATH
    $step11Success = $true
    try {
	# Define the Python installer URL (adjust the URL to the desired version)
	$pythonInstallerUrl = "https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe"
		
	# Set the download path to a temporary directory
	$downloadPath = Join-Path $env:TEMP "PythonInstaller.exe"
		
	# Download the Python installer
	Invoke-WebRequest -Uri $pythonInstallerUrl -OutFile $downloadPath
		
	# Install Python and add to PATH using /quiet and PrependPath=1
	Start-Process -Wait -FilePath $downloadPath -ArgumentList "/quiet", "PrependPath=1"
    } catch {
	$step11Success = $false
    }

    ConfirmStepSuccess "Install Python 3.7" $step11Success
    $stepsStatus += [PSCustomObject]@{Step = "Install Python 3.7"; Success = $step11Success}
	
    if ($step11Success) {
	# Check if Python and Scripts directories are in the user's PATH
	# Get the full domain-qualified username
	$FullUsername = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

	# Split the username to extract the part after the backslash (domain\username format)
	$UsernameParts = $FullUsername -split '\\'
	$Username = $UsernameParts[1]

	$existingPath = [System.Environment]::GetEnvironmentVariable('PATH', [System.EnvironmentVariableTarget]::User)
	$pythonDirectory = "C:\Users\$Username\AppData\Local\Programs\Python\Python37"
	$scriptsDirectory = "C:\Users\$Username\AppData\Local\Programs\Python\Python37\Scripts"

	$pythonInPath = $existingPath -like "*$pythonDirectory*"
	$scriptsInPath = $existingPath -like "*$scriptsDirectory*"

	$step11aSuccess = $pythonInPath -and $scriptsInPath

	# Step 11a: Is Python 3.7 and Scripts added to PATH?
	ConfirmStepSuccess "Python 3.7 and Scripts directory added to PATH" $step11aSuccess
	$stepsStatus += [PSCustomObject]@{Step = "Python 3.7 and Scripts added to PATH"; Success = $step11aSuccess}
		
	# Step 11b: Install Selenium
	if ($step11aSuccess) {
	    # Define the full path to the Python interpreter
	    $pythonPath = "$pythonDirectory\python.exe"

	    # Define the package you want to install (e.g., Selenium)
	    $packageName = "selenium"

	    # Run pip to install the package using the full Python path
	    $pipProcessSelenium = Start-Process -Wait -FilePath $pythonPath -ArgumentList "-m", "pip", "install", $packageName -PassThru	
	    if ($pipProcessSelenium.ExitCode -eq 0) {
	        Write-Host "Selenium successfully installed."
	        $stepsStatus += [PSCustomObject]@{Step = "Selenium installation"; Success = $true}
	    } else {
	        Write-Host "Selenium installation failed with exit code $($pipProcess.ExitCode)."
	        $stepsStatus += [PSCustomObject]@{Step = "Selenium installation"; Success = $false}
	    }

            # Define the package you want to install (e.g., Selenium)
	    $packageName = "psutil"
     
	    # Run pip to install the package using the full Python path
	    $pipProcessPsutil = Start-Process -Wait -FilePath $pythonPath -ArgumentList "-m", "pip", "install", $packageName -PassThru	
	    if ($pipProcessPsutil.ExitCode -eq 0) {
	        Write-Host "psutil successfully installed."
	        $stepsStatus += [PSCustomObject]@{Step = "psutil installation"; Success = $true}
	    } else {
	        Write-Host "psutil installation failed with exit code $($pipProcess.ExitCode)."
	        $stepsStatus += [PSCustomObject]@{Step = "psutil installation"; Success = $false}
	    }
	}
    }
	
    # Restore the original working directory
    Set-Location $originalWorkingDirectory
	
    # Step 11: Install Python 3.7 and Add to PATH
    $step12Success = $true
    try {
	# Get the full domain-qualified username
	$FullUsername = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

	# Split the username to extract the part after the backslash (domain\username format)
	$UsernameParts = $FullUsername -split '\\'
	$Username = $UsernameParts[1]

	# Define the source file path (CWD in this case)
	$sourceFilePath = Join-Path ($originalWorkingDirectory) "browser-youtube.py"
		
	# Define the destination directory path (Documents directory)
	$destinationDirectory = "C:\Users\$Username\Documents"

	# Use Copy-Item to copy the file to the destination
	Copy-Item -Path $sourceFilePath -Destination $destinationDirectory
    } catch {
	$step12Success = $false
    }
    ConfirmStepSuccess "Moved browser-youtube.py to $destinationDirectory" $step12Success

    $stepsStatus += [PSCustomObject]@{Step = "Moved browser-youtube.py to destinationDirectory"; Success = $step12Success}

    # Display status of each step
    Write-Host
    Write-Host "RESULT"
    Write-Host "============================================"
    $stepsStatus | ForEach-Object { ConfirmStepSuccess $_.Step $_.Success }
    Write-Host "============================================"

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
}

# Ask the user to press any key to exit
Write-Host
Write-Host "Press any key to continue..."