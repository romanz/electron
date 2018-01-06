// Copyright (c) 2018, Neil Booth
//
// All rights reserved.
//
// See the file "LICENCE" for information about the copyright
// and warranty status of this software.

import QtQuick 2.9
import QtQuick.Window 2.2
import QtQuick.Controls 1.4

ApplicationWindow {
    title: "Electron Cash"
    width: 640
    height: 480
    color: "#00000000"
    opacity: 1
    visible: true

    menuBar: MenuBar {
        Menu {
            title: qsTr("&Wallet")
            MenuItem {
                text: qsTr("New")
                shortcut: "Ctrl+N"
                onTriggered: console.log("New action triggered");
            }
        }
    }

    Button {
        text: qsTr("Hello World")
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
    }
}
