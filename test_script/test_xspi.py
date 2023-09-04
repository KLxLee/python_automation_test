import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
Mem_addr_write = "0xa0000000"
Mem_addr_read = "0x44000000"
checkerboard_pattern_1 = 'aaaacccc'
checkerboard_pattern_2 = '12345678'
Flash_Basic_Addr = "0x0"
Flash_Cross_Boundary_Addr = "0xfff000"
Test_len = "0x2000"
Result_CRC_Erased = "b4293435"

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_xspi_probe = -11
Err_basic_destructive_test = -12
Err_protect_flash = -13
Err_xspi_erase_flash = -14
Err_xspi_read_flash = -15
Err_xspi_write_flash = -16
Err_do_crc = -17
Err_crc_result = -18
Err_cmp_memory_byte_result = -19
Err_spl_boot_source = -20

###################################### Global Variable #######################################
Test_ID_Init_Val = -5
XSPI_001_result = Test_ID_Init_Val
XSPI_001_result_msg = ''
XSPI_002_result = Test_ID_Init_Val
XSPI_002_result_msg = ''
XSPI_003_result = Test_ID_Init_Val
XSPI_003_result_msg = ''
XSPI_004_result = Test_ID_Init_Val
XSPI_004_result_msg = ''
XSPI_005_result = Test_ID_Init_Val
XSPI_005_result_msg = ''

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
# sf probe 1:0
# SF: Detected gd25lq256d with page size 256 Bytes, erase size 4 KiB, total 32 MiB
def xspi_probe(bus, cs):
  global res_msg

  cmd_send = "sf probe " + bus + ":" + cs
  resp_string = "SF: Detected "
  time_wait = 1
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to probe flash memory"
    return Err_xspi_probe
  else:
    return 0

# sf protect lock 0 0x2000000
# sf protect unlock 0 0x2000000
def xspi_protect(lock, flash_addr):
  if lock:
    send_command("sf protect lock " + flash_addr + " 0x2000000")
  else: 
    send_command("sf protect unlock " + flash_addr + " 0x2000000")
  time.sleep(0.2)

# sf test 0x0 0x10000
# Test passed
# If protected, Test failed
def basic_destructive_test(flash_addr, len):
  global res_msg

  cmd_send = "sf test " + flash_addr + " " + len
  resp_string = "Test passed"
  time_wait = 20

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Basic Destructive Test flash addr " + flash_addr + " with length " + len
    return Err_basic_destructive_test
  else:
    return 0

# sf erase 0 +0x5000
# SF: 20480 bytes @ 0x0 Erased: OK
def xspi_erase_flash(flash_addr, len, lock_state=False):
  global res_msg

  cmd_send = "sf erase " + " " + flash_addr + " +" + len
  resp_string = "Erased: OK|ERROR: flash area is locked"
  time_wait = 20
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)

  if line == None:
    res_msg = "Err: Erase flash addr " + flash_addr + " with length " + len
    return Err_xspi_erase_flash

  if lock_state == True:
    match = re.search("is locked", line)
    if match == None:
      res_msg = "Err: Lock memory failed. Memory address, " + flash_addr + " with length " + len + " is still unlocked after protected flash"
      return Err_protect_flash
  else:
    match = re.search("Erased: OK", line)
    if match == None:
      res_msg = "Err: Unlock memory failed. Memory address, " + flash_addr + " with length " + len + " is still locked after unprotected flash"
      return Err_protect_flash

  return 0

# sf read 0xc0000000 0xfff000 0x2000
# device 0 offset 0xfff000, size 0x2000
# SF: 8192 bytes @ 0xfff000 Read: OK
def xspi_read_flash(mem_addr, flash_addr, len):
  global res_msg

  cmd_send = "sf read " + mem_addr + " " + flash_addr + " " + len
  resp_string = "Read: OK"
  time_wait = 20
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Read flash addr " + flash_addr + " with length " + len + " to memmory addr " + mem_addr
    return Err_xspi_read_flash
  else:
    return 0

# sf write 0xc0000000 0xfff000 0x2000
# device 0 offset 0xfff000, size 0x2000
# SF: 8192 bytes @ 0xfff000 Written: OK
def xspi_write_flash(mem_addr, flash_addr, len):
  global res_msg

  cmd_send = "sf write " + mem_addr + " " + flash_addr + " " + len
  resp_string = "Written: OK"
  time_wait = 20
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Read flash addr " + flash_addr + " with length " + len + " to memmory addr " + mem_addr
    return Err_xspi_write_flash
  else:
    return 0

def from_hex(hexdigits):
    return int(hexdigits, 16)

def write_memory(addr, data_pattern, len):
  cmd_send = "mw.l " + addr + " " + data_pattern + " " + len
  send_command(cmd_send)
  time.sleep(1)

def do_crc(mem_addr, len):
  global res_msg
  
  cmd_send = "crc32 " + mem_addr + " " + len
  resp_string = "==> ........"
  time_wait = 5

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Do crc error"
    return Err_do_crc
  
  x = re.search(resp_string, line)
  return x.group().strip("==> ")

def cmp_memory_byte(addr1, addr2, len):
  len_dec = str(int(len, 16))
  cmd_send = "cmp.b " + addr1 + " " + addr2 + " " + len
  resp_string = "Total of " + len_dec + " byte"
  time_wait = 10
  
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    return -1
  else: 
    return 0

def ewr_test(bus, cs, flash_addr):
  global Mem_addr_write
  global Mem_addr_read
  global checkerboard_pattern_1
  global checkerboard_pattern_2
  global Test_len
  global res_msg

  ret = detect_CMD_startup()
  if ret < 0:
    return ret

  ret = xspi_probe(bus, cs)
  if ret < 0:
    return ret

  ret = xspi_erase_flash(flash_addr, Test_len)
  if ret < 0:
    return ret
  
  ret = xspi_read_flash(Mem_addr_read, flash_addr, Test_len)
  if ret < 0:
    return ret
  
  crc_erased = do_crc(Mem_addr_read, Test_len)
  if isinstance(crc_erased, (int)):
    return crc_erased
  if crc_erased != Result_CRC_Erased:
    res_msg = "Err: CRC result for erased data at basic memory wrong"
    return Err_crc_result

  byte_len = from_hex(Test_len)
  Test_len_long = hex(int(byte_len/4))
  write_memory(Mem_addr_write, checkerboard_pattern_1, Test_len_long)
  write_memory(Mem_addr_read, checkerboard_pattern_2, Test_len_long)

  ret = xspi_write_flash(Mem_addr_write, Flash_Basic_Addr, Test_len)
  if ret < 0:
    return ret

  ret = xspi_read_flash(Mem_addr_read, Flash_Basic_Addr, Test_len)
  if ret < 0:
    return ret

  ret = cmp_memory_byte(Mem_addr_read, Mem_addr_write, Test_len)
  if ret < 0:
    res_msg = "Err: Memory read at " + Mem_addr_read + " is different with memory write at " + Mem_addr_write
    return Err_cmp_memory_byte_result
  
  res_msg = "Pass: "
  return 0

def XSPI_001_PROTECT_BASIC_TEST(bus, cs):
  global Flash_Basic_Addr
  global Test_len
  global res_msg

  ret = detect_CMD_startup()
  if ret < 0:
    return ret

  ret = xspi_probe(bus, cs)
  if ret < 0:
    return ret

  ret = basic_destructive_test(Flash_Basic_Addr, Test_len)
  if ret < 0:
    return ret

  xspi_protect(1, Flash_Basic_Addr)
  ret = xspi_erase_flash(Flash_Basic_Addr, Test_len, True)
  if ret < 0:
    return ret

  xspi_protect(0, Flash_Basic_Addr)
  ret = xspi_erase_flash(Flash_Basic_Addr, Test_len)
  if ret < 0:
    return ret

  res_msg = "Pass: "
  return 0

def XSPI_002_ERASE_READ_WRITE(bus, cs):
  global Flash_Basic_Addr

  return ewr_test(bus, cs, Flash_Basic_Addr)

def XSPI_003_CROSS_BOUNDARY(bus, cs):
  global Flash_Cross_Boundary_Addr

  return ewr_test(bus, cs, Flash_Cross_Boundary_Addr)

def XSPI_004_LOAD_UBOOT_IMG(bus, cs, img_addr, flash_off, file_size):
  global Mem_addr_read
  global res_msg

  file_size_hex = hex(int(file_size))

  ret = detect_CMD_startup()
  if ret < 0:
    return ret

  ret = xspi_probe(bus, cs)
  if ret < 0:
    return ret

  ret = xspi_erase_flash(flash_off, file_size_hex)
  if ret < 0:
    return ret
  
  ret = xspi_write_flash(img_addr, flash_off, file_size_hex)
  if ret < 0:
    return ret

  ret = xspi_read_flash(Mem_addr_read, flash_off, file_size_hex)
  if ret < 0:
    return ret

  ret = cmp_memory_byte(Mem_addr_read, img_addr, file_size_hex)
  if ret < 0:
    res_msg = "Err: Memory read at " + Mem_addr_read + " is different with memory write at " + img_addr
    return Err_cmp_memory_byte_result

  res_msg = "Pass: Success to load uboot image from RAM address "  + img_addr + " to XSPI flash with offset" + flash_off + ", size " + file_size + " bytes"
  return 0

def XSPI_005_SPLBOOT():
  global res_msg

  resp_string = "Trying to boot from SPI"
  time_wait = 5
  if not scan_expected_resp("", resp_string, time_wait): 
    res_msg = "Err: SPL Boot source type is not SPI"
    return Err_spl_boot_source

  time_wait = 25
  if not scan_expected_resp("", "StarFive #", time_wait): 
    res_msg = "Err: Uboot is not ready for receiving command"
    return Err_CMD_startup

  res_msg = "Pass: SPL BOOT from SPI success"
  return 0

def run_test(COM, handling_path, busnum, chipsel):
  global sl
  global res_msg
  global XSPI_001_result
  global XSPI_001_result_msg
  global XSPI_002_result
  global XSPI_002_result_msg
  global XSPI_003_result
  global XSPI_003_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = XSPI", 'WARN')

  Open_COMPORT(COM)

  XSPI_001_result = XSPI_001_PROTECT_BASIC_TEST(busnum, chipsel)
  XSPI_001_result_msg = res_msg
  sl.log("XSPI_001_PROTECT_BASIC_TEST " + str(XSPI_001_result) + ' ' + XSPI_001_result_msg, 'WARN')
  XSPI_002_result = XSPI_002_ERASE_READ_WRITE(busnum, chipsel)
  XSPI_002_result_msg = res_msg
  sl.log("XSPI_002_ERASE_READ_WRITE " + str(XSPI_002_result) + ' ' + XSPI_002_result_msg, 'WARN')
  XSPI_003_result = XSPI_003_CROSS_BOUNDARY(busnum, chipsel)
  XSPI_003_result_msg = res_msg
  sl.log("XSPI_003_CROSS_BOUNDARY " + str(XSPI_003_result) + ' ' + XSPI_003_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def xspi_load_uboot_img(COM, handling_path, busnum, chipsel, img_addr='0xa0000000', flash_off='0', file_size='1000000'):
  global sl
  global res_msg
  global XSPI_004_result
  global XSPI_004_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  XSPI_004_result = XSPI_004_LOAD_UBOOT_IMG(busnum, chipsel, img_addr, flash_off, file_size)
  XSPI_004_result_msg = res_msg
  sl.log("XSPI_004_LOAD_UBOOT_IMG " + str(XSPI_004_result) + ' ' + XSPI_004_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def spl_boot(COM, handling_path):
  global sl
  global res_msg
  global XSPI_005_result
  global XSPI_005_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  XSPI_005_result = XSPI_005_SPLBOOT()
  XSPI_005_result_msg = res_msg
  sl.log("XSPI_005_SPLBOOT " + str(XSPI_005_result) + ' ' + XSPI_005_result_msg, 'WARN')

def main():
  current_path = path.dirname( path.abspath(__file__) )

  run_test('COM12', current_path)

  return 0

if __name__ == "__main__":
  main()

# Send Command: "mw.l 0x10000004 0x00001020" manually to solve RTL083 UART0 error
# bitfile = 0063 RTL083
# Clock 1 24
# Clock 2 50
# Clock 3 16
# Clock 4 12.288
# Clock 5 200
# Clock 6 48
# Clock 7 100
# Clock 8 48

# If test error may need to power cycle flash IC

# XSPI_001_PROTECT_BASIC_TEST
# 1. Lock a region of SPI flash memory with spi protect lock command
# 2. Do basic destructive test to makesure result is failed
# 3. Unlock that region of SPI flash memory with spi protect unlock command
# 4. Do basic destructive test to makesure result is successed

# XSPI_002_ERASE_READ_WRITE
# 1. Erase a region of SPI flash memory
# 2. Read from that region of SPI flash memory and do CRC to make sure the contents are erased
# 3. Write data to Flash from RAM of address 1.
# 4. Read data from Flash to RAM of address 2.
# 5. Perform CRC to makesure data at both RAM are same.

# XSPI_003_CROSS_BOUNDARY
# 1. Erase a region of SPI flash memory
# 2. Read from that region of SPI flash memory and do CRC to make sure the contents are erased
# 3. Write data to Flash from RAM of address 1. Make sure the data is written from bank 0 to bank 1 (cross the boundary of 16MB or 0x100 0000)
# 4. Read data from Flash to RAM of address 2.
# 5. Perform CRC to makesure data at both RAM are same.

# XSPI_004_LOAD_UBOOT_IMG
# 1. Probe flash via XSPI
# 2. Erase and write the flash from RAM u-boot.itb image 
# 3. Read the image from flash and makesure the data of read and write are the same.

# XSPI_005_SPLBOOT
# 1. Reload another SPL SPI boot image.
# 2. Detect uboot success enter prompt.