echo "start program by riscv gdb"

set riscv_gdb_path=%~1
set build_path=%~2

cd %build_path%

SET a=source
SET b=cmd.gdb
SET c="%a% %cd%\%b%"

start %riscv_gdb_path% -ex %c%
