"""
インストール後のフォルダ作成などを行うモジュール。

以下のファイル群をコピー（venv/lib/python#.##/site-packages/ -> インストールフォルダ）する。

:設定ファイル: config/config.toml
:テキストデータ: textdata/*.txt
:データベースファイル: database/*.json
:デレステ譜面データファイル: database/music/*.json
"""

from pathlib import Path

# Python3.14からはpathlibにcopyが実装されるので、不要
from shutil import copy

# 設定ファイルのフォルダ
CONFIG_FOLDERNAME: str = "config"
# テキストデータのフォルダ
TEXTDATA_FOLDERNAME: str = "textdata"
# データベースファイルのフォルダ
DATABASE_FOLDERNAME: str = "database"
# デレステ譜面データファイルのフォルダ
MUSIC_FOLDERNAME: str = "databese/music"


def setup_folders() -> None:
    """
    フォルダを作成する。
    """

    Path("./" + CONFIG_FOLDERNAME).mkdir(exist_ok=True)
    Path("./" + TEXTDATA_FOLDERNAME).mkdir(exist_ok=True)
    Path("./" + DATABASE_FOLDERNAME).mkdir(exist_ok=True)
    Path("./" + MUSIC_FOLDERNAME).mkdir(exist_ok=True)


def setup_files() -> None:
    """
    ファイルをコピーする。
    """

    site_packages_folder = Path(__file__).parents[1]

    for foldername in zip(
        ["*.toml", "*.txt", "*.json", "*.json"], ["config", "textdata", "database", "database/music"]
    ):
        [
            copy(path, Path("./" + foldername[1]))
            for path in (site_packages_folder / Path(foldername[1])).glob(foldername[0])
        ]


def main() -> None:
    """
    インストール後の処理。
    """

    setup_folders()
    setup_files()


if __name__ == "__main__":
    print(__file__)
