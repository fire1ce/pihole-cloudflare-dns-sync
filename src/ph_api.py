import pihole_api as pi


class PhApi:
    def __init__(self, server_config, SyncError, logger):
        self.server_config = server_config
        self.SyncError = SyncError
        self.logger = logger
        self.pihole_server_name = self.server_config["host"]
        self.pihole_api = self.create_pihole_connection()

    def create_pihole_connection(self):
        pihole_host = self.server_config["host"]
        pihole_port = self.server_config["port"]
        use_https = self.server_config["use_https"]
        pihole_password = self.server_config["password"]

        # create the pihole url
        prefix = "https://" if use_https else "http://"
        pihole_url = f"{prefix}{pihole_host}:{pihole_port}/admin/"

        # create a pihole object with the url and password
        try:
            pihole_api = pi.Pihole(pihole_url, pihole_password)
        except Exception as error:
            self.logger.error(
                f"Could not connect to Pi-hole server {self.pihole_server_name} at {pihole_url}. Please check your server status, network settings, and credentials.\n Error: {str(error)}"
            )
            raise self.SyncError(error)

        self.logger.info(f"Connection established with Pihole server {self.pihole_server_name}: {pihole_url}")
        return pihole_api

    def get_records_from_pihole(self, record_type, cloudflare_domains):
        try:
            if record_type == "a":
                pihole_record_list = self.pihole_api.dns("get")["data"]
            elif record_type == "cname":
                pihole_record_list = self.pihole_api.cname("get")["data"]
            else:
                self.logger.error(f"Invalid record type: {record_type} on server {self.pihole_server_name}")
                raise self.SyncError(f"Invalid record type: {record_type}")

            self.logger.debug(f"{record_type}_record_list for {self.pihole_server_name}:\n {pihole_record_list}")
        except Exception as error:
            self.logger.error(f"Could not get {record_type} records from server {self.pihole_server_name}: {error}")
            raise self.SyncError(error)

        pihole_records_dict = {}
        for pihole_record in pihole_record_list:
            domain = pihole_record[0]
            if any(domain.endswith(cf_domain) for cf_domain in cloudflare_domains):
                pihole_records_dict[domain] = pihole_record[1]

        self.logger.info(f"Fetched {self.pihole_server_name} Pihole's {record_type} records")
        return pihole_records_dict

    def _delete_single_record(self, hostname: str, record_data: str, record_type: str):
        try:
            if record_type == "a":
                self.pihole_api.dns("delete", ip_address=record_data, domain=hostname)
            elif record_type == "cname":
                self.pihole_api.cname("delete", hostname, record_data)
            else:
                self.logger.error(f"Invalid record type: {record_type} on server {self.pihole_server_name}")
                raise self.SyncError(f"Invalid record type: {record_type}")

            self.logger.info(
                f"Deleted {record_type.upper()} record {hostname}: {record_data} from server {self.pihole_server_name}"
            )
        except Exception as error:
            self.logger.error(
                f"Could not delete {record_type.upper()} record {hostname}: {record_data} from server {self.pihole_server_name}"
            )
            raise self.SyncError(error)

    def delete_records(self, records_diff, pihole_records_dict, cloudflare_domains, record_type):
        for record in records_diff.get("dictionary_item_removed", {}):
            hostname = record.split("['")[1].split("']")[0]
            # Check if the hostname ends with any of the cloudflare_domains before deleting
            if any(hostname.endswith(cf_domain) for cf_domain in cloudflare_domains):
                record_data = pihole_records_dict[hostname]
                self._delete_single_record(hostname, record_data, record_type)

    def _add_single_record(self, hostname: str, record_data: str, record_type: str):
        try:
            if record_type == "a":
                self.pihole_api.dns("add", ip_address=record_data, domain=hostname)
            elif record_type == "cname":
                self.pihole_api.cname("add", hostname, record_data)
            else:
                self.logger.error(f"Invalid record type: {record_type} on server {self.pihole_server_name}")
                raise self.SyncError(f"Invalid record type: {record_type}")

            self.logger.info(
                f"Added {record_type.upper()} record {hostname}: {record_data} to server {self.pihole_server_name}"
            )
        except Exception as error:
            self.logger.error(
                f"Could not add {record_type.upper()} record: {hostname} -> {record_data} to server {self.pihole_server_name}"
            )
            raise self.SyncError(error)

    def add_records(self, records_diff, cf_records_dict, record_type):
        for record in records_diff.get("dictionary_item_added", {}):
            hostname = record.split("['")[1].split("']")[0]
            record_data = cf_records_dict[hostname]
            self._add_single_record(hostname, record_data, record_type)

    def _update_single_record(self, hostname: str, old_record: str, new_record: str, record_type: str):
        try:
            if record_type == "a":
                self.pihole_api.dns("delete", ip_address=old_record, domain=hostname)
                self.pihole_api.dns("add", ip_address=new_record, domain=hostname)
            elif record_type == "cname":
                self.pihole_api.cname("delete", hostname, old_record)
                self.pihole_api.cname("add", hostname, new_record)
            else:
                self.logger.error(f"Invalid record type: {record_type} on server {self.pihole_server_name}")
                raise self.SyncError(f"Invalid record type: {record_type}")

            self.logger.info(
                f"Updated {record_type.upper()} record {hostname}: {old_record} -> {new_record} on server {self.pihole_server_name}"
            )
        except Exception as error:
            self.logger.error(
                f"Could not update {record_type.upper()} record {hostname}: {old_record} -> {new_record} on server {self.pihole_server_name}"
            )
            raise self.SyncError(error)

    def update_records(self, records_diff, cf_records_dict, pihole_records_dict, record_type):
        for record in records_diff.get("values_changed", {}):
            hostname = record.split("['")[1].split("']")[0]
            old_record = pihole_records_dict[hostname]
            new_record = cf_records_dict[hostname]
            self._update_single_record(hostname, old_record, new_record, record_type)
