from __future__ import annotations

import os
import sys
from functools import partial, wraps
from threading import Thread
from tkinter.filedialog import (
    askdirectory,
    askopenfilename,
    askopenfilenames
)
from tkinter.messagebox import showerror
from typing import Callable, Sized, TypeVar
from urllib.error import URLError
from urllib.request import urlopen

import darkdetect
from kivy.clock import Clock, mainthread
from kivy.core.window import Window, WindowBase
from kivy.metrics import dp
from kivy.properties import (AliasProperty, BooleanProperty, ObjectProperty, StringProperty)
from kivy.resources import resource_add_path
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import BaseButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.textfield import MDTextField

from pyimgedit import IMGArchive
from pyimgedit import PACKAGE_DIR
from pyimgedit import __version__
from pyimgedit.gui.archive_data_view import ArchiveDataView, SELECTED_ICON_PADDING, get_item
from pyimgedit.gui.archive_info_view import ArchiveInfoView
from pyimgedit.gui.archive_log_view import ArchiveLogView
from pyimgedit.gui.custom_widgets import ActionIconButton, ThemeLightbulb

T = TypeVar('T')
T2 = TypeVar('T2')

toast_mainthread = mainthread(toast)


def version_check_message() -> str:
    last_version_url = 'https://github.com/NIKDISSV-Forever/UniversalIMG/blob/main/version.txt?raw=true'
    try:
        with urlopen(last_version_url) as resp:
            last_version = (*(int(i) for i in resp.read().split(b'.')),)
    except URLError:
        return '.'.join(str(i) for i in __version__)
    if __version__ == last_version:
        return 'latest'
    return 'not latest'


def _disable_brothers(func: Callable[[T], T2]):
    @wraps(func)
    def handler(self: T, btn: BaseButton) -> T2:
        reset = {*()}
        for child in btn.parent.parent.children:
            if not isinstance(child, ActionIconButton):
                continue
            button = child.button
            button.disabled = True
            reset.add(button)
        try:
            return func(self)
        finally:
            for i in reset:
                i.disabled = False

    return handler


def _act_button_process(func: Callable[[T], T2]):
    return _disable_brothers(func)


def askstring(title: str, prompt: str, *, initialvalue: str, on_validate: Callable[[str], None] = None):
    def _on_validate(_):
        if on_validate:
            on_validate(field.text)
        dialog.dismiss()

    field = MDTextField(
        text=initialvalue,
        hint_text=prompt,
        pos_hint={'center_x': .5, 'center_y': .5},
        on_text_validate=_on_validate,
        required=True
    )
    dialog = MDDialog(
        title=title,
        type='custom',
        content_cls=field,
        buttons=[
            MDFlatButton(
                text='OK',
                on_release=_on_validate
            )
        ],
    )
    dialog.open()


def new_thread(func: Callable):
    fix_wrapper = wraps(func)

    @fix_wrapper
    def wrapper(*args, **kwargs) -> None:
        @fix_wrapper
        def wrapper2():
            try:
                func(*args, **kwargs)
            except Exception as e:
                showerror(f'{e.__class__.__name__} ({func.__name__})', str(e))

        Thread(target=wrapper2, daemon=True).start()

    return wrapper


class UniversalIMGApp(MDApp):
    __slots__ = ()

    TITLE = 'Universal IMG'

    icon = str(PACKAGE_DIR / 'icon.png')
    _version_verdict = StringProperty('')

    def build(self):
        MDLabel.font_size = BaseButton.font_size = dp(18)

        self.theme_cls.theme_style = darkdetect.theme() or 'Dark'
        self.theme_cls.primary_palette = 'DeepOrange'

        self.archive_data_view = ArchiveDataView(size_hint_x=.75)
        self.archive_data_view.get_item = partial(get_item, on_release=self.rename_file)
        self.log_view = ArchiveLogView()

        self.opened_info_view = ArchiveLogView()
        self.progress_bar = MDProgressBar(value=100)

        self.archive_info_view = MDBoxLayout(
            self.log_view,
            self.progress_bar,
            self.opened_info_view,
            orientation='vertical',
            size_hint_x=.2,
        )

        self.add_files = new_thread(self.add_files)
        self.extract_files = new_thread(self.extract_files)
        self.delete_files = new_thread(self.delete_files)
        self.reload_list = new_thread(self.reload_list)
        self.rebuild_archive = new_thread(self.rebuild_archive)

        layout = MDBoxLayout(
            MDBoxLayout(

                MDBoxLayout(
                    ActionIconButton(
                        icon='file',
                        text='Open',
                        on_release=self.open_new_file
                    ),
                    add_files_button
                    := ActionIconButton(
                        icon='file-download',
                        text='Add',
                        on_release=self.add_files
                    ),
                    extract_files_button
                    := ActionIconButton(
                        icon='file-upload',
                        text='Extract',
                        on_release=self.extract_files
                    ),
                    delete_files_button
                    := ActionIconButton(
                        icon='delete',
                        text='Delete',
                        on_release=self.delete_files
                    ),
                    reload_list_button
                    := ActionIconButton(
                        icon='sync',
                        text='Reload',
                        on_release=self.reload_list
                    ),
                    rebuild_archive_button
                    := ActionIconButton(
                        icon='pickaxe',
                        text='Rebuild',
                        on_release=self.rebuild_archive
                    ),
                ),

                set_theme_button
                := ThemeLightbulb(
                    icon='lightbulb-outline',
                    on_release=self.set_theme,
                    pos_hint={'center_y': .5}
                ),

                size_hint_y=.1,
                padding=(48, 0, 0, 0)
            ),

            MDBoxLayout(
                self.archive_data_view,
                self.archive_info_view,
                size_hint_y=.85
            ),

            orientation='vertical'
        )

        self.add_files_button = add_files_button.button
        self.extract_files_button = extract_files_button.button
        self.delete_files_button = delete_files_button.button
        self.reload_list_button = reload_list_button.button
        self.rebuild_archive_button = rebuild_archive_button.button
        self.set_theme_button = set_theme_button

        return layout

    @mainthread
    def retitle(self):
        title_parts = [self.TITLE]
        if self._version_verdict:
            title_parts.append(f'[{self._version_verdict}]')
        if self.open_archive_filename:
            title_parts.append(f'({self.open_archive_filename})')
        self.title = ' '.join(title_parts)

    def set_version_checked_title(self):
        self._version_verdict = version_check_message()
        self.retitle()

    def on_start(self):
        self.title = self.TITLE
        Thread(target=self.set_version_checked_title).start()
        Window.size = (1000, 500)
        Window.minimum_width = 790
        Window.minimum_height = 500
        Window.bind(on_key_down=self.on_hotkeys)
        self.auto_theme = True
        self.open_archive()

    def on_hotkeys(self, window: WindowBase, keycode: int, key_pos: int, text: str, modifiers: list):
        del window, key_pos, text
        if 'ctrl' in modifiers:
            match keycode:
                case 111:  # O
                    self.open_new_file()
                case 97:  # A
                    if 'shift' in modifiers:
                        self.archive_data_view.select_all()
                    else:
                        self.add_files(self.add_files_button)
                case 101:  # E
                    self.extract_files(self.extract_files_button)
                case 100:  # D
                    self.delete_files(self.delete_files_button)
                case 114:  # R
                    if 'shift' in modifiers:
                        self.rebuild_archive(self.rebuild_archive_button)
                    else:
                        self.reload_list(self.reload_list_button)
                case 108:  # L
                    self.set_theme()
        else:
            match keycode:
                case 283:  # F2
                    self.open_new_file()
                case 284:  # F3
                    self.extract_files(self.extract_files_button)
                case 285:  # F4
                    self.delete_files(self.delete_files_button)
                case 286:  # F5
                    self.reload_list(self.reload_list_button)
                case 287:  # F6
                    self.rebuild_archive(self.rebuild_archive_button)
                case 288:  # F7
                    self.set_theme()

    def open_archive(self):
        self._opened_archive = IMGArchive(self.open_archive_filename)
        self.reload_views()

    @mainthread
    def reload_views(self):
        open_header, archive_info, archive_files = self._opened_archive.list()
        self.log_view.set_log(open_header)
        self.opened_info_view.set_log(archive_info)
        self.archive_data_view.update_data(archive_files)

    open_archive_filename = StringProperty('')
    _opened_archive = ObjectProperty()

    def open_new_file(self, _=None):
        if filename := askopenfilename(
                filetypes=(
                        ('Image & Headers File', '*.img;*.dir'),
                        ('Image File', '*.img'),
                        ('Headers File', '*.dir'),
                        ('Any', '*')
                )):
            self.open_archive_filename = filename
            self.open_archive()
        self.retitle()

    @_act_button_process
    def reload_list(self):
        self.reload_views()

    @_act_button_process
    def add_files(self):
        filenames = askopenfilenames(filetypes=(
            ('RenderWare TeXture Dictionary & Model File', '*.txd;*.dff'),
            ('Any', '*')
        ))
        if not filenames:
            return
        cwd = os.getcwd()
        for filename in self.progress_loop(filenames):
            try:
                result = self._opened_archive.add(os.path.relpath(filename, cwd))
            except ValueError:
                os.chdir(os.path.dirname(filename))
                result = self._opened_archive.add(os.path.basename(filename))
                os.chdir(cwd)
            self.log_view.set_log(result)
        self.reload_views()

    @_act_button_process
    def delete_files(self):
        if not self.archive_data_view.selected_filenames:
            toast_mainthread("You didn't choose anything.")
            return
        for filename in self.progress_loop(self.archive_data_view.selected_filenames.copy()):
            header = self._opened_archive.delete(filename)
            self.log_view.set_log(header)
        self.reload_views()

    @_act_button_process
    def extract_files(self):
        if not self.archive_data_view.selected_filenames:
            toast_mainthread("You didn't choose anything.")
            return
        my_dir = f'{self._opened_archive.imgname}_archive'
        os.makedirs(my_dir, exist_ok=True)
        save_dir = askdirectory(initialdir=my_dir)
        if not save_dir:
            return
        for filename in self.progress_loop(self.archive_data_view.selected_filenames.copy()):
            header = self._opened_archive.extract(filename, os.path.join(save_dir, filename))
            self.log_view.set_log(header)

    def _rename_file(self, filename: str, filename2: str):
        self.log_view.set_log(
            self._opened_archive.rename(filename, filename2)
        )
        self.reload_views()

    def rename_file(self, button: BaseButton):
        name = button.text
        askstring(title=f'Rename {name}',
                  prompt='New name',
                  initialvalue=name,
                  on_validate=partial(self._rename_file, name))

    @_act_button_process
    def rebuild_archive(self):
        _, header, executor = self._opened_archive.rebuild()
        header = self.log_view.form_string(header)
        for name, progress in executor:
            self.progress_bar.value = self._get_rebuild_progress(progress)
            self.log_view.set_text_mainthread(f'{header}\n\n{name}: {progress}')

    @staticmethod
    def _get_rebuild_progress(progress_line: str):
        i, m = (*(*progress_line.split(), '')[0].split('/'), '')[:2]
        try:
            return int(i) / int(m) * 100.
        except (ValueError, TypeError):
            return 100.

    def progress_loop(self, iters, length: int = None):
        if length is None:
            length = len(iters) if isinstance(iters, Sized) else 100
        for i, v in enumerate(iters, 1):
            self.progress_bar.value = i / length * 100.
            yield v

    def set_theme(self, button: ThemeLightbulb = None):
        if button is None:
            button = self.set_theme_button
        is_light, is_auto = button.get_theme()
        new_icon = 'lightbulb'
        theme = 'Light'
        if not (is_light or is_auto):
            self.auto_theme = True
            return
        if is_auto:
            self.auto_theme = False
            new_icon += '-outline'
        elif is_light:
            theme = 'Dark'
        button.icon = new_icon
        self.theme_cls.theme_style = theme

    def _auto_theme_changer(self, _):
        new_theme = darkdetect.theme()
        it_light = new_theme == 'Light'
        is_light = self.set_theme_button.get_theme()[0]
        if is_light ^ it_light:
            self.theme_cls.theme_style = new_theme
            self.set_theme_button.icon = 'lightbulb-auto'
            if it_light:
                self.set_theme_button.icon += '-outline'

    _theme_auto = BooleanProperty(False)

    def _auto_theme_get(self):
        return self._theme_auto

    def _auto_theme_set(self, value):
        self._theme_auto = value
        if self._theme_auto:
            new_theme = darkdetect.theme()
            it_light = new_theme == 'Light'
            self.theme_cls.theme_style = new_theme
            self.set_theme_button.icon = 'lightbulb-auto'
            if it_light:
                self.set_theme_button.icon += '-outline'
            Clock.schedule_interval(self._auto_theme_changer, 1.)
            return
        Clock.unschedule(self._auto_theme_changer)

    auto_theme = AliasProperty(_auto_theme_get, _auto_theme_set)


def run():
    if hasattr(sys, '_MEIPASS'):
        resource_add_path(os.path.join(sys._MEIPASS))
    UniversalIMGApp(
        open_archive_filename=sys.argv[-1] if len(sys.argv) > 1 else ''
    ).run()
