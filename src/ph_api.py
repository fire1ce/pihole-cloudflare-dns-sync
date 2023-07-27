import pihole_api as pi


def create_pihole_connection(server_config, SyncError):
    pihole_host = server_config["host"]
    pihole_port = server_config["port"]
    use_https = server_config["use_https"]
    pihole_password = server_config["password"]

    # create the pihole url
    prefix = "https://" if use_https else "http://"
    pihole_url = f"{prefix}{pihole_host}:{pihole_port}/admin/"

    # create a pihole object with the url and password
    try:
        pihole_api = pi.Pihole(pihole_url, pihole_password)
    except Exception as error:
        raise SyncError(f"Could not connect to pihole: {pihole_url}. Check your password.")

    return pihole_api


# Create a dictionary of the pihole A records
def get_records_from_pihole(pihole_api, record_type, pihole_host, SyncError, logger):
    try:
        if record_type == "a":
            pihole_record_list = pihole_api.dns("get")["data"]
        elif record_type == "cname":
            pihole_record_list = pihole_api.cname("get")["data"]
        else:
            raise ValueError(f"Invalid record type: {record_type}")

        logger.debug(f"{record_type}_record_list for {pihole_host}:\n {pihole_record_list}")
    except Exception as error:
        raise SyncError(f"Could not get {record_type} records from pihole: {error}")

    pihole_records_dict = {}
    for pihole_record in pihole_record_list:
        pihole_records_dict[pihole_record[0]] = pihole_record[1]

    logger.info(f"Fetched {pihole_host} Pihole's {record_type} records")
    return pihole_records_dict


def add_records(records_diff, cf_records_dict, pihole_api, pihole_host, record_type, SyncError, logger):
    for record in records_diff.get("dictionary_item_added", {}):
        hostname = record.split("['")[1].split("']")[0]
        try:
            if record_type == "a":
                ip = cf_records_dict[hostname]
                pihole_api.dns("add", ip_address=ip, domain=hostname)
                logger.info(f"Added A record {hostname}: {ip} to {pihole_host} Pihole")
            elif record_type == "cname":
                target_hostname = cf_records_dict[hostname]
                pihole_api.cname("add", hostname, target_hostname)
                logger.info(f"Added CNAME record {hostname}: {target_hostname} to {pihole_host} Pihole")
            else:
                raise ValueError(f"Invalid record type: {record_type}")
        except Exception as error:
            raise SyncError(f"Could not add {record_type} record: {hostname} to {pihole_host} Pihole {error}")
    return


def delete_records(
    records_diff, pihole_records_dict, pihole_api, cf_domains, pihole_host, record_type, SyncError, logger
):
    for record in records_diff.get("dictionary_item_removed", {}):
        hostname = record.split("['")[1].split("']")[0]
        # Check if the hostname ends with any of the cf_domains before deleting
        if any(hostname.endswith(cf_domain) for cf_domain in cf_domains):
            record_data = pihole_records_dict[hostname]
            try:
                if record_type == "a":
                    pihole_api.dns("delete", ip_address=record_data, domain=hostname)
                    logger.info(
                        f"Deleted {record_type.upper()} record {hostname}: {record_data} from {pihole_host} Pihole"
                    )
                elif record_type == "cname":
                    pihole_api.cname("delete", hostname, record_data)
                    logger.info(
                        f"Deleted {record_type.upper()} record {hostname}: {record_data} from {pihole_host} Pihole"
                    )
                else:
                    raise ValueError(f"Invalid record type: {record_type}")
            except Exception as error:
                raise SyncError(
                    f"Could not delete {record_type.upper()} record {hostname}: {record_data} from {pihole_host} Pihole. {error}"
                )

    return


def update_records(
    records_diff,
    cf_records_dict,
    pihole_records_dict,
    pihole_api,
    cf_domains,
    pihole_host,
    record_type,
    SyncError,
    logger,
):
    for record in records_diff.get("values_changed", {}):
        hostname = record.split("['")[1].split("']")[0]
        old_record_data = pihole_records_dict[hostname]
        new_record_data = cf_records_dict[hostname]

        # Create a single-item dictionary for deletion and addition
        old_records_dict = {hostname: old_record_data}
        new_records_dict = {hostname: new_record_data}

        try:
            delete_records(
                old_records_dict,
                pihole_records_dict,
                pihole_api,
                cf_domains,
                pihole_host,
                record_type,
                SyncError,
                logger,
            )
        except SyncError as error:
            logger.error(
                f"Could not delete (for update) {record_type.upper()} record {hostname}: {old_record_data} to {pihole_host} Pihole {error}"
            )

        try:
            add_records(new_records_dict, cf_records_dict, pihole_api, pihole_host, record_type, SyncError, logger)
            logger.info(
                f"Updated {record_type.upper()} record {hostname}:{old_record_data} -> {new_record_data} to {pihole_host} Pihole"
            )
        except SyncError as error:
            logger.error(
                f"Could not add {record_type.upper()} (update) record: {hostname}:{new_record_data} to {pihole_host} Pihole {error}"
            )

    return


# def update_a_records(a_records_diff, pihole_api, cf_a_records, pihole_a_records_dict, pihole_host, SyncError, logger):
#     for record in a_records_diff.get("values_changed", {}):
#         hostname = record.split("['")[1].split("']")[0]
#         old_ip = pihole_a_records_dict[hostname]
#         new_ip = cf_a_records[hostname]
#         try:
#             pihole_api.dns("delete", ip_address=old_ip, domain=hostname)
#         except Exception as error:
#             raise SyncError(
#                 f"Could not delete (for update) A record {hostname}: {old_ip} to {pihole_host} Pihole {error}"
#             )

#         try:
#             pihole_api.dns("add", ip_address=new_ip, domain=hostname)
#             logger.info(f"Updated A record {hostname}:{old_ip} -> {new_ip} to {pihole_host} Pihole")
#         except Exception as error:
#             raise SyncError(f"Could not add A (update) record: {hostname}:{new_ip} to {pihole_host} Pihole {error}")

#     return


# def update_cname_records(cname_records_diff, pihole_api, cf_cname_records_dict, pihole_host, SyncError, logger):
#     for record in cname_records_diff.get("values_changed", {}):
#         hostname = record.split("['")[1].split("']")[0]
#         old_target_hostname = pihole_api.cname("get")["data"][hostname]
#         new_target_hostname = cf_cname_records_dict[hostname]
#         try:
#             pihole_api.cname("delete", hostname, old_target_hostname)
#         except Exception as error:
#             raise SyncError(f"Could not delete CNAME record: {hostname}:{old_target_hostname} to {pihole_host} Pihole")

#         try:
#             pihole_api.cname("add", hostname, new_target_hostname)
#             logger.info(
#                 f"Updated CNAME record: {hostname}:{old_target_hostname} -> {new_target_hostname} to {pihole_host} Pihole"
#             )
#         except Exception as error:
#             raise SyncError(f"Could not add CNAME record: {hostname}:{new_target_hostname} to {pihole_host} Pihole ")

#     return


# def add_new_a_records(a_records_diff, pihole_api, cf_a_records_dict, pihole_host, SyncError, logger):
#     for record in a_records_diff.get("dictionary_item_added", {}):
#         hostname = record.split("['")[1].split("']")[0]
#         ip = cf_a_records_dict[hostname]
#         try:
#             pihole_api.dns("add", ip_address=ip, domain=hostname)
#             logger.info(f"Added A record {hostname}: {ip} to {pihole_host} Pihole")
#         except Exception as error:
#             raise SyncError(f"Could not add A record: {hostname}: {ip} to {pihole_host} Pihole {error}")

#     return


# def delete_a_records(a_records_diff, pihole_api, cf_domains, pihole_a_records, pihole_host, SyncError, logger):
#     for record in a_records_diff.get("dictionary_item_removed", {}):
#         hostname = record.split("['")[1].split("']")[0]
#         # Check if the hostname ends with any of the cf domains before deleting
#         if any(hostname.endswith(cf_domain) for cf_domain in cf_domains):
#             ip = pihole_a_records[hostname]
#             try:
#                 pihole_api.dns("delete", ip_address=ip, domain=hostname)
#                 logger.info(f"Deleted A record {hostname}: {ip} to {pihole_host} Pihole")
#             except Exception as error:
#                 raise SyncError(f"Could not delete A record {hostname}: {ip} to {pihole_host} Pihole {error}")

#     return


# def delete_cname_records(
#     cname_records_diff, pihole_api, cf_domains, pihole_cname_records, pihole_host, SyncError, logger
# ):
#     for record in cname_records_diff.get("dictionary_item_removed", {}):
#         hostname = record.split("['")[1].split("']")[0]
#         # Check if the hostname ends with any of the cf domains before deleting
#         if any(hostname.endswith(cf_domain) for cf_domain in cf_domains):
#             target_hostname = pihole_cname_records[hostname]
#             try:
#                 pihole_api.cname("delete", hostname, target_hostname)
#                 logger.info(f"Deleted CNAME record: {hostname}:{target_hostname} to {pihole_host} Pihole")
#             except Exception as error:
#                 raise SyncError(f"Could not delete CNAME record: {hostname}:{target_hostname} to {pihole_host} Pihole")
#     return


# def add_new_cname_records(cname_records_diff, pihole_api, cf_cname_records_dict, pihole_host, SyncError, logger):
#     for record in cname_records_diff.get("dictionary_item_added", {}):
#         hostname = record.split("['")[1].split("']")[0]
#         target_hostname = cf_cname_records_dict[hostname]
#         try:
#             pihole_api.cname("add", hostname, target_hostname)
#             logger.info(f"Added CNAME record {hostname}: {target_hostname} to {pihole_host} Pihole")
#         except Exception as error:
#             raise SyncError(
#                 f"Could not add CNAME record: {hostname}: {target_hostname} to {pihole_host} Pihole {error}"
#             )

#     return
