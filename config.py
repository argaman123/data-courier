import logging
from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=["resources/settings.toml"],  # main config file
    environments=True,                 # enable profiles
    envvar_prefix="APP"                # optional: override via environment variables
)



# Configure it once at the top of your file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)