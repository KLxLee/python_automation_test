call getCmdPID
set "current_pid=%errorlevel%"

for /f "skip=3 tokens=2 delims= " %%a in ('tasklist /fi "imagename eq cmd.exe"') do (
    if "%%a" neq "%current_pid%" (
        TASKKILL /PID %%a /f >nul 2>nul
    )
)

set automationtasklist=riscv64-unknown-elf-gdb.exe putty.exe ttermpro.exe FreedomStudio.exe openocd.exe python.exe
for %%L in (%automationtasklist%) do (
    echo %%L
    tasklist | findstr %%L && taskkill /t /F /im %%L
)

exit 0
