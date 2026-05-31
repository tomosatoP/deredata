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
    def __init__(self) -> None:
        self._levels: list[MusicLevel] = list()
        self._path: Path = Path(MUSICLEVELSDB)

    @property
    def filename(self) -> str:
        """曲係数データベースのファイル名。"""
        return self._path.name

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    def rate(self, level: int) -> float:
        return [musiclevel.rate for musiclevel in self._levels if musiclevel.level == level][0]

    def add(self, musiclevel: MusicLevel) -> None:
        self._levels.append(musiclevel)

    def load(self) -> None:
        self._levels.clear()

        if not isinstance(self._path, Path) or not self._path.exists():
            raise MusiclevelsError(f"{self.__class__.__name__}.load: ")

        with self._path.open("r", encoding="utf-8-sig") as f:
            datas = json.load(f)

            for data in datas:
                self._levels.append(
                    MusicLevel(
                        level=int(data["楽曲Lv"]),
                        rate=float(data["曲係数"]),
                    )
                )

        LibsMusiclevelsLogger.info(
            f"{self.__class__.__name__}.load: {len(self._levels)}件の曲係数データを読み込みました。"
        )

    def save(self) -> None:
        if not isinstance(self._path, Path):
            raise MusiclevelsError(f"{self.__class__.__name__}.save: ")

        musiclevels = [
            {
                "楽曲Lv": musiclevel.level,
                "曲係数": musiclevel.rate,
            }
            for musiclevel in self._levels
        ]

        with self._path.open("w", encoding="utf-8") as f:
            json.dump(musiclevels, f, indent=4, ensure_ascii=False)

        LibsMusiclevelsLogger.info(f"{self.__class__.__name__}.save: 曲係数データベースを保存しました。")


if __name__ == "__main__":
    print(__file__)
