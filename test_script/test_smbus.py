import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
SMBus_ID = '0'
SMBus_EP_ID = '18'
MFGID = '4d'
MFGID_cmd = 'fe'
DEVID = '01'
DEVID_cmd = 'ff'
RW_reg1_cmd = '05'
RW_reg2_cmd = '06'

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_show_current_bus = -11
Err_set_bus = -12
Err_show_current_bus_speed = -13
Err_set_bus_speed = -14
Err_probe = -15
Err_read_SMBus_register = -16
Err_check_MFGID = -17
Err_check_DEVID = -18
Err_test_RW_reg = -19

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
SMBUS_001_result = Test_ID_Init_Val
SMBUS_001_result_msg = ''

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

def read_SMBus_register(EP_ID, cmd):
  global res_msg

  cmd_send = "i2c md " + EP_ID + " " + cmd + " 1"
  resp_string = "00" + cmd + ": "
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None: 
    res_msg = "Err: read_EEPROM_Data_Set"
    return Err_read_SMBus_register

  return line[5:7]

def write_SMBus_register(EP_ID, cmd, val):
  global res_msg

  cmd_send = "i2c mw " + EP_ID + " " + cmd + " " + val
  send_command(cmd_send)
  time.sleep(0.2)

def test_RW_reg(EP_ID, cmd):
  global res_msg

  dat1 = '01'
  write_SMBus_register(EP_ID, cmd, dat1)
  if read_SMBus_register(EP_ID, cmd) != dat1:
    res_msg = "Err: Read Write register with command " + cmd + " not get expected value, " + dat1
    return Err_test_RW_reg
  
  dat2 = 'f0'
  write_SMBus_register(EP_ID, cmd, dat2)
  if read_SMBus_register(EP_ID, cmd) != dat2:
    res_msg = "Err: Read Write register with command " + cmd + " not get expected value, " + dat2
    return Err_test_RW_reg

  return 0

def SMBUS_001_RW():
  global SMBus_ID
  global SMBus_EP_ID
  global MFGID
  global MFGID_cmd
  global DEVID
  global DEVID_cmd
  global RW_reg1_cmd
  global RW_reg2_cmd
  global res_msg
  
  ret = detect_CMD_startup()
  if ret != 0:
    return ret
  
  ret = set_bus_speed("100000")
  if ret < 0:
    return ret

  ret = set_bus(SMBus_ID)
  if ret < 0:
    return ret
  
  ret = probe_device_on_bus(SMBus_EP_ID)
  if ret < 0:
    res_msg = "Err: Failed to detect to SMBus_EP_ID, " + SMBus_EP_ID
    return ret
  
  ret = read_SMBus_register(SMBus_EP_ID, MFGID_cmd)
  if ret < 0:
    return ret
  if ret != MFGID:
    res_msg = "Err: Failed to get correct manufacturer ID code, " + MFGID
    return Err_check_MFGID
  
  ret = read_SMBus_register(SMBus_EP_ID, DEVID_cmd)
  if ret < 0:
    return ret
  if ret != DEVID:
    res_msg = "Err: Failed to get correct device ID code, " + DEVID
    return Err_check_DEVID

  ret = test_RW_reg(SMBus_EP_ID, RW_reg1_cmd)
  if ret < 0:
    return ret
  
  ret = test_RW_reg(SMBus_EP_ID, RW_reg2_cmd)
  if ret < 0:
    return ret
  
  res_msg = "Pass: SMBus test at bus, " + SMBus_ID + " device ID, " + SMBus_EP_ID + " success"
  return 0

def run_test(COM, handling_path):
  global sl
  global res_msg
  global SMBUS_001_result
  global SMBUS_001_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = SMBUS", 'WARN')

  Open_COMPORT(COM)

  SMBUS_001_result = SMBUS_001_RW()
  SMBUS_001_result_msg = res_msg
  sl.log("SMBUS_001_RW " + str(SMBUS_001_result_msg) + ' ' + SMBUS_001_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()
  

# SMBUS_001_RW
# 1. Select & set I2C bus
# 2. Probe and read the endpoint device (MAX1617A) address
# 3. Perform memory dump from device ID register(0xFF)
# 4. Check device ID is correct
# 5. Perform memory dump from manufacturer ID register(0xFE)
# 6. Check manufacturer ID is correct
# 7. Perform memory write to local temperature-high limit register (0x05)
# 8. Perform memory dump from the same register and check the value has been updated
# 9. Perform memory write to local temperature-low limit register (0x06)
# 10. Perform memory dump from the same register and check the value has been updated
