import pihole_api as pi
import CloudFlare
from deepdiff import DeepDiff
from time import sleep
from os import environ


### Schedule ###

run_every_x_min = int(environ["RUN_EVERY"])
sleep_for_x_sec = 60 * run_every_x_min

### CloudFlare params ###
cf = CloudFlare.CloudFlare(token=str(environ["CLOUDFLARE_API_TOKEN"]))
cf_domain = str(environ["CLOUDFLARE_DOMAIN"])
exclude_proxied_records = str(environ["EXCLUDE_PROXIED_RECORDS"])

### Pihole params ###
pihole_host = str(environ["PIHOLE_HOST"])
pihole_port = int(environ["PIHOLE_PORT"])
use_https = str(environ["USE_HTTPS"])
pihole_password = str(environ["PIHOLE_PASSWORD"])


if use_https == "yes":
    prefix = "https://"
else:
    prefix = "http://"

pihole_url = prefix + pihole_host + ":" + str(pihole_port) + "/admin/"


# create a pihole object with the url and password
try:
    pihole = pi.Pihole(pihole_url, pihole_password)
except Exception as error:
    print("Could not connect to pihole: " + str(pihole_url) + " check your password")
    exit(1)


# Create a dictionary of the pihole A records
def get_a_records_from_pihole():
    try:
        pihole_a_record_list = pihole.dns("get")["data"]
    except Exception as error:
        print("Could not get A records from pihole: " + str(error))
        exit(1)
    pihole_a_records_dict = {}
    for pihole_a_record in pihole_a_record_list:
        pihole_a_records_dict[pihole_a_record[0]] = pihole_a_record[1]
    print("Fetched Pihole's A records")
    return pihole_a_records_dict


# Create a dictionary of the pihole cname records
def get_cname_records_from_pihole():
    try:
        pihole_cname_record_list = pihole.cname("get")["data"]
    except Exception as error:
        print("Could not get CNAME records from pihole: " + str(error))
        exit(1)
    pihole_cname_records_dict = {}
    for pihole_cname_record in pihole_cname_record_list:
        pihole_cname_records_dict[pihole_cname_record[0]] = pihole_cname_record[1]
    print("Fetched Pihole's CNAME records")
    return pihole_cname_records_dict


# Get cloudflare dns records from cloudflare api
def get_cf_records():
    # Query for the zone name and expect only one value back
    try:
        zones = cf.zones.get(params={"name": cf_domain, "per_page": 10})
    except CloudFlare.exceptions.CloudFlareAPIError as error:
        print("Cloudflare api call failed: " + str(error))
        exit(1)
    except Exception as error:
        print("Cloudflare api call failed: " + str(error))
        exit(1)

    if len(zones) == 0:
        print("No zones found for domain: " + cf_domain)
        exit(1)

    # Extract the zone_id which is needed to process that zone
    try:
        zone_id = zones[0]["id"]
    except Exception as error:
        print("Could not get zone id: " + str(error))
        exit(1)

    # Request the DNS records from that zone
    try:
        if exclude_proxied_records == "yes":
            cf_dns_records = cf.zones.dns_records.get(
                zone_id, params={"per_page": 500, "proxied": False}
            )
        elif exclude_proxied_records == "no":
            cf_dns_records = cf.zones.dns_records.get(zone_id, params={"per_page": 500})
    except CloudFlare.exceptions.CloudFlareAPIError as error:
        print("Cloudflare api call failed: " + str(error))
        exit(1)

    print("Fetched Cloudflare's DNS records")
    return cf_dns_records


# Create a dictionary of the cloudflare A records
def get_cf_a_records(cf_dns_records):
    cf_a_record_dict = {}
    for dns_record in cf_dns_records:
        if dns_record["type"] == "A":
            cf_a_record_dict[dns_record["name"]] = dns_record["content"]
    # if cf_a_record_dict has cf_proxied_records remove them
    return cf_a_record_dict


# Create a dictionary of the cloudflare CNAME records
def get_cf_cname_records(cf_dns_records):
    cf_cname_record_dict = {}
    for dns_record in cf_dns_records:
        if dns_record["type"] == "CNAME":
            cf_cname_record_dict[dns_record["name"]] = dns_record["content"]
    return cf_cname_record_dict


### Sync the A records ###
def add_new_a_records(a_records_diff):
    for record in a_records_diff.get("dictionary_item_added", {}):
        hostname = record.split("['")[1].split("']")[0]
        ip = cf_a_records[hostname]
        try:
            pihole.dns("add", ip_address=ip, domain=hostname)
            print("Added A record: " + hostname + ": " + ip)
        except Exception as error:
            print("Could not add A record: " + str(hostname) + ": " + str(ip) + " " + str(error))
            exit(1)
    return


def delete_a_records(a_records_diff):
    for record in a_records_diff.get("dictionary_item_removed", {}):
        hostname = record.split("['")[1].split("']")[0]
        ip = pihole_a_records[hostname]
        try:
            pihole.dns("delete", ip_address=ip, domain=hostname)
            print("Deleted A record: " + hostname + ": " + ip)
        except Exception as error:
            print("Could not delete A record: " + str(hostname) + ": " + str(ip) + " " + str(error))
            exit(1)
    return


def update_a_records(a_records_diff):
    for record in a_records_diff.get("values_changed", {}):
        hostname = record.split("['")[1].split("']")[0]
        old_ip = pihole_a_records[hostname]
        new_ip = cf_a_records[hostname]
        try:
            pihole.dns("delete", ip_address=old_ip, domain=hostname)
        except Exception as error:
            print(
                "Could not delete A record: "
                + +str(hostname)
                + ": "
                + str(old_ip)
                + " "
                + str(error)
            )
            exit(1)
        try:
            pihole.dns("add", ip_address=new_ip, domain=hostname)
            print("Updated A record: " + hostname + ":" + old_ip + " -> " + new_ip)
        except Exception as error:
            print(
                "Could not add A record: " + +str(hostname) + ":" + str(new_ip) + " " + str(error)
            )
            exit(1)
    return


### Sync the CNAME records ###
def add_new_cname_records(cname_records_diff):
    for record in cname_records_diff.get("dictionary_item_added", {}):
        hostname = record.split("['")[1].split("']")[0]
        targe_hostname = cf_cname_records[hostname]
        try:
            pihole.cname("add", hostname, targe_hostname)
            print("Added CNAME record: " + hostname + ":" + targe_hostname)
        except Exception as error:
            print(
                "Could not add CNAME record: "
                + str(hostname)
                + " : "
                + str(targe_hostname)
                + " "
                + str(error)
            )
            exit(1)
    return


def delete_cname_records(cname_records_diff):
    for record in cname_records_diff.get("dictionary_item_removed", {}):
        hostname = record.split("['")[1].split("']")[0]
        targe_hostname = pihole_cname_records[hostname]
        try:
            pihole.cname("delete", hostname, targe_hostname)
            print("Deleted CNAME record: " + hostname + ":" + targe_hostname)
        except Exception as error:
            print(
                "Could not delete CNAME record: "
                + str(hostname)
                + ":"
                + str(targe_hostname)
                + " "
                + str(error)
            )
            exit(1)
    return


def update_cname_records(cname_records_diff):
    for record in cname_records_diff.get("values_changed", {}):
        hostname = record.split("['")[1].split("']")[0]
        old_target_hostname = pihole_cname_records[hostname]
        new_target_hostname = cf_cname_records[hostname]
        try:
            pihole.cname("delete", hostname, old_target_hostname)
        except Exception as error:
            print(
                "Could not delete CNAME record: "
                + str(hostname)
                + ":"
                + str(old_target_hostname)
                + " "
                + str(error)
            )
            exit(1)
        try:
            pihole.cname("add", hostname, new_target_hostname)
            print(
                "Updated CNAME record: "
                + hostname
                + ":"
                + old_target_hostname
                + " -> "
                + new_target_hostname
            )
        except Exception as error:
            print(
                "Could not add CNAME record: "
                + str(hostname)
                + ":"
                + str(new_target_hostname)
                + " "
                + str(error)
            )
            exit(1)
    return


### Main function ###
while True:
    pihole_a_records = get_a_records_from_pihole()
    pihole_cname_records = get_cname_records_from_pihole()
    cf_dns_records = get_cf_records()
    cf_a_records = get_cf_a_records(cf_dns_records)
    cf_cname_records = get_cf_cname_records(cf_dns_records)

    a_records_diff = DeepDiff(
        pihole_a_records, cf_a_records, ignore_string_case=True, ignore_order=True
    )

    cname_records_diff = DeepDiff(
        pihole_cname_records, cf_cname_records, ignore_string_case=True, ignore_order=True
    )

    if a_records_diff != {}:
        add_new_a_records(a_records_diff)
        update_a_records(a_records_diff)
        delete_a_records(a_records_diff)
    else:
        print("All A records are synced")

    if cname_records_diff != {}:
        add_new_cname_records(cname_records_diff)
        update_cname_records(cname_records_diff)
        delete_cname_records(cname_records_diff)
    else:
        print("All CNAME records are synced")

    print("Sleeping for " + str(run_every_x_min) + " minutes")
    print("----------------------------------------------------")
    sleep(sleep_for_x_sec)
