"""
デレステ譜面ファイルを扱うモジュール。
"""

from enum import StrEnum
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
import json

from kivy.logger import Logger as LibsSongLogger


#### song API用のエラーハンドラ
class SongError(Exception):
    """songのエラーハンドラ"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        LibsSongLogger.error(f"SongError: {args}")


class SongType(StrEnum):
    """
    デレステ楽曲タイプの列挙クラス。
    """

    ALL = "ALL"
    CUTE = "CUTE"
    COOL = "COOL"
    PASSION = "PASSION"


class SongCategory(StrEnum):
    """
    デレステ楽曲カテゴリの列挙クラス。
    """

    WIDE_DEBUT = "WIDE:DEBUT"
    WIDE_REGULAR = "WIDE:REGULAR"
    WIDE_PRO = "WIDE:PRO"
    WIDE_MASTER = "WIDE:MASTER"
    WIDE_MASTER_PLUS = "WIDE:MASTER+"
    WITCH_WITCH = "WITCH:WITCH"
    SMART_LIGHT = "SMART:LIGHT"
    SMART_TRICK = "SMART:TRICK"
    GRAND_PIANO = "GRAND:PIANO"
    GRAND_FORTE = "GRAND:FORTE"


class NoteType(StrEnum):
    """
    ノートタイプの列挙クラス。
    """

    START = "START"
    END = "END"
    TAP = "TAP"
    FLICK_LEFT = "FLICK:LEFT"
    FLICK_RIGHT = "FLICK:RIGHT"
    LONG_ON = "LONG:ON"
    LONG_OFF = "LONG:OFF"
    LONG_FLICK_LEFT = "LONG:FLICK:LEFT"
    LONG_FLICK_RIGHT = "LONG:FLICK:RIGHT"
    SLIDE_ON = "SLIDE:ON"
    SLIDE_PASS = "SLIDE:PASS"
    SLIDE_OFF = "SLIDE:OFF"
    SLIDE_FLICK_LEFT = "SLIDE:FLICK:LEFT"
    SLIDE_FLICK_RIGHT = "SLIDE:FLICK:RIGHT"
    DAMAGE = "DAMAGE"
    COUNT = "COUNT"


@dataclass
class Song:
    """
    デレステ楽曲情報のデータクラス。

    :param str name: タイトル
    :param SongCategory category: デレステ楽曲カテゴリ
    :param SongType type: デレステ楽曲タイプ
    :param int level: レベル
    """

    name: str = "未設定"
    category: SongCategory = SongCategory.WIDE_MASTER
    type: SongType = SongType.ALL
    level: int = 1


@dataclass(order=True, eq=True, frozen=True)
class Note:
    """
    ノートのデータクラス。

    :param int timestamp: time_base単位のタイムスタンプ。ソート対象。
    :param int lane: 左端から数えたレーン番号。ソート対象。
    :param int width: レーン幅。
    :param NoteType type: ノートタイプ。
    :param Fraction time_base: 単位時間（秒）。
    """

    timestamp: int = 0
    lane: int = 1
    width: int = field(default=1, compare=False)
    type: NoteType = field(default=NoteType.TAP, compare=False)
    time_base: Fraction = field(default=Fraction(1, 1), compare=False)


NoteLink = deque
"""
ノート（ロング、スライド）の始点・節点・終点を保持する ``deque`` 。
    - ロング: LONG_ON, LONG_OFF, LONG_FLICK_LEFT, LONG_FLICK_RIGHT
    - スライド: SLIDE_ON, SLIDE_PASS, SLIDE_OFF, SLIDE_FLICK_LEFT, SLIDE_FLICK_RIGHT
"""


class Chart:
    """
    デレステ譜面データを扱うクラス。

    :todo: self._notelink でロング・スライドのノートのつながりを扱う。
    :todo: self._notes グランドの複数レーンに跨るノートを扱う。
    """

    def __init__(self) -> None:
        self._video: str = ""
        self._last_index: int = 0
        self._song: Song = Song()
        self._notes: set[Note] = set()
        self._notelink: list[NoteLink] = list()
        self._path: Path = Path()

        LibsSongLogger.debug(f"{self.__class__.__name__}: init.")

    @property
    def filename(self) -> str:
        """
        デレステ譜面ファイルのパス名。
        """

        return str(self._path)

    @filename.setter
    def filename(self, value: str) -> None:
        self._path = Path(value)

    @property
    def videofile(self) -> str:
        """
        デレステ動画ファイルのパス名。
        """

        return self._video

    @videofile.setter
    def videofile(self, value: str) -> None:
        self._video = value

    @property
    def song(self) -> Song:
        """
        デレステ楽曲情報。
        """

        return self._song

    @song.setter
    def song(self, value: Song) -> None:
        self._song = value

    @property
    def last_index(self) -> int | None:
        """
        デレステ譜面ファイル保存時の画面フレームのインデックス。
        """

        return self._last_index

    @last_index.setter
    def last_index(self, value: int) -> None:
        self._last_index = value

    @property
    def note_number(self) -> int:
        """
        ``Note`` の全数。
        """

        return len(self._notes)

    @property
    def tap_number(self) -> int:
        """
        ``Note`` のうち、タップノートの数。
        """

        return len({note for note in self._notes if note.type == NoteType.TAP})

    @property
    def flick_number(self) -> int:
        """
        ``Note`` のうち、フリックノートの数。
        """

        return len(
            {
                note
                for note in self._notes
                if note.type
                in {
                    NoteType.FLICK_LEFT,
                    NoteType.FLICK_RIGHT,
                    NoteType.LONG_FLICK_LEFT,
                    NoteType.LONG_FLICK_RIGHT,
                    NoteType.SLIDE_FLICK_LEFT,
                    NoteType.SLIDE_FLICK_RIGHT,
                }
            }
        )

    @property
    def long_number(self) -> int:
        """
        ``Note`` のうち、ロングノートの数。
        """

        return len(
            {
                note
                for note in self._notes
                if note.type
                in {
                    NoteType.LONG_ON,
                    NoteType.LONG_OFF,
                    NoteType.LONG_FLICK_LEFT,
                    NoteType.LONG_FLICK_RIGHT,
                }
            }
        )

    @property
    def slide_number(self) -> int:
        """
        ``Note`` のうち、スライドノートの数。
        """

        return len(
            {
                note
                for note in self._notes
                if note.type
                in {
                    NoteType.SLIDE_ON,
                    NoteType.SLIDE_PASS,
                    NoteType.SLIDE_OFF,
                    NoteType.SLIDE_FLICK_LEFT,
                    NoteType.SLIDE_FLICK_RIGHT,
                }
            }
        )

    def current_notes(self, timestamp: int) -> int:
        """
        ``timestamp`` 直前までの ``Note`` を数える。

        :param int timestamp: タイムスタンプ
        :return: ``Note`` の数
        :rtype: int
        """

        return len(list(filter(lambda note: note.timestamp < timestamp, self._notes)))

    def search_within_range(self, min_timestamp: int, max_timestamp: int) -> Iterator[Note]:
        """
        ``timestamp`` 範囲内の ``Note`` のリストを得る。

        :param int min_timestamp: タイムスタンプ範囲の下限
        :param int max_timestamp: タイムスタンプ範囲の上限
        :return: ``Note`` のリスト
        :rtype: Iterator[Note]
        """

        return filter(lambda note: min_timestamp < note.timestamp < max_timestamp, self._notes)

    def find(self, timestamp: int) -> Iterator[Note]:
        """
        ``timestamp`` の ``Note`` のリストを得る。

        :param int timestamp: タイムスタンプ
        :return: ``Note`` のリスト
        :rtype: Iterator[Note]
        """

        return filter(lambda note: note.timestamp == timestamp, self._notes)

    def push(self, note: Note) -> None:
        """
        ``Note`` を追加する。

        :param Note note: 追加する ``Note``
        """

        self._notes.add(note)

    def remove(self, note: Note) -> None:
        """
        ``Note`` を削除する。

        :param Note note: 削除する ``Note``
        """

        self._notes.remove(note)

    def save(self) -> None:
        """
        デレステ譜面ファイルを保存する。
        """

        data = {
            "video": self._video,
            "song": {
                "name": self._song.name,
                "level": self._song.level,
                "type": self._song.type.value,
                "category": self._song.category.value,
            },
            "last_index": self._last_index,
            "notes": [
                {
                    "timestamp": note.timestamp,
                    "lane": note.lane,
                    "width": note.width,
                    "type": note.type.value,
                    "time_base": str(note.time_base),
                }
                for note in sorted(self._notes)
            ],
        }

        with self._path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        LibsSongLogger.info(f"{self.__class__.__name__}: save to {self._path}")

    def load(self) -> None:
        """
        デレステ譜面ファイルを読み込む。
        """

        with self._path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self._video = data["video"]

        song_data = data["song"]
        self._song = Song(
            name=song_data["name"],
            level=song_data["level"],
            type=SongType(song_data["type"]),
            category=SongCategory(song_data["category"]),
        )

        self._last_index = data["last_index"]

        for note_data in data["notes"]:
            note = Note(
                timestamp=note_data["timestamp"],
                lane=note_data["lane"],
                width=note_data["width"],
                type=NoteType(note_data["type"]),
                time_base=Fraction(note_data["time_base"]),
            )
            self._notes.add(note)

        LibsSongLogger.info(f"{self.__class__.__name__}: loaded from {self._path}")


if __name__ == "__main__":
    print(__file__)
