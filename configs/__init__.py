import configparser
from pathlib import Path

def get_config():
    config = configparser.ConfigParser()
    # Path(__file__).parent gives us the 'configs' directory
    # Then we join it with 'config.ini' which is inside the configs folder
    config_path = Path(__file__).parent / 'config.ini'
    
    config.read(config_path)
    return config

# Global config object
CONFIG = get_config()