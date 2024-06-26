from cli import configure, cli, configurep, executep
import re
import time
import sys
import logging
from logging.handlers import RotatingFileHandler

# Global variable

# Fallback on IP if DNS servers are not reachable from device
http_server = 'x.x.x.x'
# ZTP server settings
http_server_fqdn = 'http://ztp.local'
http_server_tcp_port = '8080'
http_server_config_directory = '/config_files/'
http_server_firmware_directory = '/images/'

# e-mail vars
mail_status = False
sender_email = ""
receiver_email = ""
smtp_server = ""
smtp_server_port = "" 

# Logging to flash:guest-share/ztp.log
log_tofile = True


software_mappings = {
    ## 9300 SERIES
    'C9300-24P': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },
    'C9300-24S': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },    
    'C9300-48P': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },
    'C9300-48S': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },
    ## 9200 SERIES    
    'C9200-48S': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },
    'C9200-48P': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },
    'C9200-24S': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },    
    'C9200-24P': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },    
    ## 9200CX SERIES    
    'C9200CX-12P-2X2G': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    },
    ## Wireless LAN Controllers
    'C9800-L-F-K9': {
        'software_image': '',
        'software_version': '', # DON'T FORGET THIS!
        'software_md5_checksum': ''
    }                                 
}

def activate_beacon_led(model):
    cli("send log 7 ### ZTP SCRIPT - DEVICE IS PREPPED - ACTIVATING BEACON LED ###")
    print("### ZTP SCRIPT - DEVICE IS PREPPED - ACTIVATING BEACON LED ###")
    log_info("### ZTP SCRIPT - DEVICE IS PREPPED - ACTIVATING BEACON LED ###")

    # Moduel selection
    if 'C9200CX-12P-2X2G' in model:
        # Not supported
        print("************************ Activating beacon LED ************************\n")
        log_info("************************ Activating beacon LED ************************\n")           
        cli('hw-module beacon slot 1 on')          

    elif 'C9200' in model:
        print("************************ Activating beacon LED ************************\n")
        log_info("************************ Activating beacon LED ************************\n")           
        try:
            cli('hw-module beacon slot 1 on')

        except Exception as e:
            # Log unexpected exceptions
            print(f"An unexpected error occurred: {e}. Trying different way to activate beacon")
            log_info(f"An unexpected error occurred: {e}. Trying different way to activate beacon")
            configure('#hw-module beacon on switch 1')

    elif 'C9300' in model:
        print("************************ Activating beacon LED ************************\n")
        log_info("************************ Activating beacon LED ************************\n")           
        cli('hw-module beacon slot 1 on')

    elif 'C9800' in model:
        # Not supported
        print(f"********* {model} not supported for activating beacon led. Skipping task *********")
        log_info(f"********* {model} not supported for activating beacon led. Skipping task *********")
        cli(f"send log 7 ********* {model} not supported for activating beacon led. Skipping task *********")             

    else:
        # If no defined model is found
        print(f"********* {model} not supported for activating beacon led. Skipping task *********")
        log_info(f"********* {model} not supported for activating beacon led. Skipping task *********")
        cli(f"send log 7 ********* {model} not supported for activating beacon led. Skipping task *********")                                   
        
def bug_work_around_696657788():
    # This bug workaround is for the 9200 series that have more then two stack members
    # TAC CASE: 696657788
    eem_commands = ['event manager applet 9200_stack_bug_workaround',
                    'event syslog occurs 1 pattern "SYS-5-RESTART" maxrun 600',
                    'action 1.0 wait 180',
                    'action 2.0 cli command "enable"',
                    'action 3.0 cli command "write mem"',
                    'action 4.1 cli command "erase startup-config" pattern "[confirm]"',
                    'action 4.2 cli command "y"',
                    'action 5.1 cli command "reload" pattern "[confirm]"',
                    'action 5.2 cli command "y"',                                                                                                          
                    ]
    results = configurep(eem_commands)
    print ('*** Successfully configured 9200_stack_bug_workaround script! ***')
    log_info('*** Successfully configured 9200_stack_bug_workaround script! ***')      

def clean_config_file(config_file):
    # Search if a config_file is present
    search_config = cli('show flash: | include %s' % (config_file))

    if config_file in search_config:
        print('**** removing config file *******\n')
        log_info('**** removing config file *******\n')
        res = cli('delete flash:%s' % (config_file))
        print(res)
        log_info(res)
        print("\n")
        print('**** Finished removing configuration file *******\n')
        log_info('**** Finished removing configuration file *******\n')

    else: 
        print('**** No configuration file found, skipping clean up *******\n')
        log_info('**** No configuration file found, skipping clean up *******\n')
        
def cisco_stack_v_mismatch_check(model):

    def cisco_9200_v_mismatch_flash_cleaner():
        # Obtains show version output, needed to determine which version the switch has
        sh_version = cli('show version')
        current_version = re.search(r"Cisco IOS XE Software, Version\s+(\S+)", sh_version).group(1)
        current_version_int = int(current_version.replace('.', ''))

        # Detect how many flash drives are present
        show_switch = cli('show switch')
        switches = re.findall(r"^\s*\*?(\d+)\s+", show_switch, re.MULTILINE)

        # Skip the master switch, which is presumably the first one
        non_master_switches = switches[1:]  # Start from the second switch

        # Initialize a flag to check if any files were deleted
        files_deleted = False

        try:
            for switch in non_master_switches:
                output = cli(f'show flash-{switch}: | include cat9k_lite_iosxe_npe')
                files = re.findall(r'cat9k_lite_iosxe_npe\.\d+\.\d+\.\d+\.SPA\.bin', output)

                for file in files:
                    if "cat9k_lite_iosxe_npe." + str(current_version) not in file:
                        cli(f"delete /force flash-{switch}:{file}")
                        print(f"Deleted flash-{switch}:{file}")
                        files_deleted = True
                    else:
                        print(f"Skipping current version file {file} on flash-{switch}")

                if not files_deleted:
                    print(f"No old version files found to be deleted on flash-{switch} of switch {switch}")
                    log_info(f"No old version files found to be deleted on flash-{switch} of switch {switch}")

        except Exception as e:
            print(f'*** Failure to make room on flash for upgrade: {e} ***\n')
            log_critical(f'*** Failure to make room on flash for upgrade: {e} ***\n')

    if stack_switch_status == True:
        try:
            print('**** Determining if switch members have same firmware as master switch ****')
            log_info('**** Determining if switch members have same firmware as master switch ****')

            show_switch_version = cli("show switch").strip()  # Stripping any leading/trailing whitespace

            if 'V-Mismatch' in show_switch_version:
                print('*** Version mismatch detected! Starting auto upgrade ***')
                log_info('*** Version mismatch detected! Starting auto upgrade ***')

                if "9200" in model:
                    # First cleaning disk if 9200
                    print('*** Cleaning up files to make space ***')
                    log_info('*** Cleaning up files to make space ***')
                    cisco_9200_v_mismatch_flash_cleaner()

                print('*** Deploying auto upgrade ***')
                log_info('*** Deploying auto upgrade ***')
                # Deploy EEM script to auto upgrade
                eem_commands = ['event manager applet autoupgrade',
                                'event none maxrun 900',
                                'action 1.0 cli command "enable"',
                                'action 2.0 cli command "install autoupgrade"',
                                ]
                results = configurep(eem_commands)

                if "9300" in model:
                    erase_startup_config()
                    cli("reload in 15 reason - *** Whole stack needs to restart in order for ZTP to work ***")
                    cli('event manager run autoupgrade')

                else: 
                    print('*** Upgrade in progress. Waiting for 10 min ***')
                    log_info('*** Upgrade in progress. Waiting for 10 min ***')
                    # Wait untill upgrade is finished
                    time.sleep(600)  # Wait for 15 minutes

                print('*** Removing autoupgrade script***')
                log_info('*** Removing autoupgrade script***')
                configure("no event manager applet autoupgrade")

            else:
                print('*** All stack members have same firmware as stack master ***')
                log_info('*** All stack members have same firmware as stack master ***')

        except Exception as e:
            print(f"An error occurred: {e}")
            log_info(f"An error occurred: {e}")

def clean_reload():
    # Reboot switch(es) with clean configuration
    # Needed to enable to ZTP script from the beginning
    if stack_switch_status == False:
        # if single device
        print('**** Starting Clean reload with no startup-config *******\n')
        log_info('**** Starting Clean reload with no startup-config *******\n')
        cli('erase startup-config')
        cli('reload')
    elif stack_switch_status == True:
        # Clean configuration on whole stack
        print('**** Starting Clean reload with no startup-config - ALL STACKED SWITCHES *******\n')
        log_info('**** Starting Clean reload with no startup-config - ALL STACKED SWITCHES *******\n')
        cli('erase startup-config')
        cli('delete stby-nvram:startup-config')
        cli('reload')

def erase_startup_config():
    print('**** Erasing config *******\n')
    log_info('**** Erasing config *******\n')
    cli('erase startup-config')  # This command erases the startup configuration.   

def configure_default_interfaces_c9800():
    log_info("*** Removing pnp/ztp interface configuration ***")
    default_interface_list = {
        'TenGigabitEthernet0/1/0',
        'TenGigabitEthernet0/1/1',
    }
    for interface in default_interface_list:
        log_info(f"*** Applying default configuration for {interface} ***")                    
        configure(f"default interface {interface}")

def configure_replace(file,file_system='flash:/' ):
    config_command = 'configure replace %s%s force' % (file_system, file)
    print("************************Replacing configuration************************\n")
    log_info('************************Replacing configuration************************\n')
    config_repl = executep(config_command)
    time.sleep(10)
    
def configure_merge_file_to_running_config(file,file_system='flash:/'):
    print("************************Merging running config with given config file************************\n")
    log_info('************************Merging running config with given config file************************\n')
    config_command = 'copy %s%s running-config' %(file_system,file)
    config_repl = executep(config_command)
    time.sleep(10)

def configure_merge_file_to_startup_config(file,file_system='flash:/'):
    print(f"************************Merging {config_file} with startup-config ************************\n")
    log_info(f'************************Merging {config_file} with startup-config ************************\n')
    config_command = 'copy %s%s startup-config' %(file_system,file)
    config_repl = executep(config_command)
    time.sleep(10)     

def configure_replace_file_to_running_config(file,file_system='flash:'):
    print(f"************************Replacing running config with {config_file} ************************\n")
    log_info(f"************************Replacing running config with {config_file} ************************\n")
    config_command = 'configure replace %s%s force' %(file_system,file)
    log_info(f"DEBUG config_command {config_command}")
    config_repl = executep(config_command)
    time.sleep(10) 

def configure_startup(file,file_system='flash:/'):
     print(f"************************Merging {file} to startup config************************\n")
     log_info(f"************************Merging {file} to startup config************************\n")
     config_command = 'copy %s%s startup-config' %(file_system,file)
     config_repl = executep(config_command)
     time.sleep(10)

def configure_ssh_keys():
    print("************************Configuring ssh keys************************\n")
    log_info('************************Configuring ssh keys************************\n')    
    cli('crypto key generate rsa modulus 4096')

def create_logfile():
    try:
        print ("******** Creating  a persistent log file *********** ")
        path = '/flash/guest-share/ztp.log'
        #file_exists = os.path.isfile(path)
        #if(file_exists == False):
          #print ("******** ztp.log file dont exist .  *********** ")
        with open(path, 'a+') as fp:
             pass
        return path
    except IOError:
      print("Couldnt create a log file at guset-share .Trying to use  /flash/ztp.log as an alternate log path")
      path = '/flash/ztp.log'
      #file_exists = os.path.isfile(path)
      #if(file_exists == False):
      #    print ("******** ztp.log file dont exist .  *********** ")
      with open(path, 'a+') as fp:
             pass
      return path
    except Exception as e:
         print("Couldnt create a log file to proceed")

def configure_logger(path):
    log_formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
    logFile = path
    #create a new file > 5 mb size
    log_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024, backupCount=10, encoding=None, delay=0)
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(logging.INFO)
    ztp_log = logging.getLogger('root')
    ztp_log.setLevel(logging.INFO)
    ztp_log.addHandler(log_handler)
    
def configuration_transfer(http_server, http_server_config_directory, config_file):
    # Transfers a file from an HTTP server to the flash storage on the device.

    try:
        print('**** Start transferring file *******\n')
        log_info('**** Start transferring file *******\n')

        if http_server_firmware_directory != '':
            url = f"http://{http_server}:{http_server_tcp_port}{http_server_config_directory}{config_file}"
        elif http_server_firmware_directory == '':
            url = f"http://{http_server}:{http_server_tcp_port}{config_file}"            
        
        # Run the command and capture the output
        res = cli(f'copy {url} flash:{config_file}')
        #res = cli(f'copy http://{http_server}:8080{http_server_config_directory}{config_file} flash:{config_file}')
        
        # It's a good practice to log the full CLI response for debugging
        print(res)
        log_info(res)
        
        # Check if there's an indication of a CLI syntax error or execution failure
        if "cli syntax error or execution failure" in res.lower():
            print('**** CLI syntax error or execution failure detected *******\n')
            log_info('**** CLI syntax error or execution failure detected *******\n')
            configuration_present = False
            return configuration_present

        else:
            print('**** Finished transferring device configuration file *******\n')
            log_info('**** Finished transferring device configuration file *******\n')
            configuration_present = True
            return configuration_present

    except Exception as e:
        # Log unexpected exceptions
        print(f"An unexpected error occurred: {e}")
        log_info(f"An unexpected error occurred: {e}")
        configuration_present = False
        return configuration_present


    # # Transfers a file from an HTTP server to the flash storage on the device.

    # try:

    #     print('**** Start transferring file *******\n')
    #     log_info('**** Start transferring file *******\n')
        
    #     # Run the command and capture the output
    #     res = cli(f'copy http://{http_server}:8080/{file} flash:')
        
    #     # It's a good practice to log the full CLI response for debugging
    #     print(res)
    #     log_info(res)
        
    #     # Check if there's an indication of a CLI syntax error or execution failure
    #     if "cli syntax error or execution failure" in res.lower():
    #         print('**** CLI syntax error or execution failure detected *******\n')
    #         log_info('**** CLI syntax error or execution failure detected *******\n')
    #         configuration_present = False
    #         return configuration_present

    #     else:
    #         print('**** Finished transferring device configuration file *******\n')
    #         log_info('**** Finished transferring device configuration file *******\n')
    #         configuration_present = True
    #         return configuration_present

    # except Exception as e:
    #     # Log unexpected exceptions
    #     print(f"An unexpected error occurred: {e}")
    #     log_info(f"An unexpected error occurred: {e}")
    #     configuration_present = False
    #     return configuration_present

def configuration_status(config_file):
    # Initialize configuration_status
    configuration_status_value = {}
    show_config_status = cli(f"more flash:{config_file}")

    matches = re.findall(r"! configuration status (\w+)", show_config_status, re.IGNORECASE)
    
    if matches:
        first_match = matches[0].strip().lower()  # Remove leading/trailing whitespaces and convert to lowercase
        if first_match:
            if "active" == first_match:
                configuration_status_value = "active"
            if "planned" == first_match:
                configuration_status_value = "planned"                
            elif "decommissioning" == first_match:
                configuration_status_value = "decommissioning"
            # Add more cases as needed
        else:
            configuration_status_value = "unknown"
    else:
        configuration_status_value = "unknown"

    return configuration_status_value

def copy_startup_to_running():
     print("************************Merging startup config with running-config************************\n")
     log_info('************************Merging startup config with running-config************************\n')
     config_command = 'copy startup-config running'
     config_repl = executep(config_command)
     time.sleep(10)
      
def check_file_exists(file, file_system='flash:/'):
    dir_check = 'dir ' + file_system + file
    print ('*** Checking to see if %s exists on %s ***' % (file, file_system))
    log_info('*** Checking to see if %s exists on %s ***' % (file, file_system))
    results = cli(dir_check)
    if 'No such file or directory' in results:
        print ('*** The %s does NOT exist on %s ***' % (file, file_system))
        log_info('*** The %s does NOT exist on %s ***' % (file, file_system))
        return False
    elif 'Directory of %s%s' % (file_system, file) in results:
        print ('*** The %s DOES exist on %s ***' % (file, file_system))
        log_info('*** The %s DOES exist on %s ***' % (file, file_system))
        return True
    elif 'Directory of %s%s' % ('bootflash:/', file) in results:
        print ('*** The %s DOES exist on %s ***' % (file, 'bootflash:/'))
        log_info('*** The %s DOES exist on %s ***' % (file, 'bootflash:/'))
        return True
    else:
        log_critical('************************Unexpected output from check_file_exists************************\n')
        raise ValueError("Unexpected output from check_file_exists")

def day_zero_script_runner():

    ## Function to get configuration
    try:
        print ('###### STARTING ZTP SCRIPT ######\n')
        # switch to enable/disbale persistent logger
        if(log_tofile == True):
            filepath = create_logfile()
            configure_logger(filepath)
      
        log_info('###### STARTING ZTP SCRIPT ######\n')

        # Todo download CA certificate
        # ssl_installer()

        # Fetch device type
        device_type = get_device_type()

        # Fetch device model
        model = get_model()

        # Fetch serial or multiple serials (if stack)
        serial, stack_switch_status = get_serial(device_type)

        # Disable dnac discovery
        disable_dna_discovery()

        #print config file name to download
        #config_file = '%s.cfg' % model
        config_file = '%s.cfg' % serial
        
        # Cleaning files
        clean_config_file(config_file)

        # Download config from ZTP (based on serial number)
        print('**** Downloading config file ****\n')
        log_info('**** Downloading config file ****\n')
        configuration_present = configuration_transfer(http_server, http_server_config_directory, config_file)

        
        # if configuration_present == True:
        #     # Saving configuration towards startup-configuration
        #     print ('*** Trying to perform  Day 0 configuration push  ****')
        #     log_info('*** Trying to perform  Day 0 configuration push  ****')
        #     configure_startup(config_file)

        if configuration_present == False:
            # Saving configuration towards startup-configuration
            print ('*** No configuration present on the ZTP server. No configuration will be saved  ****')
            log_info('*** No configuration present on the ZTP server. No configuration will be saved  ****')
     
        return config_file, device_type, model, serial, stack_switch_status

    except Exception as e:
        print('*** Failure encountered during day 0 provisioning . Aborting ZTP script execution. Error details below   ***\n')
        log_critical('*** Failure encountered during day 0 provisioning . Aborting ZTP script execution. Error details below   ***\n' + e)
        print(e)
        sys.exit(e) 

def deactivate_beacon_led(model):
    cli("send log 7 ### ZTP SCRIPT - SCRIPT STARTED - DEACTIVATING BEACON LED ###")
    print("### ZTP SCRIPT - SCRIPT STARTED - DEACTIVATING BEACON LED ###")
    log_info("### ZTP SCRIPT - SCRIPT STARTED - DEACTIVATING BEACON LED ###")

    print(f'*** DEBUG: model: {model} ***')
    log_info(f'*** DEBUG: model: {model} ***')         

    # Moduel selection
    if 'C9200CX-12P-2X2G' in model:
        # Not supported
        print("************************ Dectivating beacon LED ************************\n")
        log_info("************************ Dctivating beacon LED ************************\n")          
        cli('hw-module beacon slot 1 off')
     
    elif 'C9200' in model:
        print("************************ Dectivating beacon LED ************************\n")
        log_info("************************ Dctivating beacon LED ************************\n")           
        try:
            cli('hw-module beacon slot 1 off')

        except Exception as e:
            # Log unexpected exceptions
            print(f"An unexpected error occurred: {e}. Trying different way to deactivate beacon")
            log_info(f"An unexpected error occurred: {e}. Trying different way to deactivate beacon")
            configure('#hw-module beacon of switch 1')

    elif 'C9300' in model:
        print("************************ Dectivating beacon LED ************************\n")
        log_info("************************ Dctivating beacon LED ************************\n")          
        cli('hw-module beacon slot 1 off')

    elif 'C9800' in model:
        # Not supported
        print(f"********* {model} not supported for deactivating beacon led. Skipping task *********")
        log_info(f"********* {model} not supported for deactivating beacon led. Skipping task *********")
        cli(f"send log 7 ********* {model} not supported for deactivating beacon led. Skipping task *********")             

    else:
        # If no defined model is found
        print(f"********* {model} not supported for deactivating beacon led. Skipping task *********")
        log_info(f"********* {model} not supported for deactivating beacon led. Skipping task *********")
        cli(f"send log 7 ********* {model} not supported for deactivating beacon led. Skipping task *********")                               

def disable_dna_discovery():

    cli("send log 7 ### ZTP SCRIPT - DEACTIVATING DNA CONFIGURATION ###")
    print("### ZTP SCRIPT - DEACTIVATING DNA CONFIGURATION ###")
    log_info("### ZTP SCRIPT - DEACTIVATING DNA CONFIGURATION ###")

    try:
        print('**** Stopping dnac discovery *******\n')
        log_info('**** Stopping dnac discovery *******\n')
        cli('pnpa service discovery stop')
        
    except Exception as e:
        # Log unexpected exceptions
        print(f"An unexpected error occurred: {e}.")
        log_info(f"An unexpected error occurred: {e}.")

    try:
        print('**** Removing dnac pnp certificate *******\n')
        log_info('**** Removing dnac pnp certificate *******\n')
        cli('pnpa service trustpoint-uninstall SLA-TrustPoint')
        cli('pnpa service trustpool-uninstall')

        
    except Exception as e:
        # Log unexpected exceptions
        print(f"An unexpected error occurred: {e}.")
        log_info(f"An unexpected error occurred: {e}.")            

def deploy_eem_cleanup_script():
    install_remove_inactive_command = 'install remove inactive'
    eem_commands = ['event manager applet cleanup',
                    'event none maxrun 600',
                    'action 1.0 cli command "enable"',
                    'action 2.0 cli command "%s" pattern "\[y\/n\]"' % install_remove_inactive_command,
                    'action 2.1 cli command "y" pattern "proceed"',
                    'action 2.2 cli command "y"'
                    ]
    results = configurep(eem_commands)
    print ('*** Successfully configured cleanup EEM script on device! ***')
    log_info('*** Successfully configured cleanup EEM script on device! ***')

def deploy_eem_cleanup_script_reload():
    install_remove_inactive_command = 'install remove inactive'
    eem_commands = ['event manager applet cleanup_reload',
                    'event none maxrun 600',
                    'action 1.0 wait 15',
                    'action 2.0 cli command "enable"',
                    'action 3.0 cli command "%s" pattern "\[y\/n\]"' % install_remove_inactive_command,
                    'action 4.1 cli command "y" pattern "proceed"',
                    'action 4.2 cli command "y"'
                    ]
    results = configurep(eem_commands)
    print ('*** Successfully configured cleanup EEM script on device! ***')
    log_info('*** Successfully configured cleanup EEM script on device! ***')

def deploy_eem_clean_config_reload():
    install_command_remove_inactive = 'install remove inactive'    
    eem_commands = ['event manager applet CLEAR_CONFIG_AND_RELOAD',
                    'event syslog pattern "SYS-5-RESTART" maxrun 31536000',
                    'action 1.0 wait 180',
                    'action 2.0 cli command "enable"',
                    'action 3.0 cli command "configure terminal"',
                    'action 3.1 cli command "event manager applet upgrade"',
                    'action 3.2 cli command "no event manager applet upgrade"',
                    'action 3.3 cli command "exit"',
                    'action 3.4 syslog msg "removed upgrade script"',
                    'action 4.0 cli command "write mem"',
                    'action 4.1 cli command "reload in 5" pattern "confirm"',
                    'action 4.2 cli command "y"',
                    'action 5.0 cli command "erase startup-config" pattern "confirm"',
                    'action 5.1 cli command "y"',
                    'action 6.0 syslog msg "Configuration erased and device will reload in 5 minutes"',
                    'action 7.0 policy cleanup_reload'
                    ]
    results = configurep(eem_commands)
    print('*** Successfully configured cleanup EEM CLEAR_CONFIG_AND_RELOAD script on device! ***')
    log_info('*** Successfully configured cleanup EEM CLEAR_CONFIG_AND_RELOAD script on device! ***') 

def deploy_eem_upgrade_script(image):
    
    # upgrade or downgrade is in install mode
    # Cleaning switch for next reboot
    erase_startup_config()
    try:
        # Upgrade process
        install_command = 'install add file flash:' + image + ' activate commit'
        eem_commands = ['event manager applet upgrade',
                        'event none maxrun 600',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "%s" pattern "\[y\/n\/q\]"' % install_command,
                        'action 2.1 cli command "n" pattern "proceed"',
                        'action 2.2 cli command "y"'
                        ]
        results = configurep(eem_commands)
        print ('*** Successfully configured upgrade EEM script on device! ***')
        log_info('*** Successfully configured upgrade EEM script on device! ***')

    except Exception as e:
        print("Error with upgrade switch:", e)
        log_info(f"Error with upgrade switch: {e}") 

def deploy_eem_config_activation_c9800(file,file_system='flash:'):
    try:
        # activate configuration script
        config_activate_command = 'configure replace %s%s force' %(file_system,file)
        eem_commands = ['event manager applet config_activate',
                        'event none maxrun 600', 
                        'action 1.0 wait 120',
                        'action 2.0 cli command "enable"',
                        'action 3.0 cli command "%s"' % config_activate_command,
                        ]
        results = configurep(eem_commands)
        print ('*** Successfully configured config activation EEM script on device! ***')
        log_info('*** Successfully configured config activation EEM script on device! ***')

        # Running EEM script
        cli('event manager run config_activate')
        print ('*** Configuration will be soon activated towards running-configuration! ***')
        log_info ('*** Configuration will be soon activated towards running-configuration! ***')   

    except Exception as e:
        print("Error with upgrade switch:", e)
        log_info(f"Error with upgrade switch: {e}") 

def exit_guest_shell():
    try:
        print('**** Exiting the Guest Shell *******\n')
        log_info('**** Exiting the Guest Shell *******\n')     
        cli('exit')

    except Exception as e:
        print(f"An error occurred while exiting the Guest Shell: {e}")
        log_info(f"An error occurred while exiting the Guest Shell: {e}")

def exit_program():
    print("Exiting the program...")
    sys.exit(0)

def exit_auto_installer():
    try:
        print('**** Exiting the Auto installer  *******\n')
        log_info('**** Exiting the Auto installer  *******\n')     
        cli('no')
        cli('yes')        

    except Exception as e:
        print(f"An error occurred while exiting Auto installer: {e}")
        log_info(f"An error occurred while Auto installer: {e}")    

def file_transfer(http_server, file):
  print('**** Start transferring  file *******\n')
  log_info('**** Start transferring  file *******\n')
  res = cli('copy http://%s:8080/%s flash:%s' % (http_server,file,file))
  print(res)
  log_info(res)
  print("\n")
  print('**** Finished transferring device configuration file *******\n')
  log_info('**** Finished transferring device configuration file *******\n')

def firmware_transfer(http_server,file):
    # Transfer firmware to device
    print('**** Start transferring  file *******\n')
    log_info('**** Start transferring  file *******\n')

    if http_server_firmware_directory != '':
        url = f"http://{http_server}:{http_server_tcp_port}{http_server_firmware_directory}{file}"
    elif http_server_firmware_directory == '':
        url = f"http://{http_server}:{http_server_tcp_port}{file}"    

    try:
        res = cli(f'copy {url} flash:{file}')
        print(res)
        log_info(res)
        print("\n")
        print('**** Finished transferring device configuration file *******\n')
        log_info('**** Finished transferring device configuration file *******\n')

    except Exception as e:
        print(f"An error occurred while transfering firmware {e}")
        log_info(f"An error occurred while transfer firmware: {e}")

def find_certs():
    certs = cli('show run | include crypto pki')
    if certs:
        certs_split = certs.splitlines()
        certs_split.remove('')
        for cert in certs_split:
            command = 'no %s' % (cert)
            configure(command)

def firmware_upgrade_selector(model):
    ### software upgrade section
    if 'C9200CX-12P-2X2G' in model:
        # Running upgrade function for C9200
        print("Cisco C9200CX-12P-2X2G model detected for software upgrade")
        firmware_upgrade_status = upgrade_runner_cisco_ios_xe_9200_cx(model)

    elif 'C9200' in model:
        # Running upgrade function for C9200
        print("Cisco 9200 model detected for software upgrade")
        firmware_upgrade_status = upgrade_runner_cisco_ios_xe_9200(model, config_file)

    elif 'C9300' in model:
        # Running upgrade function for C9300
        print("Cisco 9300 model detected for software upgrade")
        firmware_upgrade_status = upgrade_runner_cisco_ios_xe_9300(model)

    elif 'C9800' in model:
        # Running upgrade function for C9300
        print("Cisco 9300 model detected for software upgrade")
        firmware_upgrade_status = upgrade_runner_cisco_ios_xe_9800(model)

    else:
        # If no defined model is found
        print("Model not supported in firmware upgrade, skipping task")
        
    
    return firmware_upgrade_status

def get_device_type():
    print("******** Trying to get Device type *********** ")
    log_info("******** Trying to get Device type *********** ")  

    try:
        show_inventory = cli('show inventory')

    except Exception as e:
        time.sleep(90)
        show_inventory = cli('show inventory')
        

    if "Switch" in show_inventory:
        print("******** Device type - Switch detected *********** ")
        log_info("******** Device type - Switch detected *********** ")          
        device_type = "switch"
        return device_type
    elif "Wireless Controller" in show_inventory:
        print("******** Device type - Wireless controller detected *********** ")
        log_info("******** Device type - Wireless controller detected *********** ")          
        device_type = "wlc"
        return device_type
    elif "Router" in show_inventory:
        print("******** Device type - Wireless controller detected *********** ")
        log_info("******** Device type - Wireless controller detected *********** ")          
        device_type = "router"
        return device_type    
    else:
        print("******** Device type - Failed to detect Device type *********** ")
        log_info("******** Device type - Failed to detect Device type *********** ")    
        device_type = "unknown"
        return device_type  

    return device_type   
  
def get_file_system():
    pass

def get_serial(device_type):
    print("******** Trying to get Serial ***********")
    log_info("******** Trying to get Serial ***********")

    stack_switch_status = False # Initialize stack_switch_status as false
    serial = None  # Initialize serial as None

    if device_type == "switch":
        try:
            show_switch = cli('show switch')
            print(f"DEBUG: show_switch = {show_switch}")
            log_info(f"DEBUG: show_switch = {show_switch}")
            switches = re.findall(r"^\s*\*?(\d+)\s+", show_switch, re.MULTILINE)
            print(f"DEBUG: switches = {switches}")
            log_info(f"DEBUG: switches = {switches}")
    
            if len(switches) > 1:  # It's a stack
                print("DEBUG: Stack detected")
                log_info("DEBUG: Stack detected")
                master_switch = re.search(r"^\s*\*?(\d+)\s+Active", show_switch, re.MULTILINE).group(1)
                print(f"Master switch is switch {master_switch}")
                log_info(f"Master switch is switch {master_switch}")
                show_inventory = cli('show inventory')
                serial_search = re.search(r'NAME: "Switch ' + master_switch + r'".*?PID:.*?,.*?SN: (\S+)', show_inventory, re.DOTALL)
                serial = serial_search.group(1)  # get the captured group
                stack_switch_status = True
                
            else:  # Not a stack
                print("DEBUG: Single switch detected")
                log_info("DEBUG: Single switch detected")
                show_version = cli('show version')
                try:
                    serial = re.search(r"System Serial Number\s+:\s+(\S+)", show_version).group(1)
                except AttributeError:
                    serial = re.search(r"Processor board ID\s+(\S+)", show_version).group(1)
                stack_switch_status = False

        except Exception as e:
            print("An error occurred:", e)
            log_info(f"An error occurred: {e}")
            # Handle the exception appropriately here

    elif device_type == "wlc":
        try:
            show_inventory = cli('show inventory')
            # Updated regex pattern to specifically match the serial number of the first entry
            serial = re.search(r"SN:\s+(\S+)", show_inventory).group(1)
        except Exception as e:
            print("An error occurred:", e)
            log_info(f"An error occurred: {e}")
            # Handle the exception appropriately here

    if serial:
        print(f"******** Serial number is {serial} ***********")
        log_info(f"******** Serial number is {serial} ***********")
    else:
        print("Serial number could not be determined.")
        log_info("Serial number could not be determined.")

    return serial, stack_switch_status

def get_model():
    print ("******** Trying to  get Model *********** ")
    log_info("******** Trying to  get Model *********** ")
    try:
        show_version = cli('show version')
    except Exception as e:
        time.sleep(90)
        show_version = cli('show version')
    model = re.search(r"Model Number\s+:\s+(\S+)", show_version)
    if model != None:
        model = model.group(1)
    else:     
        model = re.search(r"cisco\s(\w+-.*?)\s", show_version)
        if model != None:
          model = model.group(1)
    return model

def ios_xe_upgrade_bundle_mode(image):
    # Upgrade or downgrade in install mode
    print(f"Activating {image} in BUNDLE mode")
    log_info(f"Activating {image} in BUNDLE mode")

    cli('enable')
    configure('no boot system ')
    configure(f'boot system flash://{image}')
    cli('write mem')
    
    # Clean relad with new firmware version
    clean_reload()

def main_task_printer():
    # This is for log purpose to show what the script is going to do based on several variables
    
    if configuration_status_value == "active":
        print('######  ZTP SCRIPT DETECTED - CONFIGURATION ACTIVE ######\n')
        log_info('######  ZTP SCRIPT DETECTED - CONFIGURATION ACTIVE ######')
        cli("send log 7 ######  ZTP SCRIPT DETECTED - CONFIGURATION ACTIVE ######")
        time.sleep(2)

        print('######  ZTP SCRIPT TASKS WILL BE ######\n')
        log_info('######  ZTP SCRIPT TASKS WILL BE  ######')
        cli("send log 7 ######  ZTP SCRIPT TASKS WILL BE  ######")
        time.sleep(2)

        if stack_switch_status == True:
            print("*** Stack software sync  ***\n")
            log_info("*** Stack software sync  ***")
            cli("send log 7 *** Stack software sync  ***")
            print("*** Stack renumber check  ***\n")
            log_info("*** Stack renumber check  ***")
            cli("send log 7 *** Stack renumber check  ***")
            print("*** Stack priority check  ***\n")
            log_info("*** Stack priority check  ***")
            cli("send log 7 *** Stack priority check  ***")
            time.sleep(2)
            
        print("*** Software upgrade check  ***\n")
        log_info("*** Software upgrade check  ***")
        cli("send log 7 *** Software upgrade check  ***")
        print("*** Save config file to running configuration ***\n")
        log_info("*** Save config file to running configuration ***")
        cli("send log 7 *** Save config file to running configuration ***")
        time.sleep(2)

    elif configuration_status_value == "planned":
        print('######  ZTP SCRIPT DETECTED - CONFIGURATION PLANNED ######\n')
        log_info('######  ZTP SCRIPT DETECTED - CONFIGURATION PLANNED ######')
        cli("send log 7 ######  ZTP SCRIPT DETECTED - CONFIGURATION PLANNED ######")
        time.sleep(2)

        print('######  ZTP SCRIPT TASKS WILL BE ######\n')
        log_info('######  ZTP SCRIPT TASKS WILL BE  ######')
        cli("send log 7 ######  ZTP SCRIPT TASKS WILL BE  ######")
        time.sleep(2)

        print("*** Software upgrade check  ***\n")
        log_info("*** Software upgrade check  ***")
        cli("send log 7 *** Software upgrade check  ***")
        print("*** copy configuration file to startup config ***\n")
        log_info("*** copy configuration file to startup config ***")
        cli("send log 7 *** copy configuration file to startup config ***")
        time.sleep(2)

    elif configuration_status_value == "decommissioning":
        print('######  ZTP SCRIPT DETECTED - CONFIGURATION DECOMMISSIONING ######\n')
        log_info('######  ZTP SCRIPT DETECTED - CONFIGURATION DECOMMISSIONING ######')
        cli("send log 7 ######  ZTP SCRIPT DETECTED - CONFIGURATION DECOMMISSIONING ######")
        time.sleep(2)

        print('######  ZTP SCRIPT TASKS WILL BE ######\n')
        log_info('######  ZTP SCRIPT TASKS WILL BE  ######')
        cli("send log 7 ######  ZTP SCRIPT TASKS WILL BE  ######")
        time.sleep(2)
              
        print("*** Erase startup config ***\n")
        log_info("*** Erase startup config ***")
        cli("send log 7 *** Erase startup config ***")
        time.sleep(2)

    if configuration_status_value == "unknown":
        print('######  ZTP SCRIPT DETECTED - CONFIGURATION UNKNOWN ######\n')
        log_info('######  ZTP SCRIPT DETECTED - CONFIGURATION UNKNOWN ######')
        cli("send log 7 ######  ZTP SCRIPT DETECTED - CONFIGURATION UNKNOWN ######")
        time.sleep(2)

        print('######  ZTP SCRIPT TASKS WILL BE ######\n')
        log_info('######  ZTP SCRIPT TASKS WILL BE  ######')
        cli("send log 7 ######  ZTP SCRIPT TASKS WILL BE  ######")
        time.sleep(2)
              
        print("*** Software upgrade check  ***\n")
        log_info("*** Software upgrade check  ***")
        cli("send log 7 *** Software upgrade check  ***")
        print("*** Erase startup config ***\n")
        log_info("*** Erase startup config ***")
        cli("send log 7 *** Erase startup config ***")
        time.sleep(2)


    print('######  END OF TASK LIST ######\n')
    log_info('######  END OF TASK LIST ######')
    cli("send log 7 ######  END OF TASK LIST ######")
    time.sleep(5)

def log_info(message ):
    if(log_tofile == True):
        ztp_log = logging.getLogger('root')
        ztp_log.info(message)

def log_critical(message ):
    if(log_tofile == True):
        ztp_log = logging.getLogger('root')
        ztp_log.critical(message)

def reload():
    print('**** Starting reload with startup-config *******\n')
    log_info('**** Starting reload with startup-config *******\n')
    cli('reload')

def save_configuration():
    print('**** Saving config*******\n')
    log_info('**** Saving config*******\n')
    cli('write mem')  # This command saves the startup configuration.

def send_email_status(serial, model, configuration_status_value, firmware_upgrade_status):
    ### Form message for mail based on ZTP actions

    def message_body():
        if configuration_status_value == "active":
            mail_text = "Golden firmware image present and configuration merged to running-config."
            return mail_text
        
        elif configuration_status_value == "planned":
            mail_text = "Golden firmware image present and clean startup-config for next boot."
            return mail_text
                    
        elif configuration_status_value == "unknown":
            mail_text = "Golden firmware image present and clean startup-config for next boot."
            return mail_text
        
        elif configuration_status_value == "decommissioning":
            mail_text = "Configuration removed and clean startup-config for next boot."
            return mail_text

    def mailer():
        # Send the email
        try:
            subject = f"ZTP SERVER: DEVICE {model} - {serial} Configuration status: {configuration_status_value}"
            send_mail_line = f'{smtp_server}" port {smtp_server_port} to "{receiver_email}" from "{sender_email}" subject "{subject}" body "{mail_text}'

            eem_commands = ['event manager applet SendEmail',
                            'event none maxrun 600',
                            'action 1.0 cli command "enable"',
                            'action 2.0 mail server "%s"' % send_mail_line,
                            ]

            results = configurep(eem_commands)
            cli("event manager run SendEmail")
            time.sleep(5)

            print('###### Email sent successfully! ######\n')
            log_info('###### Email sent successfully! ######\n')
            cli("send log 7 '###### Email sent successfully! ######")                                   
        except Exception as e:
            print(f'###### Failed to send email: {e} ######\n')
            log_info(f'###### Failed to send email: {e} ######\n')
            cli("send log 7 '###### Failed to send email ######")                    

    if firmware_upgrade_status == False:
        # Form mail text
        mail_text = message_body()
        # Send mail
        mailer()            
    elif firmware_upgrade_status == True:
        # Form mail text
        mail_text = f"{serial} will upgrade to Golden image on reboot with startup config."
        # Send mail
        mailer()

def switch_stack_task_selector():
    if stack_switch_status == True:
        ## switch numbering task
        try:
            # switch stack rumbering task
            switch_stack_renumbering(config_file, model) 
            # switch stack prio numbering
            switch_stack_prio_renumbering(config_file)                                    
            
        except Exception as e:
            print('*** Failure encountered during switch renumbering **\n')
            log_critical('*** Failure encountered during switch renumbering ***\n' + e)
            print(e)
            sys.exit(e)

def switch_stack_prio_renumbering(config_file):
    print("******** Checking if switch stack priority renumbering is needed based on config *********** ")
    log_info("******** Checking if switch stack priority renumbering is needed based on config *********** ")

    time.sleep(60)

    # count switches
    def count_switches():
        try:
            show_switch_output = cli('show switch')
            switch_count = re.findall(r"^\s*\*?(\d+)\s+", show_switch_output, re.MULTILINE)
            return len(switch_count)
        except Exception as e:
            print("Error counting switches:", e)
            log_info(f"Error counting switches: {e}")

    def switch_stack_prio_renumbering_task(config_file):

        # This function checks if the priority numbers are correct of the switches based on the configuration
        # It will change if these are not in sync

        def fetch_current_setup():
            current_setup = {}
            
            # Fetch 'show switch' data
            show_switch = cli('show switch')
            
            # Fetch active and standby switch numbers
            active_switches = re.findall(r"^\s*\*?(\d+)\s+Active", show_switch, re.MULTILINE)
            standby_switches = re.findall(r"^\s*\*?(\d+)\s+Standby", show_switch, re.MULTILINE)
            
            # Fetch 'show inventory' data
            show_inventory = cli('show inventory')

            # Consolidate switch numbers into a list for easy iteration
            switch_numbers = active_switches + standby_switches
            
            for switch_number in switch_numbers:
                try:
                    # Get the priority of the switch
                    priority_match = re.search(fr"^\s*\*?{switch_number}\s+(Active|Standby)\s+\S+\s+(\d+)\s+", show_switch, re.MULTILINE)
                    priority = priority_match.group(2)

                    # Get the serial number of the switch
                    serial_match = re.search(fr'NAME: "Switch {switch_number}".*?PID:.*?,.*?SN: (\S+)', show_inventory, re.DOTALL)
                    serial_number = serial_match.group(1)

                    current_setup[int(switch_number)] = (serial_number, int(priority))
                except Exception as e:
                    print(f"Error while fetching info for switch {switch_number}: {e}")
            
            return current_setup

        def fetch_config_instructions():
            instructions = {}
            show_stack_config = cli(f"more flash:{config_file}")
            matches = re.findall(r"! stack member (\d+) (\S+) priority (\d+)", show_stack_config)
            for match in matches:
                instructions[int(match[0])] = (match[1], int(match[2]))
            return instructions

        current_setup = fetch_current_setup()
        config_instructions = fetch_config_instructions()
        
        # Loop to check if the priority per switch member is correct
        for stack_member, (serial, priority) in config_instructions.items():
            current_serial, current_priority = current_setup.get(stack_member, (None, None))

            if current_serial is None:
                print(f"Stack member {stack_member} is not present in the current setup.")
                log_info(f"Stack member {stack_member} is not present in the current setup.")
                continue
            
            if current_serial != serial:
                print(f"Serial for stack member {stack_member} doesn't match: {current_serial} != {serial}")
                log_info(f"Serial for stack member {stack_member} doesn't match: {current_serial} != {serial}")
                continue
            
            if current_priority != priority:
                print(f"Changing priority for stack member {stack_member} from {current_priority} to {priority}")
                log_info(f"Changing priority for stack member {stack_member} from {current_priority} to {priority}")
                cli(f"switch {stack_member} priority {priority} ")

            else:
                print(f"No priority renumbering needed for {stack_member}, config is in sync with setup")
                log_info(f"No priority renumbering needed for {stack_member}, config is in sync with setup") 

    def switch_stack_prio_renumbering_task_trio_stack(config_file):

        # This function checks if the priority numbers are correct of the switches based on the configuration
        # It will change if these are not in sync

        def fetch_current_setup():
            current_setup = {}
            
            # Fetch 'show switch' data
            show_switch = cli('show switch')
            
            # Fetch active and standby switch numbers
            active_switches = re.findall(r"^\s*\*?(\d+)\s+Active", show_switch, re.MULTILINE)
            standby_switches = re.findall(r"^\s*\*?(\d+)\s+Standby", show_switch, re.MULTILINE)
            member_switches = re.findall(r"^\s*\*?(\d+)\s+Member", show_switch, re.MULTILINE)
            
            # Fetch 'show inventory' data
            show_inventory = cli('show inventory')

            # Consolidate switch numbers into a list for easy iteration
            switch_numbers = active_switches + standby_switches + member_switches
            
            for switch_number in switch_numbers:
                try:
                    # Get the priority of the switch
                    priority_match = re.search(fr"^\s*\*?{switch_number}\s+(Active|Standby|Member)\s+\S+\s+(\d+)\s+", show_switch, re.MULTILINE)
                    priority = priority_match.group(2)

                    # Get the serial number of the switch
                    serial_match = re.search(fr'NAME: "Switch {switch_number}".*?PID:.*?,.*?SN: (\S+)', show_inventory, re.DOTALL)
                    serial_number = serial_match.group(1)

                    current_setup[int(switch_number)] = (serial_number, int(priority))
                except Exception as e:
                    print(f"Error while fetching info for switch {switch_number}: {e}")
            
            return current_setup

        def fetch_config_instructions():
            instructions = {}
            show_stack_config = cli(f"more flash:{config_file}")
            matches = re.findall(r"! stack member (\d+) (\S+) priority (\d+)", show_stack_config)
            for match in matches:
                instructions[int(match[0])] = (match[1], int(match[2]))
            return instructions

        current_setup = fetch_current_setup()
        config_instructions = fetch_config_instructions()
        
        # Loop to check if the priority per switch member is correct
        for stack_member, (serial, priority) in config_instructions.items():
            current_serial, current_priority = current_setup.get(stack_member, (None, None))

            if current_serial is None:
                print(f"Stack member {stack_member} is not present in the current setup.")
                log_info(f"Stack member {stack_member} is not present in the current setup.")
                continue
            
            if current_serial != serial:
                print(f"Serial for stack member {stack_member} doesn't match: {current_serial} != {serial}")
                log_info(f"Serial for stack member {stack_member} doesn't match: {current_serial} != {serial}")
                continue
            
            if current_priority != priority:
                print(f"Changing priority for stack member {stack_member} from {current_priority} to {priority}")
                log_info(f"Changing priority for stack member {stack_member} from {current_priority} to {priority}")
                cli(f"switch {stack_member} priority {priority} ")

            else:
                print(f"No priority renumbering needed for {stack_member}, config is in sync with setup")
                log_info(f"No priority renumbering needed for {stack_member}, config is in sync with setup") 

    def switch_stack_prio_reboot_task(config_file):
    
        def fetch_current_setup():
            current_setup = {}
    
            show_switch = cli('show switch')
            switch_roles = re.findall(r"^\s*\*?(\d+)\s+(Active|Standby)\s+", show_switch, re.MULTILINE)
    
            show_inventory = cli('show inventory')
    
            for switch_number, role in switch_roles:
                try:
                    serial_match = re.search(fr'NAME: "Switch {switch_number}".*?PID:.*?,.*?SN: (\S+)', show_inventory, re.DOTALL)
                    serial_number = serial_match.group(1)
                    current_setup[int(switch_number)] = {'serial_number': serial_number, 'role': role}
                except Exception as e:
                    print(f"Error while fetching info for switch {switch_number}: {e}")
    
            return current_setup
    
        def fetch_config_instructions():
            instructions = {}
            show_stack_config = cli(f"more flash:{config_file}")
            matches = re.findall(r"! stack member (\d+) (\S+) priority (\d+)", show_stack_config)
            for match in matches:
                instructions[match[1]] = {'stack_member': int(match[0]), 'priority': int(match[2])}
    
            return instructions
    
        current_setup = fetch_current_setup()
        config_instructions = fetch_config_instructions()
    
        output_X = {}
        for switch_number, switch_data in current_setup.items():
            serial_number = switch_data['serial_number']
            for config_serial, config_data in config_instructions.items():
                if config_serial == serial_number:
                    output_X[switch_number] = config_data
    
        # Correlate the switch roles with output_X
        for switch_number, switch_data in current_setup.items():
            if switch_number in output_X:
                output_X[switch_number]['current_role'] = switch_data['role']
    
        # Output based on the last correlation
        for switch_number, switch_data in output_X.items():
            expected_role = 'Active' if switch_data['stack_member'] == 1 else 'Standby'
            print(f"Switch {switch_number} is currently {switch_data['current_role']}. It is supposed to be {expected_role} and has a priority of {switch_data['priority']}.")
    
        # Output based on the last correlation
        for switch_number, switch_data in output_X.items():
            expected_role = 'Active' if switch_data['stack_member'] == 1 else 'Standby'
    
            # Corrective actions if needed
            if switch_data['current_role'] != expected_role:
                print(f"Switch {switch_number} is currently {switch_data['current_role']}, but it is supposed to be {expected_role}. Reloading switch with clean configuration.")
                save_configuration()
                clean_reload()
            else:
                print(f"Switch {switch_number} is currently {switch_data['current_role']}. It is correctly set to be {expected_role} and has a priority of {switch_data['priority']}.")

    # Runner of function
    # In the switch_stack_renumbering function
    switch_count = count_switches()

    # Selector based on how many switches are in the stack
    if switch_count == 2:
        # Running function for stack of two members
        switch_stack_prio_renumbering_task(config_file)
    elif switch_count == 3:
        # Running function for stack of three members
        switch_stack_prio_renumbering_task_trio_stack(config_file)
    else:
        print(f"Stack member count is {switch_count}. Not supported yet")
        log_info(f"Stack member count is {switch_count}. Not supported yet")

    if switch_count <= 3:
        # Reboot task if switch(es) need to change role
        switch_stack_prio_reboot_task(config_file)

def switch_stack_renumbering(config_file, model):
    print("******** Checking if switch stack renumbering is needed based on config *********** ")
    log_info("******** Checking if switch stack renumbering is needed based on config *********** ")
    time.sleep(60)

    # Segmented in two types
    # 1. For stack members of two
    # 3. For stack members of three

    # Renumbering has a difference in syntax for 9300 and 9200

    # count switches
    def count_switches():
        try:
            show_switch_output = cli('show switch')
            switch_count = re.findall(r"^\s*\*?(\d+)\s+", show_switch_output, re.MULTILINE)
            return len(switch_count)
        except Exception as e:
            print("Error counting switches:", e)
            log_info(f"Error counting switches: {e}")
    # Get stack info for two member stack situation
    def get_active_standby_switches():
        try:
            show_switch = cli('show switch')
            active_switch = re.search(r"^\s*\*?(\d+)\s+Active", show_switch, re.MULTILINE).group(1)
            standby_switch = re.search(r"^\s*\*?(\d+)\s+Standby", show_switch, re.MULTILINE).group(1)

            print(f"******** Active switch {active_switch} *********** ")
            log_info(f"******** Active switch {active_switch} *********** ")            
            print(f"******** Standby switch {standby_switch} *********** ")
            log_info(f"******** Standby switch {standby_switch} *********** ")   

            return active_switch, standby_switch
        except Exception as e:
            print("Error getting active and standby switches:", e)
            log_info(f"Error getting active and standby switches: {e}")
    # Get stack info if the are more then two members in the stack
    def get_active_standby_member_switches():
        try:
            show_switch_output = cli('show switch')
            active_switch = re.search(r"^\s*\*?(\d+)\s+Active", show_switch_output, re.MULTILINE).group(1)
            standby_switch = re.search(r"^\s*\*?(\d+)\s+Standby", show_switch_output, re.MULTILINE).group(1)
            # member_switches = re.search(r"^\s*\*?(\d+)\s+Member", show_switch_output, re.MULTILINE).group(1)
            
            member_switches_pattern = r"^\s*(\d+)\s+Member" if switch_count > 3 else r"^\s*\*?(\d+)\s+Member"
            member_switches = re.findall(member_switches_pattern, show_switch_output, re.MULTILINE)

            print(f"******** Active switch {active_switch} *********** ")
            log_info(f"******** Active switch {active_switch} *********** ")            
            print(f"******** Standby switch {standby_switch} *********** ")
            log_info(f"******** Standby switch {standby_switch} *********** ")            
            print(f"******** Member switches {member_switches} *********** ")
            log_info(f"******** Member switches {member_switches} *********** ")            

            return active_switch, standby_switch, member_switches

        except Exception as e:
            print("Error getting active and standby switches:", e)
            log_info(f"Error getting active and standby switches: {e}")        
    # Get member info (if the stack is with three members)
    def get_member_switch():
        try:
            show_switch_output = cli('show switch')
            member_switch = re.search(r"^\s*\*?(\d+)\s+Member", show_switch_output, re.MULTILINE).group(1)      
            print(f"******** Member switch is {member_switch} *********** ")
            log_info(f"******** Member switch is {member_switch} *********** ")            
            return member_switch
        except Exception as e:
            print("Error getting member switch:", e)
            log_info(f"Error getting member switch: {e} ")              
    # Get members info (if the stack is with more then three members)        
    def get_members_switch():
        y = "y"
    # Corolate switch numbers with serial numbers
    def get_serial_by_switch_number(switch_number):
        try:
            show_inventory = cli('show inventory')
            serial_search = re.search(r'NAME: "Switch ' + switch_number + r'".*?PID:.*?,.*?SN: (\S+)', show_inventory, re.DOTALL)
            return serial_search.group(1)
        except Exception as e:
            print("Error getting serial by switch number:", e)
            log_info(f"Error getting serial by switch number: {e}")
    # Corrective actions for two stack members
    def correction_active_standby_switches():
        print("******** Current stack switch situation *********** ")
        log_info("******** Current stack switch situation *********** ")
        
        if active_switch != active_info.get('switch') or standby_switch != standby_info.get('switch'):
            print("Mismatch found between configuration file and current switch setup.")
            log_info("Mismatch found between configuration file and current switch setup.")
            

            # Changes if needed
            print("Corrective actions:")
            log_info("Corrective actions:")

            ## For Cisco 9200 series (stack)
            if 'C9200' in model:
                if active_switch != active_info.get('switch'):
                    print(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    cli(f"switch {active_switch} renumber {active_info.get('switch')}")
                    cli(f"switch {standby_switch} renumber {standby_info.get('switch')}")
                    save_configuration()
                    clean_reload()

                if standby_switch != standby_info.get('switch'):
                    print(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    cli(f"switch {active_switch} renumber {active_info.get('switch')}")
                    cli(f"switch {standby_switch} renumber {standby_info.get('switch')}")
                    save_configuration()
                    clean_reload()

            ## For Cisco 9300 series (stack)
            elif 'C9300' in model:
                if active_switch != active_info.get('switch'):
                    print(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    cli(f"switch {active_switch} renumber {active_info.get('switch')}")
                    save_configuration()
                    clean_reload()

                if standby_switch != standby_info.get('switch'):
                    print(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    cli(f"switch {standby_switch} renumber {standby_info.get('switch')}")
                    save_configuration()
                    clean_reload()

        else:
            print("No switch stack renumbering is needed. Config in sync with switch nummers.")
            log_info("No switch stack renumbering is needed. Config in sync with switch nummers.")
    # Corrective actions for stacked switches larger then two members
    def correction_active_standby_members_switches():

        # Debug
        print(f"current active switch = {active_switch} configuration switch = {active_info.get('switch')}")
        log_info(f"current active switch = {active_switch} configuration switch = {active_info.get('switch')}")
        print(f"current standby standby = {standby_switch} configuration switch = {standby_info.get('switch')}")
        log_info(f"current standby standby = {standby_switch} configuration switch = {standby_info.get('switch')}")                       
        print(f"current member switch = {member_switch} configuration switch = {member_info.get('switch')}")
        log_info(f"current member switch = {member_switch} configuration switch = {member_info.get('switch')}")

        print("******** Correcting Stack Switch Numbers *********** ")
        log_info("******** Correcting Stack Switch Numbers *********** ")

        if active_switch != active_info.get('switch') or standby_switch != standby_info.get('switch') or member_switch != member_info.get('switch'):
            print("Mismatch found between configuration file and current switch setup.")
            log_info("Mismatch found between configuration file and current switch setup.")

            # Changes if needed
            print("Corrective actions:")
            log_info("Corrective actions:")

            ## For Cisco 9200 series (stack)
            if 'C9200' in model:
                if member_switch != member_info.get('switch'):                    
                    print(f"Reconfigure Switch {member_switch} to be Switch {member_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {member_switch} to be Switch {member_info.get('switch')}.")

                    if active_switch != active_info.get('switch'):                       
                        cli(f"switch {member_switch} renumber {member_info.get('switch')}")                        
                        cli(f"switch {active_switch} renumber {active_info.get('switch')}")
                        bug_work_around_696657788()
                        save_configuration()
                        cli("reload")                   
            

                    if standby_switch != standby_info.get('switch'):                                               
                        cli(f"switch {member_switch} renumber {member_info.get('switch')}")
                        cli(f"switch {standby_switch} renumber {standby_info.get('switch')}")                    
                        bug_work_around_696657788()
                        save_configuration()
                        cli("reload")

                if active_switch != active_info.get('switch') and standby_switch != standby_info.get('switch'):
                    print(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    cli(f"switch {active_switch} renumber {active_info.get('switch')}")
                    cli(f"switch {standby_switch} renumber {standby_info.get('switch')}")
                    bug_work_around_696657788()
                    save_configuration()
                    cli("reload")
                    #clean_reload()

                # if standby_switch != standby_info.get('switch'):
                #     print(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                #     log_info(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                #     cli(f"switch {active_switch} renumber {active_info.get('switch')}")
                #     cli(f"switch {standby_switch} renumber {standby_info.get('switch')}")
                #     save_configuration()
                #     clean_reload()

            ## For Cisco 9300 series (stack)
            elif 'C9300' in model:
                if active_switch != active_info.get('switch'):
                    print(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {active_switch} to be Switch {active_info.get('switch')}.")
                    cli(f"switch {active_switch} renumber {active_info.get('switch')}")
                    save_configuration()
                    clean_reload()

                if standby_switch != standby_info.get('switch'):
                    print(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    cli(f"switch {standby_switch} renumber {standby_info.get('switch')}")
                    save_configuration()
                    clean_reload()

                if member_switch != member_info.get('switch'):
                    print(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    log_info(f"Reconfigure Switch {standby_switch} to be Switch {standby_info.get('switch')}.")
                    cli(f"switch {member_switch} renumber {member_info.get('switch')}")
                    save_configuration()
                    clean_reload()                    

        else:
            print("No switch stack renumbering is needed. Config in sync with switch nummers.")
            log_info("No switch stack renumbering is needed. Config in sync with switch nummers.")              

    # Runner of function
    # In the switch_stack_renumbering function
    switch_count = count_switches()
    print(f"******** Switches in stack: {switch_count}  *********** ")
    log_info(f"******** Switches in stack: {switch_count}  *********** ")


    # For stacks with only two members
    if (switch_count) == 2:
        # Information gathering
        active_switch, standby_switch = get_active_standby_switches()
        
        show_stack_config = cli(f"more flash:{config_file}")
        stack_members = re.findall(r"! stack member (\d+) (\S+)", show_stack_config)

        # Corolation loop: switch numbering based on configuration to serial
        switch_info = {}
        for switch, serial in stack_members:
            switch_info[serial] = {"switch": switch}
        
        active_info = switch_info.get(get_serial_by_switch_number(active_switch), {})
        standby_info = switch_info.get(get_serial_by_switch_number(standby_switch), {})

        # Correction handler
        correction_active_standby_switches()

    # For stacks with more then two members        
    elif (switch_count) > 2:       
        # For stacks with more two members
        # Information handler
        active_switch, standby_switch = get_active_standby_switches()
        
        show_stack_config = cli(f"more flash:{config_file}")
        stack_members = re.findall(r"! stack member (\d+) (\S+)", show_stack_config)

        # Corolation loop: switch numbering based on configuration to serial
        switch_info = {}
        for switch, serial in stack_members:
            switch_info[serial] = {"switch": switch}

        active_info = switch_info.get(get_serial_by_switch_number(active_switch), {})
        standby_info = switch_info.get(get_serial_by_switch_number(standby_switch), {})

        if switch_count == 3:
            member_switch = get_member_switch()
            member_info = switch_info.get(get_serial_by_switch_number(member_switch), {})
        # elif switch_count > 3:
        #      # Todo --> Function to corolate members to switch numbers
        #     print("******** Stacks with more then three members not supported yet for renumbering  *********** ")
        #     log_info("******** Stacks with more then three members not supported yet for renumbering  *********** ")
        #     break        
        # Correction handler

        print(f"******** stack members detected {stack_members}  *********** ")
        log_info(f"******** stack members detected {stack_members}  *********** ")
        correction_active_standby_members_switches()

def update_config(file,file_system='flash:/'):
    update_running_config = 'copy %s%s running-config' % (file_system, file)
    save_to_startup = 'write memory'
    print("************************Copying to startup-config************************\n")
    running_config = executep(update_running_config)
    startup_config = executep(save_to_startup)

def upgrade_required(target_version):
    def version_components(version):
        # Find all numeric and non-numeric components of the version
        components = re.findall(r'(\d+|\D+)', version)
        # Convert numeric strings to integers
        return [int(part) if part.isdigit() else part for part in components]

    def compare_versions(version1, version2):
        for part1, part2 in zip(version_components(version1), version_components(version2)):
            if part1 < part2:
                return -1
            elif part1 > part2:
                return 1
        return 0

    # Obtains show version output
    sh_version = cli('show version')
    current_version = re.search(r"Cisco IOS XE Software, Version\s+(\S+)", sh_version).group(1)
    print('**** Current Code Version is %s ****** \n' % current_version)
    print('**** Target Code Version is %s ****** \n' % target_version)
    log_info('**** Current Code Version is %s ****** \n' % current_version)
    log_info('**** Target Code Version is %s ****** \n' % target_version)

    comparison_result = compare_versions(target_version, current_version)

    if comparison_result == 0:
        return False, current_version
    elif comparison_result > 0:
        return 'upgrade', current_version
    else:
        return 'downgrade', current_version

def upgrade_runner_cisco_ios_xe_9200_cx(model):

    def deploy_9200_cx_eem_upgrade_script(software_image, config_file):
        # Upgrade action is preformed after guest-shell is detroyed (to make more space on storage)
        print ('*** Performing the upgrade in 300 seconds - switch will reboot ***\n')
        log_info('*** Performing the upgrade in 300 seconds - switch will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        merge_config_to_startup = f'copy flash:{config_file} startup-config'
        eem_commands = ['event manager applet upgrade',
                        'event timer countdown time 300 maxrun 1200',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "configure terminal"',
                        'action 3.1 cli command "file prompt quiet"',
                        'action 3.2 cli command "exit"',
                        'action 4.0 cli command "write mem"',
                        'action 5.0 cli command "%s"' % install_command,                                       
                        'action 6.0 cli command "%s"' % merge_config_to_startup, 
                        'action 7.0 cli command "configure terminal"',
                        'action 7.1 cli command "no file prompt quiet"',
                        'action 7.2 cli command "exit"',
                        ]
        results = configurep(eem_commands)

    def deploy_9200_cx_eem_reboot_clean():
        eem_commands = ['event manager applet reboot_clean',
                        'event syslog pattern "SYS-5-RESTART" maxrun 600',
                        'action 1.0 wait 180',
                        'action 2.0 cli command "enable"',
                        'action 3.0 cli command "configure terminal"',
                        'action 4.0 cli command "no event manager applet upgrade"',
                        'action 5.0 cli command "exit"',
                        'action 6.0 cli command "install remove inactive" pattern "Do you want to remove the above files?"',
                        'action 7.0 cli command "y"'         
                        ]
        results = configurep(eem_commands)
        print ('*** Successfully configured cleanup EEM reboot cleaner script on device! ***')
        log_info('*** Successfully configured cleanup EEM reboot cleaner script on device! ***')      

    def cisco_9200_cx_update_runner(current_version, software_image):

        # Making space on flash drive for firmware to download
        time.sleep(30)
        print('*** Deploying clean up script ***')
        log_info('*** Deploying clean up script ***')
        deploy_eem_cleanup_script()
        cli('event manager run cleanup')
        time.sleep(90) 
            
        ## Check if image transfer needed (boolean)
        # If image excists on flash drives:
        if check_file_exists(software_image):
            pass

        # If image doens't excist
        else:
            print ('*** Attempting to transfer image to switch.. ***')
            log_info('*** Attempting to transfer image to switch.. ***')
            
            # Download firmware
            print ('*** Attempting to transfer image to flash.. ***')
            log_info('*** Attempting to transfer image to flash.. ***')
            firmware_transfer(http_server ,software_image)

        # md5 hash checker
        verify_dst_image_md5(software_image, software_md5_checksum)
                            
        # Add post reload cleaner script
        deploy_9200_cx_eem_reboot_clean()             

        ## Deploy upgrade script
        deploy_9200_cx_eem_upgrade_script(software_image, config_file)

        # Run upgrade script
        print('*** Upgrading switch - Reload while start soon ***')
        log_info('*** Upgrading switch - Reload while start soon ***')     
        cli("event manager run upgrade")

        ### Remove configuration reload (To invoke ZTP again, if device has no configuration) ###
        if configuration_status_value == "planned" or configuration_status_value == "unknown":
            # Removing all the configuration    
            cli("send log 7 ### ZTP SCRIPT - REMOVING START-UP CONFIGURATION")
            deploy_eem_cleanup_script_reload()   
            deploy_eem_clean_config_reload()
            save_configuration()        

        ### Merging configuration to startup to let the 9800 start with configuration
        if configuration_status_value == "active":
            # Merge configuration file from ztp to startup
            configure_merge_file_to_startup_config(config_file) 

        # Return firmware upgrade status
        firmware_upgrade_status = True
        return firmware_upgrade_status                             

    # Set firmware upgrade status default on false
    firmware_upgrade_status = False

   # Main function runner        
    try:
        software_image = software_mappings[model]['software_image']
        software_version = software_mappings[model]['software_version']
        software_md5_checksum = software_mappings[model]['software_md5_checksum']
        
        print ('**** Checking if upgrade is required or not ***** \n')
        log_info('**** Checking if upgrade is required or not ***** \n')

        #Unpack the tuble returned by upgrade_required()
        firmware_action, current_version = upgrade_required(software_version)

        # Upgrade taskdir 
        if firmware_action == 'upgrade':

            # Upgrade is required
            print ('*** Upgrade is required!!! *** \n')
            log_info('*** Upgrade is required!!! *** \n')
            firmware_upgrade_status = cisco_9200_cx_update_runner(current_version, software_image)

        # downgrade task
        elif firmware_action == 'downgrade':            

            # Upgrade is required
            print ('*** Downgrade is required!!! *** \n')
            log_info('*** Downgrade is required!!! *** \n')
            firmware_upgrade_status = cisco_9200_cx_update_runner(current_version, software_image)
            
        else:
            print ('*** No upgrade is required!!! *** \n')
            log_info('*** No upgrade is required!!! *** \n')
            firmware_upgrade_status = False

        return firmware_upgrade_status               
           
    except Exception as e:
        print('*** Failure encountered during upgrade of software **\n')
        log_critical('*** Failure encountered during upgrade of software ***\n' + e)
        print(e)
        sys.exit(e)

def upgrade_runner_cisco_ios_xe_9200(model, config_file):

    # This function upgrades the Cisco 9200 series. 
    # The code looks a bit sloppy, but this is because there is limit
    # storage space on the drive.

    def cisco_9200_flash_cleaner(current_version):
        # Delete current firmware version and files to make space
        print(f"Deleting files of {current_version}")
        
        # IOS firmware files
        show_flash_space = cli("show flash: | i cat9k_lite")
        print(show_flash_space)
    
        # Initialize a flag to check if any files were deleted
        files_deleted = False
    
        try:
            if "cat9k_lite_iosxe_npe." + str(current_version) in show_flash_space:
                cli(f"delete /force flash:cat9k_lite_iosxe_npe.{current_version}.SPA.bin")
                print(f"Deleted flash:cat9k_lite_iosxe_npe.{current_version}.SPA.bin")
                log_info(f"Deleted flash:cat9k_lite_iosxe_npe.{current_version}.SPA.bin")
                files_deleted = True
                             
            if not files_deleted:
                print("No files found to be deleted")
                log_info("No files found to be deleted")
    
        except Exception as e:
            print(f'*** Failure to make room on flash for upgrade: {e} ***\n')
            log_critical(f'*** Failure to make room on flash for upgrade: {e} ***\n')

    def cisco_9200_flash_cleaner_stack(current_version): 
        # Detect how many flash drives are present
        show_switch = cli('show switch')
        switches = re.findall(r"^\s*\*?(\d+)\s+", show_switch, re.MULTILINE)

        # Delete current firmware version and files to make space
        print(f"Deleting files of {current_version}")

        # Initialize a flag to check if any files were deleted
        files_deleted = False

        try:
            for switch in switches:
                output = cli(f'show flash-{switch}: | i cat9k_lite')
                print(output)
                
                if "cat9k_lite_iosxe_npe." + str(current_version) in output:
                    cli(f"delete /force flash-{switch}:cat9k_lite_iosxe_npe.{current_version}.SPA.bin")
                    print(f"Deleted flash-{switch}:cat9k_lite_iosxe_npe.{current_version}.SPA.bin")
                    files_deleted = True                    
        
                elif not files_deleted:
                    print(f"No files found to be deleted on flash-{switch} of switch {switch}")
                    log_info(f"No files found to be deleted on flash-{switch} of switch {switch}")

    
        except Exception as e:
            print(f'*** Failure to make room on flash for upgrade: {e} ***\n')
            log_critical(f'*** Failure to make room on flash for upgrade: {e} ***\n')

    def deploy_9200_eem_upgrade_script(software_image, config_file):
        # Upgrade action is preformed after guest-shell is detroyed (to make more space on storage)
        print ('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        log_info('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        merge_config_to_startup = f'copy flash:{config_file} startup-config'
        eem_commands = ['event manager applet upgrade',
                        'event timer countdown time 360 maxrun 1200',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "configure terminal"',
                        'action 3.1 cli command "file prompt quiet"',
                        'action 3.2 cli command "exit"',
                        'action 4.0 cli command "write mem"',
                        'action 5.0 cli command "%s"' % merge_config_to_startup,                        
                        'action 6.0 cli command "%s"' % install_command,                                       
                        'action 7.0 cli command "%s"' % merge_config_to_startup, 
                        'action 8.0 cli command "configure terminal"',
                        'action 8.1 cli command "no file prompt quiet"',
                        'action 8.2 cli command "exit"',
                        ]
        results = configurep(eem_commands)

    def deploy_9200_eem_upgrade_script_stack(software_image, config_file):
        # Upgrade action is preformed after guest-shell is detroyed (to make more space on storage)
        print ('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        log_info('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        merge_config_to_startup = f'copy flash:{config_file} startup-config'
        eem_commands = ['event manager applet upgrade',
                        'event timer countdown time 360 maxrun 1200',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "configure terminal"',
                        'action 3.1 cli command "file prompt quiet"',
                        'action 3.2 cli command "exit"',
                        'action 4.0 cli command "write mem"',
                        'action 5.0 cli command "%s"' % install_command,                                       
                        'action 6.0 cli command "%s"' % merge_config_to_startup, 
                        'action 7.0 cli command "configure terminal"',
                        'action 7.1 cli command "no file prompt quiet"',
                        'action 7.2 cli command "exit"',
                        ]
        results = configurep(eem_commands)

    def deploy_9200_eem_upgrade_script_clean(software_image, config_file):
        # Upgrade action is preformed after guest-shell is detroyed (to make more space on storage)
        print ('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        log_info('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        eem_commands = ['event manager applet upgrade',
                        'event timer countdown time 360 maxrun 1200',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "configure terminal"',
                        'action 3.1 cli command "file prompt quiet"',
                        'action 3.2 cli command "exit"',
                        'action 4.0 cli command "write mem"',                    
                        'action 6.0 cli command "%s"' % install_command,                                       
                        'action 7.0 cli command "configure terminal"',
                        'action 7.1 cli command "no file prompt quiet"',
                        'action 7.2 cli command "exit"',
                        ]
        results = configurep(eem_commands)

    def deploy_9200_eem_upgrade_script_stack_clean(software_image, config_file):
        # Upgrade action is preformed after guest-shell is detroyed (to make more space on storage)
        print ('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        log_info('*** Performing the upgrade in 360 seconds - switch will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        eem_commands = ['event manager applet upgrade',
                        'event timer countdown time 360 maxrun 1200',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "configure terminal"',
                        'action 3.1 cli command "file prompt quiet"',
                        'action 3.2 cli command "exit"',
                        'action 4.0 cli command "write mem"',
                        'action 5.0 cli command "%s"' % install_command,                                       
                        'action 6.0 cli command "configure terminal"',
                        'action 6.1 cli command "no file prompt quiet"',
                        'action 6.2 cli command "exit"',
                        ]
        results = configurep(eem_commands)

    def cisco_9200_update_runner(current_version, software_image):
        # Making space on flash drive for firmware to download
        time.sleep(30)
        print('*** Deploying clean up script ***')
        log_info('*** Deploying clean up script ***')
        deploy_eem_cleanup_script()
        cli('event manager run cleanup')
        # Wait until cleanup is done
        if stack_switch_status == True:
            time.sleep(120) 
        # single upgrade
        elif stack_switch_status == False: 
            time.sleep(30)       

        
        # Extra file remover        
        print("Cisco 9200 series detected, using 9200 flash cleaner")
        if stack_switch_status == True:
            cisco_9200_flash_cleaner_stack(current_version)
        # single upgrade
        elif stack_switch_status == False: 
            cisco_9200_flash_cleaner(current_version)        

        ## Check if image transfer needed (boolean)
        # If image excists on flash drives:
        if check_file_exists(software_image):
            pass

        # If image doens't excist
        else:
            print ('*** Attempting to transfer image to switch.. ***')
            log_info('*** Attempting to transfer image to switch.. ***')

            # Making space on flash drive for firmware to download
            print('*** Deploying clean up script ***')
            log_info('*** Deploying clean up script ***')
            
            print("Cisco 9200 series detected, using 9200 flash cleaner")
            cisco_9200_flash_cleaner(current_version)
            
            # Download firmware
            print ('*** Attempting to transfer image to flash.. ***')
            log_info('*** Attempting to transfer image to flash.. ***')
            firmware_transfer(http_server ,software_image)

        # md5 hash checker
        verify_dst_image_md5(software_image, software_md5_checksum)


        ## Deploy upgrade script
        # activate configuration after reload
        if configuration_status_value == "active":
            # stack upgrade
            if stack_switch_status == True:
                deploy_9200_eem_upgrade_script_stack(software_image, config_file)
            # single upgrade
            elif stack_switch_status == False: 
                deploy_9200_eem_upgrade_script(software_image, config_file)

        # Deploy upgrade with no configuration save
        if configuration_status_value == "planned" or configuration_status_value == "unknown":
            # stack upgrade
            if stack_switch_status == True:
                deploy_9200_eem_upgrade_script_clean(software_image, config_file)
            # single upgrade
            elif stack_switch_status == False: 
                deploy_9200_eem_upgrade_script_stack_clean(software_image, config_file)  

        ### Remove configuration reload (To invoke ZTP again, if device has no configuration) ###
        if configuration_status_value == "planned" or configuration_status_value == "unknown":
            # Removing all the configuration    
            cli("send log 7 ### ZTP SCRIPT - REMOVING START-UP CONFIGURATION")   
            deploy_eem_clean_config_reload()

        # Make storage free after reboot to ensure that space is free
        deploy_eem_cleanup_script_reload()
        

        # Return firmware upgrade status
        firmware_upgrade_status = True
        return firmware_upgrade_status
                                                                                         
    # Main function runner        
    try:
        software_image = software_mappings[model]['software_image']
        software_version = software_mappings[model]['software_version']
        software_md5_checksum = software_mappings[model]['software_md5_checksum']
        
        print ('**** Checking if upgrade is required or not ***** \n')
        log_info('**** Checking if upgrade is required or not ***** \n')

        #Unpack the tuble returned by upgrade_required()
        firmware_action, current_version = upgrade_required(software_version)

        # Upgrade taskdir 
        if firmware_action == 'upgrade':

            # Upgrade is required
            print ('*** Upgrade is required!!! *** \n')
            log_info('*** Upgrade is required!!! *** \n')
            # upgrade runner
            firmware_upgrade_status = cisco_9200_update_runner(current_version, software_image)

        # downgrade task
        elif firmware_action == 'downgrade':            
            # Upgrade is required
            print ('*** Downgrade is required!!! *** \n')
            log_info('*** Downgrade is required!!! *** \n')
            # downgrade runner
            firmware_upgrade_status = cisco_9200_update_runner(current_version, software_image)

        else:
            print ('*** No upgrade is required!!! *** \n')
            log_info('*** No upgrade is required!!! *** \n')
            firmware_upgrade_status = False
                  
        return firmware_upgrade_status   


    except Exception as e:
        print('*** Failure encountered during upgrade of software **\n')
        log_critical('*** Failure encountered during upgrade of software ***\n' + e)
        print(e)
        sys.exit(e)

def upgrade_runner_cisco_ios_xe_9300(model):

    def deploy_9300_eem_upgrade_script(software_image):

        print ('*** Performing the upgrade - switch will reboot ***\n')
        log_info('*** Performing the upgrade - switch will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        eem_commands = ['event manager applet upgrade',
                        'event none maxrun 600',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "write mem"',
                        'action 3.0 cli command "%s"' % install_command,
                        ]
        results = configurep(eem_commands)

    def deploy_9300_eem_reboot_clean():
        eem_commands = ['event manager applet reboot_clean',
                        'event syslog pattern "SYS-5-RESTART" maxrun 600',
                        'action 1.0 wait 180',
                        'action 2.0 cli command "enable"',
                        'action 3.0 cli command "configure terminal"',
                        'action 4.0 cli command "no event manager applet upgrade"',
                        'action 5.0 cli command "exit"',
                        'action 6.0 cli command "install remove inactive" pattern "Do you want to remove the above files?"',
                        'action 7.0 cli command "y"'         
                        ]
        results = configurep(eem_commands)
        print ('*** Successfully configured cleanup EEM reboot cleaner script on device! ***')
        log_info('*** Successfully configured cleanup EEM reboot cleaner script on device! ***')      

    def cisco_9300_update_runner(current_version, software_image):

        # Making space on flash drive for firmware to download
        time.sleep(30)
        print('*** Deploying clean up script ***')
        log_info('*** Deploying clean up script ***')
        deploy_eem_cleanup_script()
        cli('event manager run cleanup')
        time.sleep(30)
            
        ## Check if image transfer needed (boolean)
        # If image excists on flash drives:
        if check_file_exists(software_image):
            pass

        # If image doens't excist
        else:
            print ('*** Attempting to transfer image to switch.. ***')
            log_info('*** Attempting to transfer image to switch.. ***')
            
            # Download firmware
            print ('*** Attempting to transfer image to flash.. ***')
            log_info('*** Attempting to transfer image to flash.. ***')
            firmware_transfer(http_server ,software_image)

        # md5 hash checker
        verify_dst_image_md5(software_image, software_md5_checksum)
        
        # Add post reload cleaner script
        deploy_9300_eem_reboot_clean()             

        # Save new config
        save_configuration()

        ## Deploy upgrade script
        deploy_9300_eem_upgrade_script(software_image)

        # Run upgrade script
        print('*** Upgrading switch - Reload while start soon ***')
        log_info('*** Upgrading switch - Reload while start soon ***')     
        cli("event manager run upgrade")


        ### Remove configuration reload (To invoke ZTP again, if device has no configuration) ###
        if configuration_status_value == "planned" or configuration_status_value == "unknown":
            # Removing all the configuration    
            cli("send log 7 ### ZTP SCRIPT - REMOVING START-UP CONFIGURATION")
            deploy_eem_cleanup_script_reload()   
            deploy_eem_clean_config_reload()
            save_configuration()       

        if configuration_status_value == "active":
            # Merge configuration file from ztp to startup
            configure_merge_file_to_startup_config(config_file)
            
            # Because Cisco makes there products not uniform, the script has to dubble save
            # The start-up configuration. And stop the whole script from working
            if stack_switch_status == True:
                configure_merge_file_to_startup_config(config_file)
                configure_ssh_keys()
                time.sleep(24000)

        firmware_upgrade_status = True
        return firmware_upgrade_status                               

   # Main function runner        
    try:
        software_image = software_mappings[model]['software_image']
        software_version = software_mappings[model]['software_version']
        software_md5_checksum = software_mappings[model]['software_md5_checksum']
        
        print ('**** Checking if upgrade is required or not ***** \n')
        log_info('**** Checking if upgrade is required or not ***** \n')

        #Unpack the tuble returned by upgrade_required()
        firmware_action, current_version = upgrade_required(software_version)

        # Upgrade taskdir 
        if firmware_action == 'upgrade':

            # Upgrade is required
            print ('*** Upgrade is required!!! *** \n')
            log_info('*** Upgrade is required!!! *** \n')
            firmware_upgrade_status = cisco_9300_update_runner(current_version, software_image)          

        # downgrade task
        elif firmware_action == 'downgrade':            

            # Upgrade is required
            print ('*** Downgrade is required!!! *** \n')
            log_info('*** Downgrade is required!!! *** \n')
            firmware_upgrade_status = cisco_9300_update_runner(current_version, software_image)
                   
        else:
            print ('*** No upgrade is required!!! *** \n')
            log_info('*** No upgrade is required!!! *** \n')
            firmware_upgrade_status = False
                  
        return firmware_upgrade_status   

    except Exception as e:
        print('*** Failure encountered during upgrade of software **\n')
        log_critical('*** Failure encountered during upgrade of software ***\n' + e)
        print(e)
        sys.exit(e)

def upgrade_runner_cisco_ios_xe_9800(model):

    def deploy_9800_eem_upgrade_script(software_image, config_file):
        # Upgrade action is preformed after guest-shell is detroyed (to make more space on storage)
        print ('*** Performing the upgrade in 360 seconds - WLC will reboot ***\n')
        log_info('*** Performing the upgrade in 360 seconds - WLC will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        merge_config_to_startup = f'copy flash:{config_file} startup-config'
        eem_commands = ['event manager applet upgrade',
                        'event timer countdown time 360 maxrun 1200',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "configure terminal"',
                        'action 3.1 cli command "file prompt quiet"',
                        'action 3.2 cli command "exit"',
                        'action 4.0 cli command "write mem"',
                        'action 5.0 cli command "%s"' % merge_config_to_startup,                        
                        'action 6.0 cli command "%s"' % install_command,                                       
                        'action 7.0 cli command "%s"' % merge_config_to_startup, 
                        'action 8.0 cli command "configure terminal"',
                        'action 8.1 cli command "no file prompt quiet"',
                        'action 8.2 cli command "exit"',                       
                        ]
        results = configurep(eem_commands)

    def deploy_9800_eem_upgrade_script_clean(software_image, config_file):
        # Upgrade action is preformed after guest-shell is detroyed (to make more space on storage)
        print ('*** Performing the upgrade in 360 seconds - WLC will reboot ***\n')
        log_info('*** Performing the upgrade in 360 seconds - WLC will reboot ***\n')
        # Upgrade process
        install_command = 'install add file flash:' + software_image + ' activate commit prompt-level none'
        eem_commands = ['event manager applet upgrade',
                        'event timer countdown time 360 maxrun 1200',
                        'action 1.0 cli command "enable"',
                        'action 2.0 cli command "write mem"',                    
                        'action 3.0 cli command "%s"' % install_command,                                       
                        ]
        results = configurep(eem_commands)

    def deploy_9800_eem_reboot_clean():
        eem_commands = ['event manager applet reboot_clean',
                        'event syslog pattern "SYS-5-RESTART" maxrun 600',
                        'action 1.0 wait 180',
                        'action 2.0 cli command "enable"',
                        'action 3.0 cli command "configure terminal"',
                        'action 4.0 cli command "no event manager applet upgrade"',
                        'action 5.0 cli command "exit"',
                        'action 6.0 cli command "install remove inactive" pattern "Do you want to remove the above files?"',
                        'action 7.0 cli command "y"'         
                        ]
        results = configurep(eem_commands)
        print ('*** Successfully configured cleanup EEM reboot cleaner script on device! ***')
        log_info('*** Successfully configured cleanup EEM reboot cleaner script on device! ***')      

    def cisco_9800_update_runner(current_version, software_image):
        ## Check if image transfer needed (boolean)
        # If image excists on flash drives:
        if check_file_exists(software_image):
            pass

        # If image doens't excist
        else:
            # First clean flash:
            print ('*** Attempting make some space on flash: ***')
            log_info('*** Attempting make some space on flash: ***')
            deploy_eem_cleanup_script()
            cli("event manager run cleanup")
            time.sleep(300)

            # Download firmware
            print ('*** Attempting to transfer image to flash.. ***')
            log_info('*** Attempting to transfer image to flash.. ***')
            firmware_transfer(http_server ,software_image)

        # md5 hash checker
        verify_dst_image_md5(software_image, software_md5_checksum)

        # Add post reload cleaner script
        deploy_9800_eem_reboot_clean()             

        # Activating boot config
        configurep("boot sys flash bootflash:packages.conf")

        
        ### Remove configuration reload (To invoke ZTP again, if device has no configuration) ###
        if configuration_status_value == "planned" or configuration_status_value == "unknown":
            # Removing all the configuration    
            cli("send log 7 ### ZTP SCRIPT - REMOVING START-UP CONFIGURATION")
            deploy_eem_cleanup_script_reload()   
            deploy_eem_clean_config_reload()
            deploy_9800_eem_upgrade_script_clean(software_image, config_file)

        ### Merging configuration to startup to let the 9800 start with configuration
        if configuration_status_value == "active":
            # Merge configuration file from ztp to startup
            deploy_9800_eem_upgrade_script(software_image, config_file) 

        
        # Return firmware upgrade status
        firmware_upgrade_status = True
        return firmware_upgrade_status 

                        
   # Main function runner      
    try:
        software_image = software_mappings[model]['software_image']
        software_version = software_mappings[model]['software_version']
        software_md5_checksum = software_mappings[model]['software_md5_checksum']
        
        print ('**** Checking if upgrade is required or not ***** \n')
        log_info('**** Checking if upgrade is required or not ***** \n')

        #Unpack the tuble returned by upgrade_required()
        firmware_action, current_version = upgrade_required(software_version)

        # Upgrade taskdir 
        if firmware_action == 'upgrade':
            # Upgrade is required
            print ('*** Upgrade is required!!! *** \n')
            log_info('*** Upgrade is required!!! *** \n')
            cisco_9800_update_runner(current_version, software_image)
            firmware_upgrade_status = True
            return firmware_upgrade_status                   

        # downgrade task
        elif firmware_action == 'downgrade':           
            # Upgrade is required
            print ('*** Downgrade is required!!! *** \n')
            log_info('*** Downgrade is required!!! *** \n')
            firmware_upgrade_status = cisco_9800_update_runner(current_version, software_image)
                              
        else:
          print ('*** No upgrade is required!!! *** \n')
          log_info('*** No upgrade is required!!! *** \n')
          firmware_upgrade_status = False
          
        return firmware_upgrade_status           

    except Exception as e:
        print('*** Failure encountered during upgrade of software **\n')
        log_critical('*** Failure encountered during upgrade of software ***\n' + e)
        print(e)
        sys.exit(e)
           
def verify_dst_image_md5(image, src_md5, file_system='flash:/'):
    # Function to check MD5 hashing with firmware file
    print('*** Checking MD5 Hashing on firmware file ***')
    log_info('*** Checking MD5 Hashing on firmware file ***')

    try:
        check_md5_on_firmware = cli(f"verify /md5 {file_system}{image}")

        if src_md5 in check_md5_on_firmware:
            print('*** MD5 hashes match!! ***')
            log_info('*** MD5 hashes match!! ***')

        elif src_md5 not in check_md5_on_firmware:
            print('!!! !WARNING! - MD5 HASH DOES NOT MATCH FIRMWARE FILE! !POSSIBLE BREACH! CANCELING DEPLOYMENT OF ZTP !!!')
            log_info('!!! !WARNING! - MD5 HASH DOES NOT MATCH FIRMWARE FILE! !POSSIBLE BREACH! CANCELING DEPLOYMENT OF ZTP !!!')
            
            # If md5 check fails, the ZTP wil stop and will not reboot the switch for safety reasons
            print('*** Failure encountered during day 0 provisioning . Aborting ZTP script execution.  ***')
            log_critical('*** Failure encountered during day 0 provisioning . Aborting ZTP script execution.  ***')
            exit_guest_shell()
            exit_auto_installer()
            time.sleep(12000)

    except Exception as e:
        print(f'****  MD5 checksum failed due to an exception: {e}  *****')
        log_info(f'****  MD5 checksum failed due to an exception: {e}  *****')

def ztp_script_main_cleaner():
    # Function to remove all eem script created by ztp script
    print('*** Deplying ZTP EEM cleaner script ***')
    log_info('*** Deplying ZTP EEM cleaner script ***')

    # Create ztp cleaner script
    eem_commands = ['event manager applet ztp_clear',
                    'event syslog pattern "ZTP SCRIPT - ENDED" maxrun 300',
                    'action 1 wait 60',
                    'action 2 cli command "enable"',
                    ]
    results = configurep(eem_commands)

    # Get the running-config related to EEM scripts
    show_eem_scripts = cli("show run | include event manager applet")

    # Start action sequence from 3.0
    action_sequence = 3

    # Loop over the found applet names to delete them
    for applet in show_eem_scripts:
        cli("enable")
        cli(f"event manager applet ztp_clear")
        cli(f"action {action_sequence:.1f} cli command no event manager applet {applet}")
        action_sequence += 1  # Increment the action sequence

def main():

    ### ZTP SCRIPT - WORK FLOW ###
    # 1. Day zero function
    # 2. Fetch configuration status
    # 3. Print tasks
    # 4. Switch renumbering & priority tasks
    # 5. (Optional) remove startup-config for decommisioning, planned or unkown status devices
    # 6. (Optional) Upgrade software for planned or unknown status devices
    # 7. (Optional) Activate configuration for devices with status active
    # 8. (Optional) Activate beacon led if switch has status planned or unknown, and update status is false
    # 9. (Optional) Mail ZTP status if mail_status is active and upgrade is false (otherwise it will send a false ready status)
    # 10. Close and exit ZTP script

    # cli send log is for when the ztp script is run outside of
    # auto installer. Running the ztp script directly results
    # running the script in the background. With no terminal log

    ### Global vars ###
    global configuration_status_value, config_file, model, serial, stack_switch_status

    ### Log for starting ZTP script ###
    cli("send log 7 ### ZTP SCRIPT - STARTED")

    ### ZTP script element checker ####
    #http_server = ztp_script_verify()
    
    ### Day zero runner ###
    cli("send log 7 ### ZTP SCRIPT - STARTING DAY ZERO SCRIPT")
    config_file, device_type, model, serial, stack_switch_status = day_zero_script_runner()

    ### Deactivate becaon led, because cisco is full of bugs :) ###
    deactivate_beacon_led(model)

    ### Check configuration status ###
    cli("send log 7 ### ZTP SCRIPT - VALIDATING CONFIGURATION")    
    configuration_status_value = configuration_status(config_file)

    ### Print tasks ###
    cli("send log 7 ### ZTP SCRIPT - TASK OVERVIEW")        
    main_task_printer()

    ### Switch renumbering ###
    if device_type == "switch":
        ### Switch stack version runner ###
        # Don't run stack software sync if device is decommissioning 
        if configuration_status_value != "decommissioning":
            cli("send log 7 ### ZTP SCRIPT - FIRMWARE VERSION SYNC TASK ")         
            cisco_stack_v_mismatch_check(model) 
    
        ### Switch renumbering ###       
        if configuration_status_value == "active":
            cli("send log 7 ### ZTP SCRIPT - STACK NUMBERING AND PRIORITY TASK")           
            switch_stack_task_selector()    

    ### decommissioning, planned and unknown task ###
    if configuration_status_value == "decommissioning" or configuration_status_value == "planned" or configuration_status_value == "unknown":
        # Removing all the configuration
        cli("send log 7 ### ZTP SCRIPT - REMOVING START-UP CONFIGURATION")   
        erase_startup_config()

    ### software upgrade section ###
    # Don't run software upgrade if device needs decom #
    if configuration_status_value != "decommissioning":
        ### Run firmware upgrade ###
        cli("send log 7 ### ZTP SCRIPT - SOFTWARE UPGRADE TASK")      
        firmware_upgrade_status = firmware_upgrade_selector(model)

    ### Configuration activation ###
    # Status active
    # Don't save configuration if device needs decom, or firmware upgrade is runing
    if configuration_status_value == "active" and not firmware_upgrade_status:  
        # activating configuration
        cli(f"send log 7 ### ZTP SCRIPT - ACTIVATING {config_file} ###")            
        # if device type is switch, copy the config file with running
        if device_type == "switch": 
            # Merge configuration file to startup
            configure_merge_file_to_startup_config(config_file)            
            # Merge configuration file to running
            configure_merge_file_to_running_config(config_file)
        # if device type is wlc, replace the config file with running            
        if device_type == "wlc":
            # For 9800, remove pnp/ztp interface configuration before applying configuration
            if '9800' in model:
                # Default uplink interface for C9800
                configure_default_interfaces_c9800()
                # Merge configuration file to startup
                configure_merge_file_to_startup_config(config_file)                
                # Merge configuration file to running
                configure_merge_file_to_running_config(config_file)

        # Always configure SSH keys
        configure_ssh_keys()

    # Status planned
    # Don't save configuration if device needs decom, or firmware upgrade is runing
    if configuration_status_value == "planned" and not firmware_upgrade_status:  
        # Saving configuration
        cli(f"send log 7 ### ZTP SCRIPT - SAVING {config_file} TO STARTUP-CONFIG ###")            
        # if device type is switch, copy the config file with running
        if device_type == "switch": 
            erase_startup_config()
            # Merge configuration file to startup
            configure_merge_file_to_startup_config(config_file)
        # if device type is wlc, replace the config file with running            
        if device_type == "wlc":
            # For 9800, remove pnp/ztp interface configuration before applying configuration
            if '9800' in model:
                erase_startup_config()
                # Merge configuration file to startup
                configure_merge_file_to_startup_config(config_file)
      

    ### LED Notification when ZTP script is done for status planned and unkown ###
    if (configuration_status_value == "planned" or configuration_status_value == "unknown") and not firmware_upgrade_status:
        activate_beacon_led(model)   

    ### Send e-mail with ZTP script results  ###
    if mail_status == True:
        print ('###### Sending e-mail with ZTP results ######\n')
        log_info('###### Sending e-mail ZTP results ######\n')
        cli("send log 7 ###### Sending e-mail ZTP results ######")                   
        send_email_status(serial, model, configuration_status_value, firmware_upgrade_status)    
        

    ### End of ZTP script ###
    print ('######  END OF ZTP SCRIPT ######\n')
    log_info('######  END OF ZTP SCRIPT ######\n')
    cli("send log 7 ###### ZTP SCRIPT - ENDED ######")   

    ### Exit guest shell ###
    exit_guest_shell()

if __name__ == "__main__":
    main()