
# The Proxy Interface

[Proxy](../../proxy) is the gateway to Faraday. It is a Flask server providing a RESTful interface with Faraday hardware. All actions with Faraday from a computer go through Proxy. To learn the details of Proxy read its documentation.

## Configuring Proxy
Proxy.ini is a plaintext ASCII file which contains the necessary configuration values to properly connect with and identify hardware when Proxy is initialized. Multiple Radios can be connected at once by simple extension of the [UNITx] sections where x is the zero-indexed enumeration of Faraday radios connected to the computer.

>This guide assumes you have already [connected a Faraday radio](connecting-hardware.md) to your computer!

### Proxy Configs Overview
 * `[FLASK]`: Flask server configuration values
  * `HOST`: IP Address or hostname of flask server
  * `PORT`: Network port to serve data
 * `[PROXY]`: Proxy server high level configuration
  * `UNITS`: Quantity of Faraday radios connected to computer
 * `[UNIT0]`: Unit 0 Proxy configuration values section
  * `CALLSIGN`: Callsign to associate with radio on this USB port
  * `NODEID`: Node ID of radio connected on this USB port
  * `COM`: COM/serial Port associated with the radio connected
  
The image below shows the default `proxy.ini` contents as viewed in a text editor.

![Proxy INI Text Editor](images/Proxy-INI.png "Proxy INI Text Editor")

### Windows

> There is no need to change any other Proxy.ini settings unless you know what you're doing!

 1. Open the `proxy-template.ini` file in a text editor to edit `[UNIT0]` values
 2. Change `CALLSIGN` Replace `REPLACEME` to match your callsign
 3. Change `NODEID` to an appropriate node ID value that is not already in use. Numbers between 0-255 are valid.
 4. Change `COM` to match the COM port indicated while [connecting Faraday](connecting-hardware.md). `x` represents a number.
 5. Save the file as `proxy.ini`

A proper configuration file will look similar to the configuration below. Notice the radio is `KB1LQD-1` on `COM71`.

![Proxy INI Example](images/Proxy-INI-Example.png "Proxy INI Example")

###Linux (Debian-Based)

> There is no need to change any other Proxy.ini settings unless you know what you're doing!

 1. Open `proxy-template.ini` with a text editor i.e `gedit git/faradayrf/software/proxy/proxy-template.ini`
 2. Update `CALLSIGN` Replace `REPLACEME` to match your callsign
 3. Update `NODEID` to an appropriate node ID value that is not already in use. Numbers between 0-255 are valid.
 4. Update `COM` to match the device dev path indicated while [connecting Faraday](connecting-hardware.md).
 5. Save the file as `proxy.ini`

A proper configuration file will look similar to the configuration below. Notice the radio is `KB1LQD-1` on `COM71`. For Debian `COM71` would be `/dev/ttyUSB0` in this example.

###Mac OS X

> There is no need to change any other Proxy.ini settings unless you know what you're doing!

 1. Open `proxy-template.ini` with a text editor `faradayrf/software/proxy/proxy-template.ini`
 2. Update `CALLSIGN` Replace `REPLACEME` to match your callsign
 3. Update `NODEID` to an appropriate node ID value that is not already in use. Numbers between 0-255 are valid.
 4. Update `COM` to match the device dev path indicated while [connecting Faraday](connecting-hardware.md).
 5. Save the file as `proxy.ini`

A proper configuration file will look similar to the configuration below. Notice the radio is `KB1LQD-1` on COM71. For Mac OS X `COM71` would be `/dev/cu.usbserial-40` as an example.

## Connecting Proxy to Faraday

Double-click on `proxy.py` to run it from a file explorer.
Alternatively one can simply run proxy from command line:

### Windows
For example `python C:\faradayrf\software\proxy\proxy.py`

###Linux (Debian-Based)
For example `python faradayrf/software/proxy/proxy.py`

###Mac OS X
For example `python faradayrf/software/proxy/proxy.py`

###Proxy Running
With Faraday connected and `proxy.py` properly configured you will see a screen similar to that shown below upon initialization.

![Successful Proxy Connection](images/Proxy-Success-Connection.png "Successful Proxy Connection")

> Once connected leave proxy running. It is a background application which provides a service to our core applications.

Congratulations, Proxy is now running successfully!

### Connection Error

An incorrect COM/serial port assignment or unconnected Faraday radio will cause the following common error to appear.

![Proxy Connection ERROR](images/Proxy-Error-Connection.png "Proxy Connection ERROR")

> Check your COM port settings and that you did not change `baudrate` in `proxy.ini`

## Connecting To Multiple Faraday Devices

> This feature is currently broken in `Master` and we are actively working on [Issue #86](https://github.com/FaradayRF/Faraday-Software/issues/86) to fix it!

The proxy interface can connect to more than one Faraday digital radio at a time and this is achieved by creating more instances of `[UNITx]` sections and updating the `UNITS` value in the `[PROXY]` section.

### Windows
 1. [Connect](connecting-hardware.md) ***both*** Faraday radios to your computer via USB and identify their respective COM ports. 
 2. Open and configure the `proxy.ini` by changing `UNITS` in the [PROXY] section to indicate the quantity of radios connected to the computer. Also add a `[UNITx]` section for each radio.

A proper ```proxy.ini``` configuration file will resemble the example below.

![Device Manager](images/Proxy-INI-Example-Multiple-Units.png "Device Manager")

# It's Time To Configure Faraday
Now that Proxy is running, we can communicate with the radio. This means we should program it with some basic information such as your callsign and its node ID. Let's [configure Faraday](configuring-faraday.md).
