"""
この例では、Python に組み込まれている asyncio イベントループを利用して、
Kivy を単なる非同期コルーチンとして実行する推奨方法を示しています。
"""

import asyncio

from kivy.app import App
from kivy.lang.builder import Builder

kv = """
BoxLayout:
    orientation: 'vertical'
    BoxLayout:
        ToggleButton:
            id: btn1
            group: 'a'
            text: 'Sleeping'
            allow_no_selection: False
            on_activated: if self.activated: label.status = self.text
        ToggleButton:
            id: btn2
            group: 'a'
            text: 'Swimming'
            allow_no_selection: False
            on_activated: if self.activated: label.status = self.text
        ToggleButton:
            id: btn3
            group: 'a'
            text: 'Reading'
            allow_no_selection: False
            activated: True
            on_activated: if self.activated: label.status = self.text
    Label:
        id: label
        status: 'Reading'
        text: 'Beach status is "{}"'.format(self.status)
"""


class AsyncApp(App):
    other_task = None

    def build(self):
        return Builder.load_string(kv)

    def app_func(self):
        """
        これにより、両方のメソッドが非同期で実行され、
        それらが完了するまで待機します。
        """
        self.other_task = asyncio.ensure_future(self.waste_time_freely())

        async def run_wrapper():
            # 実際には、asyncio はデフォルトのライブラリなので明示的に設定する必要はありませんが、
            # 明示的に指定しておいても問題はありません。
            await self.async_run(async_lib="asyncio")
            print("App done")
            self.other_task.cancel()

        return asyncio.gather(run_wrapper(), self.other_task)

    async def waste_time_freely(self):
        """
        このメソッドも asyncio ループによって実行され、
        定期的に何かを出力します。
        """
        try:
            i = 0
            while True:
                if self.root is not None:
                    status = self.root.ids.label.status
                    print("{} on the beach".format(status))

                    # get some sleep
                    if not self.root.ids.btn1.activated and i >= 2:
                        i = 0
                        print("Yawn, getting tired. Going to sleep")
                        self.root.ids.btn1.activated = True

                i += 1
                await asyncio.sleep(2)
        except asyncio.CancelledError as e:
            print("Wasting time was canceled", e)
        finally:
            # when canceled, print that it finished
            print("Done wasting time")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(AsyncApp().app_func())
    loop.close()
