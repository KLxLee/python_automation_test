from operator import truediv
import time
import serial
import re
import random

###################################### Define ######################################
spi_dev = "0"
chip_sel = ["0", "1"]
spi_mode = ["0", "1", "2", "3"]
bit_len = "16"
device_id_addr = "8000"
####################################################################################

################################### Error Code #####################################
Err_CMD_startup = -10
Err_loopback = -11
Err_read_device_id = -12
Err_read_and_write = -13
####################################################################################

########################################## Variable ################################
SPI_001_LOOPBACK_result = -8
SPI_003_RWR_result = -3

s = "COMPORT"
####################################################################################

def open_COMPORT():
    global s

    COM_PORT = 'COM1'
    s = serial.Serial(COM_PORT)
    if not s.isOpen():
        print("COM port Fail to open")
        exit()
    print("Open success")
    s.baudrate = 115200
    s.parity=serial.PARITY_NONE
    s.stopbits=serial.STOPBITS_TWO
    s.bytesize=serial.EIGHTBITS
    s.flush()
    s.write_timeout = 3
    s.timeout = 10

def close_COMPORT():
    global s
    s.close()

def send_command(com_string):
    global s

    s.reset_input_buffer()
    s.timeout = 2

    s.write(com_string.encode("utf-8"))
    s.write('\n'.encode("utf-8"))

def scan_expected_resp(cmd_send, reps_string, timeout_period):
    global s

    s.reset_input_buffer()
    s.timeout = timeout_period

    send_command(cmd_send)

    while True:
        line = s.readline()
        print(line)
        if len(line) == 0:
            print(reps_string + " not found.\n")
            return

        match = re.search(reps_string, line.decode('utf-8')) #line.decode('utf-8')

        if match:
            print(reps_string + " found\n")
            return line.decode('utf-8')

def detect_CMD_startup():
    time_wait = 10

    if scan_expected_resp("","StarFive #", time_wait): 
        print("Booting done \n")
        return 0
    else:
        print("Booting failed \n")
        return Err_CMD_startup

def summarize_test_id():
    global SPI_001_LOOPBACK_result
    global SPI_003_RWR_result

    if SPI_001_LOOPBACK_result != 0:
        print("SPI_001_LOOPBACK failed\n")
    else:
        print("SPI_001_LOOPBACK success\n")

    if SPI_003_RWR_result != 0:
        print("SPI_003_RWR failed\n")
    else:
        print("SPI_003_RWR success\n")

    if SPI_001_LOOPBACK_result == 0 and SPI_003_RWR_result == 0:
        print("All SPI testing are done\n")

def spi_loopback():
    global s
    global SPI_001_LOOPBACK_result

    for x in range(len(spi_mode)):
        for y in range(len(chip_sel)):
            x = str(x)
            y = str(y)
            hex_val = "FFFF"

            while hex_val == "0000" or hex_val == "FFFF":
                hex_val = [random.choice('0123456789ABCDEF') for z in range(4)]
                hex_val = "".join(hex_val)

            cmd_send = "sspi " + spi_dev + ":" + y + "." + x + " " + bit_len + " " + hex_val
            send_command(cmd_send)

            while True:
                line = s.readline()
                print(line)

                match = re.search(hex_val, line.decode('utf-8'))

                if match:
                    print(hex_val + " found\n")
                    SPI_001_LOOPBACK_result += 1
                    break

                if len(line) == 0:
                    print(hex_val + " not found.\n")
                    return Err_loopback
                
    return SPI_001_LOOPBACK_result
                
def spi_read_write():
    global s
    global SPI_003_RWR_result

    cmd_send = "sspi " + spi_dev + ":" + chip_sel[0] + "." + spi_mode[3] + " " + bit_len + " " + device_id_addr
    send_command(cmd_send)

    device_id = "E5$"     # ensure return value ends with E5

    while True:
        line = s.readline()
        print(line)

        match = re.search(device_id, line.decode('utf-8'))

        if match:
            print("Device ID " + device_id + " found\n")
            SPI_003_RWR_result += 1
            break

        if len(line) == 0:
            print(device_id + " not found.\n")
            return Err_read_device_id

    # write 0xA5 to address 0x1F
    cmd_send = "sspi " + spi_dev + ":" + chip_sel[0] + "." + spi_mode[3] + " " + bit_len + " 1FA5"
    send_command(cmd_send)
    SPI_003_RWR_result += 1

    # read 0x00 from address 0x9F
    cmd_send = "sspi " + spi_dev + ":" + chip_sel[0] + "." + spi_mode[3] + " " + bit_len + " 9F00"
    send_command(cmd_send)

    while True:
        line = s.readline()
        print(line)

        match = re.search("A5$", line.decode('utf-8'))

        if match:
            print("Write value A5 found\n")
            SPI_003_RWR_result += 1
            break

        if len(line) == 0:
            print("Write value A5 not found.\n")
            return Err_read_and_write
            
    return SPI_003_RWR_result

def main():
    global SPI_001_LOOPBACK_result
    global SPI_003_RWR_result

    # detect cmd input prompt
    SPI_001_LOOPBACK_result = detect_CMD_startup()
    if SPI_001_LOOPBACK_result < 0:
        summarize_test_id()
        return -1

    # SPI loopback test
    print("\n*************** SPI LOOPBACK TEST ***************")
    SPI_001_LOOPBACK_result = spi_loopback()
    if SPI_001_LOOPBACK_result < 0:
        summarize_test_id()
        return -1

    # SPI read/write test
    print("\n*************** SPI READ AND WRITE TEST ***************")
    SPI_003_RWR_result = spi_read_write()
    if SPI_003_RWR_result < 0:
        summarize_test_id()
        return -1

    summarize_test_id()

    return 0

if __name__ == "__main__":
    open_COMPORT()
    main()
    close_COMPORT()
