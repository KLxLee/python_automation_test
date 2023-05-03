# xspi
import os
from os import path
import sys

#############################################   Import Test Scritp   #############################################
main_path = path.dirname( path.dirname( path.dirname( path.dirname( path.dirname( path.abspath(__file__) ) ) ) ) )
test_script_path = main_path + "\\test_script"
sys.path.append( test_script_path )
import std_func as sf
import test_xspi

##################################################################################################################
COMPORT_UNIT_1 = sf.get_comport_number(1)
COMPORT_UNIT_2 = sf.get_comport_number(2)

current_path = path.dirname( path.abspath(__file__) )
bitfile_path = path.dirname( current_path )
RTL_path = path.dirname( bitfile_path )

build_path = current_path + "\\build"
spl_build_path = current_path + "\\build_splboot"

load_time = '30'

bus_num = "1"
chip_sel = "0"

#############################################  Design Task Schedule  #############################################
def task1():
    sf.program_FPGA(build_path)
    sf.load_uboot(build_path, load_time)

    test_xspi.run_test(COMPORT_UNIT_2, current_path, bus_num, chip_sel)

    sf.load_uboot_endtask()

def task2():
    sf.program_FPGA(build_path)
    sf.load_uboot(build_path, load_time)
    
    test_xspi.xspi_load_uboot_img(COMPORT_UNIT_2, current_path, bus_num, chip_sel)

    sf.load_uboot_endtask()

def task3():
    sf.program_FPGA(spl_build_path)
    sf.load_uboot(spl_build_path, load_time) 

    test_xspi.spl_boot(COMPORT_UNIT_2, current_path)

    sf.load_uboot_endtask()

def main():

    sf.backup_old_log(current_path)
    task1()
    task2()
    task3()

if __name__ == "__main__":
    main()
