#! /usr/bin/python
"""
Change log 20160307:
    make symbolic link to /dev/ttyUSB* by add script to
    /etc/udev/rules.d/99-usb-serial.rules as
SUBSYSTEMS=="usb", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", SYMLINK+="PROLIFIC", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="FUTURETECH", MODE="0666"

so that /dev/PROLIFIC is for coated and /dev/FUTURETECH is for uncoated

for filename, must use absolute path for rc.local
"""

from tristar import *
ts60 = TristarPWM(method='rtu', port='/dev/PROLIFIC', baudrate=9600, stopbits=2, parity='N', timeout=1, debug_flag=True)
ts60.connect()

try:
    while True:
        ts60.write_thingspeak_oneshot([2,4,6], ["array_V", "charge_I","powerIn"])
        ts60.log_data(["tid", "array_V", "charge_I", "powerIn", "pwm_duty", "batt_V", "batt_sens_V", "mode_num", "state_num"], "/home/pi/Tristar/logfile/coated")
except KeyboardInterrupt:
    ts60.close()
