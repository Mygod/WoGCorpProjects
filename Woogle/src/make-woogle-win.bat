@echo off
python setupconsole.py py2exe
cd dist
move /y wogeditor.exe wogeditor-debug.exe
cd ..
python setup.py py2exe
pause
