"""
インストール後のフォルダ作成などを行うモジュール。

以下のファイル群をコピー（venv/lib/python3.12/site-packages/ -> インストールフォルダ）する。

:設定ファイル: config/config.toml
:テキストデータ: textdata/*.txt
:データベースファイル: database/*.json
:デレステ譜面データファイル: database/music/*.json
"""

from pathlib import Path
from shutil import copy

# 設定ファイルのフォルダ
CONFIG_FOLDERNAME: str = "config"
# テキストデータのフォルダ
TEXTDATA_FOLDERNAME: str = "textdata"
# データベースファイルのフォルダ
DATABASE_FOLDERNAME: str = "database"
# デレステ譜面データファイルのフォルダ
MUSIC_FOLDERNAME: str = "database/music"


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
    サイトパッケージフォルダからファイルをフォルダへコピーする。
    """

    site_packages_folder = Path(__file__).parents[1]

    for foldername in zip(
        ["*.toml", "*.txt", "*.json", "*.json"],
        [CONFIG_FOLDERNAME, TEXTDATA_FOLDERNAME, DATABASE_FOLDERNAME, MUSIC_FOLDERNAME],
    ):
        [
            copy(path, Path("./" + foldername[1]))
            for path in (site_packages_folder / Path(foldername[1])).glob(foldername[0])
        ]


def setup_databeses() -> None:
    """
    テキストデータからデータベース（JSONファイル）を作成する。

    idols_from_textdata.py などを実行。
    """

    from deredata.libs.database.convert import idols_from_textdata

    idols_from_textdata.main()


def main() -> None:
    """
    インストール後の処理。
    """

    setup_folders()
    setup_files()
    setup_databeses()


if __name__ == "__main__":
    print(__file__)
