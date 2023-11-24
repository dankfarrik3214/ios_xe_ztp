
# IOS XE ZTP

This script can be used with the ZTP process of Cisco IOS-XE

## Key features

- **Configuration management**: Able to Fetch configuration from a server
- **Configuration status action**: It's possible to prepaire or decom a device
- **Firmware upgrade**: Downgrading and upgrade supported.
- **Stack firmware sync**: Stack firmware sync if version mismatch is present.
- **Stack renumbering**: Based on configuration it's possible to renumber switches in a stack
- **Stack priority**: Based on configuration it's possible to correct stack priority per switch
- **Currently only via http**: https will be introduced later

## Supported devices

| Device Type | Minimum Firmware on IOS-XE |
|-------------|----------------------------|
| Catalyst 9300         | 17.03.06         
| Catalyst 9200         | 17.03.06  
| Catalyst 9200CX       | 17.03.06
| Catalyst 9800         | 17.09.04             

Currently only supporting IPv4

## Requirements

- **Cisco IOS-XE device**: Will run only on cisco IOS-XE devices
- **Cisco IOS-XE install mode firmware**: In order for ZTP to work, the device has to have install mode as firmware.
- **DHCP server**: To receive an IP address
- **DHCP server options**: To instruct the ZTP process to fetch the ztp.py script
- **ZTP server**: A server where the ZTP is
- **Minimum firmware**: Check Supported device to see which firmware is supporting the ZTP script
- **Configuration files**: (Optional)




## ZTP Process

When a Cisco IOS-XE boots with no configuration it will start the autoinstaller process with ZTP. It will then try to get IP address via DHCP. 

In the DHCP offer it will check if there is a DHCP option that can instruct to fetch a file to run ZTP. 

It will save the ZTP file, start the guest-shell and then execute ztp.py file via python.
## Setup

This ZTP script has been succesfully tested with the following setup:

- **DHCP server**: With option 67
- **ZTP server**: To service to files
- **Connected device with pnp config**: In order to fetch DHCP via different vlan then vlan 1 it needs instruction

### Example of DHCP configuration
```
ip dhcp pool DHCP_X
 network x.x.x.x x.x.x.x
 default-router x.x.x.x
 option 67 ascii "http://x.x.x.x:8080/ztp.py"
```

### ZTP server
In order to make this ztp.py file available towards the Cisco IOS-XE device, it needs to be present on a server. On this server should be the following items:

- **ztp.py script**: referenced in the option 67 option
- **Firmware files**: To be able to download firmware files
- **Configuration files**: (Optional)

### Connected device pnp startup configuration
If the Cisco IOS-XE device needs to fetch it's DHCP via another VLAN then VLAN 1 it can be forced via another VLAN (example 100). In order to do so it will need to get this instructions via another connected Cisco device. 

These instructions can be propagated via the command pnp startup-vlan x. (where x is the vlan which the DHCP server is in).

```
pnp startup-vlan 100
```

It's also possible to boot a Cisco IOS-XE device without propgating the startup vlan. However this is done via a USB script. I've made a repo for this, this can be found in:


## Configuration

This ZTP script can read configuration files with instructions. These instructions are:

- **Configuration status**: Active, prep and decom
- **Configuration stack member**: Specify which switch is which stack role
- **Configuration stack priority**: Specify which switch has wich stack priority

### Configuration process
The ZTP script will use it's serial number as reference to look for a firmware file on the ZTP server. It will try to download this and then copy it towards it's flash drive. 

Based on some instructions in the configuration file, it will run tasks.

#### Example of a configuration
```
! stack member 1
!
! stack member 1 FOC12345678 priority 15
! stack member 2 FOC91011123 priority 10
!
! configuration status active
!
```

In the example above the file name is FOC12345678.cfg, when the ztp script reads this configuration file it will make sure that switch FOC12345678 in the stack will be master and FOC91011123. Same goes with the priority. To avoid no instructions with stack election it's recommended to make for every stack member within a stack a configuration file on the ztp server.

### Configuration status
There are currently three options with configuration status

#### Configuration status active
- **Stack software sync**
- **Stack renumber check**
- **Stack renumber check**
- **Stack priority check**
- **Software upgrade check**
- **Save config file to running configuration**

#### Configuration status prep
- **Software upgrade check**
- **Erase startup config**

#### Configuration status decom
- **Erase startup config**

## Documentation

In the folder documentation you will find examples of setups and configuration examples.
Also will be documentated the flow charts.
## Credits and Acknowledgments

This project utilizes concepts and/or code from the following repository:

- [Cisco IE's IOSXE_ZTP](https://github.com/cisco-ie/IOSXE_ZTP) - A repository by Cisco IE providing resources and examples for Zero Touch Provisioning on Cisco IOS XE.

We thank the contributors of this repository for their work and encourage users to explore it for additional insights into ZTP on Cisco IOS XE devices.
