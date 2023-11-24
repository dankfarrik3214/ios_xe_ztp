
# IOS XE ZTP

This script can be used with the ZTP process of Cisco IOS-XE.

## Key Features

- **Configuration Management**: Able to fetch configuration from a server.
- **Configuration Status Action**: It's possible to prepare or decommission a device.
- **Firmware Upgrade**: Downgrading and upgrading supported.
- **Stack Firmware Sync**: Stack firmware sync if version mismatch is present.
- **Stack Renumbering**: Based on configuration, it's possible to renumber switches in a stack.
- **Stack Priority**: Based on configuration, it's possible to correct stack priority per switch.
- **Currently only via HTTP**: HTTPS will be introduced later.

## Supported Devices

| Device Type         | Minimum Firmware on IOS-XE |
|---------------------|----------------------------|
| Catalyst 9300       | 17.03.06                   |
| Catalyst 9200       | 17.03.06                   |
| Catalyst 9200CX     | 17.10.01                   |
| Catalyst 9800       | 17.09.04                   |

Currently only supporting IPv4.

## Requirements

- **Cisco IOS-XE Device**: Will run only on Cisco IOS-XE devices.
- **Cisco IOS-XE Install Mode Firmware**: In order for ZTP to work, the device has to have install mode as firmware.
- **DHCP Server**: To receive an IP address.
- **DHCP Server Options**: To instruct the ZTP process to fetch the ztp.py script.
- **ZTP Server**: A server where the ZTP is.
- **ZTP port 8080**: Server needs to listen to port 8080
- **Minimum Firmware**: Check Supported Devices to see which firmware is supporting the ZTP script.
- **Configuration Files**: (Optional)

## ZTP Process

When a Cisco IOS-XE boots with no configuration, it will start the autoinstaller process with ZTP. It will then try to get an IP address via DHCP. 

In the DHCP offer, it will check if there is a DHCP option that can instruct to fetch a file to run ZTP. 

It will save the ZTP file, start the guest-shell, and then execute the ztp.py file via python.

## Setup

### HTTP Server
Change the following line in the ztp.py script towards your ZTP server
```
http_server = 'x.x.x.x'
```

x.x.x.x is the IP address of your server. This can also be its hostname, as long as DNS is working with the DHCP offer.

### Logging
It's also possible to turn logging on or off. By default, it's on. To change this, change the boolean on this line in the ztp.py script.
```
log_tofile = True
```

### Logging Directory
The log of the ZTP script is to be found in this path on the Cisco IOS-XE device (when the ZTP script has run)
```
flash:guest-share/ztp.log
```

To view this, you can use more:

```
more flash:guest-share/ztp.log
```

## Examples

This ZTP script has been successfully tested with the following setup:

- **DHCP Server**: With option 67.
- **ZTP Server**: To service files.
- **Connected Device with PnP Config**: In order to fetch DHCP via a different VLAN than VLAN 1, it needs instruction.

### Example of DHCP Configuration
```
ip dhcp pool DHCP_X
 network x.x.x.x x.x.x.x
 default-router x.x.x.x
 option 67 ascii "http://x.x.x.x:8080/ztp.py"
```

### ZTP Server
In order to make this ztp.py file available to the Cisco IOS-XE device, it needs to be present on a server. On this server should be the following items:

- **HTTP via port 8080**: HTTPS is to be introduced later.
- **ztp.py Script**: Referenced in the option 67 option.
- **Firmware Files**: To be able to download firmware files.
- **Configuration Files**: (Optional)

### Connected Device PnP Startup Configuration
If the Cisco IOS-XE device needs to fetch its DHCP via another VLAN than VLAN 1, it can be forced via another VLAN (example 100). In order to do so, it will need to get these instructions via another connected Cisco device. 

These instructions can be propagated via the command pnp startup-vlan x (where x is the VLAN in which the DHCP server is).

```
pnp startup-vlan 100
```

It's also possible to boot a Cisco IOS-XE device without propagating the startup VLAN. However, this is done via a USB script. I've made a repo for this, which can be found in: https://github.com/dankfarrik3214/ztp_boot_usb_cisco_iosxe

## Configuration

This ZTP script can read configuration files with instructions. These instructions are:

- **Configuration Status**: Active, prep, and decom.
- **Configuration Stack Member**: Specify which switch is which stack role.
- **Configuration Stack Priority**: Specify which switch has which stack priority.

### Configuration Process
The ZTP script will use its serial number as a reference to look for a firmware file on the ZTP server. It will try to download this and then copy it to its flash drive. 

Based on some instructions in the configuration file, it will run tasks.

#### Example of a Configuration
```
! stack member 1
!
! stack member 1 FOC12345678 priority 15
! stack member 2 FOC91011123 priority 10
!
! configuration status active
!
```


In the example above, the file name is FOC12345678.cfg. When the ztp script reads this configuration file, it will ensure that switch FOC12345678 in the stack will be master and FOC91011123. The same goes for the priority. To avoid no instructions with stack election, it's recommended to make a configuration file for every stack member within a stack on the ZTP server.

### Configuration Status
There are currently three options for configuration status:

#### Configuration Status Active
- **Stack Software Sync**
- **Stack Renumber Check**
- **Stack Priority Check**
- **Software Upgrade Check**
- **Save Config File to Running Configuration**

#### Configuration Status Prep
- **Software Upgrade Check**
- **Erase Startup Config**

#### Configuration Status Decom
- **Erase Startup Config**

## Documentation

In the folder documentation, you will find examples of setups and configuration examples.
Also, there will be documented flow charts.

## Credits and Acknowledgments

This project utilizes concepts and/or code from the following repository:

- [Cisco IE's IOSXE_ZTP](https://github.com/cisco-ie/IOSXE_ZTP) - A repository by Cisco IE providing resources and examples for Zero Touch Provisioning on Cisco IOS XE.

Thanks to the contributors of this repository for their work and encourage users to explore it for additional insights into ZTP on Cisco IOS XE devices.

## Relevant repositories:

- https://github.com/dankfarrik3214/ztp_boot_usb_cisco_iosxe