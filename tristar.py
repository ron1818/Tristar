#!/usr/bin/env python
""" Tristar ts-45/ts60 modbus data aquisition,
reference: tristar ts-45/60 modbus specification, morningstar corp.
v-4, 6 sept. 2012
www.fieldlines.com/index.php?topic=147639.0

Changelog 20160308:
    change register_dict to self.register_dict
    log file will use external tid and will not read the modbus again
    instead, it will save latest data into file
"""

import time
import os
# import the server implementation
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.mei_message import ReadDeviceInformationRequest
import thingspeak

__version__ = '0.1.1'
__author__ = 'Ren Ye'


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
# scaling
v_scale = 96.667
i_scale = 66.667
iload_scale = 316.67
array_scale = 139.15
ah_scale = 0.1

# register address
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

def mean(L):
    """ calculate mean"""
    return sum(L) / float(len(L))

class TristarPWM(object):
    """ tristar pwm ts45 or ts60 for data logging,
    it can read the holding/input register and save to csv file
    """

    def __init__(self, method, port, baudrate, stopbits, parity, timeout,
                 DT=10, COUNT=6,
                 debug_flag=True, log_flag=True, thingspeak_flag=True):
        self.method = method
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.parity = parity
        self.timeout = timeout
        self.DT = DT
        self.COUNT = COUNT
        self.debug_flag = debug_flag
        self.log_flag = log_flag
        self.thingspeak_flag = thingspeak_flag
        self.register_dict={}

    def connect(self):
        """ connect to modbus client """
        try:
            self.client = ModbusClient(method=self.method,
                                  port=self.port,
                                  baudrate=self.baudrate,
                                  stopbits=self.stopbits,
                                  parity=self.parity,
                                  timeout=self.timeout)
            self.client.connect()
            print "connected"
        except KeyboardInterrupt:
            self.client.close()

    def close(self):
        """ disconnect client """
        self.client.close()

    def read_registers(self):
        """ read holding registers """
        # read the registers from logical address 0 to 0x1e.
        response = self.client.read_holding_registers(0x00, 0x1e, unit=1)
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

        return {"batt_V":batt_V,"batt_sens_V":batt_sens_V,
                "array_V":array_V,"charge_I":charge_I,"load_I":load_I,
                "batt_V_slow":batt_V_slow,"heatsink_T":heatsink_T,
                "batt_T":batt_T,"reference_V":reference_V,
                "ah_reset":ah_reset,"ah_total":ah_total,
                "hourmeter":hourmeter,"alarm_bits":alarm_bits,
                "fault_bits":fault_bits,"dip_num":dip_num,
                "mode_num":mode_num,"state_num":state_num,
                "pwm_duty":pwm_duty,"powerIn":powerIn,
                "mode":mode,"state":state}

    def read_modbus(self):
        """read output from modbus,
        save them into a list"""
        assert(self.client is not None), "client not connected"
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

        while counter <= self.COUNT:
            try:
                self.register_dict = self.read_registers()
            except KeyboardInterrupt:
                print "interrupted"
                break
            except:
                print "port not available"
                continue

            # debug
            if self.debug_flag:
                print self.register_dict.items()
                # for key in register_dict:
                #     print key
                #     print register_dict[key]

            # calculate average
            batt_V_list.append(self.register_dict["batt_V"])
            batt_sens_V_list.append(self.register_dict["batt_sens_V"])
            array_V_list.append(self.register_dict["array_V"])
            charge_I_list.append(self.register_dict["charge_I"])
            load_I_list.append(self.register_dict["load_I"])
            batt_V_slow_list.append(self.register_dict["batt_V_slow"])
            heatsink_T_list.append(self.register_dict["heatsink_T"])
            batt_T_list.append(self.register_dict["batt_T"])
            pwm_duty_list.append(self.register_dict["pwm_duty"])
            powerIn_list.append(self.register_dict["powerIn"])

            # return value
            counter += 1
            time.sleep(self.DT)
        else:
            # add time point
            tid = time.strftime("%Y/%m/%d %H:%M:%S")
            self.register_dict["tid"] = str(tid)
            # calculate average
            self.register_dict["batt_V"] = mean(batt_V_list)
            self.register_dict["array_V"] = mean(array_V_list)
            self.register_dict["charge_I"] = mean(charge_I_list)
            self.register_dict["pwm_duty"] = mean(pwm_duty_list)
            self.register_dict["heatsinke_T"] = mean(heatsink_T_list)
            self.register_dict["powerIn"] = mean(powerIn_list)

    def write_thingspeak(self, field_id, field_var_name):
        """ write certain fields to thingspeak, while loop """
        if self.thingspeak_flag:
            channel = thingspeak.channel()
            try:
                while True:
                    # register_dict = self.read_modbus()
                    self.read_modbus()
                    field_var = [self.register_dict[i] for i in field_var_name]
                    channel.update(field_id, field_var)
            except KeyboardInterrupt:
                self.close()
        else:
            pass

    def write_thingspeak_oneshot(self, field_id, field_var_name):
        """ write certain fields to thingspeak, no loop """
        if self.thingspeak_flag:
            channel = thingspeak.channel()
            self.read_modbus()
            field_var = [self.register_dict[i] for i in field_var_name]
            channel.update(field_id, field_var)
        else:
            pass

    def log_data(self, field_var_name, filename, tid=None):
        """ log data into a file
        Changelog 20160308: insert external tid for data to have same tid
        """
        if self.log_flag:
            filename_new = filename + time.strftime("%Y%m%d") + '.csv'
            if not os.path.isfile(filename_new):  # write new file with header
                # create new file
                os.mknod(filename_new)
                # chmod
                os.chmod(filename_new, 0o755)
                fil = open(filename_new, 'w+')
                # write header
                # select items to write
                header = ",".join(field_var_name)
                fil.write(header+"\n")
            else:  # append
                if not os.access(filename_new, os.W_OK):
                    # chmod
                    os.chmod(filename_new, 0o755)
                else:
                    fil = open(filename_new, 'a+')

            # pass register_dict to file write
            # check if have external tid
            if tid is not None:
                self.register_dict['tid'] = str(tid)
            field_var = [str(self.register_dict[i]) for i in field_var_name]
            output_text = ",".join(field_var)
            # print output_text
            fil.write(output_text+"\n")
            fil.close()
        else:  # no log
            pass


if __name__ == "__main__":
    """ ttyUSB0: coated, ttyUSB1: uncoated """
    ts45 = TristarPWM(method='rtu', port='/dev/ttyUSB0', baudrate=9600, stopbits=2, parity='N', timeout=1, debug_flag=True, COUNT=6)
    ts45.connect()
    ts60 = TristarPWM(method='rtu', port='/dev/ttyUSB1', baudrate=9600, stopbits=2, parity='N', timeout=1, debug_flag=True, COUNT=6)
    # ts60.connect()

    try:
        while True:
            ts45.write_thingspeak_oneshot([1,3], ["array_V", "charge_I"])
            #ts60.write_thingspeak_oneshot([2,4], ["array_V", "charge_I"])
            #ts45.log_data(["tid", "array_V", "charge_I", "powerIn", "pwm_duty", "batt_V"], "logfile/coated")
            #ts60.log_data(["tid", "array_V", "charge_I", "powerIn", "pwm_duty", "batt_V"], "logfile/uncoated")
    except KeyboardInterrupt:
        ts45.close()
        #ts60.close()
    except:
        pass
