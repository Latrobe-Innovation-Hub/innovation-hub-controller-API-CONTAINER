=================================================================================

Uninstall Script Guide

Before running the uninstall.bat script, please follow these instructions:

Right-click on the uninstall.bat file.
Select "Run as Administrator" from the context menu. This will ensure the script has the necessary permissions to make changes to the system.
After running the script, it will proceed with the following steps:

Check if PsTools are installed and remove them if present.
Close Port 22, which was opened for SSH communication.
Stop SSH services.
Remove OpenSSH from the system.
Restore certain registry settings.
Re-enable User Account Control (UAC) if it was previously disabled.
Please be aware of the following:

The script will require administrative privileges to run successfully.
Some steps might encounter errors, and the script will attempt to handle them gracefully.
After running the uninstall.bat script, you may need to restart your computer for some changes to take effect.

If you encounter any issues or have concerns, please seek help from your IT department or a knowledgeable system administrator.

=================================================================================
