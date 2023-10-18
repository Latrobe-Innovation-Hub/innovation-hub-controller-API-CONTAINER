
function ShowStatus {
    param([string]$description, [bool]$status)
    $statusOutput = if ($status) { "Yes" } else { "No" }
    Write-Host ("{0,-80} {1}" -f $description, $statusOutput)
}

#function ShowStatus {
#    param([string]$stepName, [bool]$changeMade, [object]$actualValue)
#    $status = if ($changeMade) { "[ Yes ]" } else { "[ No  ]" }
#    Write-Host ("Step {0,-30} {1} (Actual Value: {2})" -f $stepName, $status, $actualValue)
#}

Write-Host
Write-Host "Status of Changes:"
Write-Host "============================================"

# Check if sshd service is running
$sshdStatus = Get-Service -Name sshd -ErrorAction SilentlyContinue
$sshdRunning = ($sshdStatus -ne $null) -and ($sshdStatus.Status -eq 'Running')

# Check if sshd is set to auto start at boot
$sshdStartupType = (Get-Service -Name sshd -ErrorAction SilentlyContinue).StartType
$sshdAutoStart = ($sshdStartupType -eq 'Automatic')

# Check if ssh-agent service is running
$sshagentStatus = Get-Service -Name ssh-agent -ErrorAction SilentlyContinue
$sshAgentRunning = ($sshagentStatus -ne $null) -and ($sshagentStatus.Status -eq 'Running')

# Check if ssh-agent is set to auto start at boot
$sshagentStartupType = (Get-Service -Name ssh-agent -ErrorAction SilentlyContinue).StartType
$sshagentAutoStart = ($sshagentStartupType -eq 'Automatic')

# Set $openSshInstalled to true if all conditions are met
$openSshInstalled = $sshdRunning -and $sshdAutoStart -and $sshAgentRunning -and $sshagentAutoStart

# Wait for commands to run
#Start-Sleep -Seconds 2

# check all services to confirm if openssh is installed
ShowStatus "Is OpenSSH installed?" $openSshInstalled

# show openssh service state messages
ShowStatus "Is sshd running?" $sshdRunning
ShowStatus "Is sshd set to auto start at boot?" $sshdAutoStart
ShowStatus "Is ssh-agent running?" $sshAgentRunning
ShowStatus "Is ssh-agent set to auto start at boot?" $sshagentAutoStart

$port22Rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue

if ($port22Rule -eq $null) {
    ShowStatus "Firewall Rule 'OpenSSH-Server-In-TCP' exists" $false
} else {
    ShowStatus "Firewall Rule 'OpenSSH-Server-In-TCP' exists and is enabled" $port22Rule.Enabled
}

# Check if LocalAccountTokenFilterPolicy is created and set to 1
$localAccountTokenFilterPolicyValue = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system" -Name "LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue
$localAccountTokenFilterPolicyExists = if ($localAccountTokenFilterPolicyValue) {
    $localAccountTokenFilterPolicyValue.LocalAccountTokenFilterPolicy -eq 1
} else {
    $false
}
ShowStatus "Has LocalAccountTokenFilterPolicy been created and set to 1?" $localAccountTokenFilterPolicyExists

# Check if UAC is disabled
$enableLUAValue = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -ErrorAction SilentlyContinue
$enableLUAExists = if ($enableLUAValue) {
    $enableLUAValue.EnableLUA -eq 0
} else {
    $false
}
ShowStatus "Is UAC disabled?" $enableLUAExists

# Check if c:\PsTools exists and has files inside it
$psToolsInC = Test-Path "C:\PsTools" -PathType Container
ShowStatus "Does c:\PsTools exist and have files inside it?" $psToolsInC

# Check if c:\PsTools is in PATH
$psToolsInPath = $false
$envPathEntries = $env:Path -split ';'

foreach ($entry in $envPathEntries) {
    if ($entry -eq "C:\PsTools") {
        $psToolsInPath = $true
        break
    }
}

ShowStatus "Is c:\PsTools in PATH?" $psToolsInPath

# Check the status of Auto-Login -test?
$autoLoginStatus = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'AutoAdminLogon' -ErrorAction SilentlyContinue).AutoAdminLogon -eq "1"
ShowStatus "Is Auto-Login enabled?" $autoLoginStatus

# Step 8: Check if NirCmd is installed
$nircmdInstalled = (Test-Path "C:\NirCmd\nircmd.exe" -PathType Leaf)
ShowStatus "Is NirCmd installed?" $nircmdInstalled

# Check if Windows 10 display sleep settings are set to "Never" when plugged in - testing
$displaySleepSettings = Get-ItemProperty -Path "HKCU:\Control Panel\PowerCfg" -Name "ACSettingIndex" -ErrorAction SilentlyContinue
$displayNeverSleep = ($displaySleepSettings.ACSettingIndex -eq 0)

# Display the status using ShowStatus
ShowStatus "Is display sleep set to 'Never' when plugged in?" $displayNeverSleep

# Check if Windows 10 standby timeout settings are set to "Never" when on AC power - testing
$standbyTimeoutSettings = Get-ItemProperty -Path "HKCU:\Control Panel\PowerCfg" -Name "ACSettingIndex" -ErrorAction SilentlyContinue
$standbyNeverSleep = ($standbyTimeoutSettings.ACSettingIndex -eq 0)

# Display the status using ShowStatus
ShowStatus "Is standby timeout set to 'Never' when on AC power?" $standbyNeverSleep

# Step 9: Check if standby is set to 'Never'
$standbyNeverSet = ($standbyTimeoutSettings.ACSettingIndex -eq 0)
ShowStatus "Is standby timeout set to 'Never' when on AC power?" $standbyNeverSet

# Step 10: Check if Google Chrome is installed
$chromeInstalled = Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe" -PathType Leaf
ShowStatus "Is Google Chrome installed?" $chromeInstalled

# Step 11: Check if Python is installed and added to PATH
$pythonInstalled = Test-Path "C:\Users\$Username\AppData\Local\Programs\Python\Python37\python.exe" -PathType Leaf
$pythonInPath = $existingPath -like "*C:\Users\$Username\AppData\Local\Programs\Python\Python37*"
$scriptsInPath = $existingPath -like "*C:\Users\$Username\AppData\Local\Programs\Python\Python37\Scripts*"
ShowStatus "Is Python 3.7 installed?" $pythonInstalled
ShowStatus "Is Python 3.7 in PATH?" $pythonInPath
ShowStatus "Are Python Scripts in PATH?" $scriptsInPath

# Step 12: Check if Selenium is installed
$seleniumInstalled = (Test-Path "$pythonDirectory\Scripts\selenium.exe" -PathType Leaf)
ShowStatus "Is Selenium installed?" $seleniumInstalled

# Step 13: Check if 'browser-youtube.py' is in the user's Documents folder
$browserScriptInDocuments = Test-Path "C:\Users\$Username\Documents\browser-youtube.py" -PathType Leaf
ShowStatus "Is 'browser-youtube.py' in the user's Documents folder?" $browserScriptInDocuments

# Ask the user to press any key to exit
Write-Host
Write-Host "Press any key to continue..."
