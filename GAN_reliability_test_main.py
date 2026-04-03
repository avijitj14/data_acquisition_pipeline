# -*- coding: utf-8 -*-
try:
    from Tkinter import *
except ImportError:
    from tkinter import *
import sys
import time
import datetime
import os
import logging
# Oscilloscope
import visa
# Send Email
import smtplib
# Power Supply
import serial
# Google Drive Upload
import glob
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pydrive.settings
# CSV read and write
import csv
import sqlite3
import mysql.connector
# plotting
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
import pandas as pd
import string
import random


EMAIL_RECIPIANTS = ['ajaiswa1@uncc.edu']
ocilloscopeArray = []
OFFSET_TOP = 2.818705926  # offsets needed
OFFSET_BOT = 0#1.8801172126
MULTIPLYER = 0.3  # scale properly
WAIT_TIME = 10
startPoint = .0
endPoint = .22
ctr=0

# Select scope
# "TCPIP0::DESKTOP-IR5VCMI::inst0::INSTR"
# "USB0::0x0957::0x17A4::MY53401281::0::INSTR"
# "USB0::0x2A8D::0x1774::MY54440041::0::INSTR"
# "USB0::0x2391::0x5956::MY44002318::0::INSTR"
scope_id = "USB0::0x0957::0x1744::MY44002318::0::INSTR"
# "USB0::0x2A8D::0x1770::MY54440043::0::INSTR"
# "USB0::0x10893::0x6000::MY54440043::0::INSTR"

data_list = []

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='logfile.log',
                    level=logging.DEBUG)
logging.shutdown()
timeStart = time.time()



################################## RUN ########################################
# Main Loop

def run():
    try:
        # powerSupply(57.25)
        initOscilloscope()
        while True:
            vclamp = 0
            ind_current = 0
            outputVoltage = 0
            output_current = 0
            waveOne = [0] * 62500
            waveTwo = [0] * 62500
            waveThree = [0] * 62500
            waveFour = [0] * 62500
            # sendmail(EMAIL_RECIPIANTS,"ERROR - VERY LARGE VOLTAGE DROP","ERROR - LOW VOLTAGE")    
            # sendmail(EMAIL_RECIPIANTS, "ERROR - MAXIMUM VOLTAGE EXEEDED", "MAXIMUM VOLTAGE EXEEDED")

            waveOne = runOscilloscope("1")
            waveTwo = runOscilloscope("2")
            #waveThree = runOscilloscope("3")
            #waveFour = runOscilloscope("4")
            # waveThree = runOscilloscope("3")
            # waveFour = runOscilloscope("4")
            #print(waveOne)

            # vdsTop = calculateData(waveTwo,False,False)
            #vdsBot = calculateData(waveOne,False,True)
            #outputVoltage = calculateData(waveThree,True,False)
            ind_current = calculateData(waveTwo,True,True)
            vclamp = calculateData(waveOne,False,True)
            #output_current = calculateData(waveFour,False,True)

            # current_sensor = (current_sensor - 2.4)*20
            # rdsTop = MULTIPLYER*(vdsTop/currentTop - OFFSET_TOP)
            
            #rds1 = MULTIPLYER*((vclamp - 0.95)/(currentBot + OFFSET_BOT))
            # rds2 = (vclamp - 0.85)/current_sensor

            # print("RdsTOP: "+str(rdsTop))
            print("Inductor current: " + str(ind_current))
            #print("Output current: " + str(output_current))
            print("Vclamp: " + str(vclamp))
            #print("Output voltage: " + str(outputVoltage))
            #print("Rds1: "+str(rds1))
            # print("Rds2: "+str(rds2))

            #plot(theData, 'yellow')

            # sendmail(EMAIL_RECIPIANTS, "ERROR - MAXIMUM VOLTAGE EXEEDED", "MAXIMUM VOLTAGE EXEEDED")

            ts = datetime.datetime.now()
            dateAndTime = ts.strftime("%m-%d-%Y %H:%M:%S")
            print(dateAndTime)
            
            saveData(waveOne,waveTwo,waveThree,waveFour,vclamp,ind_current,outputVoltage,output_current,dateAndTime)

            #safetyCheck(vclamp,vclamp_prev,currentBot,currentBot_prev)

            vclamp_prev = vclamp
            #currentBot_prev = currentBot

            # plotMe(dateAndTime.strftime("%Y-%m-%d %I:%M"))

            # googleDriveUpload()
            #time.sleep(3)
            


            #1800 for 15 mins
            print('')
            print('Processing ...')
            print('|'+'_'*WAIT_TIME*2+'|')
            sys.stdout.write("|")
            for i in range(0, WAIT_TIME*2):
                time.sleep(.5)
                sys.stdout.write("=")
            sys.stdout.write("|")
            print('\n')


    except Exception as expt:
        print(expt)
        # time how long the setup has been running
        timeEnd = time.time()
        print(timeEnd - timeStart)
        timeRun = open("timeRun.txt", "a")
        timeRun.write(str(timeEnd - timeStart) + ",\n")
        timeRun.close()
        # powerSupply(False, 0)

    finally:
        # time how long the setup has been running
        timeEnd = time.time()
        print(timeEnd - timeStart)
        timeRun = open("timeRun.txt", "a")
        timeRun.write(str(timeEnd - timeStart) + ",\n")
        timeRun.close()
        # powerSupply(False, 0)


##################################################################### END RUN #
############################ SEND MAIL ########################################
# format to use: sendmail("majazi@uncc.edu", "Message goes here", "Subject")
def sendmail(address, msg, subject):
    print("SENDING EMAIL ...")
    message = 'Subject: {}\n\n{}'.format(subject, msg)
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login('automaticpythonmessage@gmail.com', 'Sarah1997!')
    mail.sendmail('automaticpythonmessage@gmail.com', address, message)
    mail.close()
    print("EMAIL SENT")


############################################################### END SEND MAIL #
############################## POWER SUPPLY ###################################
# Power supply communication
def powerSupply(voltage, powerOn=True):
    try:
        logging.info('Power supply voltage changed to ' + str(voltage) + 'V')
        # configure the serial connections
        ser = serial.Serial(
            port='COM3',
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )

        if (voltage >= MAX_VOLTAGE):
            powerOn = False
            print("ERROR - MAXIMUM VOLTAGE EXEEDED")
            logging.error("###############################")
            logging.error("ERROR - MAXIMUM VOLTAGE EXEEDED")
            logging.error("###############################")
            sendmail(EMAIL_RECIPIANTS, "ERROR - MAXIMUM VOLTAGE EXEEDED", "MAXIMUM VOLTAGE EXEEDED")

        elif ((powerOn == True)):
            ser.write('ADR 06\r')
            time.sleep(.1)
            ser.write('OUT 1\r')
            time.sleep(.1)
            ser.write('PV ' + str(voltage) + '\r')
            time.sleep(.1)
        if (powerOn == False):
            timeEnd = time.time()
            ser.write('OUT 0\r')
            ser.close()
            logging.shutdown()
            sys.exit
            exit(1)
    except:
        print("ERROR - FAILED TO CONNECT TO POWER SUPPY")
        sendmail(EMAIL_RECIPIANTS, "ERROR - Failed to connect to power supply", "FAILED POWER SUPPLY CONNECTION")
        ser.write('OUT 0\r')
        timeEnd = time.time()
        logging.shutdown()
        ser.close()
        sys.exit


############################################################ END POWER SUPPLY #
############################## OSCILLOSCOPE ###################################
# Oscilloscope startup
def initOscilloscope():
    try:

        rm = visa.ResourceManager('C:\\Program Files (x86)\\IVI Foundation\\VISA\\WinNT\\agvisa\\agbin\\visa32.dll')

        scope = rm.open_resource(scope_id)
        
        # set scope timeout
        scope.timeout = 5000

        # Set the ratio for the probes I.E. 10:1, 5:1
        # scope.write(":ACQ:SRAT 20E+9");
        # scope.write(":CHANnel1:PROBe 10")
        # scope.write(":CHANnel2:PROBe 10")
        # scope.write(":CHANnel3:PROBe 5")
        # scope.write(":CHANnel4:PROBe 10")
        # scope.write(":TRIGger:EDGE:LEVel 0.5V")

        # Clear the scope and autoscale it
        # scope.write("*CLS")
        print(scope.write("*IDN?"))
        # print("Scope initialized")
        # scope.write(":AUToscale")
        #scope.close()
        time.sleep(1)


    except Exception as err:
        timeEnd = time.time()
        # print('Exception: ' + str(err.message))
        logging.error("########################################################")
        logging.error("ERROR - FAILED TO INIT OSCILLOSCOPE (initOscilloscope())")
        logging.error("########################################################")
        logging.shutdown()
    # finally:
    #    print("Finished Ocilloscope Init\n\n")


def runOscilloscope(CHANNEL):
    try:
        rm = visa.ResourceManager('C:\\Program Files (x86)\\IVI Foundation\\VISA\\WinNT\\agvisa\\agbin\\visa32.dll')
        
        scope = rm.open_resource(scope_id)
        
        scope.timeout = 5000

        scope.write(':SYSTem:DSP ".";DSP ""')
        scope.write(':SYSTem:DSP Hello?')

        scope.write("*IDN?")
        #scope.write(":TRIGger:EDGE:SOURce CHANnel"+CHANNEL)
        print("Getting data from Oscilloscope ...")
        scope.read_termination = '\n'  # For ascii transfers the read is terminated with a newline character
        num_pts = int(scope.query(":WAV:POIN?"))  # Get the number of sample points in the waveform
        print("Max points: " + str(num_pts))
        scope.write(":WAV:SOURce CHANnel" + CHANNEL)
        scope.write(":WAV:FORMAT ASCII")
        scope.write(":WAVeform:POINts" + str(num_pts))
        wfm_ascii = scope.query(":WAV:DATA?")  # Get the first 1000 points of waveform data
        # print("The raw data is...")
        # print(wfm_ascii)
        wfm_ascii = wfm_ascii[10:-1]  # Remove a trailing ','
        wfm = [float(s) for s in wfm_ascii.split(',')]  # Convert the ascii list of strings to a list of floats
        # print("\nThe final cleaned signal is...")
        # print(wfm)
        x_inc = float(scope.query(":WAV:XINC?"))  # Get the waveform's X increment
        x_or = float(scope.query(":WAV:XOR?"))  # Get the waveform's X origin
        # mem_depth = float(scope.query(":ACQ:POIN?")) # Get the current memory depth
        # t = np.linspace(-mem_depth/sa_rate,mem_depth/sa_rate, len(wfm)) # Calculate the sample times of the waveform
        # t = np.linspace(x_or, x_or+1001*x_inc, 1000) # Calculate the sample times of the waveform
        # plt.plot(t,wfm) # Plot the waveform vs sample times
        time.sleep(.2)
        scope.close()
        
        # scope.write(":AUToscale") 

        print("Scope Connection Closed")
        return wfm

    except:
        timeEnd = time.time()
        print("ERROR - OSCILLOSCOPE")
        logging.error("######################################################")
        logging.error("ERROR - FAILED TO RUN OSCILLOSCOPE (runOscilloscope())")
        logging.error("######################################################")
        logging.shutdown()

###############################################################################

##############################  SAFETY CHECK & EMAIL  #########################
def safetyCheck(vc,vcp,cb,cbp):
    if(vc < (0.4 * vcp)):
       sendmail(EMAIL_RECIPIANTS,"ERROR - VERY LARGE VOLTAGE DROP","ERROR - LOW VOLTAGE")
    
    if(cb > (1.6 * cbp)):
       sendmail(EMAIL_RECIPIANTS,"ERROR - VERY LARGE CURRENT INCREASE","ERROR - HIGH CURRENT")

###############################################################################


######################## CALCULATE DATA FROM SCOPE ############################
def calculateData(scopeData1, channelThreeData=False, positiveData=False):
    
    try:
        halfOfWaveform = (len(scopeData1) * .5)
        quarterOfWaveform = (len(scopeData1) * .25)
        tenthOfWaveform = (len(scopeData1) * .10)
        tenthOfQuarterWaveform = (quarterOfWaveform * .10)
    
        trimmedData = scopeData1[int(len(scopeData1) * startPoint): int(len(scopeData1) * endPoint)]
        averageDataPoint = sum(trimmedData) / len(trimmedData)

        return averageDataPoint
    except:
        print("ERROR in Calculate Waveform Data")

######################################## END CALCULATE DATA FROM SCOPE ########


##############################  CAPTURE ID  ###################################

def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

#############################  END CAPTURE ID  ################################


#############################  SAVE TO DATABASE  ##############################

def saveData(dataOne,dataTwo,dataThree,dataFour,voltage,ind_current,outputVoltage,output_current,dateAndTime):
    
    # conn = sqlite3.connect('test.db')

    # print("Opened database successfully")

    print("Saving...")
    
    capture_id = randomString()

    # c = conn.cursor()

    # # conn.execute('''CREATE TABLE ABCD
    # #         (CURRENT INT PRIMARY NOT NULL);''')

    cnx = mysql.connector.connect(user='avijit', password='12345678',
                              host='DESKTOP-5FHA2FU',
                              database='arl_gan_db')
    
    c = cnx.cursor()

    # c.execute("INSERT INTO CALC_AVG1 VALUES(%s,%s,%f,%f,%f)", (dateAndTime,capture_id,voltage,ind_current,rds_1))

    # mySql_insert_query = """INSERT INTO CALC_AVG1 VALUES(?,?,?,?,?)", (dateAndTime,capture_id,voltage,ind_current,rds_1)"""

    add_query_1 = ("INSERT INTO CALC_AVG1"
                  "(DATE_TIME,CAPTURE_ID,CLAMP_VOLTAGE,IND_CURRENT,OUTPUT_VOLTAGE,OUTPUT_CURRENT)"
                  " VALUES(%s,%s,%s,%s,%s,%s)")
    add_values_1 = (dateAndTime,capture_id,voltage,ind_current,outputVoltage,output_current)

    c.execute(add_query_1,add_values_1)

    add_query_2 = ("INSERT INTO RAW_DATA1"
                  "(DATE_TIME,CAPTURE_ID,CLAMP_VOLTAGE,IND_CURRENT,OUTPUT_VOLTAGE,OUTPUT_CURRENT)"
                  " VALUES(%s,%s,%s,%s,%s,%s)")
    add_values_1 = (dateAndTime,capture_id,voltage,ind_current,outputVoltage,output_current)

    if(not((dataOne == None) or (dataTwo == None) or (dataThree == None) or (dataFour == None))):
        for x in range(len(dataOne)):
            c.execute(add_query_2, (dateAndTime,capture_id,dataOne[x],dataTwo[x],dataThree[x],dataFour[x]))
    
    #conn.execute("INSERT INTO TEST_TABLE (ID, NAME, AGE) \
    #    VALUES (7, 'jkea', 35)");

    '''cursor = conn.execute("SELECT ID, NAME, AGE from TEST_TABLE")
    for row in cursor:
        print("ID = ", row[0])
        print("NAME = ", row[1])
        print("AGE = ", row[2])'''

    # print("Table created successfully")

    cnx.commit()

    cnx.close()
    print("Saved to database")
    
###############################################################################


############################### TESTING #######################################

if __name__ == "__main__":
    run()

# sendmail("majazi@uncc.edu", "Test", "Subject")
# initOscilloscope()
# powerSupply(25)
# time.sleep(5)
# powerSupply(0, False)


# -> oscilloscope()

# googleDriveUpload()