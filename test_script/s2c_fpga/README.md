# Automation Pipeline

## Jenkins Scripted Pipeline :

In Scripted Pipeline syntax, one or more node blocks do the core work throughout the entire Pipeline. It schedules the steps contained within the block to run by adding to the Jenkins queue. As soon as the executor is free on a node, the steps will run. For FPGA, the execution time is set to 3:00 AM, the log will be generated. The Jenkins pipeline creates a workspace (a directory specific to that particular Pipeline) where work can be done on files checked out from source control. User have to include the test scripts and test batch file in the respective workspace.

### Stage 1: Pre-run
At this stage, Jenkins will instruct the Jenkins agent to run the pre-run batch file and display a notification that conuts for 5 minutes. After 5 minutes, the executor (FPGA) will kill other running tasks.

```
pipeline {
    agent none
    stages {
        stage('Pre_run') {
            agent {label "fpga_1_host_machine"}
            steps {
                catchError() {
                    bat "echo $WORKSPACE > ../../automation/dir.txt"
                    dir ("../../automation") {
                        sh 'pwd'
                        sh './pre_run.bat'
                    }
                }
            }
        }
```
### Stage 2: Run-test
At this stage, the executor will run the python script, test_config.py to read input from the yaml file to set FPGA power and clock, download bit file, and run <testname>.bat from the workspace.
```
        stage('Run_Test') {
            agent {label "fpga_1_host_machine"}
            steps {
                catchError() {
                    dir ("../../automation") {
                        sh 'pwd'
                        sh 'python test_config.py'
                    }
                }
            }
        }
```

### Stage 3: Post-run
At this stage, the executor will run the post-run batch file to kill tasks and power off FPGA.
```
        stage('Post_run') {
            agent {label "fpga_1_host_machine"}
            steps {
                catchError() {
                    dir("../../automation") {
                        bat 'echo $WORKSPACE'
                        sh './post_run.bat'
                    }
                }
            }
        }
    }
}
```

# Quick Guide to Create Jenkins Pipeline Task
In the FPGA host PC, install the following libraries:
```
$ pip install pyside6-essentials jsonschema pyyaml
```
Also please install pyserial if the testcase is using python serial library
```
$ pip install pyserial
```

Setup system environment variables:
* RTHome
* S2C_WORKDIR
* S2C_IP
* S2C_PWR_CTRL_IP
* S2C_HOSTNAME

Example:
* RTHome = C:\S2C\PlayerPro_Runtime
* S2C_WORKDIR = C:\Users\mdc_fpga_2\
* S2C_IP = 192.168.152.253
* S2C_PWR_CTRL_IP = 192.168.152.254
* S2C_HOSTNAME = MDC_FPGA_1

The automation folder is located in `C:/jenkins` which is same path in all FPGAs.

Upon creating a new pipeline in Jenkins, a new workspace will be created in `C:/jenkins/workspace`. In the workspace, there are a few files required to run automated test on FPGA:
1. YAML file (.yml)
2. Testname batch file (.bat)
3. Test script(s)

### YAML file
---
In  test_config.yml, replace `testname` and input power, clock value, and path for bitfile accordingly.
Refer to OneNote:
[How to Setup Yaml file](https://mystarfivetech.sharepoint.com/sites/StarFiveMalaysiaSoftware/_layouts/OneNote.aspx?id=%2Fsites%2FStarFiveMalaysiaSoftware%2FShared%20Documents%2FGeneral%2FIntegration%2FBenchmark&wd=target%28Automated%20Test.one%7CE261CDED-0318-47FD-9ED3-37EA2D00C81C%2FHow%20to%20setup%7C20BBFC20-B1DF-4A7A-AC82-D519826C3E6C%2F%29).

We can have more than 1 test, and framework will run all tests iteratively.
```
# yaml-language-server: $schema=test_config.json
testname1:
  fpga:
    power_1_8V: "On"
    power_3_3V: "On"
    power_5_0V: "On"
    S2CCLK_1: 100
    S2CCLK_2: 100
    S2CCLK_3: 100
    S2CCLK_4: 100
    S2CCLK_5: 100
    S2CCLK_6: 100
    S2CCLK_7: 100
    S2CCLK_8: 100
    bitfile_fpga1: "full path"
    bitfile_fpga2: "null"
testname2:
  fpga:
    power_1_8V: "On"
    power_3_3V: "On"
    power_5_0V: "On"
    S2CCLK_1: 50
    S2CCLK_2: 50
    S2CCLK_3: 50
    S2CCLK_4: 50
    S2CCLK_5: 50
    S2CCLK_6: 50
    S2CCLK_7: 50
    S2CCLK_8: 50
    bitfile_fpga1: "full path"
    bitfile_fpga2: "null"
```

### Batch file
---
Create a batch file with the same name as the `testname` in the yaml file. Take note that the filename should comply to the file naming conventions which avoid special characters or spaces in the file name. The `testname.bat` is scripted to call the test script(s) in the same workspace.




