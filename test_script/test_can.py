import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
dev_index = '0'
dev_base_addr = '12200000'
can_driver_name = "starfive_can"
CFG_STAT_offset = 'a0'
TX_addr = '50000000'
RX_addr = '60000000'
can_data_frame_1 = ['00000000', '00000008', '12345678', '87654321']
can_data_frame_2 = ['000007ff', '00000008', 'abcdef01', 'ffffffff']
Int_lpbk = 1
Ext_lpbk = 2

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_find_can_device = -11
Err_read_register = -12
Err_write_register = -13
Err_receive_data  = -14
Err_cmp_memory = -15

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
CAN_001_result = Test_ID_Init_Val
CAN_001_result_msg = ''
CAN_002_result= Test_ID_Init_Val
CAN_002_result_msg = ''

dev_name = None

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
def find_can_device(index, driver_name):
  global dev_name
  global res_msg

  cmd_send = "misc list"
  resp_string = "   " + index + " "
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)

  if line == None:
    res_msg = "Err: Device with index " + index + " is not found in misc list"
    return Err_find_can_device
  
  if not re.search(driver_name, line):
    res_msg = "Err: Device with index " + index + " is not using driver with name " + driver_name
    return Err_find_can_device

  dev_name = line[0:19].strip()
  return 0

def read_register(reg_addr):
  global res_msg

  cmd_send = "md.l " + reg_addr + " 1"
  resp_string = reg_addr[2:10] + ": .{8} "
  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to read register with address, " + reg_addr
    return Err_read_register
  
  reg_val = line[10:18]
  if reg_val.isalnum:
    return reg_val
  else:
    res_msg = "Err: Failed to read register with address, " + reg_addr
    return Err_read_register

def write_register(reg_addr, reg_val_write):
  global res_msg

  time.sleep(0.1)
  cmd_send = "mw.l " + reg_addr + " " + reg_val_write
  send_command(cmd_send)
  time.sleep(0.1)

  reg_val_read = read_register(reg_addr)
  if isinstance(reg_val_read, (int)):
    return reg_val_read

  if reg_val_write != reg_val_read:
    res_msg = "Err: Failed to write register with address, " + reg_addr
    return Err_write_register
  else:
    return 0

def set_lpbk(reg_adr, mode):
  global CFG_STAT_offset

  reg_CFG_STAT = reg_adr[0:6] + CFG_STAT_offset

  reg_val_read = read_register(reg_CFG_STAT)
  if isinstance(reg_val_read, (int)):
    return reg_val_read

  if mode == Int_lpbk: # internal
    reg_val_write = reg_val_read[0:6] + '2' + reg_val_read[7:8] # set LBMI
    reg_val_write = reg_val_write[0:4] + '0' + reg_val_write[5:8] # unset LOM
    reg_val_write = '0' + reg_val_write[1:8] # unset Self-ACK
  else: # external
    reg_val_write = reg_val_read[0:6] + '4' + reg_val_read[7:8] # set LBME
    reg_val_write = reg_val_write[0:4] + '4' + reg_val_write[5:8] # set LOM
    reg_val_write = '9' + reg_val_write[1:8] # set Self-ACK
  write_register(reg_CFG_STAT, reg_val_write)

def transmit_can_frame(name, addr):
  global res_msg

  time.sleep(0.1)
  cmd_send = " misc write " + name + " 0 " + addr + " 0"
  send_command(cmd_send)
  time.sleep(0.1)

def receive_can_frame(name, addr):
  global res_msg

  cmd_send = " misc read " + name + " 0 " + addr + " 0"
  resp_string = "Command 'read' failed: Error"
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    sl.log("RX buffer empty", 'INFO')
    return -1
  else:
    sl.log("RX buffer not empty", 'INFO')
    return 1

def cmp_memory(addr1, addr2, len):
  len_dec = str(int(len, 16))
  cmd_send = "cmp.l " + addr1 + " " + addr2 + " " + len
  resp_string = "Total of " + len_dec + " word"
  time_wait = 5
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    return -1
  else: 
    return 0

def RX_TX_test(can_data_frame):
  global TX_addr
  global RX_addr
  global dev_name
  global res_msg

  addr_t = TX_addr
  addr_r = RX_addr
  for data in can_data_frame:
    write_register(addr_t, data)
    addr_t = int(addr_t, 16)
    addr_t = hex(addr_t + 4)

    write_register(addr_r, '0')
    addr_r = int(addr_r, 16)
    addr_r = hex(addr_r + 4)

  ret = receive_can_frame(dev_name, RX_addr)
  if ret != -1:
    res_msg = "Err: CAN received is not empty, supposed do not received any data yet"
    return Err_receive_data

  transmit_can_frame(dev_name, TX_addr)

  ret = receive_can_frame(dev_name, RX_addr)
  if ret != 1:
    res_msg = "Err: CAN received is empty, supposed to receive data from loopback"
    return Err_receive_data

  ret = cmp_memory(TX_addr, RX_addr, '4')
  if ret < 0:
    res_msg = "Err: CAN received data at " + TX_addr + " and CAN transmit data from " + RX_addr + " are different"
    return Err_cmp_memory
  
  return 0

def CAN_001_INT_LPBK():
  global dev_index
  global dev_base_addr
  global can_driver_name
  global can_data_frame_1
  global can_data_frame_2
  global Int_lpbk
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = find_can_device(dev_index, can_driver_name)
  if ret < 0:
    return ret

  set_lpbk(dev_base_addr, Int_lpbk)

  ret = RX_TX_test(can_data_frame_1)
  if ret < 0:
    return ret
  
  ret = RX_TX_test(can_data_frame_2)
  if ret < 0:
    return ret

  res_msg = "Pass: "
  return 0

def CAN_002_EXT_LPBK():
  global dev_index
  global dev_base_addr
  global can_driver_name
  global can_data_frame_1
  global can_data_frame_2
  global Ext_lpbk
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = find_can_device(dev_index, can_driver_name)
  if ret < 0:
    return ret

  set_lpbk(dev_base_addr, Ext_lpbk)

  ret = RX_TX_test(can_data_frame_1)
  if ret < 0:
    return ret
  
  ret = RX_TX_test(can_data_frame_2)
  if ret < 0:
    return ret

  res_msg = "Pass: "
  return 0

def run_test(COM, handling_path):
  global sl
  global res_msg
  global CAN_001_result
  global CAN_001_result_msg
  global CAN_002_result
  global CAN_002_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = CAN", 'WARN')

  Open_COMPORT(COM)

  CAN_001_result = CAN_001_INT_LPBK()
  CAN_001_result_msg = res_msg
  sl.log("CAN_001_INT_LPBK " + str(CAN_001_result) + ' ' + CAN_001_result_msg, 'WARN')
  CAN_002_result = CAN_002_EXT_LPBK()
  CAN_002_result_msg = res_msg
  sl.log("CAN_002_EXT_LPBK " + str(CAN_002_result) + ' ' + CAN_002_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

# CAN_001_INT_LPBK
# 1. Detect available CAN device with selected index
# 2. Set mode to INTERNAL loopback
# 3. Set CAN frame data pattern in TX_address
# 4. Receivie CAN data to RX_address, supposed empty RX buffer
# 5. Transmit CAN data from TX_address
# 6. Receivie CAN data to RX_address, supposed not empty RX buffer
# 7. Compare RX_address and TX_address data, the data are the same
# 8. Repeat with second CAN frame data pattern

# CAN_002_EXT_LPBK
# 1. Detect available CAN device with selected index
# 2. Set mode to EXTERNAL loopback
# 3. Set CAN frame data pattern in TX_address
# 4. Receivie CAN data to RX_address, supposed empty RX buffer
# 5. Transmit CAN data from TX_address
# 6. Receivie CAN data to RX_address, supposed not empty RX buffer
# 7. Compare RX_address and TX_address data, the data are the same
# 8. Repeat with second CAN frame data pattern