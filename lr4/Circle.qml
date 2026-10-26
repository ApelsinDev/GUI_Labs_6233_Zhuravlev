import QtQuick 2.15

// Компонент толщины кисти из исходного каркаса.
Rectangle {
    id: root
    property bool active: false
    property int thickness: 4
    property string text: thickness.toString()
    signal clicked()
    width: 32
    height: 32
    radius: width / 2
    color: active ? "#ff791e" : "#303030"
    border.color: active ? "#ff791e" : "#555555"
    Accessible.role: Accessible.Button
    Accessible.name: "Толщина кисти " + thickness
    activeFocusOnTab: true
    Keys.onSpacePressed: clicked()
    Text {
        anchors.centerIn: parent
        text: root.text
        color: root.active ? "#111111" : "#ffffff"
        font.family: "Segoe UI"
        font.pixelSize: 13
        font.bold: true
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
