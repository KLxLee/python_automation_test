import time
import serial
import re
from os import path
import std_func as sf

########################################## Define ############################################
SD_mode_ID = ["0", "2"]
eMMC_mode_ID = ["0", "1", "3", "4", "10", "11"]
SDMMC_speed_mode_name = [
  "MMC legacy",
  "MMC High Speed (26MHz)",
  "SD High Speed (50MHz)",
  "MMC High Speed (52MHz)",
  "MMC DDR52 (52MHz)",
  "UHS SDR12 (25MHz)",
  "UHS SDR25 (50MHz)",
  "UHS SDR50 (100MHz)",
  "UHS DDR50 (50MHz)",
  "UHS SDR104 (208MHz)",
  "HS200 (200MHz)",
  "HS400 (200MHz)",
  "HS400ES (200MHz)"
  ]

FAT_Dummy_File_Name = "dummy.txt"
ext4_root_file_DIR = "/etc/"
ext4_root_file_Name = "profile"
checkerboard_pattern_1 = 'aaaacccc'
checkerboard_pattern_2 = '12345678'
Test_len = '0x2000'
mem_addr1 = "0x50000000"
mem_addr2 = "0x51000000"
mmc_rw_blk = '0'
mmc_rw_cnt = '2'
RPMB_auth_key = ['aaaaaaaa', 'aaaaaaaa', 'aaaaaaaa', 'aaaaaaaa', 'aaaaaaaa'
                 'aaaaaaaa', 'aaaaaaaa', 'aaaaaaaa', 'aaaaaaaa', 'aaaaaaaa']
RPMB_auth_key_mem_addr = '0x52000000'

####################################     Error Number     ####################################
Err_CMD_startup = -10
Err_find_device = -11
Err_select_device = -12
Err_get_speed_mode = -13
Err_set_speed_mode = -14
Err_fatwrite = -15
Err_fileload = -16
Err_mmc_write = -17
Err_mmc_read = -18
Err_test_FAT_FS = -19
Err_test_ext4_FS = -20
Err_test_raw_dat = -21
Err_load_FAT_boot_img = -22
Err_find_dev_ID = -23
Err_boot_part_not_FAT = -24
Err_spl_boot_source = -25
Err_mmc_rpmb_write = -26
Err_mmc_rpmb_read = -27
Err_RPMB_counter = -28
Err_test_rw_rpmb = -29

###################################### Global Variable #######################################
Device_ID_List = []
command_dev_part = ""

Test_ID_Init_Val = -5
SD_001_result = Test_ID_Init_Val
SD_001_result_msg = ''
SD_002_result = Test_ID_Init_Val
SD_002_result_msg = ''

EMMC_001_result = Test_ID_Init_Val
EMMC_001_result_msg = ''
EMMC_002_result = Test_ID_Init_Val
EMMC_002_result_msg = ''

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
def init_mmc():
  global s

  s.reset_input_buffer()
  s.timeout = 2
  send_command("mmc info")
  time.sleep(1)

  total_num_device = 1
  s.reset_input_buffer()
  send_command("mmc list")
  while True:
    line = s.readline()
    sl.log(line, 'DEBUG')
    if len(line) == 0:
      break
    if re.search(": [0-9] ", line.decode('utf-8')):
      total_num_device = total_num_device + 1

  for dev_num in range(total_num_device):
    send_command("mmc dev " + str(dev_num))
    time.sleep(1)

def find_device(dev_type):
  global Device_ID_List
  global s
  global sl
  global res_msg

  s.reset_input_buffer()
  s.timeout = 2

  send_command("mmc list")

  while True:
    line = s.readline()
    sl.log(line, 'DEBUG')
    if len(line) == 0:
      break

    if re.search(dev_type, line.decode('utf-8')): 
      x = re.search(": [0-9] ", line.decode('utf-8'))
      if x == None:
        res_msg = "Err: Cannot get valid device ID of " + dev_type
        return Err_find_device
      else:
         Device_ID_List.append(x.group()[2])

  if not Device_ID_List:
    res_msg = "Err: Do not found any device of " + dev_type
    return Err_find_device
  else:
    return 0

def select_device(DeviceID):
  global res_msg

  cmd_send = "mmc dev " + DeviceID
  resp_string = "mmc" + DeviceID + ".* is current device"
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    return 0
  else:
    res_msg = "Err: Failed to select Device ID, " + DeviceID
    return Err_select_device

def detect_file_system():
  cmd_send = "mmc part"
  time_wait = 2

  resp_string = "\t0b\r\n|\t0c\r\n|\t0c Boot\r\n"
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    Present_PartitionFS = "fat"
    Present_PartitionID = line[2]
    return [Present_PartitionID, Present_PartitionFS]

  resp_string = "\t83\r\n"
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    Present_PartitionFS = "ext4" 
    Present_PartitionID = line[2]
    return [Present_PartitionID, Present_PartitionFS]
  
  Present_PartitionFS = "invalid_fs" 
  Present_PartitionID = "0"
  return [Present_PartitionID, Present_PartitionFS]

def detect_file_system_from_ID(Part_ID):
  cmd_send = "mmc part"
  resp_string = "  " + Part_ID
  time_wait = 2

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
    if re.search("\t0b\r\n|\t0c\r\n|\t0c Boot\r\n", line):
      return "fat"
    if re.search("\t83\r\n", line):
      return "ext4"

  return "invalid_fs" 

def get_speed_mode():
  global SDMMC_speed_mode_name
  global res_msg

  cmd_send = "mmc info"
  resp_string = "Mode: "
  time_wait = 1

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line:
      mode_name = line.replace("Mode: ","").rstrip()
  else:
    res_msg = "Err: Failed to get speed mode info"
    return Err_get_speed_mode
  
  for mode_ID in range(len(SDMMC_speed_mode_name)):
    if SDMMC_speed_mode_name[mode_ID] == mode_name:
      return str(mode_ID)

  res_msg = "Err: Failed to recognise speed mode found"
  return Err_get_speed_mode

def set_speed_mode(mode_ID_set):
  global SDMMC_speed_mode_name
  global res_msg

  send_command("mmc rescan " + mode_ID_set)
  time.sleep(0.5)
  
  mode_ID_get = get_speed_mode()
  if isinstance(mode_ID_get, int):
    return mode_ID_get

  if mode_ID_set == mode_ID_get:
    return 0
  else:
    res_msg = "Err: speed mode set to " + SDMMC_speed_mode_name[int(mode_ID_set)] + " is failed"
    return Err_set_speed_mode

def remove_FAT_file(file_name):
  global command_dev_part
  global res_msg

  send_command("fatrm" + command_dev_part + file_name)
  time.sleep(0.5)

def fatwrite(file_name, mem_addr, data_len):
  global command_dev_part
  global res_msg

  cmd_send = "fatwrite" + command_dev_part + mem_addr + " " + file_name + " " + data_len
  resp_string = " bytes written in "
  time_wait = 10

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to write file to FAT partition " + command_dev_part + " from RAM memory, " + mem_addr
    return Err_fatwrite
  else:
    return 0

def fileload(file_system, file_name, mem_addr):
  global command_dev_part
  global res_msg

  cmd_send = file_system + "load" + command_dev_part + mem_addr + " " + file_name
  resp_string = " bytes read in"
  time_wait = 10

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = "Err: Failed to load file in " + command_dev_part + " with file system, " + file_system + " to RAM memory, " + mem_addr
    return [Err_fileload, "0"]
  else:
    byte_load_int = re.sub('[^0-9]','', line[0:10])
    byte_load_hex = hex(int(byte_load_int))
    return [0, byte_load_hex]

def mmc_write(mem_addr, blk, cnt):
  global res_msg

  cmd_send = "mmc write " + mem_addr + " " + blk + " " + cnt
  resp_string = cnt + " blocks written: OK"
  time_wait = 10

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = 'Err: mmc write raw data in to memory addr, ' + mem_addr
    return Err_mmc_write
  else:
    return 0
  
def mmc_read(mem_addr, blk, cnt):
  global res_msg

  cmd_send = "mmc read " + mem_addr + " " + blk + " " + cnt
  resp_string = cnt + " blocks read: OK"
  time_wait = 10

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = 'Err: mmc read raw data in from memory addr, ' + mem_addr
    return Err_mmc_read
  else:
    return 0

def mmc_rpmb_write(mem_addr, blk, cnt):
  global RPMB_auth_key_mem_addr
  global res_msg
  cmd_send = "mmc rpmb write " + mem_addr + " " + blk + " " + cnt + " " + RPMB_auth_key_mem_addr
  resp_string = cnt + " RPMB blocks written: OK"
  time_wait = 10
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = 'Err: mmc write ' + cnt + ' blocks of data in to RPMB partition'
    return Err_mmc_rpmb_write
  else:
    return 0

def mmc_rpmb_read(mem_addr, blk, cnt):
  global RPMB_auth_key_mem_addr
  global res_msg
  cmd_send = "mmc rpmb read " + mem_addr + " " + blk + " " + cnt + " " + RPMB_auth_key_mem_addr
  resp_string = cnt + " RPMB blocks read: OK"
  time_wait = 10
  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = 'Err: mmc read ' + cnt + ' blocks of data in to RPMB partition'
    return Err_mmc_rpmb_read
  else:
    return 0

def write_memory(addr, data_pattern, data_len):
  cmd_send = "mw.l " + addr + " " + data_pattern + " " + data_len
  send_command(cmd_send)
  time.sleep(1)

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

def from_hex(hexdigits):
    return int(hexdigits, 16)

def write_RPMB_Auth_key_in_memory():
  global RPMB_auth_key
  global RPMB_auth_key_mem_addr

  addr = RPMB_auth_key_mem_addr

  for key in RPMB_auth_key:
    write_memory(addr, key, '1')
    addr = from_hex(addr)
    addr = hex(addr + 4)

def get_RPMB_counter():
  global res_msg

  cmd_send = "mmc rpmb counter "
  resp_string = "RPMB Write counter= "
  time_wait = 3

  line = scan_expected_resp(cmd_send, resp_string, time_wait)
  if line == None:
    res_msg = 'Err: Failed to get RPMB counter'
    return Err_RPMB_counter
  
  counter = line.strip(resp_string)
  counter = ''.join(counter.splitlines())
  
  return from_hex(counter)

def test_FAT_FS():
  global FAT_Dummy_File_Name
  global mem_addr1
  global mem_addr2
  global Test_len
  global res_msg

  remove_FAT_file(FAT_Dummy_File_Name)

  ret = fatwrite(FAT_Dummy_File_Name, mem_addr1, Test_len)
  if ret < 0:
    return ret

  [ret, byte_load] = fileload("fat", FAT_Dummy_File_Name, mem_addr2)
  if ret < 0:
    return ret

  remove_FAT_file(FAT_Dummy_File_Name)
  
  ret = cmp_memory_byte(mem_addr1, mem_addr2, Test_len)
  if ret < 0:
    res_msg = "Err: Write Memory different at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_test_FAT_FS
  
  return 0

def test_ext4_FS():
  global command_dev_part
  global ext4_root_file_DIR
  global ext4_root_file_Name
  global mem_addr1
  global mem_addr2
  global res_msg

  file_name = ext4_root_file_DIR + ext4_root_file_Name

  [ret, byte_load] = fileload("ext4", file_name, mem_addr1)
  if ret < 0:
    return ret
  
  [ret, byte_load] = fileload("ext4", file_name, mem_addr2)
  if ret < 0:
    return ret

  ret = cmp_memory_byte(mem_addr1, mem_addr2, byte_load)
  if ret < 0:
    res_msg = "Err: Write Memory different at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_test_ext4_FS
  
  return 0

def test_raw_dat(data_pattern):
  global mem_addr1
  global mem_addr2
  global mmc_rw_blk
  global mmc_rw_cnt
  global res_msg

  byte_len = (int(mmc_rw_cnt) * 512)
  byte_len_hex = hex(byte_len)
  long_len_hex = hex(int(byte_len/4))

  write_memory(mem_addr1, data_pattern, long_len_hex)

  ret = mmc_write(mem_addr1, mmc_rw_blk, mmc_rw_cnt)
  if ret < 0:
    return ret

  ret = mmc_read(mem_addr2, mmc_rw_blk, mmc_rw_cnt)
  if ret < 0:
    return ret

  ret = cmp_memory_byte(mem_addr1, mem_addr2, byte_len_hex)
  if ret < 0:
    res_msg = "Err: Write Memory different at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_test_raw_dat

  return 0

def test_rw_rpmb(data_pattern):
  global mem_addr1
  global mem_addr2
  global mmc_rw_blk
  global mmc_rw_cnt
  global res_msg

  byte_len = (int(mmc_rw_cnt) * 256) # RPMB block size is 256 bytes
  byte_len_hex = hex(byte_len)
  long_len_hex = hex(int(byte_len/4))

  write_memory(mem_addr1, data_pattern, long_len_hex)

  RPMB_counter_before = get_RPMB_counter()

  ret = mmc_rpmb_write(mem_addr1, mmc_rw_blk, mmc_rw_cnt)
  if ret < 0:
    return ret

  ret = mmc_rpmb_read(mem_addr2, mmc_rw_blk, mmc_rw_cnt)
  if ret < 0:
    return ret

  ret = cmp_memory_byte(mem_addr1, mem_addr2, byte_len_hex)
  if ret < 0:
    res_msg = "Err: Write Memory different at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_test_rw_rpmb

  RPMB_counter_after = get_RPMB_counter()

  if RPMB_counter_after != (RPMB_counter_before + from_hex(mmc_rw_cnt)):
    res_msg = "Err: RPMB counter after written " + mmc_rw_cnt + " blocks is " + str(RPMB_counter_after) + " but RPMB counter before written is " + str(RPMB_counter_before)
    return Err_RPMB_counter
  
  return 0

def SDMMC_SCAN_DEV(dev_type):
  global res_msg

  ret = detect_CMD_startup()
  if ret != 0:
    return ret
  
  init_mmc()
  ret = find_device(dev_type)
  if ret != 0:
    return ret
  
  res_msg = "Pass: " + dev_type + " device found"
  return 0

def SD_001_SCAN_DEV():
  return SDMMC_SCAN_DEV('SD')

def EMMC_001_SCAN_DEV():
  return SDMMC_SCAN_DEV('eMMC')

def SDMMC_RW_ALL_MODE(mode_ID_list):
  global command_dev_part
  global checkerboard_pattern_1
  global checkerboard_pattern_2

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  init_mmc()
  for DeviceID in Device_ID_List:
    ret = select_device(DeviceID) 
    if ret < 0:
      return ret

    [Part_ID, Part_FS] = detect_file_system()
    command_dev_part = " mmc " + DeviceID + ":" + Part_ID + " "

    for speed_mode_ID in mode_ID_list:
      ret = set_speed_mode(speed_mode_ID)
      if ret < 0:
        return ret

      if Part_FS == "fat":
        ret = test_FAT_FS()        
      elif Part_FS == "ext4":
        ret = test_ext4_FS()
      else:
        ret = test_raw_dat(checkerboard_pattern_1)
        if ret < 0:
          return ret
        ret = test_raw_dat(checkerboard_pattern_2)
      
      if ret < 0:
        return ret
    
  return 0

def SD_002_RW_ALL_MODE():
  global SD_mode_ID
  global res_msg

  ret = SDMMC_RW_ALL_MODE(SD_mode_ID)
  if ret < 0:
    return ret
  res_msg = "Pass: Read Write data to SD card with all speed mode success"
  return 0

def EMMC_002_RW_ALL_MODE():
  global eMMC_mode_ID
  global res_msg

  ret = SDMMC_RW_ALL_MODE(eMMC_mode_ID)
  if ret < 0:
    return ret
  res_msg = "Pass: Read Write data to eMMC with all speed mode success"
  return 0

def sdmmc_load_FAT_boot_img(dev_type, dev='0', part='1', img_addr='0xa0000000', img_name='u-boot.itb', data_len='1000000'):
  global Device_ID_List
  global command_dev_part
  global res_msg
  valid_mem = '0x44000000'

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  init_mmc()
  ret = find_device(dev_type)
  if ret != 0:
    return ret
  if dev not in Device_ID_List:
    res_msg = "Err: Device " + dev + " is not recognized as " + dev_type
    return Err_find_dev_ID
  ret = select_device(dev)
  if ret < 0:
    return ret
  
  Part_FS = detect_file_system_from_ID(part)
  if Part_FS != 'fat':
    res_msg = "Err: Device " + dev + " partition " + part + " is not FAT file system"
    return Err_boot_part_not_FAT

  command_dev_part = " mmc " + dev + ":" + part + " "
  
  data_len_hex = hex(int(data_len))

  remove_FAT_file(img_name)

  ret = fatwrite(img_name, img_addr, data_len_hex)
  if ret < 0:
    return ret

  [ret, byte_load] = fileload("fat", img_name, valid_mem)
  if ret < 0:
    return ret
  
  ret = cmp_memory_byte(img_addr, valid_mem, data_len_hex)
  if ret < 0:
    res_msg = "Err: Write Memory different at addr1, " + mem_addr1 + " and addr2, " + mem_addr2
    return Err_load_FAT_boot_img

  res_msg = "Pass: "
  return 0

def SD_003_LOAD_FAT_UBOOT_IMG(dev, part, img_addr, img_name, data_len):
  return sdmmc_load_FAT_boot_img('SD', dev, part, img_addr, img_name, data_len)

def EMMC_003_LOAD_FAT_UBOOT_IMG(dev, part, img_addr, img_name, data_len):
  return sdmmc_load_FAT_boot_img('eMMC', dev, part, img_addr, img_name, data_len)

def sdmmc_splboot():
  global res_msg

  resp_string = "Trying to boot from MMC"
  time_wait = 5
  if not scan_expected_resp("", resp_string, time_wait): 
    res_msg = "Err: SPL Boot source type is not MMC"
    return Err_spl_boot_source

  time_wait = 25
  if not scan_expected_resp("", "StarFive #", time_wait): 
    res_msg = "Err: Uboot is not ready for receiving command"
    return Err_CMD_startup

  res_msg = "Pass: SPL BOOT from MMC success"
  return 0

def SD_004_SPLBOOT():
  return sdmmc_splboot()

def EMMC_004_SPLBOOT():
  return sdmmc_splboot()

def EMMC_RW_RPMB_ALL_MODE(mode_ID_list):
  global checkerboard_pattern_1
  global checkerboard_pattern_2

  ret = detect_CMD_startup()
  if ret != 0:
    return ret

  init_mmc()
  ret = find_device('eMMC')
  if ret != 0:
    return ret
  
  write_RPMB_Auth_key_in_memory()

  for DeviceID in Device_ID_List:
    ret = select_device(DeviceID) 
    if ret < 0:
      return ret

    for speed_mode_ID in mode_ID_list:
      ret = set_speed_mode(speed_mode_ID)
      if ret < 0:
        return ret

      ret = test_rw_rpmb(checkerboard_pattern_1)
      if ret < 0:
        return ret
      
      ret = test_rw_rpmb(checkerboard_pattern_2)
      if ret < 0:
        return ret

  return 0

def EMMC_005_RW_RPMB_ALL_MODE():
  global eMMC_mode_ID
  global res_msg

  ret = EMMC_RW_RPMB_ALL_MODE(eMMC_mode_ID)
  if ret < 0:
    return ret

  res_msg = "Pass: Read Write data to eMMC RPMB parition with all speed mode success"
  return 0

def SD_basic_test(COM, handling_path):
  global sl
  global res_msg
  global SD_001_result
  global SD_001_result_msg
  global SD_002_result
  global SD_002_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = SD", 'WARN')

  Open_COMPORT(COM)

  SD_001_result = SD_001_SCAN_DEV()
  SD_001_result_msg = res_msg
  sl.log("SD_001_SCAN_DEV " + str(SD_001_result) + ' ' + SD_001_result_msg, 'WARN')
  SD_002_result = SD_002_RW_ALL_MODE()
  SD_002_result_msg = res_msg
  sl.log("SD_002_RW_ALL_MODE " + str(SD_002_result) + ' ' + SD_002_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def EMMC_basic_test(COM, handling_path):
  global sl
  global res_msg
  global EMMC_001_result
  global EMMC_001_result_msg
  global EMMC_002_result
  global EMMC_002_result_msg

  sl = sf.test_log(handling_path, console=False)
  sl.log("IP = EMMC", 'WARN')

  Open_COMPORT(COM)

  EMMC_001_result = EMMC_001_SCAN_DEV()
  EMMC_001_result_msg = res_msg
  sl.log("EMMC_001_SCAN_DEV " + str(EMMC_001_result) + ' ' + EMMC_001_result_msg, 'WARN')
  EMMC_002_result = EMMC_002_RW_ALL_MODE()
  EMMC_002_result_msg = res_msg
  sl.log("EMMC_002_RW_ALL_MODE " + str(EMMC_002_result) + ' ' + EMMC_002_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def SD_load_FAT_uboot_img(COM, handling_path, dev='0', part='1', img_addr='0xa0000000', img_name='u-boot.itb', data_len='1000000'):
  global sl
  global res_msg
  global SD_003_result
  global SD_003_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  SD_003_result = SD_003_LOAD_FAT_UBOOT_IMG(dev, part, img_addr, img_name, data_len)
  SD_003_result_msg = res_msg
  sl.log("SD_003_LOAD_FAT_UBOOT_IMG " + str(SD_003_result) + ' ' + SD_003_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def EMMC_load_FAT_uboot_img(COM, handling_path, dev='0', part='1', img_addr='0xa0000000', img_name='u-boot.itb', data_len='1000000'):
  global sl
  global res_msg
  global EMMC_003_result
  global EMMC_003_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  EMMC_003_result = EMMC_003_LOAD_FAT_UBOOT_IMG(dev, part, img_addr, img_name, data_len)
  EMMC_003_result_msg = res_msg
  sl.log("EMMC_003_LOAD_FAT_UBOOT_IMG " + str(EMMC_003_result) + ' ' + EMMC_003_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def SD_spl_boot(COM, handling_path):
  global sl
  global res_msg
  global SD_004_result
  global SD_004_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  SD_004_result = SD_004_SPLBOOT()
  SD_004_result_msg = res_msg
  sl.log("SD_004_SPLBOOT " + str(SD_004_result) + ' ' + SD_004_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def EMMC_spl_boot(COM, handling_path):
  global sl
  global res_msg
  global EMMC_004_result
  global EMMC_004_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  EMMC_004_result = EMMC_004_SPLBOOT()
  EMMC_004_result_msg = res_msg
  sl.log("EMMC_004_SPLBOOT " + str(EMMC_004_result) + ' ' + EMMC_004_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def EMMC_add_on_test(COM, handling_path):
  global sl
  global res_msg
  global EMMC_005_result
  global EMMC_005_result_msg

  sl = sf.test_log(handling_path, console=False)

  Open_COMPORT(COM)

  EMMC_005_result = EMMC_005_RW_RPMB_ALL_MODE()
  EMMC_005_result_msg = res_msg
  sl.log("EMMC_005_RW_RPMB_ALL_MODE " + str(EMMC_005_result) + ' ' + EMMC_005_result_msg, 'WARN')

  Close_COMPORT()
  sl.close()

def main():
  current_path = path.dirname( path.abspath(__file__) )

  SD_basic_test('COM4', current_path)

  return 0

if __name__ == "__main__":
  main()

# python3 "C:\Users\MDC_FPGA_3\Documents\kllee\uboot_script_FPGA.py"
# bitfile = 0060, 0082, 0093

# SD_001_SCAN_DEV
# 1. Scan for SD and number of device

# SD_002_RW_ALL_MODE
# 1. Write a dummy file into SD from memory_1
# 2. Load the dummy file from SD to memory_2
# 3. Compare both memory data and suppose to be same
# 4. Repeat the test on all speed mode.
# 5. Repeat the step above on all device

# SD_003_LOAD_FAT_UBOOT_IMG
# 1. Probe the SD device selected. 
# 2. Detetmine the partition selected is FAT.
# 3. Write or overwrite file name, 'u-boot.itb' into the SD device-partition from RAM
# 4. Read the file from SD and makesure the data of read and write are the same.

# SD_004_SPLBOOT
# 1. Reload another SPL MMC boot image.
# 2. Detect uboot success enter prompt.

# EMMC_001_SCAN_DEV
# 1. Scan for eMMC and number of device

# EMMC_002_RW_ALL_MODE
# 1. Write a dummy file into eMMC from memory_1
# 2. Load the dummy file from eMMC to memory_2
# 3. Compare both memory data and suppose to be same
# 4. Repeat the test on all speed mode.
# 5. Repeat the step above on all device

# EMMC_003_LOAD_FAT_UBOOT_IMG
# 1. Probe the eMMC device selected. 
# 2. Detetmine the partition selected is FAT.
# 3. Write or overwrite file name, 'u-boot.itb' into the eMMC device-partition from RAM
# 4. Read the file from eMMC and makesure the data of read and write are the same.

# EMMC_004_SPLBOOT
# 1. Reload another SPL MMC boot image.
# 2. Detect uboot success enter prompt.