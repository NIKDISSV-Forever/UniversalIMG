from __future__ import annotations

import functools
import math
from typing import SupportsInt

from kivy.clock import mainthread
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color
from kivy.input.providers.mouse import MouseMotionEvent
from kivy.metrics import dp
from kivy.properties import (AliasProperty, BooleanProperty,
                             ListProperty, NumericProperty,
                             ObjectProperty, OptionProperty)
from kivy.uix.boxlayout import BoxLayout
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.selection import MDSelectionList
from kivymd.uix.selection import selection
from kivymd.uix.textfield import MDTextField

from pyimgedit import ArchiveContent

SELECTED_ICON_PADDING = (dp(65.), 0, 0, 0)
SORT_DIRECTION = (' (+)', ' (-)')
_SCROLLS_POSITION = {'down': 1., 'up': 0.}


class SelectionList(MDSelectionList):
    __slots__ = ()
    selected_mode = AliasProperty(lambda _: True, lambda _, _2: None)


class FixedSelectionItem(selection.SelectionItem):
    __slots__ = ()
    _instance_overlay_color = ObjectProperty(Color(rgba=(0, 0, 0, 0)))


selection.SelectionItem = FixedSelectionItem


def aoi(value: str | SupportsInt):
    try:
        return int(value)
    except (ValueError, TypeError):
        return


def get_item(file: ArchiveContent, **kwargs) -> MDBoxLayout:
    fn_box = BoxLayout(
        padding=SELECTED_ICON_PADDING,
    )
    fn_box.add_widget(
        MDRectangleFlatButton(
            text=file.name,
            pos_hint={'center_y': .5},
            **kwargs
        )
    )

    return (
        MDBoxLayout(
            fn_box,
            MDLabel(
                text=str(file.size),
                halign="center"
            ),
            MDLabel(
                text=str(file.offset),
                halign="center"
            )
        )
    )


class ArchiveDataView(BoxLayout):
    __slots__ = ()

    selected_filenames = {*()}

    page_size = NumericProperty(10)
    page = NumericProperty(0)
    rows = ListProperty([])
    row_items = ListProperty([])
    scroll_direction = OptionProperty('nope', options=['up', 'nope', 'down'])

    all_selected = BooleanProperty(False)

    select_list = ObjectProperty()
    search_field = ObjectProperty()
    _last_page = NumericProperty(-1)

    @staticmethod
    def _on_name_button_press(button: MDRectangleFlatButton):
        Clipboard.copy(text := button.text)
        toast(f'{text!r} copied!')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._COLUMN_LABELS: tuple[MDLabel, MDLabel, MDLabel] = (
            MDLabel(
                text='[b][ref=name]Name',
                markup=True,
                on_ref_press=self.sort_by,
                size_hint_x=.85,
                padding=[dp(65.) - 48., 0]
            ),
            MDLabel(
                text='[b][ref=size]Size\nBlocks / Size',
                markup=True,
                halign="center",
                on_ref_press=self.sort_by
            ),
            MDLabel(
                text='[b][ref=offset]Offset\nBlocks / Offset',
                markup=True,
                halign="center",
                on_ref_press=self.sort_by
            )
        )

        self.add_widget(
            MDBoxLayout(

                MDBoxLayout(
                    select_all_button
                    := MDIconButton(
                        icon='select-all',
                        on_press=self.select_all
                    ),
                    *self._COLUMN_LABELS,
                    size_hint_y=.1,
                ),

                scroll_view
                := MDScrollView(
                    select_list := SelectionList(),
                    on_scroll_stop=self.new_scroll
                ),

                # nav line
                MDBoxLayout(
                    MDIconButton(
                        icon='arrow-collapse-up',
                        on_press=self.nav_to_up_max,
                        pos_hint={'center_y': .5}
                    ),
                    MDIconButton(
                        icon='arrow-up',
                        on_press=self.nav_to_up,
                        pos_hint={'center_y': .5}
                    ),

                    MDBoxLayout(
                        page_size_field
                        := MDTextField(
                            icon_left='format-page-break',
                            hint_text='Page size',
                            helper_text='Page size',
                            helper_text_mode='persistent',
                            on_text_validate=self.set_page_size_event,
                            mode='round',
                            size_hint_x=.4,
                            pos_hint={'center_y': .6}
                        ),
                        page_field
                        := MDTextField(
                            hint_text='Page',
                            helper_text='Page',
                            helper_text_mode='persistent',
                            on_text_validate=self.set_page_event,
                            mode='round',
                            size_hint_x=.4,
                            pos_hint={'center_y': .6}
                        ),
                        search_field
                        := MDTextField(
                            icon_left='magnify',
                            hint_text='Search',
                            helper_text='Search File Name',
                            helper_text_mode='persistent',
                            on_text_validate=lambda _: self.reform_table(),
                            mode='round',
                            size_hint_x=.6,
                            pos_hint={'center_y': .6}
                        ),
                    ),

                    MDIconButton(
                        icon='arrow-down',
                        on_press=self.nav_to_down,
                        pos_hint={'center_y': .5}
                    ),
                    MDIconButton(
                        icon='arrow-collapse-down',
                        on_press=self.nav_to_down_max,
                        pos_hint={'center_y': .5}
                    ),
                    size_hint_y=.2
                ),
                orientation='vertical',
            )
        )

        select_list.on_selected = self.on_select
        select_list.on_unselected = self.on_unselect
        self.get_item = functools.partial(get_item, on_press=self._on_name_button_press)

        self.page_field = page_field
        self.page_size_field = page_size_field
        self.search_field = search_field

        self.select_all_button = select_all_button

        self.select_list = select_list
        self.scroll_view = scroll_view

        self.set_page_size(self.page_size)
        self.reform_table()

    def reform_table(self):
        scroll_direction = self.scroll_direction
        self.scroll_direction = 'nope'
        match scroll_direction:
            case 'down':
                if self._last_page == (self.pages_num + 1):
                    return
                self.page += 1
            case 'up':
                if not self._last_page:
                    return
                self.page -= 1
        start = (self.page - 1) * self.page_size

        if start > len(self.rows):
            start = len(self.rows) - self.page_size
        elif start < 0:
            start = 0
        else:
            if scroll_direction != 'nope':
                self.scroll_view.scroll_y = _SCROLLS_POSITION[scroll_direction]

        for child in self.select_list.children.copy():
            self.select_list.remove_widget(child)

        rows = self.rows
        row: ArchiveContent

        if text := self.search_field.text.strip():
            fnmatch_func = self._get_fnmatch(text)
            rows = [row for row in rows if fnmatch_func(row.name)]

        for row in rows[start:start + self.page_size]:
            self.select_list.add_widget(
                self.get_item(row)
            )

        self._last_page = self.page
        self.reselect()
        self.set_page()

    @staticmethod
    def _get_fnmatch(text):
        text = text.casefold()

        def _filter(name: str):
            return text in name.strip().casefold()

        return _filter

    def new_scroll(self, scroll: MDScrollView, _: MouseMotionEvent):
        if scroll.scroll_y < 0.:
            self.scroll_direction = 'down'
        elif scroll.scroll_y > 1.:
            self.scroll_direction = 'up'
        else:
            return
        self.reform_table()

    def sort_by(self, label: MDLabel, attr: str):
        reverse = label.text.endswith(SORT_DIRECTION[0])
        for lab in self._COLUMN_LABELS:
            if lab.text.endswith(SORT_DIRECTION):
                lab.text = lab.text.removesuffix(SORT_DIRECTION[0]).removesuffix(SORT_DIRECTION[1])
        label.text += SORT_DIRECTION[reverse]
        self.rows.sort(key=lambda f: getattr(f, attr, -1), reverse=reverse)
        self.reform_table()

    def update_data(self, new_data):
        self.rows = new_data
        self.selected_filenames.clear()
        self.reform_table()

    def reselect(self):
        need_select = self.selected_filenames.copy()
        self.select_list.unselected_all()
        for item in self.select_list.children:
            name = self.get_filename_from_item(item)
            if name in need_select:
                item.do_selected_item()

    @mainthread
    def select_all(self, button_instance: MDIconButton = None):
        self.all_selected = not self.all_selected
        if self.all_selected:
            self.selected_filenames.clear()
            self.selected_filenames |= {file.name for file in self.rows}
        else:
            self.selected_filenames.clear()
        self.reselect()
        (button_instance or self.select_all_button).icon = ('select-all', 'select',)[self.select_list.get_selected()]

    def on_select(self, item: selection.SelectionItem):
        if (name := self.get_filename_from_item(item)) not in self.selected_filenames:
            self.selected_filenames.add(name)
        item.selected = True

    def on_unselect(self, item: selection.SelectionItem):
        if (name := self.get_filename_from_item(item)) in self.selected_filenames:
            self.selected_filenames.remove(name)
        item.selected = False

    def set_page_size_event(self, field: MDTextField):
        self.set_page_size(field.text)
        self.reform_table()

    def set_page_event(self, field: MDTextField):
        self.set_page(field.text)
        self.reform_table()

    def set_page_size(self, new_page_size):
        new_page_size = max(aoi(new_page_size) or self.page_size, 1)
        self.page_size = new_page_size
        self.page_size_field.text = str(self.page_size)

    def set_page(self, new_page=None):
        new_page = min(max(aoi(new_page) or self.page, 1), self.pages_num)
        self.page = new_page
        self.page_field.text = str(self.page)

    def nav_to_up_max(self, _=None):
        self.set_page(1)
        self.scroll_direction = 'up'
        self.reform_table()

    def nav_to_down_max(self, _=None):
        self.set_page(self.pages_num)
        self.scroll_direction = 'down'
        self.reform_table()

    def nav_to_up(self, _=None):
        self.scroll_view.scroll_y = 1.

    def nav_to_down(self, _=None):
        self.scroll_view.scroll_y = 0.

    @staticmethod
    def get_filename_from_item(item: selection.SelectionItem) -> str:
        return item.children[1].children[2].children[0].text

    @property
    def pages_num(self):
        return math.ceil(len(self.rows) / self.page_size)
