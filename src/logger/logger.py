import logging
import logging.config
import yaml


##################
### logger Use ###
##################

# from logger import iniLogger
# logger.debug("debug message")
# logger.info("info message")
# logger.warning("warn message")
# logger.error("error message")
# logger.critical("critical message")

# log file location is defined in logging.yml as:
#    filename: path_to/name.log

# Check log levels check in for main.py
# print(f"Logger level: {logger.getEffectiveLevel()}")
# for handler in logger.handlers:
#     print(f"Handler level: {handler.level}")
# print(f"Root logger level: {logging.getLogger().getEffectiveLevel()}")

##################


config_file = "src/logger/logging_settings.yml"


def iniLogger(name="root", log_level=None):
    try:
        with open(config_file, "r") as stream:
            config = yaml.load(stream, Loader=yaml.FullLoader)
        logging.config.dictConfig(config)
    except FileNotFoundError as error:
        print("Error: " + str(error))
        exit(1)

    logger = logging.getLogger(name)

    # Mapping from string log levels to logging module constants
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    if log_level is not None:
        # Check if log_level is a valid string
        if log_level in level_mapping:
            level = level_mapping[log_level]
            logging.getLogger().setLevel(level)  # Set log level of root logger
            logger.setLevel(level)  # Set log level of the logger you return
        else:
            print(f"Invalid log level: {log_level}. Using default log level.")
    return logger


def main():
    print("You are running logger.py directly. It should be imported.")


if __name__ == "__main__":
    main()
