import CloudFlare


def get_cf_records(config_data, SyncError, logger):
    cf_a_record_dict = {}
    cf_cname_record_dict = {}
    zone_ids = {}
    logger.debug(f"ZONE IDs: {zone_ids}")
    for domain_config in config_data["cloudflare"]["domains"]:
        cf_domain = domain_config["domain"]
        cf_token = domain_config["token"]
        zone_id = zone_ids.get(cf_domain)  # Get the stored zone_id, if any
        domain_dns_records = []

        try:
            cf = CloudFlare.CloudFlare(token=cf_token)  # create CloudFlare object with corresponding token
        except CloudFlare.exceptions.CloudFlareAPIError as error:
            logger.debug(f"Error creating Cloudflare object: {error}")
            raise SyncError("Aborting due to failed Cloudflare API call for domain: {cf_domain}")
        if not zone_id:  # If we don't have a stored zone_id, fetch it
            try:
                zones = cf.zones.get(params={"name": cf_domain, "per_page": 10})

                if len(zones) < 1:
                    raise SyncError(f"No zones found for domain: {cf_domain}")

                # Extract and store the zone_id
                zone_id = zones[0]["id"]
                zone_ids[cf_domain] = zone_id  # Store the zone_id for this domain

            except CloudFlare.exceptions.CloudFlareAPIError as error:
                logger.error(
                    f"Cloudflare api call failed for domain: {cf_domain} {error}. Check your cloudflare settings and token"
                )
                raise SyncError(
                    "Aborting due to failed Cloudflare API call for domain: {cf_domain}"
                )  # Raise exception to stop further execution

        # Request the DNS records from that zone
        if domain_config["include_proxied_records"]:
            domain_dns_records = cf.zones.dns_records.get(zone_id, params={"per_page": 500})
        else:
            domain_dns_records = cf.zones.dns_records.get(zone_id, params={"per_page": 500, "proxied": False})

        logger.info(f"Fetched Cloudflare's DNS records for domain: {cf_domain}")
        # logger.debug(f"Cloudflare DNS records for domain: {cf_domain} are: {domain_dns_records}")

        # Add domain records to the corresponding dictionary only if no error occurred
        for dns_record in domain_dns_records:
            if dns_record["type"] == "A":
                cf_a_record_dict[dns_record["name"]] = dns_record["content"]
            elif dns_record["type"] == "CNAME":
                cf_cname_record_dict[dns_record["name"]] = dns_record["content"]
    logger.debug(f"cf_a_record_dict: {cf_a_record_dict}")

    return cf_a_record_dict, cf_cname_record_dict


def main():
    print("You are running cf_api.py directly. It should be imported.")


if __name__ == "__main__":
    main()
