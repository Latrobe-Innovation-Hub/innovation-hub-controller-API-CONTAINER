# Windows Host Configuration Tool

The Windows Host Configuration Tool is a batch script designed to automate the process of configuring a Windows host system. It provides options to install and uninstall specific configurations and check the status of changes made to the system.

## How to Use

1. Clone or download the repository containing the configuration tool script to your local machine.

2. Run the `windows_host_config_tool.bat` script to interact with the Windows Host Configuration Tool.

3. Choose an option from the menu:

   - **Option 1**: Install Windows Host Configurations and API Controller settings.
     - Installs various configurations, such as OpenSSH, SSH Services, Port 22, Modify Registry, Disable UAC, PsTools Installation, and adds PsTools to the system PATH.

   - **Option 2**: Uninstall Windows Host Configurations and revert to default.
     - Reverts the Windows host back to its default state by undoing the changes made during installation.

   - **Option 3**: Check Status of Changes.
     - Displays the status of each configuration step, indicating whether it has been applied or not.

   - **Option 4**: Exit.
     - Exits the Windows Host Configuration Tool.

## Configurations

The Windows Host Configuration Tool facilitates the following configurations:

1. **OpenSSH Installation**: Installs the OpenSSH feature on the Windows host, allowing secure remote access via SSH.

2. **SSH Services**: Starts the SSH agent and SSH daemon services if they are not already running.

3. **Open Port 22**: Opens port 22 on the Windows Firewall to allow incoming SSH connections.

4. **Modify Registry**: Modifies specific registry settings required for certain configurations.

5. **Disable UAC (User Account Control)**: Disables the User Account Control feature, which helps prevent unwanted changes to the system.

6. **PsTools Installation**: Downloads and installs PsTools from Microsoft, a set of useful command-line utilities, into `C:\PsTools`.

7. **Add PsTools to System PATH**: Adds the `C:\PsTools` directory to the system's PATH environment variable for easy access to PsTools.

Please note that these scripts should be used with caution and only on Windows hosts where you understand the potential impact of the configurations.


# Dependencies

The Windows Host Configuration Tool relies on the following PowerShell scripts:

1. **install-host.ps1**: This PowerShell script contains the instructions to install the Windows host configurations and API Controller settings.

2. **uninstall-host.ps1**: This PowerShell script contains the instructions to uninstall the Windows host configurations and revert the host back to its default state.

3. **check-host.ps1**: This PowerShell script checks the status of the changes made to the Windows host without performing any installations or uninstallations.

These PowerShell scripts are essential components of the Windows Host Configuration Tool and should be kept in the same directory as the `windows_host_config_tool.bat` script for proper functionality.

Please ensure that you have PowerShell installed on your system and call the `windows_host_config_tool.bat` as Administrator

---
