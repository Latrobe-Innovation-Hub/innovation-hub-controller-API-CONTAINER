
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

Write-Host "Status of Changes:"
Write-Host "==================="

# Check if OpenSSH is installed
$openSshInstalled = Test-Path "$env:ProgramFiles\OpenSSH\OpenSSH-Win64\ssh.exe"

if ($openSshInstalled) {
    ShowStatus "Is OpenSSH installed?" $true

    # Check if sshd service is running
    $sshdStatus = Get-Service -Name sshd -ErrorAction SilentlyContinue
    $sshdRunning = ($sshdStatus -ne $null) -and ($sshdStatus.Status -eq 'Running')
    ShowStatus "Is sshd running?" $sshdRunning

    # Check if sshd is set to auto start at boot
    $sshdStartupType = (Get-Service -Name sshd -ErrorAction SilentlyContinue).StartType
    $sshdAutoStart = ($sshdStartupType -eq 'Automatic')
    ShowStatus "Is sshd set to auto start at boot?" $sshdAutoStart

    # Check if ssh-agent service is running
    $sshagentStatus = Get-Service -Name ssh-agent -ErrorAction SilentlyContinue
    $sshAgentRunning = ($sshagentStatus -ne $null) -and ($sshagentStatus.Status -eq 'Running')
    ShowStatus "Is ssh-agent running?" $sshAgentRunning

    # Check if ssh-agent is set to auto start at boot
    $sshagentStartupType = (Get-Service -Name ssh-agent -ErrorAction SilentlyContinue).StartType
    $sshagentAutoStart = ($sshagentStartupType -eq 'Automatic')
    ShowStatus "Is ssh-agent set to auto start at boot?" $sshagentAutoStart
} else {
    ShowStatus "Is OpenSSH installed?" $false
}

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

# Ask the user to press any key to exit
Write-Host
Write-Host "Press any key to continue..."
