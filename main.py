def main():
    import sys
    if hasattr(sys, '_MEIPASS'):  # PyInstaller
        import os
        os.environ['KIVY_PACKAGING'] = '1'
    from pyimgedit.gui import run
    run()


if __name__ == '__main__':
    main()
