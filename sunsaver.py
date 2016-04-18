#!/usr/bin/env python
""" Tristar ts-45/ts60 modbus data aquisition,
reference: tristar ts-45/60 modbus specification, morningstar corp.
v-4, 6 sept. 2012
www.fieldlines.com/index.php?topic=147639.0 """

import time
import os.path
# import the server implementation
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.mei_message import ReadDeviceInformationRequest
import thingspeak

__version__ = '0.1.1'
__author__ = 'Ren Ye'


# Define the mode and state turple
charge_state_turple = ('Start', 'Night Check', 'Disconnect', 'Night', 'Fault', \
        'Bulk', 'Absorption', 'Float', 'Equalize')
load_state_turple = ('Start', 'Load On', 'LVD Warn', 'LVD', 'Fault!', \
        'Disconnect')
led_state_turple = ('Start', 'Start2', 'Branch', 'Equalize', 'Float', \
        'Absorption', 'Green', 'Undef', 'Yellow', 'Blink Red', 'Red', \
        'R-Y-G Err', 'R/Y-G Err', 'R.G-Y Err', 'R-Y Err', 'R-G Err', 'R-Y Err', \
        'R-G Err', 'R/Y-G/Y Err', 'G/Y/R Err', 'G/Y/R * 2')
alarm_turple = ('RTS open', 'RTS shorted', 'RTS disconnected', \
        'Ths open', 'Ths shorted', 'SSMPPT hot', 'Current limit', \
        'Current offset', 'undef', 'undef', 'Uncalibrated', \
        'RTS miswire', 'undef', 'undef', 'miswire', 'FET open', 'P12', \
        'high Va current limit', 'A19', 'A20', 'A21', 'A22', 'A23', 'A24')
array_fault_turple = ('Overcurrent', 'FET short', 'Software', \
        'battery HVD', 'array HVD', 'EEPROM setting edit', 'RTS shorted', \
        'RTS was valid, now disc', 'local temp sens failed', 'Fault 10', \
        'Fault 11', 'Fault 12', 'Fault 13', 'Fault 14', 'Fault 15', 'Fault 16')
load_fault_turple = ('External short', 'Overcurrent', 'FET short', 'Software', \
        'HVD', 'heatsink over temperature', 'EEPROM setting edit', 'Fault 8')
# scaling
v_scale = 100.0
i_scale = 79.16
v_batt_scale = 96.667
ah_scale = 0.1
p_scale = 989.5

# register address
Adc_vb_f = 0x08
Adc_va_f = 0x09
Adc_vl_f = 0x0a
Adc_ic_f = 0x0b
Adc_il_f = 0x0c
T_hs = 0x0d
T_batt = 0x0e
T_amb = 0x0f
T_rts = 0x10
charge_state = 0x11
array_fault = 0x12
Vb_f = 0x13
Vb_ref = 0x14
Ahc_r_HI = 0x15
Ahc_r_LO = 0x16
Ahc_t_HI = 0x17
Ahc_t_LO = 0x18
kWhc = 0x19
load_state = 0x1a
load_fault = 0x1b
V_lvd = 0x1c
Ahl_r_HI = 0x1d
Ahl_r_LO = 0x1e
Ahl_t_HI = 0x1f
Ahl_t_LO = 0x20
hourmeter_HI = 0x21
hourmeter_LO = 0x22
alarm_HI = 0x23
alarm_LO = 0x24
dip_switch = 0x25
led_state = 0x26
Power_out = 0x27
Sweep_Vmp = 0x28
Sweep_Pmax = 0x29
Sweep_Voc = 0x2a
Vb_min_daily = 0x2b
Vb_max_daily = 0x2c
Ahc_daily = 0x2d
Ahl_daily = 0x2e
array_fault_daily = 0x2f
load_fault_daily = 0x30
alarm_HI_daily = 0x31
alarm_LO_daily = 0x32
vb_min = 0x33
vb_max = 0x34
light_should_be_on = 0x38
va_ref_fixed = 0x39
va_ref_fixed_pct = 0x3a

control_mode = 0x1a
control_state = 0x1b
d_filt = 0x1c

def mean(L):
    """ calculate mean"""
    return sum(L) / float(len(L))

class SunSaverMPPT(object):
    """ sunsaver mppt 15 for data logging,
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
        except KeyboardInterrupt:
            self.client.close()

    def close(self):
        """ disconnect client """
        self.client.close()

    def read_registers(self):
        """ read holding registers """
        # read the registers from logical address 0 to 0x1e.
        response = self.client.read_holding_registers(0x00, 0x3e, unit=1)
        # the stuff we want
        batt_V = (response.registers[Adc_vb_f] * v_scale) / (2**15)
        array_V = (response.registers[Adc_va_f] * v_scale) / (2**15)
        load_V = (response.registers[Adc_vl_f] * v_scale) / (2**15)
        charge_I = (response.registers[Adc_ic_f] * i_scale) / (2**15)
        load_I = (response.registers[Adc_il_f] * i_scale) / (2**15)
        batt_V_slow = (response.registers[Vb_f] * v_scale) / (2**15)
        heatsink_T = response.registers[t_hs]
        ah_reset = (response.registers[Ahc_r_HI]<<8 + \
        response.registers[Ahc_r_LO] ) * ah_scale
        ah_total = (response.registers[Ahc_t_HI]<<8 + \
        response.registers[Ahc_t_LO] ) * ah_scale
        hourmeter = response.registers[hourmeter_HI]<<8 + \
        response.registers[hourmeter_LO]
        alarm_bits = response.registers[alarm_HI]<<8 + \
        response.registers[alarm_LO]
        dip_num = response.registers[dip_switch]
        led_num = response.registers[led_state]
        power_out = (response.registers[Power_out] * p_scale) / (2**15)

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
            register_dict = self.read_registers()

            # debug
            if self.debug_flag:
                print register_dict.items()
                # for key in register_dict:
                #     print key
                #     print register_dict[key]

            # calculate average
            batt_V_list.append(register_dict["batt_V"])
            batt_sens_V_list.append(register_dict["batt_sens_V"])
            array_V_list.append(register_dict["array_V"])
            charge_I_list.append(register_dict["charge_I"])
            load_I_list.append(register_dict["load_I"])
            batt_V_slow_list.append(register_dict["batt_V_slow"])
            heatsink_T_list.append(register_dict["heatsink_T"])
            batt_T_list.append(register_dict["batt_T"])
            pwm_duty_list.append(register_dict["pwm_duty"])
            powerIn_list.append(register_dict["powerIn"])

            # return value
            counter += 1
            time.sleep(self.DT)
        else:
            # add time point
            tid = time.strftime("%Y/%m/%d %H:%M:%S")
            register_dict["tid"] = str(tid)
            # calculate average
            register_dict["batt_V"] = mean(batt_V_list)
            register_dict["array_V"] = mean(array_V_list)
            register_dict["charge_I"] = mean(charge_I_list)
            register_dict["pwm_duty"] = mean(pwm_duty_list)
            register_dict["heatsinke_T"] = mean(heatsink_T_list)
            register_dict["powerIn"] = mean(powerIn_list)

            # return result
            return register_dict

    def write_thingspeak(self, field_id, field_var_name):
        """ write certain fields to thingspeak, while loop """
        if self.thingspeak_flag:
            channel = thingspeak.channel()
            try:
                while True:
                    register_dict = self.read_modbus()
                    field_var = [register_dict[i] for i in field_var_name]
                    channel.update(field_id, field_var)
            except KeyboardInterrupt:
                self.close()
        else:
            pass

    def write_thingspeak_oneshot(self, field_id, field_var_name):
        """ write certain fields to thingspeak, no loop """
        if self.thingspeak_flag:
            channel = thingspeak.channel()
            register_dict = self.read_modbus()
            field_var = [register_dict[i] for i in field_var_name]
            channel.update(field_id, field_var)
        else:
            pass

    def log_data(self, field_var_name, filename):
        """ log data into a file """
        if self.log_flag:
            filename_new = filename + time.strftime("%Y%m%d") + '.csv'
            if not os.path.isfile(filename_new):  # write new file with header
                fil = open(filename_new, 'w')
                # write header
                # select items to write
                header = ",".join(field_var_name)
                fil.write(header+"\n")
            else:  # append
                fil = open(filename_new, 'a')

            # read modbus
            register_dict = self.read_modbus()
            field_var = [str(register_dict[i]) for i in field_var_name]
            output_text = ",".join(field_var)
            print output_text
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
