import wget
import json
import sys
import os
import datetime
from datetime import date
import logging
import paramiko

# logging.basicConfig(filename=configs['log_location'], level=logging.DEBUG) 
#uncomment for debugging only. 
# paramiko.util.log_to_file('logging.log', level = 'DEBUG')

# Function to get downloaded file (if one already exists)
def get_filename():
    files = []
    for f in os.listdir(configs['current_directory']):
        if f.endswith('.xml'):
            files.append(f)
    return files[0]

# Update log file start and end date
def update_log_file_info(configs_loc, configs, start_date, end_date):
    configs['start_date'] = start_date
    configs['end_date'] = end_date
    with open(configs_loc, "w") as data:
        json.dump(configs, data, indent=4, default=str)

# Get the configurations file
configs_loc = ''
if len(sys.argv) > 1:
    data = open(sys.argv[1])
    configs_loc = sys.argv[1]
else:
    try:
        data=open('configs.json')
        configs_loc = 'configs.json'
    except:
        print("Configurations file not found.", file=sys.stderr)
        sys.exit(1)
configs = json.load(data)

# Set up logging 
current_date = date.today()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(configs['log_location'])
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Set up stderr and stdout to files in directory 
sys.stderr = open(configs['current_directory'] +"/"+'err.txt', 'w')
sys.stdout = open(configs['current_directory'] +"/"+'out.txt', 'w')


# If start_date is null it means no logging has been done before.
period = datetime.timedelta(days=configs['period'])
if (configs['end_date'] != None):
    end_date = datetime.datetime.strptime(configs['end_date'], "%Y-%m-%d").date()

if configs['start_date'] == None:
    update_log_file_info(configs_loc, configs, current_date, current_date + period)

# If current date is past the 90-day period, delete all previous logs
elif current_date > end_date:
    update_log_file_info(configs_loc, configs, current_date, current_date + period)
    with open(configs['logging.log'], 'w'):
        pass

# Download XML file
url = configs['file_url']
try: 
    xml_file = wget.download(url, out=configs['current_directory'])
    filename = get_filename()
    logger.info('XML ' + filename + ' downloaded.')
except: 
    logger.info('XML failed to download.')


# SFTP to pantheon
logger.info("Starting Connection ... ")
try:
    client = paramiko.client.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(configs['host'], port=2222, username=configs['username'], key_filename=configs['private_key'], look_for_keys=False, allow_agent=False, disabled_algorithms=dict(pubkeys=["rsa-sha2-512", "rsa-sha2-256"]))
    sftp = client.open_sftp()
except:
    logger.error("SFTP Connection Failed.")
    sys.exit(1)


# Replace existing course catalog with updated course catalog 
try:
    result = sftp.put(configs["current_directory"] + "/" + filename, '/files/' + filename)
    logger.info('XML file imported.')
except:
    logger.error('Unable to import file.')

sftp.close()

os.system('terminus wp -- ' + configs['site_env'] + ' import /files/' + filename + ' --authors=create')