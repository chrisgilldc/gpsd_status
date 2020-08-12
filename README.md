# gpsd_status
Zabbix Monitoring of GPSD


Summary ---
This tool connects to gpsd and returns data for Zabbix monitoring.

On a per-GPS unit basis, this supports active checks for:
GPS Mode
GPS Status
Number of Satellites Visible
Number of Satellites Used

Also supports LLD of individual satellites and reports on their position 
and operating status. Probably not that useful in and of itself, but could
be useful to external tools.

Per-satellite data send in via trigger:
Azimuth
Elevation
GNSS ID
Signal Strength
Space Vehicle ID
Used

Known Limits ---

1. Should theoretically support multiple GPS devices, but wasn't tested with
multiple.
2. Similarly should support remote GPSD devices, but wasn't tested.
3. There are likely lots of edge cases not handled here.
4. Everything is based on the gpsd_json documentation. This is only as accurate as that is.
 ( Available here:  https://gpsd.gitlab.io/gpsd/gpsd_json.html )
5. This entire tool was written as a side project by a systems engineer who 
is in no way a trained or fully qualified developer. This is unlikely to be 
"pretty" code and plenty of "works for me" stuff going on here.


Requires ---
Python3
Python GPSD libraries (Centos8: python3-gpsd)

Installation ---

1. Put gpsd_status.py in your Zabbix agent scripts directory. By default (at least on Centos 8) this is /etc/zabbix/scripts.
2. Change gpsd_status.py owner to zabbix (or the owner of your zabbix_agent) and set to 755.
3. Put the userparameter_gpsd.conf file in your Zabbix agentd conf directory (Default: /etc/zabbix/zabbix_agent.d)
4. Restart zabbix_agentd. This will load the userparameter and make the active checks available.
5. Import the the gpsd_template.xml file as a new template into Zabbix to create a GPSD template. Then assign that template to the appropriate host.


If you want data about individual satellites, add the gpsd_status.cron cron line to the zabbix user's cron. This will use zabbix_sender to send data in. You'll need to update three parameters - the device to pass to gpsd_status (ie: /dev/ttyS1), the Zabbix Host where the data items live, and the Zabbix server to send to. Default is to update four times an hour, which should be more than sufficient.

If you're not going to get the individual satellite data, you probably want to disable the prototype items for that satellite data, so you don't wind up with lots of empty items.

Configuration ---

Not a ton! The template and discovery should do most of the work for you.

The only items you should need to configure are:

1. Settings for satellite cron pushes, if you're using it.
2. The Device Names if you want prettier names for your GPS devices. For example, in my config, I set:
	gps_device_names = {'/dev/ttyS1': 'Gar18x'}
	So that all my discovered items show up as:
	"GPSD Discovery: Gar18x: GPS Mode"
	Rather than
	"GPSD Discovery: /dev/ttyS1: GPS Mode"
