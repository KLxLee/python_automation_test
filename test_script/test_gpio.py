import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
all_gpio_bankname = ["GPIO", "RGPIO"]
all_gpio_pinnum = [64, 12]
GPIO_BANKNAME = all_gpio_bankname[0]
GPIO_PIN_1 = 23
GPIO_PIN_2 = 24

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_check_gpio_bankname = -11
Err_check_gpio_pinnum = -12
Err_read_GPIO_pin = -13
Err_write_GPIO_pin = -14
Err_simple_gpio_lpbk_test = -15

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
GPIO_001_result = Test_ID_Init_Val
GPIO_001_result_msg = ''
GPIO_002_result = Test_ID_Init_Val
GPIO_002_result_msg = ''

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
# gpio status
# Bank GPIOA:
def check_gpio_bankname_pinnum(bank_name, pin_num):
  global res_msg

  cmd_send = "gpio status -a"
  resp_string = "Bank " + bank_name + ":"
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: GPIO(bankname=" + bank_name + ") not exists"
    return Err_check_gpio_bankname
  
  resp_string = bank_name + str(pin_num-1) + ": "
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: GPIO(bankname=" + bank_name + ") has less than " + str(pin_num) + "pins"
    return Err_check_gpio_pinnum
  
  resp_string = bank_name + str(pin_num) + ": "
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    res_msg = "Err: GPIO(bankname=" + bank_name + ") has more than " + str(pin_num) + "pins"
    return Err_check_gpio_pinnum

  return 0

def read_GPIO_pin(pin):
  global GPIO_BANKNAME
  global res_msg

  cmd_send = "gpio input " + GPIO_BANKNAME + str(pin)
  resp_string = "value is [0-1]"
  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to read gpio pin, " + GPIO_BANKNAME + " " + str(pin)
    return Err_read_GPIO_pin
  
  match = re.search("value is 1", line)
  if match:
    return 1
  else:
    return 0

# gpio set a5
# gpio: pin a5 (gpio 133) value is 1
def write_GPIO_pin(pin, state):
  global GPIO_BANKNAME
  global res_msg

  if state == 1:
    cmd_send = "gpio set " + GPIO_BANKNAME + str(pin)
    resp_string = "value is 1"
  else: 
    cmd_send = "gpio clear " + GPIO_BANKNAME + str(pin)
    resp_string = "value is 0"

  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to set gpio pin, " + GPIO_BANKNAME + " " + str(pin) + " output(value=" + str(state) + ")"
    return Err_write_GPIO_pin
  
  resp_string = "Warning:"
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    res_msg = "Err: Set gpio pin, " + GPIO_BANKNAME + " " + str(pin) + " output(value=" + str(state) + ") got Warning"
    return Err_write_GPIO_pin
  
  return 0

def simple_gpio_lpbk_test(p1, p2, state_set):
  global res_msg

  ret = write_GPIO_pin(p1, state_set)
  if ret < 0:
    return ret

  state_get = read_GPIO_pin(p2)
  if state_get < 0:
    return state_get
  
  if state_set != state_get:
    res_msg = "Err: Simple loopback test at " + str(GPIO_BANKNAME) + str(p1) + " as output\
(value=" + str(state_set) + ") and " + str(GPIO_BANKNAME) + str(p2) + " as input"
    return Err_simple_gpio_lpbk_test
  
  return 0

def GPIO_001_STATUS():
  global all_gpio_bankname
  global all_gpio_pinnum
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  for i in range(len(all_gpio_bankname)):
    ret = check_gpio_bankname_pinnum(all_gpio_bankname[i], all_gpio_pinnum[i])
    if ret < 0:
      return ret
    
  res_msg = "Pass: Success to get gpio status"
  return 0

def GPIO_002_LPBK_TEST():
  global GPIO_PIN_1
  global GPIO_PIN_2
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = simple_gpio_lpbk_test(GPIO_PIN_1, GPIO_PIN_2, 0)
  if ret < 0:
    return ret
  ret = simple_gpio_lpbk_test(GPIO_PIN_1, GPIO_PIN_2, 1)
  if ret < 0:
    return ret
  ret = simple_gpio_lpbk_test(GPIO_PIN_2, GPIO_PIN_1, 0)
  if ret < 0:
    return ret
  ret = simple_gpio_lpbk_test(GPIO_PIN_2, GPIO_PIN_1, 1)
  if ret < 0:
    return ret
  
  res_msg = "Pass: Success to do loopback gpio test with " + str(GPIO_BANKNAME) + " pins " + str(GPIO_PIN_1) + " and " + str(GPIO_PIN_2)
  return 0

def run_test(COM, handling_path):
  global sl
  global res_msg
  global GPIO_001_result
  global GPIO_001_result_msg
  global GPIO_002_result
  global GPIO_002_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = GPIO", 'WARN')

  Open_COMPORT(COM)

  GPIO_001_result = GPIO_001_STATUS()
  GPIO_001_result_msg = res_msg
  sl.log("GPIO_001_STATUS " + str(GPIO_001_result) + ' ' + GPIO_001_result_msg, 'WARN')
  GPIO_002_result = GPIO_002_LPBK_TEST()
  GPIO_002_result_msg = res_msg
  sl.log("GPIO_002_LPBK_TEST " + str(GPIO_002_result) + ' ' + GPIO_002_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()


def main():
  current_path = path.dirname( path.abspath(__file__) )

  run_test('COM4', current_path)

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

# GPIO_001_STATUS
# 1 Check all the gpio banks (SYS and AON) are exist with correct pin number.

# GPIO_002_LPBK_TEST
# 1 Connect the 2 gpio pin with a jumper
# 2 Set gpio1 as output
# 3 Set gpio2 as input and read the value 
# 4 Determine gpio1 output value and gpio2 input value are the same
# 5 Toggle gpio1 output value and repeat previous step
# 6 Set gpio1 as input, gpio2 as output. Repeat previous step