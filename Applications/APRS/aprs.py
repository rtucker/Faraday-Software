#-------------------------------------------------------------------------------
# Name:        /aprs/aprs.py
# Purpose:      Query telemetry server for station data to send to an APRS-IS
#               socket connection. Currently provide only one way data flow
#
# Author:      Bryce Salmi
#
# Created:     12/4/2016
# Licence:     GPLv3
#-------------------------------------------------------------------------------

import logging.config
import threading
import ConfigParser
import os
import sys
import socket
import requests
from time import sleep

# Can we clean this up?
sys.path.append(os.path.join(os.path.dirname(__file__), "../../Faraday_Proxy_Tools/")) #Append path to common tutorial FaradayIO module
from FaradayIO import faradaybasicproxyio
from FaradayIO import telemetryparser

# Start logging after importing modules
logging.config.fileConfig('loggingConfig.ini')
logger = logging.getLogger('aprs')

# Load Telemetry Configuration from telemetry.ini file
# Should have common file for apps...
aprsConfig = ConfigParser.RawConfigParser()
aprsConfig.read('aprs.ini')

# Read in APRS-IS Credentials
aprsISConfig = ConfigParser.RawConfigParser()
aprsISConfig.read('login.ini')

# Create and initialize dictionary queues
telemetryDicts = {}


def aprs_worker(config, sock):
    """
    Obtains telemetry with infinite loop, forwards to APRS-IS server

    :param config: Configuration file descriptor from aprs.INI
    :param sock: Internet socket
    :return: None
    """
    logger.info('Starting aprs_worker thread')
    rate = config.getint("aprsis", "rate")

    # Local variable initialization
    telemSequence = 0

    # Start infinite loop to send station data to APRS-IS
    while(True):
        # Query telemetry database for station data
        stations = getStations()
        stationData = getStationData(stations)

        # Iterate through all stations sending telemetry and position data
        sendPositions(stationData, sock)
        telemSequence = sendtelemetry(stationData, telemSequence, sock)
        sendTelemLabels(stationData, sock)
        sendParameters(stationData, sock)
        sendEquations(stationData, sock)

        # Sleep for intended update rate (seconds)
        sleep(rate)

def getStations():
    """
    Queries telemetry server for active stations

    :return: JSON results from request
    """

    # Read configuration to query telemetry server
    host = aprsConfig.get("telemetry", "host")
    port = aprsConfig.get("telemetry", "port")

    # Construct station URL and query for active stations
    url = "http://" + host + ":" + port + "/stations"
    logger.debug(url)

    r = requests.get(url)
    results = r.json()

    # Return extracted JSON data
    return results

def getStationData(stations):
    """
    Queries telemetry server for detailed telemetry from active stations

    :param stations: List of callsign + nodeids to get telemetry data from
    :return: list containing latest station telemetry
    """

    # Initialize lists
    stationData = []

    # Read configuration to query telemetry server
    host = aprsConfig.get("telemetry", "host")
    port = aprsConfig.get("telemetry", "port")
    age = aprsConfig.getint('aprsis', 'stationsage')

    # Construct base URL to get station data from telemetry server
    url = "http://" + host + ":" + port + "/"

    # Iterate through each station and request latest telemetry data entry
    for station in stations:
        # Extract station identification data from active stations
        callsign = station["SOURCECALLSIGN"]
        nodeid = station["SOURCEID"]
        epoch = station["EPOCH"]

        # Construct request dictionary payload
        payload = {"callsign": callsign, "nodeid": nodeid, "timespan": age, "limit": 1}

        # Request data, append to stationData list
        try:
            r = requests.get(url, params = payload)
            data = r.json()

        except requests.exceptions.RequestException as e:
            logger.error(e)

        else:
            stationData.append(data)

    # Return all detailed stationData
    return stationData

def nmeaToDegDecMin(latitude,longitude):
    """
    Converts NMEA string latitude and longitude data into degree decimal minutes data compatible with
    APRS-IS server requirements per APRS Protocol Version 1.0

    :param latitude: NMEA latitude string
    :param longitude: NMEA longitude string
    :return: list of latitude and longitude strings per APRS protocol version 1
    """

    # Convert NMEA to Decimal Degrees
    latDeg = latitude[:2]  # latitude degrees
    lonDeg = longitude[:3]  # Longitude degrees
    latDec = round(float(latitude[2:]), 2)  # Latitude decimal minutes
    lonDec = round(float(longitude[3:]), 2)  # Longitude decimal minutes

    # round decimal minutes to 2 dec places & make 5 characters, zero fill
    latDec = str("%.2f" % latDec).zfill(5)
    lonDec = str("%.2f" % lonDec).zfill(5)

    # Combine into APRS-IS compliant lat/lon position
    latString = latDeg + str(latDec)
    lonString = lonDeg + str(lonDec)

    return [latString,lonString]


def sendPositions(stations, socket):
    """
    Constructs an APRS position string for station and sends to a socket

    :param stations: List of dictionary organized station data
    :param socket: APRS-IS server internet socket
    :return: None
    """

    # Iterate through each station and generate an APRS position string
    # then send the string to the socket for each station in list
    for item in stations:
        station = item[0]

        # Get Station data from GPS data
        sourceCallsign = station["SOURCECALLSIGN"]
        sourceID = station["SOURCEID"]
        destinationCallsign = station["DESTINATIONCALLSIGN"]
        destinationID = station["DESTINATIONID"]
        latitude = station["GPSLATITUDE"]
        longitude = station["GPSLONGITUDE"]
        latitudeDirection = station["GPSLATITUDEDIR"]
        longitudeDir = station["GPSLONGITUDEDIR"]
        altitude = station["GPSALTITUDE"]
        speed = station["GPSSPEED"]
        gpsFix = station["GPSFIX"]

        # Get APRS configuration
        qConstruct = aprsConfig.get('aprs', 'qconstruct')
        dataTypeIdent = aprsConfig.get('aprs', 'datatypeident')
        destAddress = aprsConfig.get('aprs', 'destaddress')
        symbolTable = aprsConfig.get('aprs', 'symboltable')
        symbol = aprsConfig.get('aprs', 'symbol')
        altSymbolTable = aprsConfig.get('aprs', 'altsymboltable')
        altSymbol = aprsConfig.get('aprs', 'altsymbol')
        comment = aprsConfig.get('aprs', 'comment')
        altComment = aprsConfig.get('aprs', 'altcomment')

        # Create nodes from GPS data
        node = sourceCallsign + "-" + str(sourceID)
        destNode = destinationCallsign + "-" + str(destinationID)

        # Convert position to APRS-IS compliant string
        latString,lonString = nmeaToDegDecMin(latitude,longitude)

        # Convert altitude and speed to APRS compliant values
        try:
            rawaltitude = str(round(altitude, 0)).split('.')
            rawspeed = str(round(speed, 0)).split('.')

        except TypeError as e:
            logger.error(e)
            logger.error(altitude)
            logger.error(speed)

        else:
            altitude = rawaltitude[0].zfill(6)
            speed = rawspeed[0].zfill(3)


            # If GPSFix is not valid warn user
            if gpsFix <= 0:
                logger.warning(node + " No GPS Fix")

            if node != destNode:
                # APRS string is for remote RF node
                aprsPosition = dataTypeIdent +\
                               latString +\
                               latitudeDirection +\
                               symbolTable +\
                               lonString +\
                               longitudeDir +\
                               symbol
                try:
                    logger.info(aprsPosition)
                except:
                    pass

                positionString = node +\
                                 '>' +\
                                 destAddress +\
                                 ',' +\
                                 qConstruct +\
                                 ',' +\
                                 destNode +\
                                 ':' +\
                                 aprsPosition +\
                                 '.../' +\
                                 speed +\
                                 '/A=' +\
                                 altitude +\
                                 comment +\
                                 '\r'

                logger.debug(positionString)

                try:
                    socket.sendall(positionString)

                except socket.error as e:
                    logger.error(e)

            elif node == destNode:
                # APRS string is for local node
                aprsPosition = dataTypeIdent +\
                               latString +\
                               latitudeDirection +\
                               altSymbolTable +\
                               lonString +\
                               longitudeDir +\
                               altSymbol
                positionString = node +\
                                 ">" +\
                                 destAddress +\
                                 ':' +\
                                 aprsPosition +\
                                 '.../' +\
                                 speed +\
                                 '/A=' +\
                                 altitude +\
                                 altComment +\
                                 '\r'
                logger.debug(positionString)

                try:
                    socket.sendall(positionString)

                except socket.error as e:
                    logger.error(e)

def sendtelemetry(stations, telemSequence, socket):
    """
    Constructs an APRS telemetry string for each station and sends it to the socket

    :param stations: List of dictionary organized station data
    :param telemSequence: Telemetry sequence number from 0 to 999, incrementing
    :param socket: APRS-IS server internet socket
    :return: None
    """


    for item in stations:
        station = item[0]

        # Get Station data from GPS data
        sourceCallsign = station["SOURCECALLSIGN"]
        sourceID = station["SOURCEID"]
        destinationCallsign = station["DESTINATIONCALLSIGN"]
        destinationID = station["DESTINATIONID"]
        gpsFix = station["GPSFIX"]
        gpioValues = station["GPIOSTATE"]
        rfValues = station["RFSTATE"]

        # Get APRS Telemetry configuration
        qConstruct = aprsConfig.get('aprs', 'qconstruct')
        destAddress = aprsConfig.get('aprs', 'destaddress')
        ioSource = aprsConfig.get('aprs', 'iosource')

        # Extract IO data
        if ioSource == 'gpio':
            ioList = bin(gpioValues)[2:].zfill(8)
        elif ioSource == 'rf':
            ioList = bin(rfValues)[2:].zfill(8)

        # Create nodes from GPS data
        node = sourceCallsign + "-" + str(sourceID)
        destNode = destinationCallsign + "-" + str(destinationID)

        if node != destNode:
            # APRS string is for remote RF node
            telemetry = node +\
                        '>' +\
                        destAddress +\
                        ',' +\
                        qConstruct +\
                        ',' +\
                        destNode +\
                        ':T#' +\
                        str(telemSequence).zfill(3) +\
                        ',' +\
                        str(station["ADC0"]/16).zfill(3) +\
                        ',' +\
                        str(station["ADC1"]/16).zfill(3) +\
                        ',' +\
                        str(station["ADC3"]/16).zfill(3) +\
                        ',' +\
                        str(station["ADC6"]/16).zfill(3) +\
                        ',' +\
                        str(station["BOARDTEMP"]/16).zfill(3) +\
                        ',' +\
                        ioList +\
                        '\r'

            logger.debug(telemetry)

            try:
                socket.sendall(telemetry)

            except socket.error as e:
                logger.error(e)

        elif node == destNode:
            # APRS string is for local node
            telemetry = node +\
                        '>' +\
                        destAddress +\
                        ':T#' +\
                        str(telemSequence).zfill(3) +\
                        ',' +\
                        str(station["ADC0"]/16).zfill(3) +\
                        ',' +\
                        str(station["ADC1"]/16).zfill(3) +\
                        ',' +\
                        str(station["ADC3"]/16).zfill(3) +\
                        ',' +\
                        str(station["ADC6"]/16).zfill(3) +\
                        ',' +\
                        str(station["BOARDTEMP"]/16).zfill(3) +\
                        ',' +\
                        ioList +\
                        '\r'

            logger.debug(telemetry)

            try:
                socket.sendall(telemetry)

            except socket.error as e:
                logger.error(e)

        # Check for telemetry sequence rollover
        if telemSequence >= 999:
            telemSequence = 0
        else:
            telemSequence += 1
        # Return telemetrySequence to save count
        return telemSequence

def sendTelemLabels(stations, socket):
    """
    Constructs an APRS unit/label string for each station and sends it to the socket

    :param stations: List of dictionary organized station data
    :param socket: APRS-IS server internet socket
    :return: None
    """

    for item in stations:
        station = item[0]

        # Get Station data from GPS data
        sourceCallsign = station["SOURCECALLSIGN"]
        sourceID = station["SOURCEID"]
        destinationCallsign = station["DESTINATIONCALLSIGN"]
        destinationID = station["DESTINATIONID"]
        gpsFix = station["GPSFIX"]


        # Get APRS Telemetry configuration
        qConstruct = aprsConfig.get('aprs', 'qconstruct')
        destAddress = aprsConfig.get('aprs', 'destaddress')

        # Get units and labels from configuration file
        unit0 = aprsConfig.get('aprs', 'unit0')
        unit1 = aprsConfig.get('aprs', 'unit1')
        unit2 = aprsConfig.get('aprs', 'unit2')
        unit3 = aprsConfig.get('aprs', 'unit3')
        unit4 = aprsConfig.get('aprs', 'unit4')
        bLabel0 = aprsConfig.get('aprs', 'blabel0')
        bLabel1 = aprsConfig.get('aprs', 'blabel1')
        bLabel2 = aprsConfig.get('aprs', 'blabel2')
        bLabel3 = aprsConfig.get('aprs', 'blabel3')
        bLabel4 = aprsConfig.get('aprs', 'blabel4')
        bLabel5 = aprsConfig.get('aprs', 'blabel5')
        bLabel6 = aprsConfig.get('aprs', 'blabel6')
        bLabel7 = aprsConfig.get('aprs', 'blabel7')

        # Create nodes from GPS data
        node = sourceCallsign + "-" + str(sourceID)
        destNode = destinationCallsign + "-" + str(destinationID)

        if node != destNode:
            # APRS string is for remote node
            labels = node +\
                     '>' +\
                     destAddress +\
                     ',' +\
                     qConstruct +\
                     ',' +\
                     destNode +\
                     '::' +\
                     node +\
                     ' :' +\
                     "UNIT." +\
                     str(unit0[:6]) +\
                     ',' +\
                     str(unit1[:6]) +\
                     ',' +\
                     str(unit2[:5]) +\
                     ',' +\
                     str(unit3[:5]) +\
                     ',' +\
                     str(unit4[:4]) +\
                     ',' +\
                     str(bLabel0[:5]) +\
                     ',' +\
                     str(bLabel1[:4]) +\
                     ',' +\
                     str(bLabel2[:3]) +\
                     ',' +\
                     str(bLabel3[:3]) +\
                     ',' +\
                     str(bLabel4[:3]) +\
                     ',' +\
                     str(bLabel5[:2]) +\
                     ',' +\
                     str(bLabel6[:2]) +\
                     ',' +\
                     str(bLabel7[:2]) +\
                     '\r'
            logger.debug(labels)

            try:
                socket.sendall(labels)

            except socket.error as e:
                logger.error(e)

        elif node == destNode:
            # APRS string is for local node
            labels = node +\
                     '>' +\
                     destAddress +\
                     '::' +\
                     node +\
                     ' :' +\
                     "UNIT." +\
                     str(unit0[:6]) +\
                     ',' +\
                     str(unit1[:6]) +\
                     ',' +\
                     str(unit2[:5]) +\
                     ',' +\
                     str(unit3[:5]) +\
                     ',' +\
                     str(unit4[:4]) +\
                     ',' +\
                     str(bLabel0[:5]) +\
                     ',' +\
                     str(bLabel1[:4]) +\
                     ',' +\
                     str(bLabel2[:3]) +\
                     ',' +\
                     str(bLabel3[:3]) +\
                     ',' +\
                     str(bLabel4[:3]) +\
                     ',' +\
                     str(bLabel5[:2]) +\
                     ',' +\
                     str(bLabel6[:2]) +\
                     ',' +\
                     str(bLabel7[:2]) +\
                     '\r'

            logger.debug(labels)
            try:
                socket.sendall(labels)

            except socket.error as e:
                logger.error(e)

def sendParameters(stations, socket):
    """
    Constructs an APRS parameters string for each station and sends it to the socket

    :param stations: List of dictionary organized station data
    :param socket: APRS-IS server internet socket
    :return:
    """

    for item in stations:
        station = item[0]

        # Get Station data from GPS data
        sourceCallsign = station["SOURCECALLSIGN"]
        sourceID = station["SOURCEID"]
        destinationCallsign = station["DESTINATIONCALLSIGN"]
        destinationID = station["DESTINATIONID"]
        gpsFix = station["GPSFIX"]


        # Get APRS Telemetry configuration
        qConstruct = aprsConfig.get('aprs', 'qconstruct')
        destAddress = aprsConfig.get('aprs', 'destaddress')

        adc0 = aprsConfig.get('aprs', 'adc0param')
        adc1 = aprsConfig.get('aprs', 'adc1param')
        adc2 = aprsConfig.get('aprs', 'adc2param')
        adc3 = aprsConfig.get('aprs', 'adc3param')
        adc4 = aprsConfig.get('aprs', 'adc4param')
        io0 = aprsConfig.get('aprs', 'io0param')
        io1 = aprsConfig.get('aprs', 'io1param')
        io2 = aprsConfig.get('aprs', 'io2param')
        io3 = aprsConfig.get('aprs', 'io3param')
        io4 = aprsConfig.get('aprs', 'io4param')
        io5 = aprsConfig.get('aprs', 'io5param')
        io6 = aprsConfig.get('aprs', 'io6param')
        io7 = aprsConfig.get('aprs', 'io7param')

        # Create nodes from GPS data
        node = sourceCallsign + "-" + str(sourceID)
        destNode = destinationCallsign + "-" + str(destinationID)

        if node != destNode:
            # APRS string is for remote node
            parameters = node +\
                         '>' +\
                         destAddress +\
                         ',' +\
                         qConstruct +\
                         ',' +\
                         destNode +\
                         '::' +\
                         node +\
                         ' :' +\
                         "PARM." +\
                         str(adc0[:6]) +\
                         ',' +\
                         str(adc1[:6]) +\
                         ',' +\
                         str(adc2[:5]) +\
                         ',' +\
                         str(adc3[:5]) +\
                         ',' +\
                         str(adc4[:4]) +\
                         ',' +\
                         str(io0[:5]) +\
                         ',' +\
                         str(io1[:4]) +\
                         ',' +\
                         str(io2[:3]) +\
                         ',' +\
                         str(io3[:3]) +\
                         ',' +\
                         str(io4[:3]) +\
                         ',' +\
                         str(io5[:2]) +\
                         ',' +\
                         str(io6[:2]) +\
                         ',' +\
                         str(io7[:2]) +\
                         '\r'

            logger.debug(parameters)
            try:
                socket.sendall(parameters)

            except socket.error as e:
                logger.error(e)

        elif node == destNode:
            # APRS string is for local node
            parameters = node +\
                         '>' +\
                         destAddress +\
                         '::' +\
                         node +\
                         ' :' +\
                         "PARM." +\
                         str(adc0[:6]) +\
                         ',' +\
                         str(adc1[:6]) +\
                         ',' +\
                         str(adc2[:5]) +\
                         ',' +\
                         str(adc3[:5]) +\
                         ',' +\
                         str(adc4[:4]) +\
                         ',' +\
                         str(io0[:5]) +\
                         ',' +\
                         str(io1[:4]) +\
                         ',' +\
                         str(io2[:3]) +\
                         ',' +\
                         str(io3[:3]) +\
                         ',' +\
                         str(io4[:3]) +\
                         ',' +\
                         str(io5[:2]) +\
                         ',' +\
                         str(io6[:2]) +\
                         ',' +\
                         str(io7[:2]) +\
                         '\r'

            logger.debug(parameters)
            try:
                socket.sendall(parameters)

            except socket.error as e:
                logger.error(e)

def sendEquations(stations, socket):
    """
    Constructs an APRS equation string for each station and sends it to the socket

    :param stations: List of dictionary organized station data
    :param socket: APRS-IS server internet socket
    :return: None
    """

    for item in stations:
        station = item[0]

        # Get Station data from GPS data
        sourceCallsign = station["SOURCECALLSIGN"]
        sourceID = station["SOURCEID"]
        destinationCallsign = station["DESTINATIONCALLSIGN"]
        destinationID = station["DESTINATIONID"]
        gpsFix = station["GPSFIX"]


        # Get APRS Telemetry configuration
        qConstruct = aprsConfig.get('aprs', 'qconstruct')
        destAddress = aprsConfig.get('aprs', 'destaddress')

        # Get equations from configuration file
        eq0a = aprsConfig.get('aprs', 'eq0a')
        eq0b = aprsConfig.get('aprs', 'eq0b')
        eq0c = aprsConfig.get('aprs', 'eq0c')
        eq1a = aprsConfig.get('aprs', 'eq1a')
        eq1b = aprsConfig.get('aprs', 'eq1b')
        eq1c = aprsConfig.get('aprs', 'eq1c')
        eq2a = aprsConfig.get('aprs', 'eq2a')
        eq2b = aprsConfig.get('aprs', 'eq2b')
        eq2c = aprsConfig.get('aprs', 'eq2c')
        eq3a = aprsConfig.get('aprs', 'eq3a')
        eq3b = aprsConfig.get('aprs', 'eq3b')
        eq3c = aprsConfig.get('aprs', 'eq3c')
        eq4a = aprsConfig.get('aprs', 'eq4a')
        eq4b = aprsConfig.get('aprs', 'eq4b')
        eq4c = aprsConfig.get('aprs', 'eq4c')

        # Create nodes from GPS data
        node = sourceCallsign + "-" + str(sourceID)
        destNode = destinationCallsign + "-" + str(destinationID)

        if node != destNode:
            # APRS string is for remote node
            equations = node +\
                        '>' +\
                        destAddress +\
                        ',' +\
                        qConstruct +\
                        ',' +\
                        destNode +\
                        '::' +\
                        node +\
                        ' :' +\
                        "EQNS." +\
                        str(eq0a) +\
                        ',' +\
                        str(eq0b) +\
                        ',' +\
                        str(eq0c) +\
                        ',' +\
                        str(eq1a) +\
                        ',' +\
                        str(eq1b) +\
                        ',' +\
                        str(eq1c) +\
                        ',' +\
                        str(eq2a) +\
                        ',' +\
                        str(eq2b) +\
                        ',' +\
                        str(eq2c) +\
                        ',' +\
                        str(eq3a) +\
                        ',' +\
                        str(eq3b) +\
                        ',' +\
                        str(eq3c) +\
                        ',' +\
                        str(eq4a) +\
                        ',' +\
                        str(eq4b) +\
                        ',' +\
                        str(eq4c) +\
                        '\r'

            logger.debug(equations)
            try:
                socket.sendall(equations)

            except socket.error as e:
                logger.error(e)

        elif node == destNode:
            # APRS string is for local node
            equations = node +\
                         '>' +\
                         destAddress +\
                         '::' +\
                         node +\
                         ' :' +\
                         "EQNS." +\
                         str(eq0a) +\
                         ',' +\
                         str(eq0b) +\
                         ',' +\
                         str(eq0c) +\
                         ',' +\
                         str(eq1a) +\
                         ',' +\
                         str(eq1b) +\
                         ',' +\
                         str(eq1c) +\
                         ',' +\
                         str(eq2a) +\
                         ',' +\
                         str(eq2b) +\
                         ',' +\
                         str(eq2c) +\
                         ',' +\
                         str(eq3a) +\
                         ',' +\
                         str(eq3b) +\
                         ',' +\
                         str(eq3c) +\
                         ',' +\
                         str(eq4a) +\
                         ',' +\
                         str(eq4b) +\
                         ',' +\
                         str(eq4c) +\
                         '\r'

            logger.debug(equations)
            try:
                socket.sendall(equations)

            except socket.error as e:
                logger.error(e)

def connectAPRSIS():
    """
    Connect to APRS-IS server with login credentials

    :return: APRS-IS socket connection
    """

    # Read APRS-IS login credentials from configuration file
    callsign = aprsISConfig.get('credentials', 'callsign')
    passcode = aprsISConfig.getint('credentials', 'passcode')

    # Read APRS-IS server address from configuration file
    server = aprsConfig.get("aprsis", "server")
    port = aprsConfig.getint("aprsis", "port")

    logger.info("Connecting to APRS-IS as: " + str(callsign))
    logger.info("Server: " + str(server) + ":" + str(port))

    # Set socket up
    aprssock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Infinite loop until connection is successful
    while True:
        try:
            # Create login string and connect to server
            logon_string = 'user' + ' ' + callsign + ' ' + 'pass' + ' ' + str(
                passcode) + ' vers "FaradayRF APRS-IS application" \r'
            logger.debug(logon_string)
            aprssock.connect((server, port))
            aprssock.sendall(logon_string)

        except socket.error as e:
            logger.error(e)

        else:
            logger.info("Connection successful!")
            return aprssock
            break

        sleep(10)  # Try to reconnect every 10 seconds
    return aprssock

def main():
    """
    Main function which starts telemery worker thread + Flask server.

    :return: None
    """

    logger.info('Starting Faraday APRS-IS application')
    sock = connectAPRSIS()

    # Initialize local variables
    threads = []

    t = threading.Thread(target=aprs_worker, args=(aprsConfig, sock))
    threads.append(t)
    t.start()

if __name__ == '__main__':
    main()