# timer
import os
from os import path
import sys

#############################################   Import Test Scritp   #############################################
main_path = path.dirname( path.dirname( path.dirname( path.dirname( path.dirname( path.abspath(__file__) ) ) ) ) )
test_script_path = main_path + "\\test_script"
sys.path.append( test_script_path )
import std_func as sf
import test_timer

##################################################################################################################
COMPORT_UNIT_1 = sf.get_comport_number(1)
COMPORT_UNIT_2 = sf.get_comport_number(2)

current_path = path.dirname( path.abspath(__file__) )
bitfile_path = path.dirname( current_path )
RTL_path = path.dirname( bitfile_path )

build_path_riscv = current_path + '\\build_riscv'
build_path_starfive = current_path + '\\build_starfive'

load_time = '70'

#############################################  Design Task Schedule  #############################################
def task1():
    sf.program_FPGA(build_path_riscv)
    sf.load_uboot(build_path_riscv, load_time)

    test_timer.run_test_RISCV_ticktimer(COMPORT_UNIT_2, current_path)
    
    sf.load_uboot_endtask()

def task2():
    sf.program_FPGA(build_path_starfive)
    sf.load_uboot(build_path_starfive, load_time)

    test_timer.run_test_STARFIVE_ticktimer(COMPORT_UNIT_2, current_path)
    
    sf.load_uboot_endtask()

def main():

    test_timer.StarFive_timer_base_addr = ["121c0000", "121d0000"]

    sf.backup_old_log(current_path)
    task1()
    task2()

if __name__ == "__main__":
    main()
