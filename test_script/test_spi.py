from operator import truediv
import time
import serial
import re
import random
from os import path
import std_func as sf

########################################## Define ############################################
spi_dev = ["0", "1"]
chip_sel = ["0", "1"]
spi_mode = ["0", "1", "2", "3"]
bit_len = "16"
device_id_addr = "8000"

GPIO_PIN_MOSI = 23
GPIO_PIN_MISO = 24
pinctrl_IP_base = 0x150d0000
pinctrl_doen_base = 0x00
pinctrl_dout_base = 0x40
spi_mo_dout_id = 95
spi_mo_doen_id = 43
gpi_spi_mi_addr = 0x150d00b8

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_loopback = -11
Err_read_device_id = -12
Err_read_and_write = -13
Err_read_register = -14
Err_write_register = -15

###################################### Global Variable #######################################
SPI_001_LOOPBACK_result = 0
SPI_002_RWR_result = 0

s = None
sl = None
res_msg = ""

##################################### Standard Function ######################################
def Open_COMPORT(COM_PORT = 'COM4'):
  global s
  global sl

  s = serial.Serial(COM_PORT)
  if not s.isOpen():
    sl.log(COM_PORT + " port Fail to open", 'INFO')
    exit()
  sl.log(COM_PORT + " Open success", 'INFO')
  s.baudrate = 115200
  s.parity=serial.PARITY_NONE
  s.stopbits=serial.STOPBITS_TWO
  s.bytesize=serial.EIGHTBITS
  s.flush()
  s.write_timeout = 3
  s.timeout = 10

def Close_COMPORT():
  global s
  s.close()

def send_command(com_string):
  global s
  s.write(com_string.encode("utf-8"))
  s.write('\n'.encode("utf-8"))

def scan_expected_resp(cmd_send, reps_string, timeout_period):
  global s
  global sl

  s.reset_input_buffer()
  s.timeout = timeout_period

  send_command(cmd_send)

  while True:
    line = s.readline()
    sl.log(line, 'DEBUG')
    if len(line) == 0:
      sl.log(reps_string + " not found", 'INFO')
      return

    match = re.search(reps_string, line.decode('utf-8'))
    if match:
      sl.log(reps_string + " found", 'INFO')
      return line.decode('utf-8')

def detect_CMD_startup():
  global res_msg

  time_wait = 5
  if scan_expected_resp(" ", "StarFive #", time_wait): 
    return 0
  else:
    res_msg = "Err: Uboot is not ready for receiving command"
    return Err_CMD_startup

##############################################################################################
def from_hex(hexdigits):
    return int(hexdigits, 16)

def read_register(reg_addr):
    global res_msg

    cmd_send = "md.l " + reg_addr + " 1"
    resp_string = reg_addr[2:10] + ": .{8} "
    time_wait = 1

    line = scan_expected_resp(cmd_send, resp_string, time_wait)
    if line == None:
        sl.log("Error: Failed to read register with address, " + reg_addr + "\n", 'INFO')
        res_msg = "Err: Failed to read register"
        return Err_read_register

    reg_val = line[10:18]
    if reg_val.isalnum:
        return reg_val
    else:
        print("Error: Failed to read register with address, " + reg_addr + "\n", 'INFO')
        return Err_read_register

def write_register(reg_addr, reg_val_write):
    cmd_send = "mw.l " + reg_addr + " " + reg_val_write
    send_command(cmd_send)

    reg_val_read = read_register(reg_addr)
    if isinstance(reg_val_read, (int)):
        return reg_val_read

def set_spi_pinctrl(mosi_pin, miso_pin):
    ret = set_pinctrl_en_out(mosi_pin, pinctrl_dout_base, spi_mo_dout_id)
    if isinstance(ret, (int)):
        if ret < 0:
            return ret 

    ret = set_pinctrl_en_out(mosi_pin, pinctrl_doen_base, spi_mo_doen_id)
    if isinstance(ret, (int)):
        if ret < 0:
            return ret
        
    ret = set_pinctrl_en_out(miso_pin, pinctrl_doen_base, 1)
    if isinstance(ret, (int)):
        if ret < 0:
            return ret

    ret = set_pinctrl_din(gpi_spi_mi_addr, miso_pin+2)
    if isinstance(ret, (int)):
        if ret < 0:
            return ret
            
    ret = set_pinctrl_en_out(miso_pin, pinctrl_dout_base, 0)
    if isinstance(ret, (int)):
        if ret < 0:
            return ret

    return 0

def set_pinctrl_en_out(pin, func_offset, val):
    pin_reg_addr = pinctrl_IP_base + func_offset + (pin & 0xfffffffc)
    pin_reg_addr = hex(pin_reg_addr)
    pin_reg_off = pin & (0x03)

    tmp = read_register(pin_reg_addr)
    if isinstance(tmp, (int)):
        return tmp

    shift = 8 * pin_reg_off
    mask = 0xff << shift
    tmp = from_hex(tmp) & ~mask
    tmp |= (val << shift) & mask
    val = hex(tmp)

    return write_register(pin_reg_addr, val[2:])

def set_pinctrl_din(pin_reg_addr, val):
    pin_reg_addr = pin_reg_addr & 0xfffffffc
    pin_reg_off = pin_reg_addr & (0x03)
    pin_reg_addr = hex(pin_reg_addr)

    tmp = read_register(pin_reg_addr)
    if isinstance(tmp, (int)):
        return tmp

    shift = 8 * pin_reg_off
    mask = 0xff << shift
    tmp = from_hex(tmp) & ~mask
    tmp |= (val << shift) & mask
    val = hex(tmp)
    
    return write_register(pin_reg_addr, val[2:])
    
def SPI_001_LOOPBACK():
    global s
    global sl
    global res_msg
    count = 0

    ret = detect_CMD_startup()
    if ret != 0:
        return ret

    sl.log("\n*************** SPI LOOPBACK TEST ***************", 'INFO')
    sl.log("========== Set SPI Pinctrl ==========\n", 'INFO')
    ret = set_spi_pinctrl(GPIO_PIN_MOSI, GPIO_PIN_MISO)
    if ret < 0:
        return ret

    sl.log("========== SPI Loopback Test ==========", 'INFO') 
    for x in range(len(spi_mode)):
        for y in range(len(chip_sel)):
            count += 1
            sl.log("SPI loopback #" + str(count), 'INFO')
            hex_val = "FFFF"

            while hex_val == "0000" or hex_val == "FFFF":
                hex_val = [random.choice('0123456789ABCDEF') for z in range(4)]
                hex_val = "".join(hex_val)

            cmd_send = "sspi " + spi_dev[0] + ":" + str(y) + "." + str(x) + " " + bit_len + " " + hex_val
            resp_string = hex_val
            time_wait = 10

            line = scan_expected_resp(cmd_send, resp_string, time_wait)
            if line is None:
                res_msg = "Err: SPI loopback test fail"
                return Err_loopback
    
    res_msg = "PASSED: SPI_001_LOOPBACK test runs successfully"
    return 0

def SPI_002_RWR():
    global s
    global sl
    global res_msg

    ret = detect_CMD_startup()
    if ret != 0:
        return ret

    sl.log("\n*************** SPI READ AND WRITE TEST ***************", 'DEBUG')
    sl.log("========== ADXL345 Test: Read device ID ==========", 'DEBUG')    
    cmd_send = "sspi " + spi_dev[0] + ":" + chip_sel[0] + "." + spi_mode[3] + " " + bit_len + " " + device_id_addr
    send_command(cmd_send)
    send_command(cmd_send)      # sending the command twice to workaround first read issue
    time.sleep(1)

    device_id = "E5"     # ensure return value ends with E5

    while True:
        line = s.readline()
        if s.inWaiting():
            sl.log(line)
            match = re.search(device_id, line.decode('utf-8')) #line.decode('utf-8')
        else:
            break

    if match:
        sl.log("Device ID " + device_id + " found\n", 'INFO')
    else:
        sl.log("Device ID " + device_id + " not found", 'INFO')
        res_msg = "Err: Fail to read device ID #E5"
        return Err_read_device_id
    
    if line == None:
        sl.log("Device ID " + device_id + " not found.\n", 'INFO')
        res_msg = "Err: Fail to read device ID #E5"
        return Err_read_device_id

    sl.log("========== ADXL345 Test: Read and Write ==========", 'DEBUG') 
    for x in range(5):
        hex_val = "FF"

        while hex_val == "00" or hex_val == "FF":
            hex_val = [random.choice('0123456789ABCDEF') for z in range(2)]
            hex_val = "".join(hex_val)

        # write to address 0x1F
        cmd_send = "sspi " + spi_dev[0] + ":" + chip_sel[0] + "." + spi_mode[3] + " " + bit_len + " 1F" + hex_val
        send_command(cmd_send)

        # read 0x00 from address 0x9F
        cmd_send = "sspi " + spi_dev[0] + ":" + chip_sel[0] + "." + spi_mode[3] + " " + bit_len + " 9F00"
        send_command(cmd_send)

        while True:
            line = s.readline()
            if s.inWaiting():
                sl.log(line, 'DEBUG')
                match = re.search(hex_val, line.decode('utf-8')) #line.decode('utf-8')
            else:
                break

        if match:
            sl.log("Write value " + hex_val + " found\n", 'INFO')
        else:
            sl.log("Write value " + hex_val + " not found\n", 'INFO')
            res_msg = "Err: Failed to write and read with ADXL345"
            return Err_read_and_write

    res_msg = "PASSED: SPI_002_RWR test runs successfully"
    return 0

def run_test_loopback(COM, handling_path):
    global sl
    global res_msg

    sl = sf.test_log(handling_path, console=False)
    sl.log("IP = SPI", 'WARN')

    Open_COMPORT(COM)

    SPI_001_LOOPBACK_result = SPI_001_LOOPBACK()
    sl.log("SPI_001_LOOPBACK " + str(SPI_001_LOOPBACK_result) + ' ' + res_msg, 'WARN')

    Close_COMPORT()
    sl.close()

def run_test_rwr(COM, handling_path):
    global sl
    global res_msg

    sl = sf.test_log(handling_path, console=False)

    Open_COMPORT(COM)

    SPI_002_RWR_result = SPI_002_RWR()
    sl.log("SPI_002_RWR " + str(SPI_002_RWR_result) + ' ' + res_msg, 'WARN')

    Close_COMPORT()
    sl.close()

def main():
    current_path = path.dirname( path.abspath(__file__) )

    run_test_loopback('COM4', current_path)
    run_test_rwr('COM4', current_path)

    return 0

if __name__ == "__main__":
    main()
