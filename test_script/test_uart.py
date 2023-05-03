import time
import serial
import re
import math
from ymodem.Modem import Modem
from os import path
import std_func as sf

########################################## Define ############################################
CRC = b'\x43'

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_check_Ymodem_receive_device = -11
Err_Ymodem_send_file_error = -12
Err_load_Uboot_itb = -13

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
UART_001_result = Test_ID_Init_Val
UART_001_result_msg = ''
UART_002_result = Test_ID_Init_Val
UART_002_result_msg = ''

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
def check_Ymodem_receive_device():
  global s
  global sl
  global res_msg
  global CRC

  s.reset_input_buffer()
  s.timeout = 7

  timeout = time.time() + 10
  while True:
    char = s.read()
    sl.log(char, 'DEBUG')
    if char == CRC:
      char = s.read()
      if char == CRC:
        sl.log("Device is ready to receive file by Ymodem", 'INFO')
        return 0

    if timeout < time.time():
      res_msg = "Err: Device is not ready to receive file by Ymodem"
      return Err_check_Ymodem_receive_device

class TaskProgressBar:
    global sl

    def __init__(self):
        self.bar_width = 50
        self.last_task_name = ""
        self.current_task_start_time = -1

    def show(self, task_index, task_name, total, success, failed):
        if task_name != self.last_task_name:
            self.current_task_start_time = time.perf_counter()
            if self.last_task_name != "":
                sl.log('', 'INFO')
            self.last_task_name = task_name

        success_width = math.ceil(success * self.bar_width / total)

        a = "#" * success_width
        b = "." * (self.bar_width - success_width)
        progress = (success_width / self.bar_width) * 100
        cost = time.perf_counter() - self.current_task_start_time

        sl.log(f"\r{task_index} - {task_name} {progress:.2f}% [{a}->{b}]{cost:.2f}s", 'INFO')

def sender_read(size, timeout=3):
  global s
  s.timeout = timeout
  return s.read(size) or None

def sender_write(data, timeout=3):
  global s
  s.writeTimeout = timeout
  return s.write(data)


def UART_001_BOOT_U_BOOT_PROPER(file_path_uboot_itb):
  global s
  global res_msg

  ret = check_Ymodem_receive_device()
  if ret < 0:
    return ret

  sender = Modem(sender_read, sender_write)

  progress_bar = TaskProgressBar()
  ret = sender.send([file_path_uboot_itb], callback=progress_bar.show)
  if ret == False:
    res_msg = "Err: Send file error by Ymodem"
    return Err_Ymodem_send_file_error
  
  if scan_expected_resp("", "Loaded .* bytes", 3) == None:
    res_msg = "Err: Uboot SPL loaded Uboot.itb error"
    return Err_load_Uboot_itb

  ret = detect_CMD_startup()
  if ret != 0:
    return ret
  
  res_msg = "Pass: Uboot SPL boot to Uboot.itb success"
  return 0

def splboot(COM, handling_path, uboot_itb_path):
  global sl
  global res_msg
  global UART_001_result
  global UART_001_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = UART", 'WARN')

  Open_COMPORT(COM)

  UART_001_result = UART_001_BOOT_U_BOOT_PROPER(uboot_itb_path)
  UART_001_result_msg = res_msg
  sl.log("UART_001_BOOT_U_BOOT_PROPER " + str(UART_001_result) + ' ' + UART_001_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def main():
  current_path = path.dirname( path.abspath(__file__) )
  uboot_itb_path = current_path + '\\boot_file\\u-boot.itb'

  splboot('COM4', current_path, uboot_itb_path)

  return 0

if __name__ == "__main__":
  main()

# bitfile = 0094 (RTL101)
# Clock 1 24
# Clock 2 24
# Clock 3 40
# Clock 4 12.288
# Clock 5 48
# Clock 6 48
# Clock 7 100
# Clock 8 48

# UART_001_BOOT_U_BOOT_PROPER
# 1. Create U-Boot Proper itb from U-Boot compilation.
# 2. Send the itb to board through uart YMODEM when board ready to receive.
# 3. Boot U-Boot Proper

# UART_002_BOOT_LINUX
# 1. Create kernel itb from U-Boot compilation.
# 2. Send the itb to board through uart YMODEM when board ready to receive.
# 3. Boot Linux
