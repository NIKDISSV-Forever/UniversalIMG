from __future__ import annotations

from functools import cache

from kivy.clock import mainthread
from kivy.properties import ListProperty, NumericProperty
from kivymd.uix.textfield import MDTextFieldRect


class ArchiveLogView(MDTextFieldRect):
    readonly = True
    save_last_count = NumericProperty(2)
    _saves = ListProperty([])

    @staticmethod
    @cache
    def _form_string(value):
        return f'\n'.join(f'{k}: {v}' for k, v in value)

    def form_string(self, value):
        if isinstance(value, dict):
            value = value.items()
        return self._form_string((*value,))

    def set_log(self, values):
        new_text = self.form_string(values)
        if new_text in self._saves:
            self._saves.remove(new_text)
        self._saves.append(new_text)
        if len(self._saves) > self.save_last_count:
            self._saves.pop(0)
        self.set_text_mainthread('\n\n'.join(self._saves).strip())

    @mainthread
    def set_text_mainthread(self, text: str):
        self.text = text
