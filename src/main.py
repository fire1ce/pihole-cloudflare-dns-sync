from deepdiff import DeepDiff
from time import sleep
from logger import init_logger
import config_init
from ph_api import PhApi
from cf_api import CfApi


class SyncError(Exception):
    pass


def fetch_and_compare_records(ph_api_obj, cf_api_obj, pihole_server_name, cf_domains):
    records_types = ["a", "cname"]
    cf_a_records_dict, cf_cname_records_dict = cf_api_obj.get_cf_records()
    cf_records_dict = {"a": cf_a_records_dict, "cname": cf_cname_records_dict}

    for record_type in records_types:
        pihole_records = ph_api_obj.get_records_from_pihole(record_type)

        records_diff = DeepDiff(
            pihole_records, cf_records_dict[record_type], ignore_string_case=True, ignore_order=True
        )
        logger.debug(f"{record_type}_records_diff for server {pihole_server_name}:\n {records_diff}")

        # Only call add_records if there were additions
        if "dictionary_item_added" in records_diff:
            ph_api_obj.add_records(records_diff, cf_records_dict[record_type], record_type)

        # Only call delete_records if there were removals
        if "dictionary_item_removed" in records_diff:
            ph_api_obj.delete_records(records_diff, pihole_records, cf_domains, record_type)

        # Only call update_records if there were changes
        if "values_changed" in records_diff:
            ph_api_obj.update_records(records_diff, cf_records_dict[record_type], pihole_records, record_type)

    return


def sleep_and_log(minutes, logger):
    logger.info(f"Sleeping for {minutes} minutes")
    logger.info("----------------------------------------------------")
    sleep(minutes * 60)


def check_error_counter(iteration_error_counter, error_counter, error_threshold, logger):
    if iteration_error_counter >= 1:
        error_counter += 1
        iteration_error_counter = 0
        logger.info(f"Global Error counter: {error_counter}")
    else:
        error_counter = 0

    if error_counter >= error_threshold:
        if send_notifications:
            logger.warning(f"Error threshold reached: {error_threshold} errors")
        error_counter = 0  # reset error counter

    return iteration_error_counter, error_counter


def main(config_data, logger):
    sync_interval_minutes = config_data["sync_interval_minutes"]
    error_threshold = config_data["error_threshold"]
    send_notifications = config_data["send_notifications"]
    iteration_error_counter = 0
    error_counter = 0

    while True:
        try:
            cf_domains = [domain_data["domain"] for domain_data in config_data["cloudflare"]["domains"]]
            logger.debug(f"cf_domains list: {cf_domains}")
            cf_api_obj = CfApi(config_data, SyncError, logger)

            for server_config in config_data["pihole"]["servers"]:
                ph_api_obj = PhApi(server_config, SyncError, logger)
                fetch_and_compare_records(ph_api_obj, cf_api_obj, server_config["host"], cf_domains)

        except SyncError as error:
            iteration_error_counter += 1
            logger.debug(f"Iteration Error counter: {iteration_error_counter}")

        # Check error counter after each iteration
        iteration_error_counter, error_counter = check_error_counter(
            iteration_error_counter, error_counter, error_threshold, logger
        )

        # Sleep code here...
        sleep_and_log(sync_interval_minutes, logger)


if __name__ == "__main__":
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

    main(config_data, logger)
