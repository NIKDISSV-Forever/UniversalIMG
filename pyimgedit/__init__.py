from __future__ import annotations

import logging
import os
import os.path
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlretrieve

from html_table_parser.parser import HTMLTableParser

__author__ = 'NIKDISSV'
__licence__ = 'MIT'
__version__ = (1, 2, 2)

try:
    it_file = __file__
except NameError:
    it_file = sys.argv[0]

PACKAGE_DIR = Path(it_file).parent
EXECUTABLE_DOWNLOAD_URLS = (
    'https://github.com/NIKDISSV-Forever/UniversalIMG/blob/main/pyimgedit/freimgedcs.exe?raw=true',

    # https://code.google.com/archive/p/freimgedcs
    'https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/freimgedcs/freimgedcs.exe',
)


def get_freimgedcs_exe() -> str:
    """Returns the path to freimgedcs.exe. If it doesn't exist then download it and return it"""
    status, fp = subprocess.getstatusoutput('where freimgedcs')
    if not status:
        return fp
    save_path = PACKAGE_DIR / 'freimgedcs.exe'
    if save_path.is_file():
        return str(save_path)
    for url in EXECUTABLE_DOWNLOAD_URLS:
        try:
            return urlretrieve(url, save_path)[0]
        except HTTPError:
            pass


def bytes2units(bytes_size: float) -> str:
    prefixes = ('', *'kMGTPEZY')
    for p in prefixes[:-1]:
        if abs(bytes_size) < 1000.:
            return f'{bytes_size:,.0f}{p}B'
        bytes_size /= 1000.
    return f'{bytes_size:,.0f}{prefixes[-1]}B'


class BlocksBytes:
    """Class for storing Block/Size format data present in the html file generated by the -lst command"""
    __slots__ = ('__blocks', '__bytes', '__as_str')
    __match_args__ = ('blocks', 'bytes')

    def __init__(self, bb: str):
        blocks, bytes = bb.split('/', 1)
        self.__blocks = int(blocks)
        self.__bytes = int(bytes)
        self.__as_str = self.get_string()

    @property
    def blocks(self) -> int:
        return self.__blocks

    @property
    def bytes(self) -> int:
        return self.__bytes

    @blocks.setter
    def blocks(self, value):
        self.__blocks = int(value)
        self.__as_str = self.get_string()

    @bytes.setter
    def bytes(self, value):
        self.__bytes = int(value)
        self.__as_str = self.get_string()

    def __str__(self):
        return self.__as_str

    def __lt__(self, other):
        return self.blocks < other.blocks

    def get_string(self) -> str:
        return f'{self.__blocks:,} / {bytes2units(self.__bytes)}'


class ArchiveContent:
    """Stores one line data from the generated html file"""
    __slots__ = ('offset', 'size', 'name')

    def __init__(self, offset: str, size: str, name: str):
        self.offset = BlocksBytes(offset)
        self.size = BlocksBytes(size)
        self.name = name

    def __repr__(self) -> str:
        return f'<{self.name!r} ({self.size}) {self.offset}>'


class IMGArchive:
    """API for freimgedcs.exe"""
    DATA_TEMPLATE = re.compile(r'>\s*([\w\s]+?)\s+\.+\s+(.+)')

    def __init__(self, imgname: str | Path,
                 freimgedcs_path: str = get_freimgedcs_exe()):
        self.imgname = Path(imgname)
        self.executable = freimgedcs_path

    def _call(self, key: str, imgname: str | Path, filename: str = '', filename2: str = ''):
        cwd = os.getcwd()
        parent = None
        try:
            os.chdir(parent := imgname.parent)
            imgname = imgname.name
        except OSError:
            pass
        command = [self.executable, f'-{key}', imgname]
        if filename:
            command.append(self._rel_fn(filename, parent))
        if filename2:
            command.append(self._rel_fn(filename2, parent))
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, text=True, shell=True)
        yield proc
        while True:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    break
                yield line
            else:
                break
        os.chdir(cwd)

    @staticmethod
    def _rel_fn(fn: str, parent: Path) -> str:
        try:
            return str(Path(fn).relative_to(parent))
        except ValueError:
            return fn

    def call(self, key: str, filename: str = '', filename2: str = ''):
        processor = self._call(key, self.imgname, filename, filename2)
        yield next(processor)
        for line in processor:
            if not line:
                break
            matches = self.DATA_TEMPLATE.fullmatch(line)
            if not matches:
                continue
            yield matches.groups()  # yield updates (key, value)

    def check_call(self, key: str, filename: str = '', filename2: str = '', to_end: bool = True):
        header = {}
        proc = self.call(key, filename, filename2)
        process = next(proc)
        if to_end:
            process.wait()
            for k, v in proc:
                header[k] = v
        else:
            for (k, v), _ in zip(proc, (None,) * 5):
                header[k] = v
        if to_end:
            return header
        return process, header, proc

    def rebuild(self):
        """Rebuild archive (imgname)"""
        return self.check_call('rbd', to_end=False)

    def _list(self, *, delete_html_file: bool = False):
        header = self.check_call('lst')
        p = HTMLTableParser()
        html_file = f'{self.imgname}.html'
        if not os.path.isfile(html_file):
            archive_info = (('File name', str(self.imgname)),)
            if os.path.isfile(self.imgname):
                archive_info += ('File size', f'{bytes2units(os.stat(self.imgname).st_size)}'),
            return header, archive_info, (('Offset (in blocks / bytes)', 'Size (in blocks / bytes)', 'Name'),)

        with open(html_file) as table_file:
            p.feed(table_file.read())
        if delete_html_file:
            os.remove(html_file)
        information_about_img_archive, contents = [*p.tables, [], []][:2]
        information_about_img_archive = dict(information_about_img_archive)
        if 'File name' not in information_about_img_archive:
            information_about_img_archive['File name'] = str(self.imgname)
        if 'File size' not in information_about_img_archive and os.path.isfile(self.imgname):
            information_about_img_archive['File size'] = f'{bytes2units(os.stat(self.imgname).st_size)}'

        for k, v in information_about_img_archive.copy().items():
            if v.endswith('bytes'):
                v = v.removesuffix('bytes').strip()
                if v.isdigit():
                    information_about_img_archive[k] = bytes2units(int(v))
        return header, information_about_img_archive, contents

    def list(self, *, delete_html_file: bool = False):
        """
        Returns the header of the opened archive, information about it, and a list of files of the class ArchiveContent
        """
        header, info, files = self._list(delete_html_file=delete_html_file)
        return header, info, [ArchiveContent(offset, size, name) for offset, size, name in files[1:]]

    def add(self, filename: str):
        """Add/replace file [filename] to/in archive (imgname)"""
        return self.check_call('add', filename)

    def extract(self, filename: str, filename2: str):
        """Extract file [filename] from archive (imgname) to file [filename2]"""
        return self.check_call('xtr', filename, filename2)

    def rename(self, filename: str, filename2: str):
        """Rename file [filename] in archive (imgname) to file [filename2]"""
        return self.check_call('rnm', filename, filename2)

    def delete(self, filename: str):
        """Delete file [filename] from archive (imgname)"""
        return self.check_call('del', filename)


class StreamHandler(logging.StreamHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.stream is None:
            from io import StringIO
            self.stream = StringIO()


logging.StreamHandler = StreamHandler  # fix for PyInstaller
