from deepdiff import DeepDiff
from time import sleep
from logger import init_logger
import config_init
from apprise_notifier import Notifier
from ph_api import PhApi
from cf_api import CfApi


class SyncError(Exception):
    pass


def sleep_and_log(minutes, logger):
    logger.info(f"Sleeping for {minutes} minutes")
    logger.info("----------------------------------------------------")
    sleep(minutes * 60)


def check_error_counter(iteration_error_counter, error_counter, error_threshold, logger, notifier):
    if iteration_error_counter >= 1:
        error_counter += 1
        iteration_error_counter = 0
        logger.info(f"Global Error counter: {error_counter}")
    else:
        error_counter = 0

    if error_counter >= error_threshold:
        if notifier:
            notifier.send_notification("Error threshold reached", f"{error_threshold} consecutive errors occurred.")
        error_counter = 0  # reset error counter

    return iteration_error_counter, error_counter


def sync_records(pihole_api, cf_records_dict, pihole_server_name, cloudflare_domains):
    records_types = ["a", "cname"]

    for record_type in records_types:
        pihole_records = pihole_api.get_records_from_pihole(record_type, cloudflare_domains)

        records_diff = DeepDiff(
            pihole_records, cf_records_dict[record_type], ignore_string_case=True, ignore_order=True
        )
        logger.debug(f"{record_type}_records_diff for server {pihole_server_name}:\n {records_diff}")

        # Initialize change flag
        changes_detected = False

        # Only call add_records if there were additions
        if "dictionary_item_added" in records_diff:
            pihole_api.add_records(records_diff, cf_records_dict[record_type], record_type)
            changes_detected = True

        # Only call delete_records if there were removals
        if "dictionary_item_removed" in records_diff:
            pihole_api.delete_records(records_diff, pihole_records, cloudflare_domains, record_type)
            changes_detected = True

        # Only call update_records if there were changes
        if "values_changed" in records_diff:
            pihole_api.update_records(records_diff, cf_records_dict[record_type], pihole_records, record_type)
            changes_detected = True

        # Log if no changes were detected
        if not changes_detected:
            logger.info(f"No changes detected for {record_type.upper()} records on pihole {pihole_server_name}")

    return


def main(config_data, logger):
    notifier = None
    if config_data["notifications"]["apprise"]["enabled"]:
        notifier = Notifier(config_data, SyncError, logger)
        notifier.send_notification("Pihole-Cloudflare DNS Sync", "The synchronization process has started.")
    sync_interval_minutes = config_data["sync_interval_minutes"]
    error_threshold = config_data["error_threshold"]
    iteration_error_counter = 0
    error_counter = 0

    while True:
        try:
            cloudflare_domains = [domain_data["domain"] for domain_data in config_data["cloudflare"]["domains"]]
            logger.debug(f"cloudflare_domains list: {cloudflare_domains}")
            cloudflare_api = CfApi(config_data, SyncError, logger)
            cf_A_records_dict, cf_CNAME_records_dict = cloudflare_api.fetch_and_process_cf_records()  # Fetch once
            cf_records_dict = {"a": cf_A_records_dict, "cname": cf_CNAME_records_dict}

            for server_config in config_data["pihole"]["servers"]:
                pihole_api = PhApi(server_config, SyncError, logger)
                sync_records(
                    pihole_api, cf_records_dict, server_config["host"], cloudflare_domains
                )  # Pass fetched records

        except SyncError as error:
            iteration_error_counter += 1
            logger.debug(f"Iteration Error counter: {iteration_error_counter}")

        # Check error counter after each iteration
        iteration_error_counter, error_counter = check_error_counter(
            iteration_error_counter, error_counter, error_threshold, logger, notifier
        )

        # Sleep code here...
        sleep_and_log(sync_interval_minutes, logger)


if __name__ == "__main__":
    # Create logger and load logger config file
    log_level = "INFO"
    logger = init_logger(name="root", log_level=log_level)

    # Load and validate configuration
    config_data = config_init.load_config("config/settings.yml", logger)
    if config_data is None or not config_init.validate_config(config_data, logger):
        logger.error("Invalid configuration, exiting.")
        exit(1)
    else:
        logger.info("Configuration loaded successfully")

    main(config_data, logger)
