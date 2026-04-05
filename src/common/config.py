from dynaconf import Dynaconf

from src.common.logger import setup_logger

settings = Dynaconf(
    settings_files=["resources/settings.toml", "resources/receive.toml", "resources/send.toml"],
    environments=True,
    envvar_prefix="COURIER",
    load_dotenv=True
)

logger = setup_logger(settings.log_level)