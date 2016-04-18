#!/usr/bin/env python
""" Tristar modbus data aquisition,
reference: tristar modbus specification, morningstar corp.
v-4, 6 sept. 2012
www.fieldlines.com/index.php?topic=147639.0 """

import time
# import the server implementation
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

# configure the client logging
import logging
logging.basicConfig()
log = logging.getLogger('./modbus.error')
log.setLevel(logging.ERROR)

# choose the serial client
client = ModbusClient(method='rtu', port='/dev/ttyUSB1', baudrate=9600, timeout=1)
client.connect()

# Define the mode and state turple
control_mode = ('charge', 'load', 'diversion', 'lighting')
charge_div_state = ('Start', 'Night Check', 'Disconnect', 'Night', 'Fault', \
        'Bulk', 'PWM', 'Float', 'Equalize')
load_light_state = ('Start', 'Normal', 'LVD Warn', 'LVD', 'Fault!', \
        'Disconnect', 'Normal off', 'Override LVD')
alarm_turple = ('RTS open', 'RTS shorted', 'RTS disconnected', \
        'Ths disconnected', 'Ths shorted', 'Tristar hot', 'Current limit', \
        'Current offset', 'Battery sense', 'batt sens disc', 'Uncalibrated', \
        'RTS miswire', 'HVD', 'high d', 'miswire', 'FET open', 'P12', \
        'Load disc', 'A19', 'A20', 'A21', 'A22', 'A23', 'A24')
fault_turple = ('External short', 'Overcurrent', 'FET short', 'Software', \
        'HVD', 'Tristar hot', 'DIP sw changed', 'Setting edit', 'reset?', \
        'Miswire', 'RTS shorted', 'RTS disconnected', \
        'F12', 'F13', 'F14', 'F15')

counter = 0
# time sleep interval
DT = 5

# scaling
v_scale = 96.667
i_scale = 66.667
iload_scale = 316.67
array_scale = 139.15
ah_scale = 0.1

# variable address
adc_vb_f = 0x08
adc_vs_f = 0x09
adc_vx_f = 0x0a
adc_ipv_f = 0x0b
adc_iload_f = 0x0c
vb_f = 0x0d
t_hs = 0x0e
t_batt = 0x0f
v_ref = 0x10
ah_r_hi = 0x11
ah_r_lo = 0x12
ah_t_hi = 0x13
ah_t_lo = 0x14
hourmeter_hi = 0x15
hourmeter_lo = 0x16
alarm_hi = 0x1d
alarm_lo = 0x17
fault = 0x18
dip_switch = 0x18
control_mode = 0x1a
control_state = 0x1b
d_filt = 0x1c

while True:
    # read the registers from logical address 0 to 30.
    response = client.read_holding_registers(0x00, 0x1e, unit=1)
    # the stuff we want
    batt_V = (response.registers[adc_vb_f] * v_scale) / (2**15)
    batt_sens_V = (response.registers[adc_vs_f] * v_scale) / (2**15)
    array_V = (response.registers[adc_vx_f] * array_scale) / (2**15)
    charge_I = (response.registers[adc_ipv_f] * i_scale) / (2**15)
    load_I = (response.registers[adc_iload_f] * iload_scale) / (2**15)
    batt_V_slow = (response.registers[vb_f] * v_scale) / (2**15)
    heatsink_T = response.registers[t_hs]
    batt_T = response.registers[t_batt]
    reference_V = (response.registers[v_ref] * v_scale) / (2**15)
    ah_reset = (response.registers[ah_r_hi]<<8 + \
            response.registers[ah_r_lo] ) * ah_scale
    ah_total = (response.registers[ah_t_hi]<<8 + \
            response.registers[ah_t_lo] ) * ah_scale
    hourmeter = response.registers[hourmeter_hi]<<8 + \
            response.registers[hourmeter_lo]
    alarm_bits = response.registers[alarm_hi]<<8 + \
            response.registers[alarm_lo]
    fault_bits = response.registers[fault]
    dip_num = response.registers[dip_switch]
    mode_num = response.registers[control_mode]
    state_num = response.registers[control_state]
    pwm_duty = response.registers[d_filt] /230
    if pwm_duty > 1: pwm_duty = 1  # p. 13 0: 0%, >=230: 100%
    powerIn = batt_V * charge_I

    # debug
    print "Battery Voltage: %.2f" % batt_V
    print "Battery Charge Current: %.2f" % charge_I
    print "Array Voltage: %.2f" % array_V
    print "PWM Duty: %.2f" % pwm_duty
    print "Control Mode: %d" % mode_num
    print "Control State: %d" % state_num
    print "Controller Temp: %.2f" % heatsink_T
    print "Power in: %.2f" % powerIn
    print "Ah: %.2f" % ah_total

    # out = "V:%.2f" % battsV + " A:%.3f" % chargeI + " AV:%.2f" % arrayV + " D:%.2f" % pwmDuty + " S:" + state[statenum] + " CT:%.2f" % regTemp + " P:%.2f" % powerIn + " AH:%.2f" % ampH + "\n" 
    # fil = open('/mnt/dumpdata.txt', 'w')
    # fil.write(out)
    # fil.close()
    # counter += 1

    # if counter == 24:
    #     tid = time.ctime()
    #   out = str(tid) + ",%.2f" % battsV + ",%.3f" % chargeI + ",%.2f" % arrayV + ",%.2f" % pwmDuty + "," + state[statenum]  + ",%.2f" % regTemp + ",%.2f" % powerIn + ",%.2f" % ampH + "\n" 
    #   fil = open('/mnt/dumplog.csv', 'a')
    #   fil.write(out)
    #   fil.close()
    #   counter = 0

    time.sleep(DT)

# close the client
client.close()

print "done"
