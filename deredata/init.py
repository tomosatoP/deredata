"""
インストール後のフォルダ作成などを行うモジュール。
"""

from pathlib import Path

# 設定ファイル
CONFIG_FILENAME: str = "config/config.toml"
# デレステ譜面データファイル置き場
MUSIC_FOLDER: str = "databese/music"

CONFIG_CONTENT: str = '''# データベースファイルを保持するフォルダ
database_folder = "database/"
# データベースの元テキストデータを保持するフォルダ
textdata_folder = "textdata/"'''


def setup_folders() -> None:
    """
    フォルダとファイルを作成する。
    """

    Path(CONFIG_FILENAME).mkdir(exist_ok=True)
    Path(MUSIC_FOLDER).mkdir(exist_ok=True)


def setup_files() -> None:
    """
    ファイルに中身を書き出す。
    """
    Path(CONFIG_FILENAME).write_text(CONFIG_CONTENT)


def main() -> None:
    """
    インストール後の処理。
    """

    setup_folders()
    setup_files()


if __name__ == "__main__":
    print(__file__)
