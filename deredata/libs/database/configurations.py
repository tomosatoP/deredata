"""
module
"""

import tomllib


def database_folder() -> str:
    with open("config/config.toml", "rb") as f:
        config_toml = tomllib.load(f)

    return config_toml["database_folder"]


def textdata_folder() -> str:
    with open("config/config.toml", "rb") as f:
        config_toml = tomllib.load(f)

    return config_toml["textdata_folder"]
