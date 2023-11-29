import os
import s2c
import time

if __name__ == '__main__':
    pprohome = os.getenv('RTHome')
    workdir = os.getenv('S2C_WORKDIR')
    s2c_ip = os.getenv('S2C_IP')
    s2c_pwr_ctrl_ip = os.getenv('S2C_PWR_CTRL_IP')
    hostname = os.getenv('S2C_HOSTNAME')
    print(pprohome)
    print(workdir)
    print(s2c_ip)
    print(s2c_pwr_ctrl_ip)
    print(hostname)

    ppro = s2c.S2cPlayerPro(pprohome, workdir, hostname, s2c_ip, s2c_pwr_ctrl_ip)
    ppro.powerOff()
    time.sleep(12)
