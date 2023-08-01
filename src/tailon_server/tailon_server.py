import subprocess
from typing import Optional
from shutil import copyfile
import pkg_resources
import os


class TailonServer:
    def __init__(self, enabled: bool, port: int, username: Optional[str], password: Optional[str], logger):
        self.enabled = enabled
        self.port = port
        self.username = username
        self.password = password
        self.log_file = "logs/pihole-cloudflare-dns-sync.log"
        self.logger = logger
        self.tailon_process = None

    def start(self):
        if self.enabled:
            tailon_command = ["tailon", "-f", self.log_file, "-b", f"0.0.0.0:{self.port}"]

            # If a password and username are set, enable basic HTTP authentication
            if self.password is not None and self.username is not None:
                tailon_command.extend(["-p", "basic", "-u", f"{self.username}:{self.password}"])

            # Find the location of the 'tailon' package
            tailon_location = pkg_resources.get_distribution("tailon").location
            # Construct the path to the 'assets' directory
            assets_dir = os.path.join(tailon_location, "tailon", "assets")
            # Path to the 'favicon.ico' file in the 'assets' directory
            favicon_location = os.path.join(assets_dir, "favicon.ico")

            # Check if the 'favicon.ico' file exists
            if not os.path.exists(favicon_location):
                # If not, copy the custom 'favicon.ico' file
                custom_favicon_location = os.path.join("src", "tailon_server", "assets", "favicon.ico")
                copyfile(custom_favicon_location, favicon_location)
                self.logger.debug(f"Copied custom 'favicon.ico' file to {favicon_location}")

            # Start Tailon as a subprocess
            self.tailon_process = subprocess.Popen(tailon_command)
            self.logger.info("Tailon log web server started.")

    def stop(self):
        if self.tailon_process is not None:
            self.tailon_process.terminate()
            self.logger.info("Tailon log web server stopped.")
