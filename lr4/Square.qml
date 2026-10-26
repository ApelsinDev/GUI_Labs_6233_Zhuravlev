import QtQuick 2.15

// Компонент выбора цвета из исходного каркаса.
Rectangle {
    id: root
    property bool active: false
    signal clicked()
    width: 32
    height: 32
    radius: 8
    border.width: active ? 3 : 1
    border.color: active ? "#ffffff" : "#666666"
    scale: active ? 1.08 : 1
    Accessible.role: Accessible.Button
    Accessible.name: "Цвет " + color
    activeFocusOnTab: true
    Keys.onSpacePressed: clicked()
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    Behavior on scale { NumberAnimation { duration: 100 } }
}
