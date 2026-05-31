"""Application Entry"""

from kivy.config import Config
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.resources import resource_add_path

### Settings Kivy - kivy ###
# log_level: "trace", "debug", "info", "warning", "error", "critical"
Config.set("kivy", "log_level", "info")
Config.set("kivy", "log_maxfiles", 10)
Config.set("kivy", "keyboard_mode", "")

### Settings Kivy - graphics ###
# fullscreen: 0, 1, "auto", "fake"
# window_state: "visible", "hidden", "maximaized", "minimized"
# borderless: 0, 1
# custom_titlebar: 0, 1
# width: not used if fullscreen is set to "auto".
# height: not used if fullscreen is set to "auto".
# show_cursor: 0, 1
Config.set("graphics", "fullscreen", 0)
Config.set("graphics", "window_state", "visible")
Config.set("graphics", "borderless", 0)
Config.set("graphics", "custom_titlebar", 0)
Config.set("graphics", "height", 800)
Config.set("graphics", "width", 1500)
Config.set("graphics", "show_cursor", 0)
Config.set("graphics", "font_size", 30)

### To use japanese font in Kivy ###
# resource_add_path("/usr/share/fonts/opentype/ipaexfont-gothic")
# LabelBase.register(DEFAULT_FONT, "ipaexg.ttf")
resource_add_path("/usr/share/fonts/opentype/ipafont-gothic")
LabelBase.register(DEFAULT_FONT, "ipag.ttf")

if __name__ == "__main__":
    import asyncio
    from deredata.mainview import MainviewApp as app

    asyncio.run(app().async_run())
