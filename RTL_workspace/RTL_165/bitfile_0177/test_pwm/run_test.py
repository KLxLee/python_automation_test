# PWM
from os import path
import sys

#############################################   Import Test Scritp   #############################################
main_path = path.dirname( path.dirname( path.dirname( path.dirname( path.dirname( path.abspath(__file__) ) ) ) ) )
test_script_path = main_path + "\\test_script"
sys.path.append( test_script_path )
import std_func as sf
import test_pwm

##################################################################################################################
COMPORT_UNIT_1 = sf.get_comport_number(1)
COMPORT_UNIT_2 = sf.get_comport_number(2)

current_path = path.dirname( path.abspath(__file__) )
bitfile_path = path.dirname( current_path )
RTL_path = path.dirname( bitfile_path )

build_path = current_path + '\\build'

load_time = '70'

#############################################  Design Task Schedule  #############################################
def task1():
    sf.program_FPGA(build_path)
    sf.load_uboot(build_path, load_time)

    test_pwm.run_test(COMPORT_UNIT_2, current_path)
    
    sf.load_uboot_endtask()


def main():

    test_pwm.PWM_GPIO_PIN = 43     # RPI pin 35
    test_pwm.GPIO_INPUT_PIN = 44     # RPI pin 36
    test_pwm.GPIO_BANKNAME = "SYS_EAST_GPIO"
    test_pwm.GPIO_PINNUM = 48
    test_pwm.pwm_chn_out_id = 26
    test_pwm.pwm_chn_oen_id = 10
    test_pwm.pinctrl_IP_base = 0x122d0000
    test_pwm.pinctrl_doen_base = 0x00
    test_pwm.pinctrl_dout_base = 0x30

    sf.backup_old_log(current_path)
    task1()

if __name__ == "__main__":
    main()
