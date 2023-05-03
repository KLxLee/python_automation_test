import re
import time
import tftpy
import serial
import threading
from os import path
import std_func as sf

########################################## Define ############################################
ipaddr = "192.168.152.144"
serverip = "192.168.152.55"
gatewayip = "192.168.152.1"
tftp_port = 69
tftp_transfer_time = 120

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_setenv_ipaddr = -11
Err_setenv_serverip = -12
Err_setenv_gatewayip = -13
Err_ping_server = -14
Err_start_tftp_server = -15
Err_tftp_file_transfer = -16
Err_tftp_file_transfer_timeout = -17

Err_linux_start = -31
Err_linux_running = -32
Err_linux_receive_cmd = -33

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
ETH_001_result = Test_ID_Init_Val
ETH_001_result_msg = ''

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
def setenv(env_name, env_val):
  global res_msg

  cmd_send = "setenv " + env_name + " " + env_val
  send_command(cmd_send)
  
  cmd_send = "printenv " + env_name
  resp_string = env_name + '=' + env_val
  time_wait = 1
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: setenv {env_name}"
    return -1
  return 0

def setenv_ipaddr():
  global ipaddr

  ret = setenv("ipaddr", ipaddr)
  if ret < 0:
    return Err_setenv_ipaddr
  else:
    return 0
  
def setenv_serverip():
  global serverip

  ret = setenv("serverip", serverip)
  if ret < 0:
    return Err_setenv_serverip
  else:
    return 0
  
def setenv_gatewayip():
  global gatewayip

  ret = setenv("gatewayip", gatewayip)
  if ret < 0:
    return Err_setenv_gatewayip
  else:
    return 0

def ping_server():
  global serverip

  cmd_send = "ping " + serverip
  resp_string = "is alive"
  time_wait = 3
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    return 0
  else:
    return Err_ping_server

def repeat_ping_server(times):
  global res_msg

  for i in range(times):
    ret = ping_server()
    if ret == 0:
      return ret
  
  res_msg = "Err: Failed to ping server with IP addr, {serverip} repeat {times} times"
  return ret

def tftp_server_for_ever(port, tftp_server_dir):
  global server
  global serverip

  server = tftpy.TftpServer(tftp_server_dir)
  server.listen(serverip, port, timeout=0.5, retries=10)

def start_tftp_server(boot_file_path):
  global res_msg
  global serverip
  global tftp_port

  try:
    tftp_server_thread = threading.Thread(target=tftp_server_for_ever, args=(tftp_port, boot_file_path,))
    tftp_server_thread.daemon = True
    tftp_server_thread.start()
  except:
    res_msg = "Error: Failed to start tftp server, {serverip}"
    return Err_start_tftp_server
  return 0

def stop_tftp_server():
  global server
  server.stop()
  return

def booting_linux():
  global res_msg

  resp_string = "Linux version"
  time_wait = 10
  line = scan_expected_resp("", resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to start Linux"
    return Err_linux_start
  
  resp_string = "Please press Enter to activate this console."
  time_wait = 90
  line = scan_expected_resp("", resp_string, time_wait)  
  if line == None:
    res_msg = "Err: Linux running error"
    return Err_linux_running
  
  resp_string = "/ #"
  time_wait = 5
  line = scan_expected_resp("", resp_string, time_wait)  
  if line == None:
    res_msg = "Err: Linux do not ready to receive command"
    return Err_linux_receive_cmd
  
  return 0

def run_tftpboot():
  global s
  global sl
  global tftp_transfer_time
  global res_msg

  s.reset_input_buffer()
  s.timeout = 1

  send_command("run tftpboot")
  timeout = time.time() + tftp_transfer_time

  while True:
    line = s.readline()
    if line:
      sl.log(line, 'DEBUG')

    match = re.search("Starting kernel ...", line.decode('utf-8'))
    if match:
      break
    match = re.search("Retry count exceeded;", line.decode('utf-8'))
    if match:
      res_msg = "Err: Failed to transfer linux files"
      return Err_tftp_file_transfer
  
    if timeout < time.time():
      res_msg = "Err: Timeout {tftp_transfer_time} second when transfer linux files with TFTP"
      return Err_tftp_file_transfer_timeout
    
  return booting_linux()

def ETH_001_TFTP_BOOT_LINUX(boot_file_path):
  global res_msg
    
  ret = detect_CMD_startup()
  if ret < 0:
    return ret
  ret = setenv_ipaddr()
  if ret < 0:
    return ret
  ret = setenv_serverip()
  if ret < 0:
    return ret 
  ret = setenv_gatewayip()
  if ret < 0:
    return ret
  ret = repeat_ping_server(5) # repeat ping 5 times
  if ret < 0:
    return ret
  
  ret = start_tftp_server(boot_file_path)
  if ret < 0:
    return ret 

  ret = run_tftpboot()
  stop_tftp_server()
  if ret < 0:
    return ret 

  res_msg = 'Pass: U-boot boot to Linux with Ethernet TFTP success'
  return 0

def linuxboot(COM, handling_path, boot_file_path):
  global sl
  global res_msg
  global ETH_001_result
  global ETH_001_result_msg
  
  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = Ethernet", 'WARN')

  Open_COMPORT(COM)

  ETH_001_result = ETH_001_TFTP_BOOT_LINUX(boot_file_path)
  ETH_001_result_msg = res_msg
  sl.log("ETH_001_TFTP_BOOT_LINUX " + str(ETH_001_result) + ' ' + ETH_001_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def main():
  current_path = path.dirname( path.abspath(__file__) )
  boot_file_path = current_path + '//boot_file'

  linuxboot('COM4', current_path, boot_file_path)

  return 0

if __name__ == "__main__":
  main()

# pip install tftpy
# FPGA3 Unit 1
# bitfile = 0094 (RTL101)
# Clock 1 24
# Clock 2 24
# Clock 3 40
# Clock 4 12.288
# Clock 5 48
# Clock 6 48
# Clock 7 100
# Clock 8 48

# ETH_001_TFTP_BOOT_LINUX
# 1. Establish connection between server & board throught ethernet
# 2. Set uboot environment variables
# 3. Tftp kernel image, dtb & rootfs from server to board
# 4. Run boot command to boot into Linux
