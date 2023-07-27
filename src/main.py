from deepdiff import DeepDiff
from time import sleep
from logger import init_logger
from cf_api import get_cf_records
import config_init
import ph_api


# Create logger and load logger config file
log_level = "DEBUG"
logger = init_logger(name="root", log_level=log_level)


# Load and validate configuration
config_data = config_init.load_config("config/settings.yml", logger)
if config_data is None or not config_init.validate_config(config_data, logger):
    logger.error("Invalid configuration, exiting.")
    exit(1)
else:
    logger.info("Configuration loaded successfully")

sync_interval_minutes = config_data["sync_interval_minutes"]
error_threshold = config_data["error_threshold"]
send_notifications = config_data["send_notifications"]

# Initialize the error counters
iteration_error_counter = 0
sync_interval_seconds = 10 * sync_interval_minutes


class SyncError(Exception):
    pass


def fetch_and_compare_records(pihole_api, cf_records_dict, pihole_host, cf_domains):
    records_types = ["a", "cname"]

    for record_type in records_types:
        pihole_records = ph_api.get_records_from_pihole(pihole_api, record_type, pihole_host, SyncError, logger)

        records_diff = DeepDiff(
            pihole_records, cf_records_dict[record_type], ignore_string_case=True, ignore_order=True
        )
        logger.debug(f"{record_type}_records_diff:\n {records_diff}")

        ph_api.add_new_records(
            records_diff, cf_records_dict[record_type], pihole_api, pihole_host, record_type, SyncError, logger
        )

    # ph_api.add_new_a_records(a_records_diff, pihole_api, cf_a_records_dict, pihole_host, SyncError, logger)
    # ph_api.delete_a_records(a_records_diff, pihole_api, cf_domains, pihole_a_records, pihole_host, SyncError, logger)
    # ph_api.update_a_records(
    #     a_records_diff, pihole_api, cf_a_records_dict, pihole_a_records, pihole_host, SyncError, logger
    # )

    # ph_api.add_new_cname_records(cname_records_diff, pihole_api, cf_cname_records_dict, pihole_host, SyncError, logger)
    # ph_api.delete_cname_records(
    #     cname_records_diff, pihole_api, cf_domains, pihole_cname_records, pihole_host, SyncError, logger
    # )
    # ph_api.update_cname_records(cname_records_diff, pihole_api, pihole_cname_records, pihole_host, SyncError, logger)

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


while True:
    try:
        cf_a_records_dict, cf_cname_records_dict = get_cf_records(config_data, SyncError, logger)
        cf_records_dict = {"a": cf_a_records_dict, "cname": cf_cname_records_dict}
        cf_domains = [domain_data["domain"] for domain_data in config_data["cloudflare"]["domains"]]
        logger.debug(f"cf_domains list: {cf_domains}")

        for server_config in config_data["pihole"]["servers"]:
            pihole_api = ph_api.create_pihole_connection(server_config, SyncError)
            pihole_host = server_config["host"]
            records_types = ["a", "cname"]
            for record_type in records_types:
                pihole_records_dict = ph_api.get_records_from_pihole(
                    pihole_api, record_type, pihole_host, SyncError, logger
                )
                records_diff = DeepDiff(
                    pihole_records_dict, cf_records_dict[record_type], ignore_string_case=True, ignore_order=True
                )

                # Only call add_records if there were additions
                if "dictionary_item_added" in records_diff:
                    ph_api.add_records(
                        records_diff,
                        cf_records_dict[record_type],
                        pihole_api,
                        pihole_host,
                        record_type,
                        SyncError,
                        logger,
                    )

                # Only call delete_records if there were removals
                if "dictionary_item_removed" in records_diff:
                    ph_api.delete_records(
                        records_diff,
                        pihole_records_dict,
                        pihole_api,
                        cf_domains,
                        pihole_host,
                        record_type,
                        SyncError,
                        logger,
                    )

                # Only call update_records if there were changes
                if "values_changed" in records_diff:
                    ph_api.update_records(
                        records_diff,
                        cf_records_dict[record_type],
                        pihole_records_dict,
                        pihole_api,
                        cf_domains,
                        pihole_host,
                        record_type,
                        SyncError,
                        logger,
                    )

        # Sleep between iterations
        sleep_and_log(sync_interval_seconds, logger)

    except SyncError as error:
        iteration_error_counter += 1
        logger.debug(f"Iteration Error counter: {iteration_error_counter}")
        logger.error(str(error))

    # Check error counter after each iteration
    check_error_counter()

    # Sleep code here...
    sleep_and_log(sync_interval_seconds, logger)


## Debugging ##
# while True:
#     cf_a_records_dict_dict, cf_cname_records_dict = get_cf_records()
#     logger.info(f"Cloudflare A records: {cf_a_records_dict_dict}")
#     logger.info(f"Cloudflare CNAME records: {cf_cname_records_dict}")
#     sleep(10)
# exit(1)
## Debugging ##
