"""
スコア計算で使う曲係数のモジュール。

プレイする楽曲のLvによって決まる数値です。

:dataclass MusicLevel:
:class MusicLevels:
"""

import json
from pathlib import Path
from dataclasses import dataclass

from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as LibsMusiclevelsLogger

# 曲係数データベースのファイル名。
MUSICLEVELSDB: str = database_folder() + "musiclevels.json"


class MusiclevelsError(Exception):
    """
    ポテンシャルのエラーハンドラ
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsMusiclevelsLogger.error(f"MusiclevelsError: {args}")


@dataclass
class MusicLevel:
    level: int = 0  # 楽曲Lv
    rate: float = 0.0  # 曲係数


class MusicLevels:
    _levels: list[MusicLevel] = list()

    def rate(self, level: int) -> float:
        return [musiclevel.rate for musiclevel in self.__class__._levels if musiclevel.level == level][0]

    def add(self, musiclevel: MusicLevel) -> None:
        self.__class__._levels.append(musiclevel)

    @classmethod
    def _clear(cls) -> None:
        cls._levels.clear()

    @classmethod
    def load(cls, filename: str = MUSICLEVELSDB) -> None:

        path = Path(filename)
        if any([not isinstance(path, Path), not path.exists(), not path.is_file()]):
            raise MusiclevelsError(f"{cls.__name__}.load: ")

        cls._clear()
        with path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

            for data in datas:
                cls._levels.append(
                    MusicLevel(
                        level=int(data["楽曲Lv"]),
                        rate=float(data["曲係数"]),
                    )
                )

        LibsMusiclevelsLogger.info(f"{cls.__name__}.load: {len(cls._levels)}件の曲係数データを読み込みました。")

    @classmethod
    def save(cls, filename: str = MUSICLEVELSDB) -> None:

        path = Path(filename)
        if not isinstance(path, Path):
            raise MusiclevelsError(f"{cls.__name__}.save: ")

        musiclevels = [
            {
                "楽曲Lv": musiclevel.level,
                "曲係数": musiclevel.rate,
            }
            for musiclevel in cls._levels
        ]

        with path.open("w", encoding="utf-8") as f:
            json.dump(musiclevels, f, indent=4, ensure_ascii=False)

        LibsMusiclevelsLogger.info(f"{cls.__name__}.save: {len(cls._levels)}件の曲係数データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
