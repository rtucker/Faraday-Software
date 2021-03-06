#Imports - General

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../Faraday_Proxy_Tools")) #Append path to common tutorial FaradayIO module
#Imports - Faraday Specific
from FaradayIO import faradaybasicproxyio
from FaradayIO import faradaycommands



#Local device information
local_device_callsign = 'REPLACEME'  # Should match the connected Faraday unit as assigned in Proxy configuration
local_device_node_id = REPLACEME  # Should match the connected Faraday unit as assigned in Proxy configuration

#Start the proxy server after configuring the configuration file correctly
#Setup a Faraday IO object
faraday_1 = faradaybasicproxyio.proxyio()
faraday_cmd = faradaycommands.faraday_commands()

#Remote device information
remote_callsign = 'KB1LQC' #case independant
remote_id = 1

#Define constants
PROXY_MESSAGE_EXPERIMENTAL_PORT = 3
PROXY_GET_TIMEOUT = 1 #Second(s)

#Print debug information about proxy port listening
print "Receiver operating TCP Localhost port:", faraday_1.FLASK_PORT

#Setup variables for receiving
data = None

#While loop to wait for reception of data packet from experimental message application
while(1):
    #Wait until there is new data on the message application port OR timout
    data = faraday_1.GETWait(local_device_callsign, local_device_node_id, PROXY_MESSAGE_EXPERIMENTAL_PORT, 2)

    #Check if data is False (False means that the Get() function timed out), if not then display new data
    if (data != None) and (not 'error' in data):
        #print "Received Message RAW", repr(data[0]['data'])
        print "Received Message Decoded:", faraday_1.DecodeRawPacket(data[0]['data'])

        #Set data = False so that the function loop can properly wait until the next data without printing last received data over and over
        data = None