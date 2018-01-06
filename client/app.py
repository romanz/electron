# Copyright (c) 2018, Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.


import platform

from .qt.main import QtGUI


class App(object):

    NAME = 'Electron Cash'
    VERSION = '0.001'

    def __init__(self):
        # 'Windows', 'Darwin' etc.
        self.system = platform.system()
        self.gui = QtGUI(self)

    def run(self):
        return self.gui.run()
