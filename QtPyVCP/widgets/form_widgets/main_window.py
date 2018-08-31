#!/usr/bin/env python
# coding: utf-8

#   Copyright (c) 2018 Kurt Jacobson
#      <kurtcjacobson@gmail.com>
#
#   This file is part of QtPyVCP.
#
#   QtPyVCP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   QtPyVCP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with QtPyVCP.  If not, see <http://www.gnu.org/licenses/>.


import os
import sys
import time

from PyQt5 import uic
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt, pyqtSlot, pyqtProperty, QTimer
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QPushButton,
    QAction, QMessageBox, QFileDialog, QMenu, QLineEdit, QShortcut, qApp)

from QtPyVCP.utilities import logger
LOG = logger.getLogger(__name__)

from QtPyVCP.widgets.dialogs.open_file_dialog import OpenFileDialog

class VCPMainWindow(QMainWindow):

    def __init__(self, parent=None, ui_file=None, size=None, position=None,
            hide_menu_bar=False, hide_status_bar=False, maximize=False, fullscreen=False):
        super(VCPMainWindow, self).__init__(parent=None)
        self.app = QApplication.instance()

        # QtDesigner settable vars
        self.prompt_at_exit = True

        # Variables
        self.recent_file_actions = []
        self.log_file_path = ''
        self.actions = []
        self.open_file_dialog = OpenFileDialog(self)

        # Load the UI file AFTER defining variables, otherwise the values
        # set in QtDesigner get overridden by the default values
        if ui_file is not None:
            uic.loadUi(ui_file, self)

        self.app.status.init_ui.emit()
        self.initUi()

        # QShortcut(QKeySequence("t"), self, self.test)
        self.app.focusChanged.connect(self.focusChangedEvent)

    def initUi(self):
        from QtPyVCP.utilities import action
        print "initiating"
        self.loadSplashGcode()
        self.initRecentFileMenu()
        self.initHomingMenu()

        s = time.time()

        menus = self.findChildren(QMenu)
        for menu in menus:
            menu_actions = menu.actions()
            for menu_action in menu_actions:
                if menu_action.isSeparator():
                    continue
                data = menu_action.objectName().split('_', 2)
                if data[0] == "action" and len(data) > 1:
                    try:
                        action_class =  getattr(action, data[1])
                        action_instance = action_class(menu_action, action_type=data[2])
                        # print "ACTION: ", action_instance
                    except:
                        LOG.warn("Could not connect action", exc_info=True)
                        continue
                    self.actions.append(action_instance)

        print "action time ", time.time() - s

    @pyqtSlot()
    def on_power_clicked(self):
        action.Home.unhomeAxis('x')

    def closeEvent(self, event):
        """Catch close event and show confirmation dialog if set to"""
        if self.prompt_at_exit:
            quit_msg = "Are you sure you want to exit LinuxCNC?"
            reply = QMessageBox.question(self, 'Exit LinuxCNC?',
                             quit_msg, QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def keyPressEvent(self, event):
        # super(VCPMainWindow, self).keyPressEvent(event)
        if event.isAutoRepeat():
            return

        if event.key() == Qt.Key_Up:
            action.Jogging.autoJog('Y', 1)
        elif event.key() == Qt.Key_Down:
            action.Jogging.autoJog('Y', -1)
        elif event.key() == Qt.Key_Left:
            action.Jogging.autoJog('X', -1)
        elif event.key() == Qt.Key_Right:
            action.Jogging.autoJog('X', 1)
        elif event.key() == Qt.Key_PageUp:
            action.Jogging.autoJog('Z', 1)
        elif event.key() == Qt.Key_PageDown:
            action.Jogging.autoJog('Z', -1)
        else:
            print 'Unhandled key press event'

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        if event.key() == Qt.Key_Up:
            action.Jogging.autoJog('Y', 0)
        elif event.key() == Qt.Key_Down:
            action.Jogging.autoJog('Y', 0)
        elif event.key() == Qt.Key_Left:
            action.Jogging.autoJog('X', 0)
        elif event.key() == Qt.Key_Right:
            action.Jogging.autoJog('X', 0)
        elif event.key() == Qt.Key_PageUp:
            action.Jogging.autoJog('Z', 0)
        elif event.key() == Qt.Key_PageDown:
            action.Jogging.autoJog('Z', 0)
        else:
            print 'Unhandled key release event'


    def mousePressEvent(self, event):
        print 'Button press'
        focused_widget = self.focusWidget()
        if focused_widget is not None:
            focused_widget.clearFocus()

    def focusChangedEvent(self, old_w, new_w):
        if issubclass(new_w.__class__, QLineEdit):
            print "QLineEdit got focus: ", new_w

#==============================================================================
#  menu action slots
#==============================================================================

    # File menu

    @pyqtSlot()
    def on_actionOpen_triggered(self):
        self.open_file_dialog.show()

    @pyqtSlot()
    def on_actionExit_triggered(self):
        self.close()

    #==========================================================================
    # Machine menu
    #==========================================================================

    @pyqtSlot()
    def on_actionToggle_E_stop_triggered(self):
        self.app.action.toggleEmergencyStop()

    @pyqtSlot()
    def on_actionToggle_Power_triggered(self):
        self.app.action.toggleMachinePower()

    @pyqtSlot()
    def on_actionRun_Program_triggered(self):
        self.app.action.runProgram()

    @pyqtSlot()
    def on_actionHome_All_triggered(self):
        self.app.action.homeJoint(-1)

    @pyqtSlot()
    def on_actionHome_X_triggered(self):
        self.app.action.homeJoint(1)

    @pyqtSlot(bool)
    def on_actionReport_Actual_Position_toggled(self, report_actual):
        self.app.status.setReportActualPosition(report_actual)


#==============================================================================
# menu functions
#==============================================================================

    def initRecentFileMenu(self):
        if hasattr(self, 'menuRecentFiles'):

            # remove any actions that were added in QtDesigner
            for action in self.menuRecentFiles.actions():
                self.menuRecentFiles.removeAction(action)

            # add new actions
            for i in range(self.app.status.max_recent_files):
                action = QAction(self, visible=False,
                                 triggered=(lambda:self.app.action.loadProgram(self.sender().data())))
                self.recent_file_actions.append(action)
                self.menuRecentFiles.addAction(action)

            self.updateRecentFilesMenu(self.app.status.recent_files)
            self.app.status.recent_files_changed.connect(self.updateRecentFilesMenu)

    def updateRecentFilesMenu(self, recent_files):
        for i, fname in enumerate(recent_files):
            fname = fname.encode('utf-8')
            text = "&{} {}".format(i + 1, os.path.split(fname)[1])
            action = self.recent_file_actions[i]
            action.setText(text)
            action.setData(fname)
            action.setVisible(True)


    def initHomingMenu(self):
        if hasattr(self, 'menuHoming'):

            # remove any actions that were added in QtDesigner
            for menu_action in self.menuHoming.actions():
                self.menuHoming.removeAction(menu_action)

            # Register the submenu with the action (so it will be disabled
            # if the actions are not valid), but don't connect it to method
            home_action = action.Home(widget=self.menuHoming, method=None)

            menu_action = QAction(self)
            menu_action.setText("Home &All")
            home_action = action.Home(widget=menu_action, method='homeAll', axis='all')
            self.menuHoming.addAction(menu_action)

            # add homing actions for each axis
            for aletter in self.app.info.AXIS_LETTER_LIST:
                menu_action = QAction(self)
                menu_action.setText("Home &{}".format(aletter.upper()))
                home_action = action.Home(widget=menu_action, method='homeAxis', axis=aletter)
                self.menuHoming.addAction(menu_action)
                self.actions.append(menu_action)

#==============================================================================
# helper functions
#==============================================================================

    def loadSplashGcode(self):
        # Load backplot splash code
        if self.app.status.stat.file != '':
            QTimer.singleShot(0, self.app.status.reload_backplot.emit)
        else:
            path = os.path.realpath(os.path.join(__file__, '../../../..', 'sim/example_gcode/qtpyvcp.ngc'))
            splash_code = self.app.info.getOpenFile() or path
            if splash_code is not None:
                # Load after startup to not cause delay
                QTimer.singleShot(0, lambda: self.app.action.loadProgram(splash_code, add_to_recents=False))

#==============================================================================
#  QtDesigner property setters/getters
#==============================================================================

    # Whether to show a confirmation prompt when closing the main window
    def getPromptBeforeExit(self):
        return self.prompt_at_exit
    def setPromptBeforeExit(self, value):
        self.prompt_at_exit = value
    promptAtExit = pyqtProperty(bool, getPromptBeforeExit, setPromptBeforeExit)

    # Max number of recent files to display in menu
    def getMaxRecentFiles(self):
        return self.app.status.max_recent_files
    def setMaxRecentFiles(self, number):
        self.app.status.max_recent_files = number
    maxNumRecentFiles = pyqtProperty(int, getMaxRecentFiles, setMaxRecentFiles)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
