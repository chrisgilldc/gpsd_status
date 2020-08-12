#!/usr/bin/python3

import argparse
from gps import *
import json
import os
#import time


###
# GPSd status checker for Zabbix
# Connects to GPSd, checks for lines of data and returns in a Zabbix-friendly format.
# Interprets all data based on gpsd_json documentation here: https://gpsd.gitlab.io/gpsd/gpsd_json.html

###
# Configuration options
###

# Manual name assignment for GPS LLD. If you don't assign anything here, straight device path will be need.
#gps_device_names = {'/dev/ttyS1': 'Gar18x'}

# Names for translating GNSS ID#s to names, when we need to return them.
gnss_names = {'0': 'GPS', '2': 'Galileo', '3': 'Beidou', '5': 'QZSS', '6': 'GLONASS'}

###
# Shouldn't be anything you need to change past here.
###

## Subroutines here

# Process Sky data to get satellite info.
def processSATData(gps):
	# Satellite data lives in the "Sky" object. We have to build the aggregates ourselves.
	sat_visible = 0
	sat_used = 0
	sat_info = []
	for sat in gps['satellites']:
		# Create a new specific dict for this satellite.
		this_sat = {}

		# Check for the required values for the satellite.

		# Did the satellite report its PRN assignment? It should!
		try:
			this_sat['PRN'] = sat['PRN']
		except:
			print("Error, satellite PRN not reported, but required.")
			sys.exit(1)

		# Is the satellite used in the current solution?
		if 'used' in sat:
			this_sat['used'] = sat['used']
			if sat['used']:
				sat_used = sat_used + 1
		else:
			# If satellite isn't reporting a use value at all, something's wrong, quit.
			print("Error, satellite use status not reported, but required.",file=sys.stderr)
			sys.exit(1)

		# Signal strength
		this_sat['ss'] = str(sat['ss']) or '-1'
		# Positional characteristics
		this_sat['az'] = str(sat['az']) or '-1' # Azimuth
		this_sat['el'] = str(sat['el']) or '-1' # Elevation
		# Satellite ID (from u-blox)
		this_sat['svid'] = str(sat['svid']) or '-1'
		# GNSS ID (from u-blox)
		this_sat['gnssid'] = str(sat['gnssid']) or '-1'

		# Count this satellite in the list.
		sat_visible = sat_visible + 1

		# Add this to the array of satellites
		sat_info.append(this_sat)

	return[sat_visible, sat_used, sat_info]

# Function to collect the correct data from the GPS device.
def getGPSData(gps_obj_type,device,tries):
	gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE)

	if gps_obj_type == 'DEVICES':
		# If asked for Devices, we're doing LLD and we just need to search for the DEVICES object and return it.
		while True:
			gps_data = gpsd.next()
			if gps_data['class'] == gps_obj_type:
				return(gps_data)
	else:
		# Reset our attempts counter
		gps_obj_attempts = 0

		while gps_obj_attempts < tries:
			gps_data = gpsd.next()
			# Search for an object of the right class
			if gps_data['class'] == gps_obj_type:

				# Did it come from the correct device?
				if gps_data['device'] == device:
					return(gps_data)
				else:
					# We only increment when the correct class fails, so VERSIOn, Device and other objects don't throw things off.
					gps_obj_attempts = gps_obj_attempts + 1

		# If we get here, we couldn't find the right data on the right device, so throw an error!
		print("GPS data not found. Could not find GPS object type '"+gps_obj_type+"' on device '"+device+"' after "+str(tries)+" attempts.", file=sys.stderr)
		sys.exit(1)

	# And we really should never get here.

### Main routines

## Options parsing
# Figure out our options
parser = argparse.ArgumentParser(description="GPSd Status Checker for Zabbix")
parser.add_argument('-l','--low_level_discover',action='store_true',help='Initiate low level discovery of GPS devices and visible satellites.')
parser.add_argument('-d','--device', help='GPS device to look for.', required=True)
data_group = parser.add_mutually_exclusive_group(required=True)
data_group.add_argument('-k','--key',choices=['status','mode','lat','lon','alt','device'],help='Zabbix key to check. Used with UserParameter from agent')
data_group.add_argument('-s','--satellites',action='store_true',help='Bulk output of satellite satus. Good for zabbix_sender.')
parser.add_argument('-t','--tries',type=int,default=1,help='Number of TPV lines to listen to when checking for the device. Default: 1')
options = vars(parser.parse_args())

# Determine operating mode and perform primary operations

if options['low_level_discover']:
	# Initialize our discovery variable
	discovery = []

	# Step one, get the devices
	device_list = getGPSData('DEVICES',None,None)
	device_list = device_list['devices'] # Pull the actual device list out of the dictwrapper

	# Iterate the devices.
	for device in device_list:
		# For each device, we'll collect its path, nice-name if set, and what satellites it can see.
		this_device = {}

		# Definitely need the path
		this_device['{#GPSDEV}'] = device['path']
		# If a friendly name has been set for this, use it, otherwise, use the path.
		try: 
			gps_device_names
		except:
			this_device['{#GPSNAME}'] = device['path']
		else:
			if device['path'] in gps_device_names:
				this_device['{#GPSNAME}']= gps_device_names[device['path']]
			else:
				this_device['{#GPSNAME}']  = device['path']

		# Append device to the discovery object
		#discovery.append(this_device)

		# Get a list of visible satellites. Presuming this will return something, rather than nothing.
		sky_object = getGPSData('SKY',device['path'],10)

		visible_satellites = []

		# Create a list of all the satellites visible to this device
		for satellite in sky_object['satellites']:
			# LLD only supports flat JSON, so each satellite object has to reiterate the GPS device and device name.
			# More info here: https://zabbix.org/wiki/Docs/howto/Nested_LLD
			sat_info = {'{#GPSDEV}': this_device['{#GPSDEV}'], '{#GPSNAME}': this_device['{#GPSNAME}']}
			sat_info['{#PRN}'] = satellite['PRN']
			# If we have a specific GNSS name to return, return it! Otherwise, it's probably just GPS.
			try:
				sat_info['{#GNSSNAME}'] = gnss_names[satellite['gnssid']]
			except:
				sat_info['{#GNSSNAME}'] = 'GPS'

			# Again, because it's flat JSON, we add directly to the discovery object.
			discovery.append(sat_info)


	# Pad out to have a high level data key, which Zabbix demands!
	discovery_final = {}
	discovery_final['data'] = discovery
	# Output entire discovery block for processing by Zabbix
	print(json.dumps(discovery_final, indent=4))

elif options['satellites']:
	# Doing Satellites, we need the SKY object.
	gps_data = getGPSData('SKY',options['device'],options['tries'])

	# Send data to the data processing function
	satellites = processSATData(gps_data)

	# First value is visible satellites
	print("- gpsd.sat.visible["+options['device']+"] "+str(satellites.pop(0)))
	# Next is the number of used satellites
	print("- gpsd.sat.used["+options['device']+"] "+str(satellites.pop(0)))

	# Take the list out of itself.
	satellites = satellites.pop()

	# Output individual satellites
	for satellite in satellites:
		print("- gpsd.sat.used["+options['device']+","+str(satellite['PRN'])+"] "+str(satellite['used']))
		print("- gpsd.sat.ss["+options['device']+","+str(satellite['PRN'])+"] "+str(satellite['ss']))
		print("- gpsd.sat.az["+options['device']+","+str(satellite['PRN'])+"] "+str(satellite['az']))
		print("- gpsd.sat.el["+options['device']+","+str(satellite['PRN'])+"] "+str(satellite['el']))
		print("- gpsd.sat.svid["+options['device']+","+str(satellite['PRN'])+"] "+str(satellite['svid']))
		print("- gpsd.sat.gnssid["+options['device']+","+str(satellite['PRN'])+"] "+str(satellite['gnssid']))

elif 'key' in options:
	# Specific Zabbix key was requested, so we'll need to find it in the TPV object
	gps_data = getGPSData('TPV',options['device'],options['tries'])

	# Is what we want really in here? It should be!
	if options.get('key') in gps_data:
		print(gps_data[options.get('key')])
	else:
		print("Error: Could not find requested key in TPV object.",file=sys.stderr)
		sys.exit(1)
else:
	# We should never get here, but if we do, throw an error.
	print("Error, could not determine needed GPS object type. This should never happen!",file=sys.stderr)
	sys.exit(1)

# Made it here? We must be good! Terminate nicely.
sys.exit(0)
