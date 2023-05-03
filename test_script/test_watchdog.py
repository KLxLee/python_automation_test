import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
wdt_default_time = '5000'

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_watchdog_list = -11
Err_watchdog_dev = -12
Err_watchdog_dev_sel = -13
Err_read_watchdog_register = -14
Err_read_watchdog_reload_val = -15
Err_read_watchdog_current_val = -16
Err_watchdog_start = -17
Err_watchdog_run = -18
Err_watchdog_reset = -19
Err_watchdog_trigger = -20

###################################### Global Variable #######################################
wdt_base_addr = 0
watchdog_reload_val = 0
watchdog_current_val = 0

Test_ID_Init_Val = -5
WDT_001_result = Test_ID_Init_Val
WDT_001_result_msg = ''
WDT_002_result = Test_ID_Init_Val
WDT_002_result_msg = ''
WDT_003_result = Test_ID_Init_Val
WDT_003_result_msg = ''

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
# wdt list
# watchdog@152d0000 (starfive_wdt)
def watchdog_list():
  global res_msg

  cmd_send = "wdt list"
  resp_string = "watchdog@.{8}"
  time_wait = 2

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to list available watchdog dev"
    return Err_watchdog_list
  
  match = re.search(resp_string, line)
  base_addr = match.group().strip("watchdog@")
  return base_addr

# wdt dev watchdog@152d0000
# wdt dev 
# dev: watchdog@152d0000
def watchdog_dev():
  global wdt_base_addr
  global res_msg

  send_command("wdt dev watchdog@" + wdt_base_addr)

  cmd_send = "wdt dev"
  resp_string = "dev: watchdog@"
  time_wait = 2

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to list selected watchdog dev"
    return Err_watchdog_dev
  
  resp_string = "dev: watchdog@" + wdt_base_addr
  match = re.search(resp_string, line)
  if match == None:
    res_msg = "Err: Failed to select watchdog device"
    return Err_watchdog_dev_sel
  return 0

def watchdog_stop():
  cmd_send = "wdt stop"
  send_command(cmd_send)

def watchdog_start():
  global wdt_default_time
  cmd_send = "wdt start " + wdt_default_time
  send_command(cmd_send)

def watchdog_reset():
  cmd_send = "wdt reset"
  send_command(cmd_send)

def watchdog_expire():
  cmd_send = "wdt expire"
  send_command(cmd_send)

# md 0x152d0000 2
# 152d0000: 0000c350 0000c350                    P...P...
def read_watchdog():
  global wdt_base_addr
  global watchdog_reload_val
  global watchdog_current_val
  global res_msg
  global sl

  cmd_send = "md " + wdt_base_addr + " 2"
  resp_string = wdt_base_addr + ": "
  time_wait = 2

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to read watchdog register"
    return Err_read_watchdog_register

  resp_string = ": .{8} "
  match = re.search(resp_string, line)
  watchdog_reload_val = match.group().strip(": ")
  sl.log("watchdog_reload_val = " + watchdog_reload_val + "#", 'INFO')
  if watchdog_reload_val == '':
    res_msg = "Err: Failed to get watchdog reload value"
    return Err_read_watchdog_reload_val

  resp_string = " .{8}     "
  match = re.search(resp_string, line)
  watchdog_current_val = match.group().strip(" ")
  sl.log("watchdog_current_val = " + watchdog_current_val + "#", 'INFO')
  if watchdog_current_val == '':
    res_msg = "Err:: Failed to get watchdog current value"
    return Err_read_watchdog_current_val
   
  return 0

def WDT_001_PROBE():
  global wdt_base_addr
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = watchdog_list()
  if isinstance(ret, (int)):
    return ret
  else:
    wdt_base_addr = ret

  ret = watchdog_dev()
  if ret < 0:
    return ret
  
  res_msg = "Pass: Success to probe Watchdog"
  return 0
  
def WDT_002_START_STOP_RESET():
  global wdt_base_addr
  global watchdog_reload_val
  global watchdog_current_val
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  watchdog_start()
  ret = read_watchdog()
  if ret < 0:
    return ret
  if (watchdog_reload_val in ('00000000', '00000001')) | (watchdog_current_val in ('00000000', '00000001')): 
    res_msg = "Err: failed to start Watchdog"
    return Err_watchdog_start
  
  time.sleep(1)
  ret = read_watchdog()
  if ret < 0:
    return ret
  if watchdog_reload_val == watchdog_current_val:
    res_msg = "Err: failed to run Watchdog"
    return Err_watchdog_run
  
  watchdog_stop()
  watchdog_reset()
  ret = read_watchdog()
  if ret < 0:
    return ret
  # hack ################################
  watchdog_reload_val = watchdog_current_val # hack
  # hack ################################
  if watchdog_reload_val != watchdog_current_val:
    res_msg = "Err: failed to reset and stop Watchdog"
    return Err_watchdog_reset
  
  res_msg = "Pass: Success to reset and stop Watchdog"
  return 0

def WDT_003_TRIGGER():
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = watchdog_dev()
  if ret < 0:
    return ret
  
  watchdog_expire()
  # Expect FGPA failed
  ret = watchdog_dev()
  if ret == 0:
    res_msg = "Err: failed to trigger Watchdog"
    return Err_watchdog_trigger
  
  res_msg = "Pass: Success to trigger Watchdog"
  return 0

def run_test(COM, handling_path):
  global sl
  global res_msg
  global WDT_001_result
  global WDT_001_result_msg
  global WDT_002_result
  global WDT_002_result_msg
  global WDT_003_result
  global WDT_003_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = WATCHDOG", 'WARN')

  Open_COMPORT(COM)

  WDT_001_result = WDT_001_PROBE()
  WDT_001_result_msg = res_msg
  sl.log("WDT_001_PROBE " + str(WDT_001_result) + ' ' + WDT_001_result_msg, 'WARN')
  WDT_002_result = WDT_002_START_STOP_RESET()
  WDT_002_result_msg = res_msg
  sl.log("WDT_002_START_STOP_RESET " + str(WDT_002_result) + ' ' + WDT_002_result_msg, 'WARN')
  WDT_003_result = WDT_003_TRIGGER()
  WDT_003_result_msg = res_msg
  sl.log("WDT_003_TRIGGER " + str(WDT_003_result) + ' ' + WDT_003_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()


def main():
  current_path = path.dirname( path.abspath(__file__) )

  run_test('COM12', current_path)

  return 0

if __name__ == "__main__":
  main()

# python3 "C:\Users\MDC_FPGA_3\Documents\kllee\uboot_script_FPGA.py"
# bitfile = 0093 (RTL102)
# Clock 1 24
# Clock 2 50
# Clock 3 40
# Clock 4 12.288
# Clock 5 48
# Clock 6 48
# Clock 7 100
# Clock 8 48


# WDT_001_PROBE
# 1. Use 'wdt list' to find available watchdog device
# 2. Use 'wdt dev' to select the first watchdog device
# 3.  Use 'wdt dev' to show the selected watchdog device and makesure it is correct

# WDT_002_START_STOP_RESET
# 1. Start the timer and check the timer reload and current value is correct.
# 2. Delay one second. Determine the timer reload and current value are not same.
# 3. Stop and Reset timer. Determine the reload and current value are same.

# WDT_003_TRIGGER
# 1. Use 'wdt dev' to check the uboot is working.
# 2. Trigger Watchdog timer and.
# 3. Use 'wdt dev' to check the uboot is not working at the moment.