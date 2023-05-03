import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
Bus_ID = "0"
EEPROM_ID = "50"
Max_Bus_Speed = "400000"
Data_WR_1 = ["01", "02", "03" , "04", "05", "06", "07", "08"]
Data_WR_2 = ["09", "0a", "0b", "0c", "0d", "0e", "0f", "10"]
Addr_WR = "02"

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_show_current_bus = -11
Err_set_bus = -12
Err_show_current_bus_speed = -13
Err_set_bus_speed = -14
Err_probe = -15
Err_probe_EEPROM = -16
Err_read_EEPROM_Data_Set = -17
Err_cmp_RW_EEPROM_data_set = -18

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
I2C_001_result = Test_ID_Init_Val
I2C_001_result_msg = ''
I2C_002_result= Test_ID_Init_Val
I2C_002_result_msg = ''

s = None
sl = None
res_msg = ''

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
# i2c dev
# Current bus is 0
def show_current_bus():
  global res_msg

  cmd_send = "i2c dev"
  resp_string = "Current bus is "
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)

  if line == None:
    res_msg = "Err: Show current bus failed"
    return Err_show_current_bus
  
  Bus_ID_scanned = re.search(" [0-9]", line).group()
  if Bus_ID_scanned:
    return Bus_ID_scanned.strip(" ")
  
  res_msg = "Err: Set bus failed"
  return Err_set_bus

# i2c dev 0
# Setting bus to 0
def set_bus(bus_ID):
  global res_msg

  cmd_send = "i2c dev " + bus_ID
  resp_string = "Setting bus to " + bus_ID
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  
  if line == None:
    res_msg = "Err: Set bus failed"
    return Err_set_bus
  x = re.search(bus_ID, line)
  if x == None:
    res_msg = "Err: Set Bus ID failed"
    return Err_set_bus
  
  bus_ID_scanned = show_current_bus()
  if isinstance(bus_ID_scanned, (int)):
    return Err_show_current_bus

  if bus_ID_scanned == bus_ID:
    res_msg = "Pass: Success to set bus with ID " + bus_ID
    return 0
  else:
    res_msg = "Err: Bus ID showed is different with set"
    return Err_set_bus
  
# i2c show speed
# Current bus speed=100000
def match_current_bus_speed(speed):
  global res_msg

  cmd_send = "i2c speed"
  resp_string = "Current bus speed="
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)

  if line == None:
    res_msg = "Err: Show current bus speed error"
    return Err_show_current_bus_speed
  
  match = re.search(speed, line)
  if match:
    return 0
  else:
    res_msg = "Err: Current speed unmatch with speed set"
    return Err_set_bus_speed

# i2c set speed
# Setting bus speed to 100000 Hz
def set_bus_speed(speed):
  global res_msg

  cmd_send = "i2c speed " + speed
  resp_string = "Setting bus speed to"
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)

  if line == None:
    res_msg = "Err: Failed to set bus speed"
    return Err_set_bus_speed
  x = re.search(speed, line)
  if x == None:
    res_msg = "Err: Bus Speed set error"
    return Err_set_bus_speed
  
  ret = match_current_bus_speed(speed)
  if ret < 0:
    return ret 
  else:
    res_msg = "Pass: Success to set bus with speed " + speed
    return 0

# probe
# Valid chip addresses: 1A 50 , need eeprom (50)
def probe_device_on_bus(dev_ID):
  global res_msg

  cmd_send = "i2c probe "
  resp_string = "Valid chip addresses:"
  time_wait = 5

  line = scan_expected_resp(cmd_send, resp_string, time_wait)

  if line == None:
    res_msg = "Err: Failed to show device in current I2C bus"
    return Err_probe
  x = re.search(dev_ID, line)
  if x:
    return 0
  else:
    res_msg = "Err: Failed to find device with ID, " + dev_ID
    return Err_probe

def write_byte_EEPROM(val, addr):
  global EEPROM_ID
  cmd_send = "i2c mw " + EEPROM_ID + " " + addr + " " + val
  send_command(cmd_send)
  time.sleep(0.2)

def write_EEPROM_Data_Set(data_set, addr):
  
  for i in range(len(data_set)):
    write_byte_EEPROM(data_set[i], addr)
    int_addr = int(addr) + 1
    addr = str(int_addr)

def read_EEPROM_Data_Set(addr):
  global EEPROM_ID
  global res_msg

  cmd_send = "i2c md " + EEPROM_ID + " " + addr + " 8"
  resp_string = "00" + addr + ": "
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  print(line)
  if line: 
    return line
  else: 
    res_msg = "Err: read_EEPROM_Data_Set"
    return 

def read_write_memory_test(data_set):
  global Addr_WR

  write_EEPROM_Data_Set(data_set, Addr_WR)
  data_set_dump = read_EEPROM_Data_Set(Addr_WR)
  if data_set_dump == None:
    return Err_read_EEPROM_Data_Set
  
  for i in range(len(data_set)):
    ret = re.search(data_set[i], data_set_dump)
    if ret == None:
      return Err_cmp_RW_EEPROM_data_set
    
  return 0

def I2C_001_SPEED():
  global Bus_ID
  global Max_Bus_Speed
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = set_bus(Bus_ID)
  if ret < 0:
    return ret
  
  ret = set_bus_speed("100000")
  if ret < 0:
    return ret
  
  ret = set_bus_speed(Max_Bus_Speed)
  if ret < 0:
    return ret
  
  ret = probe_device_on_bus("")
  if ret < 0:
    res_msg = "Err: Failed to find probe bus 1"
    return ret

  res_msg = "Pass: Success to set speed of I2C until " + Max_Bus_Speed + 'Hz'
  return 0

def I2C_002_RW():
  global Bus_ID
  global EEPROM_ID
  global Data_WR_1
  global Data_WR_2
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = set_bus(Bus_ID)
  if ret < 0:
    return ret

  ret = probe_device_on_bus(EEPROM_ID)
  if ret < 0:
    res_msg = "Err: Failed to detect to EEPROM, please connect EEPROM to daughter card for read write test"
    return ret

  ret = read_write_memory_test(Data_WR_1)
  if ret < 0:
    res_msg = "Err: read write data set 1 to EEPROM"
    return ret

  ret = read_write_memory_test(Data_WR_2)
  if ret < 0:
    res_msg = "Err: read write data set 2 to EEPROM"
    return ret
  
  res_msg = "Pass: Success to read write data to EEPROM"
  return 0

def run_test(COM, handling_path):
  global sl
  global res_msg
  global I2C_001_result
  global I2C_001_result_msg
  global I2C_002_result
  global I2C_002_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = I2C", 'WARN')

  Open_COMPORT(COM)

  I2C_001_result = I2C_001_SPEED()
  I2C_001_result_msg = res_msg
  sl.log("I2C_001_SPEED " + str(I2C_001_result) + ' ' + I2C_001_result_msg, 'WARN')
  I2C_002_result = I2C_002_RW()
  I2C_002_result_msg = res_msg
  sl.log("I2C_002_RW " + str(I2C_002_result) + ' ' + I2C_002_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()


def main():
  current_path = path.dirname( path.abspath(__file__) )

  run_test('COM4', current_path)

  return 0

if __name__ == "__main__":
  main()

# python3 "C:\Users\MDC_FPGA_3\Documents\kllee\uboot_script_FPGA.py"
# bitfile = 0068 RTL101
# Clock 1 24
# Clock 2 24
# Clock 3 40
# Clock 4 12.288
# Clock 5 48
# Clock 6 48
# Clock 7 100
# Clock 8 48


# I2C_001_SPEED
# Set Bus
# Probe
# Change clock speed to 400kHz/1MHz
# Check if clock speed is set correctly

# I2C_002_RW
# Set bus
# Read the endpoint device address
# Perform memory write to a register of the device
# Perform memory dump from the same register
# Check the value dump is correct 
