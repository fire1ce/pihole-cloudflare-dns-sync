from deepdiff import DeepDiff
from time import sleep
from logger import iniLogger
from cf_api import get_cf_records
import config
import ph_api


# Create logger and load logger config file
log_level = "INFO"
logger = iniLogger(name="root", log_level=log_level)


# Load and validate configuration
config_data = config.load_config("config/settings.yml", logger)
if config_data is None or not config.validate_config(config_data, logger):
    logger.error("Invalid configuration, exiting.")
    exit(1)
else:
    logger.info("Configuration loaded successfully")

sync_interval_minutes = config_data["sync_interval_minutes"]
error_threshold = config_data["error_threshold"]
send_notifications = config_data["send_notifications"]

# Initialize the error counters and zone_ids dictionary
error_counter = 0
iteration_error_counter = 0
sync_interval_seconds = 10 * sync_interval_minutes
zone_ids = {}


class SyncError(Exception):
    pass


# Create a dictionary of the pihole A records
def get_a_records_from_pihole(pihole_api, pihole_host):
    try:
        pihole_a_record_list = pihole_api.dns("get")["data"]
        print(f"pihole_a_record_list: {pihole_a_record_list}")
        # print type of pihole_a_record_list
        print(f"type of pihole_a_record_list {type(pihole_a_record_list)}")
    except Exception as error:
        raise SyncError(f"Could not get A records from pihole: {error}")

    pihole_a_records_dict = {}
    for pihole_a_record in pihole_a_record_list:
        pihole_a_records_dict[pihole_a_record[0]] = pihole_a_record[1]
    logger.info(f"Fetched {pihole_host} Pihole's A records")
    return pihole_a_records_dict


# Create a dictionary of the pihole cname records
def get_cname_records_from_pihole(pihole_api, pihole_host):
    try:
        pihole_cname_record_list = pihole_api.cname("get")["data"]
    except Exception as error:
        raise SyncError(f"Could not get CNAME records from pihole: {error}")

    pihole_cname_records_dict = {}
    for pihole_cname_record in pihole_cname_record_list:
        pihole_cname_records_dict[pihole_cname_record[0]] = pihole_cname_record[1]
    logger.info(f"Fetched {pihole_host} Pihole's CNAME records")
    return pihole_cname_records_dict


def add_new_a_records(a_records_diff, pihole_api, cf_a_records_dict, pihole_host):
    for record in a_records_diff.get("dictionary_item_added", {}):
        hostname = record.split("['")[1].split("']")[0]
        ip = cf_a_records_dict[hostname]
        try:
            pihole_api.dns("add", ip_address=ip, domain=hostname)
            logger.info(f"Added A record {hostname}: {ip} to {pihole_host} Pihole")
        except Exception as error:
            raise SyncError(f"Could not add A record: {hostname}: {ip} to {pihole_host} Pihole {error}")

    return


def delete_a_records(a_records_diff, pihole_api, cf_domains, pihole_a_records, pihole_host):
    for record in a_records_diff.get("dictionary_item_removed", {}):
        hostname = record.split("['")[1].split("']")[0]
        # Check if the hostname ends with any of the cf domains before deleting
        if any(hostname.endswith(cf_domain) for cf_domain in cf_domains):
            ip = pihole_a_records[hostname]
            try:
                pihole_api.dns("delete", ip_address=ip, domain=hostname)
                logger.info(f"Deleted A record {hostname}: {ip} to {pihole_host} Pihole")
            except Exception as error:
                raise SyncError(f"Could not delete A record {hostname}: {ip} to {pihole_host} Pihole {error}")

    return


def update_a_records(a_records_diff, pihole_api, cf_a_records, pihole_a_records_dict, pihole_host):
    for record in a_records_diff.get("values_changed", {}):
        hostname = record.split("['")[1].split("']")[0]
        old_ip = pihole_a_records_dict[hostname]
        new_ip = cf_a_records[hostname]
        try:
            pihole_api.dns("delete", ip_address=old_ip, domain=hostname)
        except Exception as error:
            raise SyncError(
                f"Could not delete (for update) A record {hostname}: {old_ip} to {pihole_host} Pihole {error}"
            )

        try:
            pihole_api.dns("add", ip_address=new_ip, domain=hostname)
            logger.info(f"Updated A record {hostname}:{old_ip} -> {new_ip} to {pihole_host} Pihole")
        except Exception as error:
            raise SyncError(f"Could not add A (update) record: {hostname}:{new_ip} to {pihole_host} Pihole {error}")

    return


def add_new_cname_records(cname_records_diff, pihole_api, cf_cname_records_dict, pihole_host):
    for record in cname_records_diff.get("dictionary_item_added", {}):
        hostname = record.split("['")[1].split("']")[0]
        target_hostname = cf_cname_records_dict[hostname]
        try:
            pihole_api.cname("add", hostname, target_hostname)
            logger.info(f"Added CNAME record {hostname}: {target_hostname} to {pihole_host} Pihole")
        except Exception as error:
            raise SyncError(
                f"Could not add CNAME record: {hostname}: {target_hostname} to {pihole_host} Pihole {error}"
            )

    return


def delete_cname_records(cname_records_diff, pihole_api, cf_domains, pihole_cname_records, pihole_host):
    for record in cname_records_diff.get("dictionary_item_removed", {}):
        hostname = record.split("['")[1].split("']")[0]
        # Check if the hostname ends with any of the cf domains before deleting
        if any(hostname.endswith(cf_domain) for cf_domain in cf_domains):
            target_hostname = pihole_cname_records[hostname]
            try:
                pihole_api.cname("delete", hostname, target_hostname)
                logger.info(f"Deleted CNAME record: {hostname}:{target_hostname} to {pihole_host} Pihole")
            except Exception as error:
                raise SyncError(f"Could not delete CNAME record: {hostname}:{target_hostname} to {pihole_host} Pihole")
    return


def update_cname_records(cname_records_diff, pihole_api, cf_cname_records_dict, pihole_host):
    for record in cname_records_diff.get("values_changed", {}):
        hostname = record.split("['")[1].split("']")[0]
        old_target_hostname = pihole_api.cname("get")["data"][hostname]
        new_target_hostname = cf_cname_records_dict[hostname]
        try:
            pihole_api.cname("delete", hostname, old_target_hostname)
        except Exception as error:
            raise SyncError(f"Could not delete CNAME record: {hostname}:{old_target_hostname} to {pihole_host} Pihole")

        try:
            pihole_api.cname("add", hostname, new_target_hostname)
            logger.info(
                f"Updated CNAME record: {hostname}:{old_target_hostname} -> {new_target_hostname} to {pihole_host} Pihole"
            )
        except Exception as error:
            raise SyncError(f"Could not add CNAME record: {hostname}:{new_target_hostname} to {pihole_host} Pihole ")

    return


def fetch_and_compare_records(pihole_api, cf_a_records, cf_cname_records, pihole_host, cf_domains):
    pihole_a_records = get_a_records_from_pihole(pihole_api, pihole_host)
    pihole_cname_records = get_cname_records_from_pihole(pihole_api, pihole_host)

    a_records_diff = DeepDiff(pihole_a_records, cf_a_records, ignore_string_case=True, ignore_order=True)
    cname_records_diff = DeepDiff(pihole_cname_records, cf_cname_records, ignore_string_case=True, ignore_order=True)

    add_new_a_records(a_records_diff, pihole_api, cf_a_records, pihole_host)
    delete_a_records(a_records_diff, pihole_api, cf_domains, pihole_a_records, pihole_host)
    update_a_records(a_records_diff, pihole_api, cf_a_records, pihole_a_records, pihole_host)

    add_new_cname_records(cname_records_diff, pihole_api, cf_cname_records, pihole_cname_records, pihole_host)
    delete_cname_records(cname_records_diff, pihole_api, cf_domains, pihole_cname_records, pihole_host)
    update_cname_records(cname_records_diff, pihole_api, pihole_cname_records, pihole_host)

    return


# Iteration between runs
def sleep_and_log(minutes, logger):
    logger.info(f"Sleeping for {minutes} minutes")
    logger.info("----------------------------------------------------")
    sleep(sync_interval_seconds)


# Function to check error threshold
def check_error_counter():
    global error_counter
    global iteration_error_counter
    logger.info(
        f"inside check_error_counter. iteration_error_counter: {iteration_error_counter} error_counter: {error_counter}"
    )
    if iteration_error_counter >= 1:
        logger.info(f"inside check_error_counter: {iteration_error_counter}")
        error_counter += 1
        iteration_error_counter = 0
        logger.info(f"Global Error counter: {error_counter}")
    else:
        error_counter = 0

    if error_counter >= error_threshold:
        if send_notifications:
            logger.warning(f"Error threshold reached: {error_threshold} errors")
        error_counter = 0  # reset error counter


### Main function ###
while True:
    try:
        cf_a_records_dict, cf_cname_records_dict = get_cf_records(zone_ids, config_data, SyncError, logger)

        # Create a list of all Cloudflare domains
        cf_domains = list(
            set(
                [
                    record.split(".")[-2] + "." + record.split(".")[-1]
                    for record in list(cf_a_records_dict.keys()) + list(cf_cname_records_dict.keys())
                ]
            )
        )
        print(f"cf_domains: {cf_domains}")
        for server_config in config_data["pihole"]["servers"]:
            pihole_api = ph_api.create_pihole_connection(server_config, SyncError)
            pihole_host = server_config["host"]
            fetch_and_compare_records(pihole_api, cf_a_records_dict, cf_cname_records_dict, pihole_host, cf_domains)

        # Sleep between iterations
        sleep_and_log(sync_interval_seconds, logger)

    except SyncError as error:
        iteration_error_counter += 1
        logger.info(f"Iteration Error counter: {iteration_error_counter}")
        logger.error(str(error))

    # Check error counter after each iteration
    check_error_counter()

    # Sleep code here...
    sleep_and_log(sync_interval_seconds, logger)


## Debugging ##
# while True:
#     cf_a_records_dict, cf_cname_records_dict = get_cf_records()
#     logger.info(f"Cloudflare A records: {cf_a_records_dict}")
#     logger.info(f"Cloudflare CNAME records: {cf_cname_records_dict}")
#     sleep(10)
# exit(1)
## Debugging ##
