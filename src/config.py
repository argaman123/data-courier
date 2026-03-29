from dynaconf import Dynaconf

from src.logger import setup_logger

settings = Dynaconf(
    settings_files=["resources/settings.toml"],
    environments=True,
    envvar_prefix="APP"
)

logger = setup_logger(settings.log_level)