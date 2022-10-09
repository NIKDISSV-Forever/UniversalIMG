from __future__ import annotations

from kivy.properties import ObjectProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDRoundFlatIconButton


class ActionIconButton(MDBoxLayout):
    __slots__ = ()
    button = ObjectProperty()

    def __init__(self, **kwargs):
        kwargs.setdefault('pos_hint', {'center_y': .5})
        self.button = MDRoundFlatIconButton(**kwargs)
        super().__init__(self.button)


class ThemeLightbulb(MDIconButton):
    __slots__ = ()

    def get_theme(self) -> tuple[bool, bool]:
        """
        :return:
        (is_light, is_auto)
        """
        return self.icon.endswith('outline'), self.icon.removesuffix('-outline').endswith('auto')
