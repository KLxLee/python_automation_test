REM kill python.exe before start
tasklist | findstr python.exe && taskkill /t /F /im python.exe

REM start notification
SCHTASKS /CREATE /TN "AUTOMATION_NOTIFICATION" /SC ONCE /st 00:00 /TR "C:\jenkins\automation\notification.py"
SCHTASKS /RUN /TN "AUTOMATION_NOTIFICATION"
SCHTASKS /DELETE /TN "AUTOMATION_NOTIFICATION" /F

@REM ping 127.0.0.1 -n 300 > nul
ping 127.0.0.1 -n 300 > nul

call getCmdPID
set "current_pid=%errorlevel%"

for /f "skip=3 tokens=2 delims= " %%a in ('tasklist /fi "imagename eq cmd.exe"') do (
    if "%%a" neq "%current_pid%" (
        TASKKILL /PID %%a /f >nul 2>nul
    )
)

set automationtasklist=riscv64-unknown-elf-gdb.exe putty.exe ttermpro.exe FreedomStudio.exe openocd.exe
for %%L in (%automationtasklist%) do (
    echo %%L
    tasklist | findstr %%L && taskkill /t /F /im %%L
)

exit 0
