#! /usr/bin/python
"""
Change log 20160308:
    combine coated.py and uncoated.py into one file

Change log 20160307:
    make symbolic link to /dev/ttyUSB* by add script to
    /etc/udev/rules.d/99-usb-serial.rules as
SUBSYSTEMS=="usb", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", SYMLINK+="PROLIFIC", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="FUTURETECH", MODE="0666"
so that /dev/PROLIFIC is for coated and /dev/FUTURETECH is for uncoated
for filename, must use absolute path for rc.local
"""

import time
from tristar import *
coated = TristarPWM(method='rtu', port='/dev/PROLIFIC', baudrate=9600, stopbits=2, parity='N', timeout=1, debug_flag=True)
uncoated = TristarPWM(method='rtu', port='/dev/FUTURETECH', baudrate=9600, stopbits=2, parity='N', timeout=1, debug_flag=True)
while True:
    try:
        coated.connect()
        uncoated.connect()
        break
    except KeyboardInterrupt:
        print "interrupted"
        break
    except:
        print "waiting for connection"
        pass

try:
    while True:
        print "coated thingspeak"
        coated.write_thingspeak_oneshot([1,3,5,7], ["array_V", "charge_I","powerIn","batt_sens_V"])
        print "uncoated thingspeak"
        uncoated.write_thingspeak_oneshot([2,4,6], ["array_V", "charge_I","powerIn"])
        # insert time stamp at each row of log file 
        tid = time.strftime("%Y/%m/%d %H:%M")
        print "coated log"
        coated.log_data(["tid", "array_V", "charge_I", "powerIn", "pwm_duty", "batt_V", "batt_sens_V", "mode_num", "state_num"], "/home/pi/Tristar/logfile/coated", tid)
        print "uncoated log"
        uncoated.log_data(["tid", "array_V", "charge_I", "powerIn", "pwm_duty", "batt_V", "batt_sens_V", "mode_num", "state_num"], "/home/pi/Tristar/logfile/uncoated", tid)
except KeyboardInterrupt:
    coated.close()
    uncoated.close()
