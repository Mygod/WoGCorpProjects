rem Embed image in python file
@echo Generating source embedded images
pyrcc4 -o goomov_rc.py goomov_rc.qrc
call pyuic4.bat -o movview_ui_test.py  movview_ui_test.ui
