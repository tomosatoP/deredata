"""
デレステ譜面ファイルを扱うモジュール。
"""

import glob
from typing import Any
from fractions import Fraction
from math import ceil

from deredata.libs.derenotes.song import Note, Song, SongCategory, SongType, NoteType, Chart
from deredata.libs.database.configurations import database_folder

from kivy.logger import Logger as MusicsLogger

FPS = 60
# glob形式のデレステ譜面ファイル名
MUSICFILENAMES: str = database_folder() + "music/*.json"


#### musics API用のエラーハンドラ
class MusicsError(Exception):
    """musicsのエラーハンドラ"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

        MusicsLogger.error(f"MusicsError: {args}")


class Music(Chart):
    """
    スコア計算用にデレステ譜面データ（class Chart）を拡張したクラス。

    class Chart からの変更点は以下の通り。

    - FPS を 60（time_base = fraction(1, 60)）に設定する。
    - 開始ノート（START）の timestamp が 0 になるようにすべてのノートの timestamp をシフトする。
    - 毎秒にカウンターノートを追加する。
    - 開始ノート（START）・終了ノート（END）・カウンターノートは、ノート総数に含まない。
    - ハッシュ可能（ハッシュ値は、ファイル名から生成する）。
    - ソート可能（ファイル名を使用して）
    - 読み出し専用。
    """

    @property
    def length(self) -> int:
        """
        譜面の長さ（秒）。
        """
        end = {note for note in self._notes if note.type == NoteType.END}.pop()

        return ceil((end.timestamp) * end.time_base)

    @property
    def last_note(self) -> Note:
        """
        最後のノート。
        """

        return sorted({note for note in self._notes if note.type != NoteType.END}, reverse=True)[0]

    @property
    def note_number(self) -> int:
        """
        ノート総数（開始ノート、終了ノート、カウンターノートを除く）。
        """

        return len({note for note in self._notes if note.type not in [NoteType.START, NoteType.END]})

    def notes(self, include_intervals: int = 0) -> set[Note]:
        """
        カウンターノートを含む全ノート集合（開始ノート、終了ノートを除く）。

        :param int include_intervals:
          カウンターノートの挿入間隔（秒）。
          初期値の 0 は、カウンターノートを挿入しないことを意味する。

        :return: カウンターノートを含む全ノート集合（開始ノート、終了ノートを除く）。
        :rtype: set[Note]
        """

        if include_intervals != 0:
            count: set[Note] = {
                Note(timestamp=i * 60, lane=0, width=0, time_base=Fraction(1, 60), type=NoteType.COUNT)
                for i in range(0, int(self.last_note.timestamp * self.last_note.time_base) + 1, include_intervals)
            }

            return count | {note for note in self._notes if note.type not in [NoteType.START, NoteType.END]}
        else:
            return {note for note in self._notes if note.type not in [NoteType.START, NoteType.END]}

    def __eq__(self, other: Any) -> Any:
        if not isinstance(other, Music):
            return NotImplemented
        # return self.__dict__ == other.__dict__
        return self.filename == other.filename

    def __lt__(self, other: Any) -> Any:
        if not isinstance(other, Music):
            return NotImplemented
        return self.filename < other.filename

    def __hash__(self) -> Any:
        return hash((self.filename,))

    def load(self) -> None:
        """
        デレスタ譜面ファイルを読み込み、スコア計算用の変更を加える。

        ライブの開始ノート（START）の ``timestamp`` を 0 にし、すべてのノートの ``timestamp`` を調整する。
        また、FPS を 60 として、すべてのノートの ``time_base`` を ``Fraction(1, 60)`` に調整する。
        """

        super().load()

        start = {note for note in self._notes if note.type == NoteType.START}.pop()

        for note in sorted(self._notes):
            timestamp = round((note.timestamp - start.timestamp) * note.time_base / Fraction(1, FPS))
            self._notes.remove(note)
            self._notes.add(
                Note(
                    timestamp=timestamp,
                    lane=note.lane,
                    width=note.width,
                    type=note.type,
                    time_base=Fraction(1, FPS),
                )
            )

    def save(self) -> None:
        """
        デレステ譜面ファイルへの上書き禁止。
        """

        raise MusicsError("デレステ譜面ファイルは読み込み専用です。")


class Musics:
    """
    デレステ譜面ファイルのデータベース。
    """

    _musics: set[Music] = set()

    def get(self, filename: str) -> Music:
        """
        デレステ譜面ファイル名で、デレステ譜面データを取得する。

        :param str filename: デレステ譜面ファイル名。

        :return: デレステ譜面データ。
        :rtype: Music
        """

        result: set[Music] = {music for music in self.__class__._musics if music.filename == filename}

        return result.pop() if result else Music()

    def gets(self) -> set[Music]:
        """
        すぺてのデレステ譜面データリスト。

        :return: すぺてのデレステ譜面データリスト。
        :rtype: list[Music]
        """

        return self.__class__._musics

    @classmethod
    def load(cls, filenames: str = MUSICFILENAMES) -> None:
        """
        デレステ譜面ファイルを読み込み、データベースに取り込む。

        :param str filenames: 初期値は、既定のglob形式のファイル名。
        """

        data: Music

        for filename in sorted(glob.glob(filenames)):
            data = Music()
            data.filename = filename
            data.load()
            cls._musics.add(data)

        MusicsLogger.info(f"{cls.__name__}.load: {len(cls._musics)}件のデレステ譜面ファイルを読み込みました。")


if __name__ == "__main__":
    print(__file__)
