from __future__ import annotations

from kivy.metrics import dp
from kivy.properties import DictProperty
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.datatables import MDDataTable


class ArchiveInfoView(BoxLayout):
    __slots__ = ()
    data_dictionary = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_data(self.data_dictionary)

    def update_data(self, new_info):
        self.clear_widgets()
        if not isinstance(new_info, dict):
            new_info = dict(new_info)
        max_len_k = dp(max([*(len(i) for i in new_info), 0]) * 1.5)
        max_len_v = dp(max([*(len(i) for i in new_info.values()), 0]) * 1.5)
        self.add_widget(
            MDDataTable(
                column_data=[('Key', max_len_k), ('Value', max_len_v)],
                row_data=new_info.items()
            )
        )
