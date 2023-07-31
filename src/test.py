from apprise_notifier import Notifier

config_file = "src/apprise_notifier/apprise_config.yml"


notifier = Notifier(config_file)
notifier.send_notification("Test Title", "Test Message")
