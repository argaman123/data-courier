import sys

from loguru import logger
from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=["resources/settings.toml"],
    environments=True,
    envvar_prefix="APP"
)

logger.remove()
logger.add(sys.stdout, colorize=True, level=settings.log_level,
           format="<green>{time:HH:mm:ss.SSS}</green> | "
                  "<level>{level}</level> | "
                  "{message}")
# logger.add("data-courier.log", colorize=False, rotation="500 MB")