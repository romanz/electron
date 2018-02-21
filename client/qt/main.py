# Copyright (c) 2018, Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

import os
import sys

from PyQt5.Qt import Qt
import PyQt5.QtCore as QtCore
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtQml import QQmlApplicationEngine


class QtGUI(object):

    def __init__(self, app):
        self.app = app

        #if app.system == 'Windows':
        #    QtCore.QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

        self.qt_app = QGuiApplication(sys.argv)

    def relative_path(self, path):
        return os.path.join(os.path.dirname(__file__), path)

    def run(self):
        engine = QQmlApplicationEngine()
        engine.load(self.relative_path('main.qml'))

        return self.qt_app.exec_()
