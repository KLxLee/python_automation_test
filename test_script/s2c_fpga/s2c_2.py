import sys, os, subprocess, threading, time
from utils import Decorator, Util

class S2cFpga:
    LS_VU19P  = 'SINGLE_VU19P'
    LS_2VU19P = 'DUAL_VU19P'

    class Board:
        def __init__(self, targetFamily, module, fpga_cnt, s2cdownload, power_main='J6', power_front_5v='J8'):
            self.targetFamily   = targetFamily
            self.module         = module
            self.fpga_cnt       = fpga_cnt
            self.s2cdownload    = s2cdownload
            self.power_main     = power_main
            self.power_front_5v = power_front_5v
    CONFIGS = {
        LS_VU19P :Board('VU Prodigy Logic System', 'Single VU19P Prodigy Logic System', 1, 's2cdownload_vuls'),
        LS_2VU19P:Board('VU Prodigy Logic System', 'Dual VU19P Prodigy Logic System'  , 2, 's2cdownload_vuls'),
    }

    def __init__(self, hostname, hostip, boardtype, connection='', ip='', pwrctrl_ip=''):
        self.hostname   = hostname
        self.hostip     = hostip
        self.boardtype  = boardtype
        self.connection = connection
        self.ip         = ip
        self.pwrctrl_ip = pwrctrl_ip
        self.board      = S2cFpga.CONFIGS[boardtype]

    def get_hostname(self):
        return self.hostname

    def get_hostip(self):
        return self.hostip

    def get_boardtype(self):
        return self.boardtype

    def get_connection(self):
        return self.connection

    def get_ip(self):
        return self.ip

    def get_pwrctrl_ip(self):
        return self.pwrctrl_ip

    def get_fpga_cnt(self):
        return self.board.fpga_cnt

    def get_targetFamily(self):
        return self.board.targetFamily

    def get_module(self):
        return self.board.module

    def get_s2cdownload(self):
        return self.board.s2cdownload

class S2cPlayerPro:
    @Decorator.logit
    def __init__(self, pprohome, workdir, hostname, ip='', pwrctrl_ip=''):
        self.s2chome  = os.path.join(workdir, '.s2chome')
        self.pprohome = pprohome
        Util.append_env('PATH', os.path.join(pprohome,'bin','tools'))
        Util.append_env('PATH', os.path.join(pprohome,'firmware', 'bin'))
        self.S2C_HardWare = 'S2C_HardWare'
        self.S2C_CPanel   = 'S2C_CPanel'
        self.s2cdownload  = 's2cdownload_vuls'
        self.fpga         = None
        print(f'pproHome: {self.pprohome}')
        print(f's2chome:  {self.s2chome}')
        if hostname == 'MDC_FPGA_1':
            self.fpga = S2cFpga(hostname, '', S2cFpga.LS_VU19P, 'USB', ip, pwrctrl_ip)
        elif hostname == 'MDC_FPGA_2' or hostname == 'MDC_FPGA_3':
            self.fpga = S2cFpga(hostname, '', S2cFpga.LS_2VU19P, 'ETH', ip, pwrctrl_ip)

        mb_config_xml = os.path.join(self.s2chome, 'mb_config.xml')
        with open(mb_config_xml, 'w') as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(f'<MB config="Standalone" connection="ETH" ip="" nm="Runtime" num="1"\n')
            f.write(f'    port="8080" targetFamily="{self.fpga.get_targetFamily()}">\n')
            f.write(f'    <Board boardNo="1" connection="{self.fpga.get_connection()}" ip="{self.fpga.get_ip()}"\n')
            f.write(f'        module="{self.fpga.get_module()}" port="8080" slot=""')
            fpga_cnt = self.fpga.get_fpga_cnt()
            if fpga_cnt > 1:
                f.write(f'>\n')
                for i in range(1, fpga_cnt+1):
                    f.write(f'        <Fpga fpgaNm="F{i}"/>\n')
                f.write(f'    </Board>\n')
            else:
                f.write(f'/>\n')
            f.write(f'</MB>')
        Util.cat(mb_config_xml)

    @Decorator.logit
    def set_power(self, fpga1, fpga2, v1_8, v3_3, v5_0):
        os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --readEth > readEth.txt')

        #TODO check if main power(J6) is On. (readEth.txt)
        isMainPowerOn = False

        if not isMainPowerOn:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J6 --setpwr on')
            time.sleep(40)

        if self.fpga.get_fpga_cnt() == 2:
            if fpga1:
                os.system('S2C_CPanel.exe --ip ' + self.fpga.get_ip() + ' --port 8080 -b ' + self.fpga.get_boardtype() + ' --dtFpgaNum 0 --PowerStatus 1')
            else:
                os.system('S2C_CPanel.exe --ip ' + self.fpga.get_ip() + ' --port 8080 -b ' + self.fpga.get_boardtype() + ' --dtFpgaNum 0 --PowerStatus 0')
            if fpga2:
                os.system('S2C_CPanel.exe --ip ' + self.fpga.get_ip() + ' --port 8080 -b ' + self.fpga.get_boardtype() + ' --dtFpgaNum 1 --PowerStatus 1')
            else:
                os.system('S2C_CPanel.exe --ip ' + self.fpga.get_ip() + ' --port 8080 -b ' + self.fpga.get_boardtype() + ' --dtFpgaNum 1 --PowerStatus 0')

        if v1_8:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J8 --setpwr on')
        else:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J8 --setpwr off')

        if v3_3:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J9 --setpwr on')
        else:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J9 --setpwr off')

        if v5_0:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J11 --setpwr on')
        else:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J11 --setpwr off')

        time.sleep(10)

        #TODO check if all power setting as expected (readEth.txt) return 0 if is same, return -1 if not the same
        #os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --readEth > readEth.txt')
        #TODO delete readEth.txt
        return 0

    @Decorator.logit
    def powerOff(self):
        #TODO check if main power(J6) is On. (readEth.txt)
        isMainPowerOn = True

        if isMainPowerOn:
            os.system('S2C_stm32_lwip.exe --ip ' + self.fpga.get_pwrctrl_ip() + ' --port 8080 --pwr J6 --setpwr off')
            time.sleep(12)

    @Decorator.logit
    def download_bit(self, f1, f2=None):
        r'''
        C:\S2C\PlayerPro_Runtime\bin\tools\S2C_CPanel.exe --bus_mode  -b SINGLE_VU19P
        C:\S2C\PlayerPro_Runtime\firmware\bin\s2cdownload_vuls.exe -b SINGLE_VU19P  -f "C:\Users\larry.chen\.s2chome\board1_download.xml"
        %RTHome%\bin\tools\S2C_CPanel.exe
        %RTHome%\firmware\bin\s2cdownload_vuls.exe

        for SINGLE_VU19P:
        <?xml version="1.0" encoding="UTF-8"?>
        <Download project="Runtime">
            <Module idx="0">
                <Fpga file="" flag="off" idx="1"/>
            </Module>
            <Module boardType="DUAL160" idx="1">
                <Fpga file="Y:\project\JH8100\bits\0047 JH8100_P1V0P8P3SEP9_SCP_EXPORT\bit\JH8100_P1V0P8P3SEP9_SCP_rtlcedd25e_fpga2c3fa3f_P1_UV19P_2209100705.bit" flag="on" idx="1"/>
            </Module>
        </Download>

        for DUAL_VU19P F1 only:
        <?xml version="1.0" encoding="UTF-8"?>
        <Download project="Runtime">
            <Module idx="0">
                <Fpga file="" flag="off" idx="1"/>
            </Module>
            <Module boardType="DUAL160" idx="1">
                <Fpga file="Y:\project\JH8100\bits\0047 JH8100_P1V0P8P3SEP9_SCP_EXPORT\bit\JH8100_P1V0P8P3SEP9_SCP_rtlcedd25e_fpga2c3fa3f_P1_UV19P_2209100705.bit" flag="on" idx="1"/>
                <Fpga file="" flag="off" idx="2"/>
            </Module>
        </Download>
        '''
        def gen_download_xml(xml, f1, f2):
            with open(xml, 'w') as f:
                f.write(f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
                f.write(f'<Download project="Runtime">\n')
                f.write(f'    <Module idx="0">\n')
                f.write(f'        <Fpga file="" flag="off" idx="1"/>\n')
                f.write(f'    </Module>\n')
                f.write(f'    <Module boardType="DUAL160" idx="1">\n')
                f1_flag = 'on'
                if f1 == 'null':
                    f1_flag = 'off'
                f.write(f'        <Fpga file="{f1}" flag="{f1_flag}" idx="1"/>\n')
                if f2 != None:
                    f2_flag = 'on'
                    if f2 == 'null':
                        f2_flag = 'off'
                    f.write(f'        <Fpga file="{f2}" flag="{f2_flag}" idx="2"/>\n')
                f.write(f'    </Module>\n')
                f.write(f'</Download>\n')
            Util.cat(xml)

        if self.fpga is None:
            print(f'Error: call select_target_hardware() first')
            return 1

        # generate download script
        download_xml = os.path.join(self.s2chome, 'board1_download_test.xml')
        gen_download_xml(download_xml, f1, f2)

        # download process
        boardtype = self.fpga.get_boardtype()
        #ret = RunnableTask(self.S2C_CPanel, ['--bus_mode  -b', self.boardtype], timeout=10).run()
        ret = Util.call(self.S2C_CPanel, ['--bus_mode', '-i', self.fpga.get_ip(), '--port', '8080','-b', boardtype], timeout=10)
        if ret != 0:
            return 1
        #ret = RunnableTask(self.s2cdownload, ['-b', self.boardtype, '-f', download_xml], timeout=600).run()
        #download_xml = os.path.join(self.s2chome, 'board1_download0.xml')
        #print("")
        s2cdownload = self.fpga.get_s2cdownload()
        ret = Util.call(s2cdownload, ['-b', boardtype, '-f', download_xml , '-i', self.fpga.get_ip(), '--port', '8200'], timeout=600)
        if ret != 0:
            return 1

        return 0

    def set_clock(self, clk1, clk2, clk3, clk4, clk5, clk6, clk7, clk8):
        clockFilePath = '"' + str(self.s2chome) + '/"'
        command = 's2cclockgen_vuls.exe -p ' + self.fpga.get_ip() + ' --port 8080 -q --ind  --file '+ clockFilePath
        os.system(command + ' -r 112 -i 50 -a '+ str(clk1) +' -b ' + str(clk2) + ' -c ' + str(clk3) + ' -d ' + str(clk4) + ' -t ' + self.fpga.get_boardtype())
        os.system(command + ' -r 113 -i 50 -a '+ str(clk5) +' -b ' + str(clk6) + ' -c ' + str(clk7) + ' -d ' + str(clk8) + ' -t ' + self.fpga.get_boardtype())
        #TODO, checking and return 0 if success, return -1 if fail
        return 0
