import re
import os
import logging
import subprocess
import shutil
from subprocess import Popen

def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(message)s')
    fileHandler = logging.FileHandler(log_file, mode='a')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)    

class test_log:
    def __init__(self, handling_path, console=False):
        self.console = console
        log_path = handling_path + '\\log'

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        detail_log_path = log_path + '\\detail.log'
        setup_logger('detail_log', detail_log_path, level=logging.DEBUG)
        self.detail_logger = logging.getLogger('detail_log')
        summary_log_path = log_path + '\\summary.log'
        setup_logger('summary_log', summary_log_path, level=logging.WARNING)
        self.summary_logger = logging.getLogger('summary_log')

    def log(self, message, level='DEBUG'):
        if level == 'DEBUG':
            self.detail_logger.debug(message)
            self.summary_logger.debug(message)
        elif level == 'INFO':
            self.detail_logger.info(message)
            self.summary_logger.info(message)
        elif level == 'WARN':
            self.detail_logger.warning(message)
            self.summary_logger.warning(message)
        elif level == 'ERROR':
            self.detail_logger.error(message)
            self.summary_logger.error(message)
        else:
            self.detail_logger.critical(message)
            self.summary_logger.critical(message)
        
        if self.console == True:
           print(message)
           print('\n')

    def close(self):
        handlers = self.detail_logger.handlers[:]
        for handler in handlers:
            self.detail_logger.removeHandler(handler)
            handler.close()
        handlers = self.summary_logger.handlers[:]
        for handler in handlers:
            self.summary_logger.removeHandler(handler)
            handler.close()

####################################### RUN TEST USE #######################################
def load_uboot(build_path, load_time):
    # load u-boot bin file
    config_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = config_path + "\\" + "riscv_gdb_path.txt"
    f2 = open(file_path, "r")
    gdb_path = f2.readline().rstrip('\r\n')
    f2.close()

    current_path = os.path.dirname(os.path.abspath(__file__))
    bat_path = current_path + "\\bat\\" + "load_bin.bat " + load_time + " " + gdb_path + " " + build_path
    p = Popen(bat_path)
    stdout, stderr = p.communicate()

def load_uboot_endtask():
    # kill gdb and openocd
    current_path = os.path.dirname(os.path.abspath(__file__))
    bat_path = current_path + "\\bat\\" + "load_bin_endtask.bat"
    p = Popen(bat_path)
    stdout, stderr = p.communicate()

def program_FPGA(build_path):
    # change dir.txt content to current bit_file dir
    config_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = config_path + "\\" + "auto_FPGA_path.txt"
    f2 = open(file_path, "r")
    path = f2.readline().rstrip('\r\n')
    f2.close()

    f = open(path+"/dir.txt", "w")
    f.write(build_path)
    f.close()

    # start to call python script to program FPGA
    subprocess.run(["python", path+"/test_config.py"])

def get_comport_number(num):
    COMPORT_NUM = ''
    config_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = config_path + "\\" + "comport_config.txt"
    f = open(file_path, "r")
    while True:
        line = f.readline()
        if len(line) == 0:
            break
        if num == 1:
            match = re.search("1 = ....", line)
            if match: 
                COMPORT_NUM = line[14:].rstrip('\r\n')
        if num == 2:
            match = re.search("2 = ....", line)
            if match: 
                COMPORT_NUM = line[14:].rstrip('\r\n')
    f.close()

    return COMPORT_NUM

def backup_old_log(handling_path):
    source_path = handling_path + '\\log'
    backup_path = handling_path + '\\log\\log_old'

    if os.path.exists(source_path):
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)
        os.mkdir(backup_path)

        for file in os.listdir(source_path):
            if file.endswith('.log') or file.endswith('.txt'):
                shutil.move(source_path+'\\'+file, backup_path+'\\'+file)

    else:
        os.mkdir(source_path)
        os.mkdir(backup_path)
