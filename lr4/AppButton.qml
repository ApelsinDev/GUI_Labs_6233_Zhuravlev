import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: control
    property bool accent: false
    implicitHeight: 42
    implicitWidth: Math.max(100, contentItem.implicitWidth + 32)
    hoverEnabled: true
    padding: 12
    font.family: "Segoe UI"
    font.pixelSize: 14
    font.weight: Font.DemiBold
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? (control.accent ? "#111111" : "#ffffff") : "#6c6c6c"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 9
        color: control.accent ? (control.down ? "#e7650c" : "#ff791e")
                              : (control.hovered ? "#333333" : "#242424")
        border.color: control.visualFocus ? "#ff791e" : (control.accent ? color : "#414141")
        border.width: control.visualFocus ? 2 : 1
    }
}
