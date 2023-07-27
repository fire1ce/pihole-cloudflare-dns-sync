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
