import yaml
import os
import sys
from os import path
import subprocess

#############################################   Import Test Scritp   #############################################
main_path = path.dirname( path.dirname( path.dirname( path.dirname( path.abspath(__file__) ) ) ) )
test_script_path = main_path + "\\test_script"
sys.path.append( test_script_path )
import std_func as sf

##################################################################################################################

current_dir = path.dirname( path.abspath(__file__) )
current_log = current_dir + '\\log\\result.txt'
current_bitfile = os.path.basename(current_dir)

def prelog():
    sf.backup_old_log(current_dir)
    f = open(current_log, 'w')
    f.write(current_bitfile + '\n')
    f.close()

def collect_log(main, sub):
    #open file1 in reading mode
    dst = open(main, 'a')

    #open file2 in writing mode
    src = open(sub,'r')
    
    #read from file1 and write to file2 using read method
    dst.write(src.read())

    src.close()
    dst.close()

def main():
    prelog()

    with open(current_dir + "\\test_case_to_run.yml") as file:
        data = yaml.load(file, yaml.SafeLoader)

    for value in data['test_case']:
        
        py_script = current_dir + '\\' + value + '\\run_test.py'
        py_script_log = current_dir + '\\' + value + '\\log\\summary.log'

        if os.path.exists(py_script):
            print("Running " + value + "\n")
            subprocess.run(["python", py_script])
            collect_log(current_log, py_script_log)
        else:
            print(value + " has no run_test.py file\n")


if __name__ == "__main__":
    main()