set load_time=%1
set gdb_path=%~2
set build_path=%~3
set batpath=%~dp0

taskkill /FI "WindowTitle eq AUTOMATION_UBOOT_OPENOCD*" /T /F
start "AUTOMATION_UBOOT_OPENOCD" /min cmd /k "%batpath%run_openocd.bat "%build_path%""

ping 127.0.0.1 -n %load_time% > nul

taskkill /FI "WindowTitle eq AUTOMATION_UBOOT_GDB*" /T /F
start "AUTOMATION_UBOOT_GDB" /min cmd /k "%batpath%run_gdb.bat "%gdb_path%" "%build_path%""

