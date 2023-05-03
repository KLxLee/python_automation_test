import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
PWM_GPIO_PIN = 23
GPIO_INPUT_PIN = 24
GPIO_BANKNAME = "GPIO"
GPIO_PINNUM = 64
pwm_ratio_tolerence = 0.015
pwm_dev = "0"
pwm_channel = "0"
pwn_chn_out_id = 55
pwn_chn_oen_id = 25
pinctrl_IP_base = 0x150d0000
pinctrl_doen_base = 0x00
pinctrl_dout_base = 0x40
max_pwm_period_sec = 10
PWM_period_applied = 5000000
PWM_duty_set = [1000000, 2000000, 3000000, 4000000]

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_read_register = -11
Err_write_register = -12
Err_config_pwm_duty = -13
Err_check_gpio_bankname = -14
Err_check_gpio_pinnum = -15
Err_read_GPIO_pin = -16
Err_timeout_GPIO_change_state = -17
Err_pwm_ratio_get = -18
Err_PWM_DUTY_NS_ERR = -19
Err_pwm_disable = -20

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
PWM_001_result = Test_ID_Init_Val
PWM_001_result_msg = ''
PWM_002_result = Test_ID_Init_Val
PWM_002_result_msg = ''
PWM_003_result = Test_ID_Init_Val
PWM_003_result_msg = ''

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

  cmd_send = "mw.l " + reg_addr + " " + reg_val_write
  send_command(cmd_send)

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

def set_pinctrl_en_out(pin, func_offset, val):
  global pinctrl_IP_base

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

def set_pwm_pinctrl(pin):
  global pinctrl_doen_base
  global pinctrl_dout_base
  global pwn_chn_oen_id
  global pwn_chn_out_id

  ret = set_pinctrl_en_out(pin, pinctrl_doen_base, pwn_chn_oen_id)
  if isinstance(ret, (int)):
    if ret < 0:
      return ret
    
  ret = set_pinctrl_en_out(pin, pinctrl_dout_base, pwn_chn_out_id)
  if isinstance(ret, (int)):
    if ret < 0:
      return ret  
    
  return 0

def enable_pwm(enable):
  global pwm_dev
  global pwm_channel

  if enable:
    cmd_send = "pwm enable " + pwm_dev + " " + pwm_channel
  else:
    cmd_send = "pwm disable " + pwm_dev + " " + pwm_channel
  send_command(cmd_send)
  time.sleep(0.1)

def config_pwm(period_ns, duty_ns):
  global pwm_dev
  global pwm_channel
  global res_msg

  cmd_send = "pwm config " + pwm_dev + " " + pwm_channel + " " + str(period_ns) + " " + str(duty_ns)
  resp_string = "error"
  time_wait = 1
    
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  
  if line:
    res_msg = "Err: PWM config setting. period_ns must be larger or equal to duty_ns"
    return Err_config_pwm_duty
  else:
    return 0

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

def wait_till_GPIO_status(pin, state_set):
  global max_pwm_period_sec
  global res_msg

  t_start = time.time() 
  while True:
    
    wait_time = time.time() - t_start
    if wait_time >  max_pwm_period_sec:
      res_msg = "Err: GPIO input pin detect PWM duty cycle transition timeout:" + str(max_pwm_period_sec) + "sec"
      return Err_timeout_GPIO_change_state

    state_get = read_GPIO_pin(pin)
    if state_get < 0:
      return state_get
    elif state_set == state_get:
      return wait_time
    
    time.sleep(0.01)

def get_gpio_status_period(pin, state_set):
  state_set ^= 1
  ret = wait_till_GPIO_status(pin, state_set)
  if ret < 0:
    return ret

  state_set ^= 1
  ret = wait_till_GPIO_status(pin, state_set)
  if ret < 0:
    return ret

  state_set ^= 1
  return wait_till_GPIO_status(pin, state_set)

def PWM_001_SET_CONFIG():
  global GPIO_BANKNAME
  global GPIO_PINNUM
  global GPIO_INPUT_PIN
  global PWM_GPIO_PIN
  global pwm_ratio_tolerence
  global PWM_period_applied
  global PWM_duty_set
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = check_gpio_bankname_pinnum(GPIO_BANKNAME, GPIO_PINNUM)
  if ret < 0:
    return ret

  ret = set_pwm_pinctrl(PWM_GPIO_PIN)
  if ret < 0:
    return ret
  
  enable_pwm(1)

  for PWM_duty_applied in PWM_duty_set:
    ret = config_pwm(PWM_period_applied, PWM_duty_applied)
    if ret < 0:
      return ret
    pwm_high_period = get_gpio_status_period(GPIO_INPUT_PIN, 1)
    if pwm_high_period < 0:
      return pwm_high_period
    pwm_low_period = get_gpio_status_period(GPIO_INPUT_PIN, 0)
    if pwm_low_period < 0:
      return pwm_low_period
    
    pwm_ratio_applied = PWM_duty_applied / PWM_period_applied
    pwm_ratio_get = pwm_high_period / (pwm_high_period+ pwm_low_period)

    if ((pwm_ratio_get < (pwm_ratio_applied + pwm_ratio_tolerence)) & (pwm_ratio_get > (pwm_ratio_applied - pwm_ratio_tolerence))):
      res_msg = "Pass: Config PWM and test with loopback pin success"
      return 0
    else:
      res_msg = "Err: Config PWM to ratio(" + str(pwm_ratio_applied) + ") is different with PWM ratio(" + str(pwm_ratio_get) + ") \
which read by GPIO with tolerance(" + str(pwm_ratio_tolerence) + ")"
      return Err_pwm_ratio_get

def PWM_002_DUTY_NS_ERR():
  global PWM_period_applied
  global PWM_duty_set
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = config_pwm(PWM_duty_set[0], PWM_period_applied)
  if ret < 0:
    res_msg = "Pass: Alert message showed after setting invalid PWM duty period"
    return 0
  else:
    res_msg = "Err: Alert message do not show after setting invalid PWM duty period"
    return Err_PWM_DUTY_NS_ERR

def PWM_003_DISABLE():
  global PWM_period_applied
  global PWM_duty_set
  global res_msg

  enable_pwm(0)

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  ret = config_pwm(PWM_period_applied, PWM_duty_set[0])
  if ret < 0:
    return ret
  
  ret = get_gpio_status_period(GPIO_INPUT_PIN, 1)
  if ret == Err_timeout_GPIO_change_state:
    res_msg = "Pass: Disable PWM success"
    return 0
  elif ret < 0:
    return ret
  else:
    res_msg = "Err: Disable PWM failed"
    return Err_pwm_disable

def run_test(COM, handling_path):
  global sl
  global res_msg
  global PWM_001_result
  global PWM_001_result_msg
  global PWM_002_result
  global PWM_002_result_msg
  global PWM_003_result
  global PWM_003_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = PWM", 'WARN')

  Open_COMPORT(COM)

  PWM_001_result = PWM_001_SET_CONFIG()
  PWM_001_result_msg = res_msg
  sl.log("PWM_001_SET_CONFIG " + str(PWM_001_result) + ' ' + PWM_001_result_msg, 'WARN')

  PWM_002_result = PWM_002_DUTY_NS_ERR()
  PWM_002_result_msg = res_msg
  sl.log("PWM_002_DUTY_NS_ERR " + str(PWM_002_result) + ' ' + PWM_002_result_msg, 'WARN') 

  PWM_003_result = PWM_003_DISABLE()
  PWM_003_result_msg = res_msg
  sl.log("PWM_003_DISABLE " + str(PWM_003_result) + ' ' + PWM_003_result_msg, 'WARN')

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


# PWM_001_SET_CONFIG
# 1. Bind PWM with one gpio pin
# 1. Enable PWM
# 2. Set period_ns = 5000000
# 3. Set duty_ns = 1000000
# 4. Ensure duty_cycle is correct (20%)
# 5. Repeat step 2,3 and 4 with different values

# PWM_002_DUTY_NS_ERR
# 1. Enable PWM
# 2. Set period_ns = 1000000
# 3. Set duty_ns = 5000000
# 4. Ensure uboot prompt error message

# PWM_003_DISABLE
# 1. Enable PWM
# 2. Set period_ns and duty_ns
# 3. Check the output is correct with logic analyser
# 4. Disable PWM
# 5. Set period_ns and duty_ns
# 6. Check the output should be LOW at all time