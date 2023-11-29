from jsonschema import validate
import json
import os
import s2c
import yaml
import time
from os import path

class FPGA_param:
    def __init__(self, fpga_data, testName):
        self.testName = testName
        data = fpga_data[testName]
        self.power_1_8V    = data['fpga']['power_1_8V']
        self.power_3_3V    = data['fpga']['power_3_3V']
        self.power_5_0V    = data['fpga']['power_5_0V']
        self.s2c_clk_1     = data['fpga']['S2CCLK_1']
        self.s2c_clk_2     = data['fpga']['S2CCLK_2']
        self.s2c_clk_3     = data['fpga']['S2CCLK_3']
        self.s2c_clk_4     = data['fpga']['S2CCLK_4']
        self.s2c_clk_5     = data['fpga']['S2CCLK_5']
        self.s2c_clk_6     = data['fpga']['S2CCLK_6']
        self.s2c_clk_7     = data['fpga']['S2CCLK_7']
        self.s2c_clk_8     = data['fpga']['S2CCLK_8']
        self.bitfile_fpga1 = data['fpga']['bitfile_fpga1']
        self.bitfile_fpga2 = data['fpga']['bitfile_fpga2']
        self.power_fpga1   = self.bitfile_fpga1 != None
        self.power_fpga2   = self.bitfile_fpga2 != None

def getWorkingDir(file_location):
    file = open(file_location)
    return file.readline().strip()

if __name__ == '__main__':
    pprohome = os.getenv('RTHome')
    workdir = os.getenv('S2C_WORKDIR')
    s2c_ip = os.getenv('S2C_IP')
    s2c_pwr_ctrl_ip = os.getenv('S2C_PWR_CTRL_IP')
    hostname = os.getenv('S2C_HOSTNAME')
    print("pprohome: " + pprohome)
    print("workdir: " + workdir)
    print("s2c_ip: " + s2c_ip)
    print("s2c_pwr_ctrl_ip:" + s2c_pwr_ctrl_ip)
    print("hostname: " + hostname)

    ppro = s2c.S2cPlayerPro(pprohome, workdir, hostname, s2c_ip, s2c_pwr_ctrl_ip)

    current_dir = path.dirname( path.abspath(__file__) )
    working_path = getWorkingDir(current_dir + "\\dir.txt")
    print("current_dir: " + current_dir)
    print("working path: " + working_path)
    os.system("type " + working_path + "\\test_config.yml")

    with open(working_path + "\\test_config.yml") as file:
        data = yaml.load(file, yaml.SafeLoader)

    with open(current_dir + "\\test_config.json") as schema_file:
        schema = json.load(schema_file)
        validate(data, schema)

    for testName in data.keys():
        print("Running " + testName)
        fpga = FPGA_param(data, testName)
        ppro.set_power(fpga.power_fpga1, fpga.power_fpga2, fpga.power_1_8V, fpga.power_3_3V, fpga.power_5_0V)
        ppro.set_clock(fpga.s2c_clk_1,
                       fpga.s2c_clk_2,
                       fpga.s2c_clk_3,
                       fpga.s2c_clk_7,
                       fpga.s2c_clk_4,
                       fpga.s2c_clk_5,
                       fpga.s2c_clk_6,
                       fpga.s2c_clk_8)
        ppro.download_bit(f1=fpga.bitfile_fpga1, f2=fpga.bitfile_fpga2)
        os.system(working_path + "\\" + testName + ".bat")
