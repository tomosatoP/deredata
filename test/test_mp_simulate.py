"""
appeal.py, stage.py の動作チェック
"""

from concurrent.futures import ProcessPoolExecutor as mp

from deredata.libs.database.units import Units, GrandliveUnit, Unit
from deredata.libs.database.musics import Musics
from deredata.libs.simulate.appeal import Calculator
from deredata.libs.simulate.stage import Simulator

from kivy.logger import Logger as LibsTestSimulateLogger

units: Units = Units()
units.load()
musics: Musics = Musics()
musics.load()
Calculator.load()
Simulator.load()
musicfilename: str = "database/music/sample_DEBUT_ALL_L5.json"

if __name__ == "__main__":
    unit: Unit | GrandliveUnit = units.get("sample")

    test_appeals = Calculator(musics.get(musicfilename))
    test_appeals.run(unit if isinstance(unit, Unit) else Unit())

    test_scores = Simulator(musics.get(musicfilename))

    n: int = 1
    with mp(max_workers=4) as executor:
        result = executor.map(
            test_scores.run,
            [test_appeals.isresonance for _ in range(n)],
            [test_appeals.unit for _ in range(n)],
            [test_appeals.supports for _ in range(n)],
        )

    LibsTestSimulateLogger.info("サポートメンバーのエピソード名リスト")
    LibsTestSimulateLogger.info(f"{test_appeals.supports[0]}")
    LibsTestSimulateLogger.info(f"サポート: {sum([int(sum(s)) for s in test_appeals.supports[1:4]])}")
    # 111470, 111455, 111419, PASSION

    LibsTestSimulateLogger.info("ゲストを含むユニットメンバーのエピソード名リスト")
    LibsTestSimulateLogger.info(f"{test_appeals.unit[0]}")
    LibsTestSimulateLogger.info(
        f"アピール値合計: {
            sum([int(sum(s)) for s in test_appeals.unit[1:4]]) + sum([int(sum(s)) for s in test_appeals.supports[1:4]])
        }"
    )
    # 261037, 450235, 451212, 444482
    LibsTestSimulateLogger.info(f"ゲストを含むユニットメンバーのライフ: {int(sum(test_appeals.unit[4]))}")
    # ALL, CUTE, 264, PASSION
    LibsTestSimulateLogger.info(f"ユニットメンバーの特技発動率: {test_appeals.unit[5][:5]}")
    # [0.94, 1.04, 1.04, 1.04, 1.04]
    # [0.72, 0.80, 0.72, 1.04, 0.94]
    # [0.94, 0.94, 0.94, 0.94, 0.94]
    #
    LibsTestSimulateLogger.info(f"ユニットメンバーの特技継続期間（秒）: {test_appeals.unit[6][:5]}")
    # [7.5, 3.0, 6.0, 6.0, 6.0]
    # [7.5, 4.5, 7.5, 3.0, 7.5]
    # [7.5, 7.5, 9.0, 7.5, 4.5]
    #
    LibsTestSimulateLogger.info([sum(r) for r in result])
    # 2882080, 2619754, 2595035, 2495076
