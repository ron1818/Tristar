#!/usr/bin/env python
""" Tristar ts-45/ts60 modbus data aquisition,
reference: tristar ts-45/60 modbus specification, morningstar corp.
v-4, 6 sept. 2012
www.fieldlines.com/index.php?topic=147639.0 """

import httplib, urllib
import time
# import the server implementation
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
# write to thingspeak, use thingspeak.py from github/bergey
import thingspeak
write_API_key = "KB7ZX4YYV7AFIM64"
read_API_key = "CQN122QG7TH5X025"
channel_ID = "57460"

# Define the mode and state turple
control_mode_turple = ('charge', 'load', 'diversion', 'lighting')
charge_div_state_turple = ('Start', 'Night Check', 'Disconnect', 'Night', 'Fault', \
        'Bulk', 'PWM', 'Float', 'Equalize')
load_light_state_turple = ('Start', 'Normal', 'LVD Warn', 'LVD', 'Fault!', \
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

# time sleep interval
DT = 5
COUNTER = 12
debug_flag = True
csv_flag = False

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


def upload_thingspeak(field_id, field_vals, Key):
    print field_vals
    field_keys = ['field' + str(n) for n in field_id]
    print zip(field_keys, field_vals)
    params = urllib.urlencode(zip(field_keys, field_vals) +[('key', Key)])
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = httplib.HTTPConnection("api.thingspeak.com:80")
    conn.request("POST", "/update", params, headers)
    response = conn.getresponse()
    print response.status, response.reason
    data = response.read()
    conn.close()
    return response


def mean(L):
    """ calculate mean"""
    return sum(L) / float(len(L))


def read_modbus(client, DT, COUNTER, debug_flag, thingspeak_flag):
    """read output from modbus,
    save them into a list"""
    counter = 1
    # initialize list
    batt_V_list = []
    batt_sens_V_list = []
    array_V_list = []
    charge_I_list = []
    load_I_list = []
    batt_V_slow_list = []
    heatsink_T_list = []
    batt_T_list = []
    pwm_duty_list = []
    powerIn_list = []

    # # write to csv file
    # if csv_flag:
    #     fil = open(filename + time.strftime("%Y%m%d%H%M") + '.csv', 'w')
    #     # write header
    #     fil.write("Time, Battery Voltage, Array Voltage, Charging Current, PWM,\
    #             Mode, State, Heat sink Temperature, Power In, Total AH"+"\n")

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
        pwm_duty = response.registers[d_filt] /230.0

        if pwm_duty > 1:
            pwm_duty = 100.0  # p. 13 0: 0%, >=230: 100%
        else:
            pwm_duty *= 100.0 # convert to percentage

        powerIn = batt_V * charge_I

        mode = control_mode_turple[mode_num]
        if mode_num == 0 or mode_num ==2:  # charge of diversion
            state = charge_div_state_turple[state_num]
        else:  # load and lighting mode
            state = load_light_state_turple[state_num]


        # debug
        if debug_flag:
            print "Battery Voltage: %.2f" % batt_V
            print "Battery Charge Current: %.2f" % charge_I
            print "Array Voltage: %.2f" % array_V
            print "PWM Duty: %.2f" % pwm_duty
            print "Control Mode: %d" % mode_num
            print "Control State: %d" % state_num
            print "Controller Temp: %.2f" % heatsink_T
            #print "Battery Temp: %.2f" % batt_T
            print "Power in: %.2f" % powerIn
            print "Ah: %.2f" % ah_total
            print "Alarm: %d" % alarm_bits
            print "Fault: %d" % fault_bits

        # calculate average
        batt_V_list.append(batt_V)
        batt_sens_V_list.append(batt_sens_V)
        array_V_list.append(array_V)
        charge_I_list.append(charge_I)
        load_I_list.append(load_I)
        batt_V_slow_list.append(batt_V_slow)
        heatsink_T_list.append(heatsink_T)
        batt_T_list.append(batt_T)
        pwm_duty_list.append(pwm_duty)
        powerIn_list.append(powerIn)

        time.sleep(DT)

        # return value
        if counter < COUNTER:
            counter += 1
            # if csv_flag:
            #     tid = time.strftime("%m/%d/%Y %H:%M:%S")
            #     out = str(tid) + ",%.2f" % mean(batt_V_list) + \
            #             ",%.2f" % mean(array_V_list) + \
            #             ",%.3f" % mean(charge_I_list) + \
            #             ",%.2f" % mean(pwm_duty_list) + "," + mode + state + \
            #             ",%.2f" % mean(heatsink_T_list) + ",%.2f" % powerIn + \
            #             ",%.2f" % ah_total + "\n"
            #     fil.write(out)
        else:
            # yield value
            tid = time.strftime("%Y/%m/%d %H:%M:%S")
            if not thingspeak_flag:
                yield str(tid) + ",%.2f" % mean(batt_V_list) + \
                    ",%.2f" % mean(array_V_list) + \
                    ",%.3f" % mean(charge_I_list) + \
                    ",%.2f" % mean(pwm_duty_list) + "," + mode + "," + state + \
                    ",%.2f" % mean(heatsink_T_list) + ",%.2f" % mean(powerIn_list) + \
                    ",%.2f" % ah_total
            else:
                yield mean(powerIn_list)
            # reset list
            counter = 1
            batt_V_list = []
            batt_sens_V_list = []
            array_V_list = []
            charge_I_list = []
            load_I_list = []
            batt_V_slow_list = []
            heatsink_T_list = []
            batt_T_list = []
            pwm_duty_list = []


def write_csv(output1, output2, csv_flag, filename):
    """write to csv file"""
    if csv_flag:
        fil = open(filename + time.strftime("%Y%m%d%H%M") + '.csv', 'w')
        # write header
        fil.write("Time, Battery Voltage, Array Voltage, Charging Current, PWM,\
                Mode, State, Heat sink Temperature, Power In, Total AH,"+\
        "Time, Battery Voltage, Array Voltage, Charging Current, PWM,\
                Mode, State, Heat sink Temperature, Power In, Total AH"+"\n")
        try:
            while True:
                output_text = output1.next() + "," + output2.next()
                print output_text
                fil.write(output_text+"\n")
        except KeyboardInterrupt:
            fil.close()

    else:
        pass

if __name__ == "__main__":
    channel = thingspeak.channel(write_API_key)
    # choose the serial client
    client1 = ModbusClient(method='rtu', port='/dev/ttyUSB0', baudrate=9600, timeout=1)
    client1.connect()
    client2 = ModbusClient(method='rtu', port='/dev/ttyUSB1', baudrate=9600, timeout=1)
    client2.connect()
    # create generator 
    output1 = read_modbus(client1, 10, 2, debug_flag=False, thingspeak_flag=True)
    output2 = read_modbus(client2, 10, 2, debug_flag=False, thingspeak_flag=True)
    # write_csv(output1, output2, True, "logfile/ts45_")
    while True:
        print output1.next()
        print output2.next()
        channel.update([3,4], [output1.next(), output2.next()])
        time.sleep(0.01)

    client1.close()
    client2.close()
