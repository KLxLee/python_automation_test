import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
zero_pattern = '0x00'
negative_pattern = '0xff'
checkerboard_pattern_1 = 'aaaacccc'
checkerboard_pattern_2 = '12345678'
data_len = '0x1000'
mem_addr1 = "0x50000000"
mem_addr2 = "0x51000000"

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_cpu_list = -11
Err_cpu_detail = -12
Err_uboot_version = -13
Err_write_memory = -14

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
BOOTING_001_result = Test_ID_Init_Val
BOOTING_001_result_msg = ''
BOOTING_002_result = Test_ID_Init_Val
BOOTING_002_result_msg = ''

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
# cpu list
#   0: cpu@0      rv64imafdc
def cpu_list():
  global res_msg

  cmd_send = "cpu list"
  resp_string = "0: cpu@0"
  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to list available CPU"
    return Err_cpu_list
  
  return 0

# cpu list
#   0: cpu@0      rv64imafdc
#     ID = 0, freq = 0 Hz: L1 cache, MMU  
def cpu_detail():
  global res_msg

  cmd_send = "cpu detail"
  resp_string = "ID = 0"
  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to list CPU detail"
    return Err_cpu_detail
  
  return 0

# version
# U-Boot 2022.10-00086-gbdbaa5834d (Mar 06 2023 - 16:54:28 +0800)
def uboot_version():
  global res_msg

  cmd_send = "version"
  resp_string = "U-Boot"
  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to list CPU detail"
    return Err_uboot_version
  
  return 0

# mw.b 0x44000000 55 100
def write_memory(addr, data_pattern, len):
  cmd_send = "mw.l " + addr + " " + data_pattern + " " + len
  send_command(cmd_send)
  time.sleep(1)

# cmp.l 0x44000000 0x46000000 200
# word at 0x44000100 (0x00) != word at 0x46000100 (0x30303034)
# Total of 64 word(s) were the same
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

def BOOTING_001_INFO():
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = cpu_list()
  if ret < 0:
    return ret
  
  ret = cpu_detail()
  if ret < 0:
    return ret
  
  ret = uboot_version()
  if ret < 0:
    return ret

  res_msg = "Pass: Success to read U-boot info"
  return 0

def BOOTING_002_MEMORY():
  global zero_pattern
  global negative_pattern
  global checkerboard_pattern_1
  global checkerboard_pattern_2
  global data_len
  global mem_addr1
  global mem_addr2
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  write_memory(mem_addr1, zero_pattern, data_len)
  write_memory(mem_addr2, negative_pattern, data_len)
  ret = cmp_memory(mem_addr1, mem_addr2, data_len)
  if ret == 0:
    res_msg = "Err: Write Memory happen not expected result at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_write_memory
  
  write_memory(mem_addr1, negative_pattern, data_len)
  ret = cmp_memory(mem_addr1, mem_addr2, data_len)
  if ret < 0:
    res_msg = "Err: Write Memory happen not expected result at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_write_memory
  
  write_memory(mem_addr1, checkerboard_pattern_1, data_len)
  write_memory(mem_addr2, checkerboard_pattern_2, data_len)
  ret = cmp_memory(mem_addr1, mem_addr2, data_len)
  if ret == 0:
    res_msg = "Err: Write Memory happen not expected result at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_write_memory
  
  write_memory(mem_addr1, checkerboard_pattern_2, data_len)
  ret = cmp_memory(mem_addr1, mem_addr2, data_len)
  if ret < 0:
    res_msg = "Err: Write Memory happen not expected result at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_write_memory
  
  res_msg = "Pass: Success to read write memory"
  return 0

def run_test(COM, handling_path):
  global sl
  global res_msg
  global BOOTING_001_result
  global BOOTING_001_result_msg
  global BOOTING_002_result
  global BOOTING_002_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = BOOTING", 'WARN')

  Open_COMPORT(COM)

  BOOTING_001_result = BOOTING_001_INFO()
  BOOTING_001_result_msg = res_msg
  sl.log("BOOTING_001_INFO " + str(BOOTING_001_result) + ' ' + BOOTING_001_result_msg, 'WARN')
  BOOTING_002_result = BOOTING_002_MEMORY()
  BOOTING_002_result_msg = res_msg
  sl.log("BOOTING_002_MEMORY " + str(BOOTING_002_result) + ' ' + BOOTING_002_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()


def main():
  current_path = path.dirname( path.abspath(__file__) )

  run_test('COM4', current_path)

  return 0

if __name__ == "__main__":
  main()

# python3 "C:\Users\MDC_FPGA_3\Documents\kllee\uboot_script_FPGA.py"
# bitfile = 0093 (RTL102), Any
# Clock 1 24
# Clock 2 50
# Clock 3 40
# Clock 4 12.288
# Clock 5 48
# Clock 6 48
# Clock 7 100
# Clock 8 48

# BOOTING_001_INFO
# 1. Use 'cpu list' to show available CPU.
# 2. Use 'cpu detail' to show CPU detail.
# 3. Use 'version' to display u-boot version.

# BOOTING_002_MEMORY
# 1. Use 'mw' to write a dummy data to a memory address 1.
# 2. Use 'mw' to write the different dummy data to a memory address 2.
# 3. Use 'cmp' to compare data among both addresses and expect not same.
# 4. Repeat with same data and expect same.
# 5. Repeat steps above with different data.
