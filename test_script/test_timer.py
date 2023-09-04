import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
timer_testing_period = 5
timer_tolerance = 0.1
unit_timer_perIP = 4
StarFive_timer_base_addr = ["15200000", "15210000"]
reg_timer_unit_offset = "0x40"
reg_timer_enable_offset = "0x10"
reg_timer_value_offset = "0x18"

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_timer_get = -11
Err_timer_slow = -12
Err_timer_fast = -13
Err_read_register = -14
Err_write_register = -15
Err_start_timer_test = -16
Err_stop_timer_test = -17

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
TIMER_001_result = Test_ID_Init_Val
TIMER_001_result_msg = ''
TIMER_002_result = Test_ID_Init_Val
TIMER_002_result_msg = ''
TIMER_003_result = Test_ID_Init_Val
TIMER_003_result_msg = ''

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
# timer start
# 
def timer_start():
  cmd_send = "timer start"
  send_command(cmd_send)

# timer get
# 5.002
def timer_get():
  global res_msg

  cmd_send = "timer get"
  resp_string = ".*[0-9][.][0-9][0-9][0-9]"
  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to get timer reading with 3 decimal place"
    return Err_timer_get
  
  time_float = float(line)
  return time_float
  
def TIMER_001_RISCV():
  global timer_testing_period
  global timer_tolerance
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  timer_start()
  time.sleep(timer_testing_period)

  ret = timer_get()
  if ret < 0:
    return ret
  else:
    time_reading = ret

  if time_reading < (timer_testing_period - timer_tolerance):
    res_msg = "Err: RISCV timer of CPU too slow"
    return Err_timer_slow
  elif time_reading > (timer_testing_period + timer_tolerance):
    res_msg = "Err: RISCV timer of CPU too fast"
    return Err_timer_fast
  
  res_msg = "Pass: RISCV timer of CPU run accurate within tolerance, " + str(timer_tolerance) + " in period " + str(timer_testing_period)
  return 0
  
def TIMER_003_STARFIVE():
  global timer_testing_period
  global timer_tolerance
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  timer_start()
  time.sleep(timer_testing_period)

  ret = timer_get()
  if ret < 0:
    return ret
  else:
    time_reading = ret

  if time_reading < (timer_testing_period - timer_tolerance):
    res_msg = "Err: StarFive timer too slow"
    return Err_timer_slow
  elif time_reading > (timer_testing_period + timer_tolerance):
    res_msg = "Err: StarFive timer too fast"
    return Err_timer_fast
  
  res_msg = "Pass: StarFive timer of CPU run accurate within tolerance, " + str(timer_tolerance) + " in period " + str(timer_testing_period)
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

def from_hex(hexdigits):
    return int(hexdigits, 16)

def timer_enable_register(timer_addr, enable):
  global reg_timer_enable_offset

  timer_enable_reg_addr = hex(from_hex(timer_addr) + from_hex(reg_timer_enable_offset))
  reg_val = "0000000" + enable

  return write_register(timer_enable_reg_addr, reg_val)
  
def timer_start_register(timer_addr):
  return timer_enable_register(timer_addr, "1")

def timer_stop_register(timer_addr):
  return timer_enable_register(timer_addr, "0")

def timer_readval_register(timer_addr):
  global reg_timer_value_offset

  timer_enable_reg_addr = hex(from_hex(timer_addr) + from_hex(reg_timer_value_offset)) 
  return read_register(timer_enable_reg_addr)

def start_timer_test(unit_base_addr):
  global res_msg

  ret = timer_start_register(unit_base_addr)
  if ret < 0:
    return ret

  reg_val1 = timer_readval_register(unit_base_addr)
  if isinstance(reg_val1, (int)):
    return reg_val1
  time.sleep(1)
  reg_val2 = timer_readval_register(unit_base_addr)
  if isinstance(reg_val2, (int)):
    return reg_val2
  
  if reg_val1 == reg_val2:
    res_msg = "Err: Failed to start StarFive timer by controlling register"
    return Err_start_timer_test
  else:
    return 0 

def stop_timer_test(unit_base_addr):
  global res_msg

  ret = timer_stop_register(unit_base_addr)
  if ret < 0:
    return ret

  reg_val1 = timer_readval_register(unit_base_addr)
  if isinstance(reg_val1, (int)):
    return reg_val1
  time.sleep(1)
  reg_val2 = timer_readval_register(unit_base_addr)
  if isinstance(reg_val2, (int)):
    return reg_val2
  
  if reg_val1 != reg_val2:
    res_msg = "Err: Failed to stop StarFive timer by controlling register"
    return Err_stop_timer_test
  else:
    return 0 

def TIMER_002_STARFIVE_REG():
  global unit_timer_perIP
  global reg_timer_unit_offset
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  for base_addr in StarFive_timer_base_addr:
    for unit in range(unit_timer_perIP):
      unit_base_addr = hex(from_hex(base_addr) + (from_hex(reg_timer_unit_offset)*unit))
      ret = stop_timer_test(unit_base_addr)
      if ret < 0:
        res_msg = "Err: Timer failed at unit " + str(unit) + " with IP base address, " + base_addr
        return ret
      ret = start_timer_test(unit_base_addr)
      if ret < 0:
        res_msg = "Err: Timer failed at unit " + str(unit) + " with base address, " + base_addr
        return ret
      ret = stop_timer_test(unit_base_addr)
      if ret < 0:
        res_msg = "Err: Timer failed at unit " + str(unit) + " with base address, " + base_addr
        return ret

  res_msg = "Pass: All units of StarFive timer can run by accessing register directly"
  return 0

def run_test_RISCV_ticktimer(COM, handling_path):
  global sl
  global res_msg
  global TIMER_001_result
  global TIMER_001_result_msg
  global TIMER_002_result
  global TIMER_002_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = TIMER", 'WARN')

  Open_COMPORT(COM)

  TIMER_001_result = TIMER_001_RISCV()
  TIMER_001_result_msg = res_msg
  sl.log("TIMER_001_RISCV " + str(TIMER_001_result) + ' ' + TIMER_001_result_msg, 'WARN')

  TIMER_002_result = TIMER_002_STARFIVE_REG()
  TIMER_002_result_msg = res_msg
  sl.log("TIMER_002_STARFIVE_REG " + str(TIMER_002_result) + ' ' + TIMER_002_result_msg, 'WARN') 

  Close_COMPORT()
  sl.close()

def run_test_STARFIVE_ticktimer(COM, handling_path):
  global sl
  global res_msg
  global TIMER_003_result
  global TIMER_003_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  TIMER_003_result = TIMER_003_STARFIVE()
  TIMER_003_result_msg = res_msg
  sl.log("TIMER_003_STARFIVE " + str(TIMER_003_result) + ' ' + TIMER_003_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()


def main():
  current_path = path.dirname( path.abspath(__file__) )

  run_test_RISCV_ticktimer('COM4', current_path)

  return 0

if __name__ == "__main__":
  main()

# bitfile = 0093 (RTL102)
# Clock 1 24
# Clock 2 50
# Clock 3 40
# Clock 4 12.288
# Clock 5 48
# Clock 6 48
# Clock 7 100
# Clock 8 48

# TIMER_001_RISCV
# 1 Use the dtb which enable RISCV timer
# 1 Use 'timer start' to start timer
# 2 Delay 5 seconds
# 3 Use 'timer get' to get the period from start
# 4 Determine the time is accurate

# TIMER_002_STARFIVE_REG
# 1 Use 'mw.l' to write register to stop timer unit
# 2 Use 'md.l' to read timer count register, delay one seconds, and read again
# 3 Makesure both results are same.
# 4 Repeat the steps with start timer and makesure both result are not same.
# 5 Repeat the steps with stop timer.

# TIMER_003_STARFIVE
# 1 Use the dtb which not enable StarFive timer
# 1 Use 'timer start' to start timer
# 2 Delay 5 seconds
# 3 Use 'timer get' to get the period from start
# 4 Determine the time is accurate

# chosen { choose timer
#   &tick-timer = &timer0;
#   &tick-timer = &timer1;
#	  tick-timer = "riscv_timer";
# };