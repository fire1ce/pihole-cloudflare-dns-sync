import requests
from requests.exceptions import RequestException


class Notifier:
    def __init__(self, config, SyncError, logger):
        self.config = config["notifications"]["apprise"]
        self.logger = logger
        self.SyncError = SyncError
        self.headers = {"Content-Type": "application/json"}
        self.base_url = f"{'https' if self.config['server']['use_https'] else 'http'}://{self.config['server']['host']}:{self.config['server']['port']}/notify"

    def send_notification(self, title, body):
        if not self.config["enabled"]:
            self.logger.info("Apprise notifications are disabled. Skipping send_notification.")
            return

        for url in self.config["urls"]:
            data = {"urls": url, "title": title, "body": body}
            try:
                response = requests.post(self.base_url, headers=self.headers, json=data)
                service = url.split(":")[0]  # Extract the service from the URL
                if response.status_code != 200 or "could not be sent" in response.text:
                    self.logger.warning(f"Failed to send notification via {service}. Response: {response.text}")
                else:
                    self.logger.debug(f"Sent notification via {url}. Response: {response.text}")
                    self.logger.info(f"Sent notification via {service}. Response: {response.text}")
            except RequestException as error:
                self.logger.error(f"Error sending notification via {service}: {error}")
