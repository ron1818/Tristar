#!/usr/bin/python
# -*- coding: UTF-8 -*-

# enable debugging
import sys
import StringIO
import time

# Set http Headere...
sys.stdout.write("Content-type: text/html\r\n\r\n")

# Les inn fila
file = open('./dumpdata.txt')
rawData = file.read()
file.close()

# Fjern crappet fra begynnelsen & slutten av linja
# rawData = rawData.replace("b'", "")
# rawData = rawData.replace("\\r\\n'", "")

# Klargjør output variabler
# V:14.80 A:5.93 AV:16.43 D:75.29 S:6.00 CT:18.00 P:87.79
v = 0.00
a = 0.00
av = 0.00
d = 0.00
s = 0
ct = 0.00
p = 0.00
ah = 0.00
kw = 0.00

# Splitt linja i en liste med ett element for hver space
elements = rawData.split()

# loop gjennom alle elementer i lista
for element in elements:

        # Split enkeltelement på ":"
        value = element.split(":")

        #Sjekk hvilket element vi jobber med, og do the right thing for hver av dem
        if value[0] == "V":
                v = value[1]
        if value[0] == "A":
                a = value[1]
        if value[0] == "AV":
                av = value[1]
        if value[0] == "D":
                d = value[1]
        if value[0] == "S":
                s = value[1]
        if value[0] == "CT":
                ct = value[1]
        if value[0] == "P":
                p = value[1]
        if value[0] == "AH":
                ah = value[1]
        if value[0] == "kW":
                kw = value[1]

tid = time.ctime()
# Sett opp html documentet
sys.stdout.write("<html>")

sys.stdout.write("<head>")
sys.stdout.write("<meta http-equiv='refresh' content='15' />")
sys.stdout.write("<title>BatteriStatus</title>")
sys.stdout.write("<link rel='stylesheet' type='text/css' href='styles.css'>")
sys.stdout.write("</head>")

sys.stdout.write("<body>")

sys.stdout.write("Status for my 12V, 1060Ah(@100hr) battery bank (4x Rolls S-4000 6V, 530Ah). <br>")
sys.stdout.write("Charged with approx. 650W (effective; rated 800W) of solar panels, connected to a <b>Tristar TS-60 controller</b>.<br>")
sys.stdout.write("Using a <b>Raspberry Pi (model B)</b> (running on power from the bank) to log data. <br><br>")


# Spytt ut en HTML tabell.
sys.stdout.write("<table border='1'>")
sys.stdout.write("<tr>")
sys.stdout.write("<th>Volt</th><th>Amp</th><th>Array</th><th>PWMDuty</th><th>Control State</th><th>Controller Temp</th><th>Power</th>")
sys.stdout.write("</tr>")
sys.stdout.write("<tr>")
# sys.stdout.write("<td>{0:.2f}".format(v)+ "</td>")
# sys.stdout.write("<td>%.2f"%v + "V </td>")
sys.stdout.write("<td>" + str(v) + "V</td>")
sys.stdout.write("<td>" + str(a) + "A</td>")
sys.stdout.write("<td>" + str(av) + "V</td>")
sys.stdout.write("<td>" + str(d) + "%</td>")
sys.stdout.write("<td>" + str(s) + "</td>")
sys.stdout.write("<td>" + str(ct) + "&deg;C</td>")
sys.stdout.write("<td>" + str(p) + "W</td>")

sys.stdout.write("</tr>")
sys.stdout.write("</table>")

# en timestamp.
sys.stdout.write(str(tid))
sys.stdout.write("<br> <br>")

sys.stdout.write("Total kAh since 3 April 2013: <b>" + str(ah) + " kAh</b><br>")
sys.stdout.write("<b>" + str(kw) + " kWh</b> has been put into the batteries from the solar array.")
sys.stdout.write("<br> <br>")

sys.stdout.write("Data from the Tristar are retrieved every 5 second, and this page are refreshed every 15 second.")
sys.stdout.write("<br> <br>")

sys.stdout.write("Cornelius. ;) <br>")

sys.stdout.write("</body>")
sys.stdout.write("</html>")
