# kivy の非同期処理

**kivy** は、非同期クロックをサポートしている（デフォルトでは、``asyncio`` モジュールを使用）。

時間のかかる処理を行う際に、**kivy** の UI処理をブロックしないように非同期クロックを利用する。非同期クロックを有効にするには、次のようにアプリケーションを開始する。

~~~python
import asyncio
from kivy.app import App

asyncio.run(App().async_run())
~~~

そうすることで、コルーチン（``coroutine`` : 非同期に呼び出されるサブルーチン。async/await 構文で宣言される。）をいつでも呼び出せる。

今回は、0.1～0.5秒ぐらいかかる計算を複数回繰り返し実行する処理をコルーチンにした。

~~~python
from collections.abc import AsyncGenerator
from concurrent.futures import ProcessPoolExecutor
import asyncio

def ddddd(eeee: Any) -> Any:

    重い処理
    return result

async def ccccc(n: int) -> AsyncGenerator:

    #　重い処理の繰り返しを、複数のプロセスに分散実行
    with ProcessPoolExecutor() as executor:
        futurers = [
            asyncio.get_running_loop.run_in_executor(
                executor,
                ddddd,  # 重い処理
                eeeee,  # 重い処理の実引数
            )
            for _ in range(n)
        ]

        for future in asyncio.as_completed(futures):
            yield await future

async def bbbbb(n: int) -> None:

    async for item in ccccc(n):
        ここで kivy の UI 処理を行ったり、
        重い処理の結果を処理する。（item は、重い処理の result が入る）

task = asyncio.ceate_task(bbbbb(100))  # 重い処理を100回繰り返す。
~~~
