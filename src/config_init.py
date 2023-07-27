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
            logger.error(f"Invalid domain: {domain_config['domain']}")
            return False
        if not isinstance(domain_config["token"], str) or len(domain_config["token"]) == 0:
            logger.error(f"Invalid token for domain: {domain_config['domain']}")
            return False
        if not isinstance(domain_config["include_proxied_records"], bool):
            logger.error(f"Invalid include_proxied_records for domain: {domain_config['domain']}")
            return False

    # Validate Pi-hole servers
    for server_config in config["pihole"]["servers"]:
        if not (ipv4(server_config["host"]) or ipv6(server_config["host"]) or domain(server_config["host"])):
            logger.error(f"Invalid host: {server_config['host']}")
            return False
        if not isinstance(server_config["port"], int) or not (1 <= server_config["port"] <= 65535):
            logger.error(f"Invalid port for host: {server_config['host']}")
            return False
        if not isinstance(server_config["password"], str) or len(server_config["password"]) == 0:
            logger.error(f"Invalid password for host: {server_config['host']}")
            return False
        if not isinstance(server_config["use_https"], bool):
            logger.error(f"Invalid use_https for host: {server_config['host']}")
            return False

    # Validate global settings
    if not isinstance(config["sync_interval_minutes"], int) or config["sync_interval_minutes"] <= 0:
        logger.error("Invalid sync_interval_minutes")
        return False
    if not isinstance(config["error_threshold"], int) or config["error_threshold"] <= 0:
        logger.error("Invalid error_threshold")
        return False
    if not isinstance(config["send_notifications"], bool):
        logger.error("Invalid send_notifications")
        return False

    # If we passed all checks, the configuration is valid
    return True


def main():
    print("You are running config.py directly. It should be imported.")


if __name__ == "__main__":
    main()
