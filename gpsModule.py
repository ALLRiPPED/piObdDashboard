import time
import socketio
import json
import datetime
from gps import *

#see https://gpsd.gitlab.io/gpsd/gpsd_json.html for more details on getting data from gpsd

SENSOR_TYPE = 'GPS'
ERROR = 'ERR'
LATITUDE_DEC_PLACES = 5
LONGITUDE_DEC_PLACES = 5
SPEED_DEC_PLACES = 2
FT_DEC_PLACES = 2
MPH_MULTIPLIER = 2.2369
FT_MULTIPLIER = 3.28084

GPS_STATUSES = { #dict key value pair of possible gps status from NMEA TPV object
    0: 'Unknown',
    1: 'Normal',
    2: 'DGPS',
    3: 'RTK Fixed',
    4: 'RTK Floating',
    5: 'DR',
    6: 'GNSSDR',
    7: 'Time (surveyed)',
    8: 'Simulated',
    9: 'P(Y)'
}
    
DELAY = 1 #gps polling interval in seconds. Max polling rate 10hz for Adafruit Ultimate GPS (MTK3339 chipset)
gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 

sio = None

numTries = 1
while True: #loop until a connection is made with the server instead of immediately exiting
    try:
        sio = socketio.Client()
        sio.connect('http://localhost:3000')
        
        break
    except Exception as ex:
        numTries += 1
        print("Unable to connect to node server, retrying attempt {0}".format(numTries))
        time.sleep(1)
            
        continue

def formatDecimalPlaces(dec, numPlaces):
    formatPlaces = "{:." + str(numPlaces) + "f}"
    return formatPlaces.format(dec)

def createLogMessage(logType, sensorType, ex, args):
    now = datetime.datetime.now()
    timeStamp = "%d:%d:%d" % (now.hour, now.minute, now.second)
            
    return {
        'logType': logType,
        'sensor' : sensorType,
        'exType' : ex, #pass empty string if not exception
        'args' : args,
        'timeStamp': timeStamp
    }

def emitGpsData():
    while True:
        time.sleep(DELAY)
     
        try:
            report = gpsd.next()

            if report['class'] == 'TPV': #time-position-velocity report object
                data = {
                    'fixType': GPS_STATUSES[getattr(report,'status','')],
                    'latitude': formatDecimalPlaces(getattr(report,'lat',0.0), LATITUDE_DEC_PLACES),
                    'longitude': formatDecimalPlaces(getattr(report,'lon',0.0), LONGITUDE_DEC_PLACES),
                    'time': getattr(report,'time',''), #Time/date stamp in ISO8601 format, UTC. May have a fractional part of up to .001sec precision. May be absent if the mode is not 2D or 3D.
                    'altitude': getattr(report,'alt','nan'),#Altitude, height above ellipsoid, in meters. Probably WGS84.
                    'speed': formatDecimalPlaces((getattr(report,'speed',0.0) * MPH_MULTIPLIER), SPEED_DEC_PLACES), #mph converted from meters per second
                    'climb': getattr(report,'climb','nan'), #Climb (positive) or sink (negative) rate, meters per second.
                    'latitudeErr': getattr(report,'epy','nan'), #Latitude error estimate in meters. Certainty unknown.
                    'longitudeErr': getattr(report,'epx','nan'), #Longitude error estimate in meters. Certainty unknown.
                    'timeErr': getattr(report,'ept','nan'), #Estimated time stamp error in seconds. Certainty unknown.
                    'altitudeErr': getattr(report,'epv','nan'), #Estimated vertical error in meters. Certainty unknown.
                    'speedErr': formatDecimalPlaces((getattr(report,'eps',0.0) * MPH_MULTIPLIER), SPEED_DEC_PLACES),#Estimated speed error in meters per second. Certainty unknown.
                    'climbErr': getattr(report,'epc', 'nan') #Estimated climb error in meters per second. Certainty unknown.
                }
                print(data)
                sio.emit('gpsData', json.dumps(data))
                
        except Exception as ex: #logs any errors encountered during reading of gps. Also allows program to pick back up if node server connection is lost
            errorLog = createLogMessage(ERROR, SENSOR_TYPE, type(ex).__name__, ex.args)
            print(errorLog)
            sio.emit('log', json.dumps(errorLog)) #will only work if exception is unrelated to node server connection
            continue

@sio.event
def connect():
    print("Gps connected to node server!")
    emitGpsData()
       
