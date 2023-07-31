import yaml
from validators import domain, ipv4, ipv6


def load_config(file_path, logger):
    with open(file_path, "r") as file:
        try:
            config = yaml.load(file, Loader=yaml.SafeLoader)
            return config
        except yaml.YAMLError as error:
            logger.error(f"Error loading configuration file: {error}")
            return None


def validate_config(config, logger):
    # Validate Cloudflare domains and tokens
    for domain_config in config["cloudflare"]["domains"]:
        if not domain(domain_config["domain"]):
            logger.error(f"Invalid domain: {domain_config['domain']}. Expected a valid domain.")
            return False
        if not isinstance(domain_config["token"], str) or len(domain_config["token"]) == 0:
            logger.error(f"Invalid token for domain: {domain_config['domain']}. Expected a non-empty string.")
            return False
        if not isinstance(domain_config["include_proxied_records"], bool):
            logger.error(
                f"Invalid include_proxied_records for domain: {domain_config['domain']}. Expected a boolean value (true/false)."
            )
            return False

    # Validate Pi-hole servers
    for server_config in config["pihole"]["servers"]:
        if not (ipv4(server_config["host"]) or ipv6(server_config["host"]) or domain(server_config["host"])):
            logger.error(f"Invalid host: {server_config['host']}. Expected a valid IP address or domain.")
            return False
        if not isinstance(server_config["port"], int) or not (1 <= server_config["port"] <= 65535):
            logger.error(f"Invalid port for host: {server_config['host']}. Expected an integer between 1 and 65535.")
            return False
        if not isinstance(server_config["password"], str) or len(server_config["password"]) == 0:
            logger.error(f"Invalid password for host: {server_config['host']}. Expected a non-empty string.")
            return False
        if not isinstance(server_config["use_https"], bool):
            logger.error(f"Invalid use_https for host: {server_config['host']}. Expected a boolean value (true/false).")
            return False

    # Validate notifications
    if "notifications" in config and "apprise" in config["notifications"]:
        if not isinstance(config["notifications"]["apprise"]["enabled"], bool):
            logger.error(
                f"Invalid enabled flag for apprise notifications: {config['notifications']['apprise']['enabled']}. Expected a boolean value (true/false)."
            )
            return False
        for notification_url in config["notifications"]["apprise"]["urls"]:
            if not isinstance(notification_url, str) or len(notification_url) == 0:
                logger.error(
                    f"Invalid Apprise notification URL: {notification_url}. "
                    f"Expected a non-empty string. Refer to Apprise documentation for correct URL formats: "
                    f"https://github.com/caronc/apprise/wiki"
                )
                return False

    # Validate web server
    if "web_server" in config:
        if not isinstance(config["web_server"]["enabled"], bool):
            logger.error(
                f"Invalid enabled flag for web server: {config['web_server']['enabled']}. Expected a boolean value (true/false)."
            )
            return False

    # Validate global settings
    if not isinstance(config["sync_interval_minutes"], int) or config["sync_interval_minutes"] <= 0:
        logger.error(f"Invalid sync_interval_minutes: {config['sync_interval_minutes']}. Expected a positive integer.")
        return False
    if not isinstance(config["error_threshold"], int) or config["error_threshold"] <= 0:
        logger.error(f"Invalid error_threshold: {config['error_threshold']}. Expected a positive integer.")
        return False

    # If we passed all checks, the configuration is valid
    return True


def main():
    print("You are running config_init.py directly. It should be imported.")


if __name__ == "__main__":
    main()
