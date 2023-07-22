function ShowStatus {
    param([string]$stepName, [bool]$changeMade)
    $status = if ($changeMade) { "[ Yes ]" } else { "[ No  ]" }
    Write-Host ("Step {0,-30} {1}" -f $stepName, $status)
}

Write-Host "Status of Changes:"
Write-Host "==================="

# Check if OpenSSH is already installed
$openSshInstalled = Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Server*' }
ShowStatus "Install OpenSSH" ($openSshInstalled -ne $null)

# Check if SSH services are running
$sshServiceStatus = Get-Service -Name ssh-agent, sshd -ErrorAction SilentlyContinue
$sshServicesRunning = ($sshServiceStatus -ne $null) -and ($sshServiceStatus.Status -contains 'Running')
ShowStatus "Start SSH Services" $sshServicesRunning

# Check if port 22 is open for SSH
$port22Rule = Get-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue
$port22Open = $port22Rule -ne $null
ShowStatus "Open Port 22" $port22Open

# Check if registry key exists for LocalAccountTokenFilterPolicy
$localAccountTokenFilterPolicyExists = Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\system\LocalAccountTokenFilterPolicy"
ShowStatus "Modify Registry" $localAccountTokenFilterPolicyExists

# Check if registry key exists for EnableLUA
$enableLUAExists = Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\EnableLUA"
ShowStatus "Disable UAC" $enableLUAExists

# Check if PsTools are already present in C:\ directory
$psToolsInC = Test-Path "C:\PsTools"
ShowStatus "PsTools in C:\" $psToolsInC

# Check if PsTools directory is in the PATH environment variable
$psToolsInPath = [Environment]::GetEnvironmentVariable('PATH', [EnvironmentVariableTarget]::Machine) -like "*;C:\PsTools;*"
ShowStatus "PsTools in PATH" $psToolsInPath

# Ask the user to return to the main batch menu
Write-Host
Write-Host "Press any key to return to the main menu..."
Read-Host > $null
