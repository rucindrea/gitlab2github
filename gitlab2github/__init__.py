from loguru import logger


config = {
    "handlers": [
        {"sink": "gitlab2github.log", "mode": "w"},
    ]
}
logger.configure(**config)
