import setuptools

import pyimgedit

with open('version.txt', 'w') as f:
    f.write('.'.join(str(i) for i in pyimgedit.__version__))
with open('README.md', encoding='UTF-8') as f:
    readme = f.read()

with open('requirements.txt', encoding='UTF-8') as f:
    requires = f.read().strip().splitlines()
with open('requirements_gui.txt', encoding='UTF-8') as f:
    requires_gui = f.read().strip().splitlines()

extras_require = {'gui': requires_gui, 'all': requires + requires_gui}

setuptools.setup(
    name="UniversalIMG",
    version='.'.join(map(str, pyimgedit.__version__)),

    description="Open & edit .img files for gta III / VC / SA (+GUI)",

    long_description=readme,
    long_description_content_type="text/markdown",

    author="Nikita (NIKDISSV)",

    install_requires=requires,
    extras_require=extras_require,
    data_files=[('pyimgedit', ['pyimgedit/icon.png', 'pyimgedit/freimgedcs.exe'])],

    author_email='nikdissv@proton.me',

    packages=setuptools.find_packages(),
    license='MIT',
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Desktop Environment',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.10'
    ]
)
