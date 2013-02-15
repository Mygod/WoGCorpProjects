from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import qthelper
import louie
import metaworld

class ResourceLibraryView(QtGui.QWidget):
   def __init__( self ):
        QtGui.QWidget.__init__( self )
#        self.window = window
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)

        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.lineEdit = QtGui.QLineEdit(self)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout.addWidget(self.lineEdit)
        self.pushButton = QtGui.QPushButton(self)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setText(QtGui.QApplication.translate("Form", "Search...", None, QtGui.QApplication.UnicodeUTF8))
        self.horizontalLayout.addWidget(self.pushButton)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.listWidget = QtGui.QListWidget(self)
        self.listWidget.setIconSize(QtCore.QSize(48, 48))
        self.listWidget.setViewMode(QtGui.QListView.IconMode)
        self.listWidget.setObjectName("listWidget")
        self.verticalLayout.addWidget(self.listWidget)

#        self.__world = world