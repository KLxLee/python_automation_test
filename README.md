
# U-boot Automation Test

The project is used to do automation testing on FPGA to verify U-boot source code and RTL on different RTL version & bitfile.

The project is able to power on/off, load file, perform testing task, clean up task, logging for multiple test cases, bitfiles.

Testing concept is using COMPORT(UART) on the host PC to send U-boot command to target FPGA and verify the functionality based on the respond returned.
## Framework Introduction

**/RTL_workspace/**  contain all projects. Normally each project can test 1 RTL version which contain various bitfile version of the RTL.

    /RTL_workspace/bitfile_xxx/  is the folder that contains the test case needed for the bitfile
    /RTL_workspace/bitfile_xxx/test_xxx/  is the folder that contains all the script, yaml setting, .cfg file, cmd.gdb, u-boot.itb and spl.bin file.  
    /RTL_workspace/RTL_demo/ is a fully run example.

**/test_script/**    contain python scripts for all test case.

    /test_script/bat/ contain contain all the batch scripts which makes scheduler task to program FPGA bitfile, load U-boot file, start the program, and clean up the scheduler task.

    /test_script/bat/openocd/ contain openocd program.

**/comport_config.txt** define the COMPORT number that connect to FPGA_unit1 and FPGA_unit2

**/auto_FPGA_path.txt** define the abosulte path to call API that program FPGA automatically.

**/riscv_gdb_path.txt** define the abosulte location of riscv64-unknown-elf-gdb.exe
## Installation

**Prerequisite**

    1. Host PC has 1-2 COMPORT connected to FPGA. 
    2. Host PC is able to control FPGA (power on/off, setting clocks, program FPGA bit file).
    3. Host PC riscv-gdb and openocd to load and run U-boot & Linux file.
    4. Python3 on the Host PC.
    5. External API to control FPGA automatically.

**Configuration**

Three configs are needed to be set:
    
    1. /comport_config.txt -- write FPGA COMPORT into the text file. 
        E.g. FPGA3_UNIT1 = COM4
             FPGA3_UNIT2 = COM12
    2. /auto_FPGA_path.txt -- write the abosulte path to call API that program FPGA automatically.
        E.g. C:/jenkins/automation
    3. /riscv_gdb_path.txt -- abosulte location of riscv64-unknown-elf-gdb.exe.
        E.g. C:\Users\MDC_FPGA_3\Documents\jjho\Freedom_SDK_2021_04\SiFive\riscv64-unknown-elf-toolchain-10.2.0-2020.12.8\bin\riscv64-unknown-elf-gdb.exe
## Create project

**RTL project**

    1. Create an empty project folder in RTL_workspace. Example name is RTL_083 & RTL_102. Because project is suggested to contain all the test case of the RTL version.
    2. Copy 'bitfile_to_run.yml' and 'run_bitfile_test.py' into the project folder from template. 

**Bitfile project**

    1. Create empty folder in project folder. Example name is bitfile_0063, bitfile_0068. The bitile folder will handle all the test case to verify the bitfile.
    2. After created multiple bitfile folders, write the sequence to run testing of each bitfile in 'bitfile_to_run.yml'. If the bitfile folder name is not written, test cases of the bitfile will not be executed.
       E.g. bitfile:
                - bitfile_0063
                - bitfile_0068
                - bitfile_0093
                - bitfile_0094
    3. Copy 'test_case_to_run.yml' and 'run_test_case.py' into the bitifle folder from template.  

**Test Case project**

    1. Create empty folder in bitfile folder. Example name is test_xspi, test_sd, test_emmc or test_ethernet. Each test case folder will handle fully testing of one IP. 
    2. After created multiple test case folders, write the sequence to run each test case of in 'test_case_to_run.yml'. If the test cases folder name is not written, test cases of the IP will not be executed.
       E.g. test_case:
                - test_xspi
                - test_sd
                - test_emmc
                - test_ethernet
    3. In the test case folder create an 'run_test.py' script to execute actual testing action. Please refer to demo/example or scripts in folder /test_script/. 
    4. Create a build folder and put 'cmd.gdb' and 'test_config.yml' inside. Create an 'load_bin' folder and put 'jh8100.cfg', 'u-boot.itb' & 'u-boot-spl.bin' inside.
## Run Test Case

**Jenkins Hook**


**Manual Run**

    1. Run the scripts "/RTL_workspace/RTL_xxx/run_bitfile_test.py" can execute all the bitfile and all the IP test case under the RTL project.
    2. Run the scripts "/RTL_workspace/RTL_xxx/bitfile_xxx/run_test_case.py" can execute  all the IP test case under the RTL project.
    3. Run the scripts "/RTL_workspace/RTL_xxx/bitfile_xxx/test_xxx/run_case.py" can run particular IP test case.

## Logging

    1. In folder "/RTL_workspace/RTL_xxx/bitfile_xxx/test_xxx/log/", 'detail.txt' log all the detailed message of U-boot command sent and respond received. 'summary.txt' log only the test case ID, result (0 = success, -ve value = error) & short message.
    2. In folder "/RTL_workspace/RTL_xxx/bitfile_xxx/log/", 'result.txt' crawl all the 'summary.txt' of every test case in the bitfile.
    3. In folder "/RTL_workspace/RTL_xxx/log/", 'result.txt' crawl all the 'result.txt' of every bitfile log folder in the RTL project folder.
    4. At starting of the script, the log file will be moved inside "/log/lof_old/" folder from "/log/" folder. Hence, last test log still can be read and compared with current test log.