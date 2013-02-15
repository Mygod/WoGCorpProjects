# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'editballdialog.ui'
#
# Created: Wed Sep 08 21:56:43 2010
#      by: PyQt4 UI code generator 4.7.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_EditBallDialog(object):
    def setupUi(self, EditBallDialog, all, original):
        EditBallDialog.setObjectName("EditBallDialog")
        EditBallDialog.resize(400, 345)
        EditBallDialog.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.verticalLayout = QtGui.QVBoxLayout(EditBallDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtGui.QLabel(EditBallDialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.comboBox = QtGui.QComboBox(EditBallDialog)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.horizontalLayout.addWidget(self.comboBox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.ballList = QtGui.QListWidget(EditBallDialog)
        self.ballList.setObjectName("ballList")
        self.verticalLayout.addWidget(self.ballList)
        self.buttonBox = QtGui.QDialogButtonBox(EditBallDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)
        self.all = all
        self.original = original

        self.retranslateUi(EditBallDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), EditBallDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), EditBallDialog.reject)
        QtCore.QObject.connect(self.ballList, QtCore.SIGNAL("itemDoubleClicked(QListWidgetItem*)"), EditBallDialog.accept)
        QtCore.QObject.connect(self.comboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.comboSelectionChanged)
        QtCore.QMetaObject.connectSlotsByName(EditBallDialog)

        settings = QtCore.QSettings()
        settings.beginGroup( "MainWindow" )
        ball_filter =  settings.value( "ball_filter", 0 ).toInt()
        settings.endGroup()
        if ball_filter[0]==0:
            self.comboSelectionChanged(0)
        else:
            self.comboBox.setCurrentIndex(ball_filter[0])


    def retranslateUi(self, EditBallDialog):
        EditBallDialog.setWindowTitle(QtGui.QApplication.translate("EditBallDialog", "Select Goo Ball to edit...", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("EditBallDialog", "Select Goo Ball to edit:", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox.setItemText(0, QtGui.QApplication.translate("EditBallDialog", "All Goo Balls", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox.setItemText(1, QtGui.QApplication.translate("EditBallDialog", "Custom Balls Only", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox.setItemText(2, QtGui.QApplication.translate("EditBallDialog", "Original Balls Only", None, QtGui.QApplication.UnicodeUTF8))

    def comboSelectionChanged(self,index):
        self.ballList.clear()
        if index == 0:
            #All
          for ball in sorted(self.all,key=str.lower):
            self.ballList.addItem( ball )
        elif index == 1:
            #Custom
            custom_balls = sorted(self.all - self.original,key=str.lower)
            for ball in custom_balls:
              self.ballList.addItem( ball )
        elif index == 2:
            #Original
          for ball in sorted(self.original,key=str.lower):
            self.ballList.addItem( ball )

        else:
            print "unknown Combo Index",index
