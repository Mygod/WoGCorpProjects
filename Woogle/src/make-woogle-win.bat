@echo off
path m:\shared\python26
python setupconsole.py py2exe
cd dist
move /y wogeditor.exe wogeditor-debug.exe
cd ..
python setup.py py2exe
pause
