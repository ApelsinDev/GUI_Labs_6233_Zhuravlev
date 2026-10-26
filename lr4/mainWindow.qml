import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Window {
    id: root
    visible: true
    width: 1180
    height: 820
    minimumWidth: 1080
    minimumHeight: 700
    color: "#111111"
    title: "Painter · Лабораторная работа 4"
    onClosing: close.accepted = _backend.confirmClose()

    Rectangle { anchors.fill: parent; color: "#111111" }

    Shortcut { sequence: "Ctrl+S"; onActivated: _backend.saveNow() }
    Shortcut { sequence: "Ctrl+Z"; onActivated: canvas.undo() }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 18

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Text {
                text: "Painter"
                color: "#ffffff"
                font.family: "Segoe UI"
                font.pixelSize: 32
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            AppButton {
                text: "Отменить"
                enabled: canvas.strokes.length > 0
                onClicked: canvas.undo()
                ToolTip.visible: hovered
                ToolTip.text: "Отменить последний штрих · Ctrl+Z"
            }
            AppButton {
                text: "Очистить"
                enabled: canvas.strokes.length > 0
                onClicked: clearDialog.open()
            }
            AppButton {
                text: "Сохранить PNG"
                accent: true
                onClicked: _backend.saveNow()
                ToolTip.visible: hovered
                ToolTip.text: "Сохранить рисунок в отдельный файл · Ctrl+S"
            }
        }

        Rectangle {
            id: tools
            objectName: "tools"
            property color paintColor: "#ff791e"
            property int thickness: 4
            Layout.fillWidth: true
            Layout.preferredHeight: 76
            color: "#202020"
            radius: 12
            RowLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10
                Repeater {
                    model: ["#161616", "#ff791e", "#33b5e5", "#87bb37", "#ee5263", "#9164db"]
                    Square {
                        objectName: "color_" + index
                        color: modelData
                        active: tools.paintColor === color
                        onClicked: tools.paintColor = color
                    }
                }
                Rectangle { Layout.leftMargin: 10; width: 1; height: 28; color: "#414141" }
                Text { text: "Кисть"; color: "#aaaaaa"; font.pixelSize: 13; Layout.leftMargin: 8 }
                Repeater {
                    model: [2, 4, 8, 12, 20]
                    Circle {
                        objectName: "brush_" + thickness
                        thickness: modelData
                        active: tools.thickness === thickness
                        onClicked: tools.thickness = thickness
                    }
                }
                Item { Layout.fillWidth: true; Layout.minimumWidth: 12 }
                CheckBox {
                    id: autoSwitch
                    objectName: "autoSwitch"
                    checked: _backend.autoSaveEnabled
                    onClicked: _backend.setAutoSaveEnabled(checked)
                    text: "Автосохранение"
                    spacing: 8
                    font.pixelSize: 13
                    indicator: Rectangle {
                        x: autoSwitch.leftPadding
                        y: (parent.height - height) / 2
                        width: 20; height: 20; radius: 5
                        color: autoSwitch.checked ? "#ff791e" : "#303030"
                        border.color: autoSwitch.visualFocus ? "#ffffff" : "#777777"
                        Text { anchors.centerIn: parent; text: autoSwitch.checked ? "✓" : ""; color: "#111111"; font.bold: true }
                    }
                    contentItem: Text {
                        text: autoSwitch.text
                        color: "#eeeeee"
                        font: autoSwitch.font
                        leftPadding: autoSwitch.indicator.width + autoSwitch.spacing
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                SpinBox {
                    id: interval
                    objectName: "interval"
                    Layout.preferredWidth: 110
                    Layout.preferredHeight: 36
                    from: 1; to: 300; value: _backend.intervalSeconds
                    editable: true
                    onValueModified: _backend.setIntervalSeconds(value)
                    ToolTip.visible: hovered
                    ToolTip.text: "Интервал автосохранения от 1 до 300 секунд"
                    font.pixelSize: 14
                    palette.text: "#ffffff"
                    palette.buttonText: "#ffffff"
                    palette.button: "#383838"
                    palette.base: "#303030"
                    palette.highlight: "#ff791e"
                }
                Text { text: "сек"; color: "#aaaaaa"; font.pixelSize: 13 }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#ffffff"
            radius: 12
            Canvas {
                id: canvas
                objectName: "canvas"
                anchors.fill: parent
                anchors.margins: 12
                renderTarget: Canvas.Image
                renderStrategy: Canvas.Immediate
                property var strokes: []
                property var currentStroke: null

                // Храним штрихи, чтобы перерисовка, сохранение и изменение размера
                // окна не стирали изображение. Координаты относительные (0..1).
                function beginStroke(x, y) {
                    currentStroke = { color: tools.paintColor.toString(), size: tools.thickness,
                                      points: [[x / width, y / height]] }
                    strokes = strokes.concat([currentStroke])
                    _backend.markDirty()
                    requestPaint()
                }
                function continueStroke(x, y) {
                    if (!currentStroke) return
                    var point = [Math.max(0, Math.min(1, x / width)),
                                 Math.max(0, Math.min(1, y / height))]
                    var last = currentStroke.points[currentStroke.points.length - 1]
                    if (point[0] === last[0] && point[1] === last[1]) return
                    currentStroke.points.push(point)
                    _backend.markDirty()
                    requestPaint()
                }
                function endStroke() { currentStroke = null }
                function undo() {
                    if (!strokes.length) return
                    currentStroke = null
                    strokes = strokes.slice(0, -1)
                    _backend.markDirty()
                    requestPaint()
                }
                function clearDrawing() {
                    currentStroke = null
                    strokes = []
                    _backend.markDirty()
                    requestPaint()
                }
                // Этот метод вызывает Python-класс Interface по своему QTimer
                // requestPaint() отложен: перед сохранением явно рисуем последние штрихи
                // Затем Canvas.save() записывает готовое изображение
                function saveToFile(filename) {
                    if (!available) return false
                    drawStrokes()
                    return save(filename)
                }
                onAvailableChanged: if (available) requestPaint()
                onWidthChanged: if (available) { requestPaint(); if (strokes.length) _backend.markDirty() }
                onHeightChanged: if (available) { requestPaint(); if (strokes.length) _backend.markDirty() }
                onPaint: drawStrokes()
                function drawStrokes() {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.fillStyle = "#ffffff"
                    ctx.fillRect(0, 0, width, height)
                    ctx.lineCap = "round"
                    ctx.lineJoin = "round"
                    for (var i = 0; i < strokes.length; ++i) {
                        var stroke = strokes[i]
                        var points = stroke.points
                        ctx.strokeStyle = stroke.color
                        ctx.fillStyle = stroke.color
                        ctx.lineWidth = stroke.size
                        ctx.beginPath()
                        if (points.length === 1) {
                            ctx.arc(points[0][0] * width, points[0][1] * height, stroke.size / 2, 0, 2 * Math.PI)
                            ctx.fill()
                        } else {
                            ctx.moveTo(points[0][0] * width, points[0][1] * height)
                            for (var j = 1; j < points.length; ++j)
                                ctx.lineTo(points[j][0] * width, points[j][1] * height)
                            ctx.stroke()
                        }
                    }
                }
                MouseArea {
                    id: paint_area
                    anchors.fill: parent
                    cursorShape: Qt.CrossCursor
                    acceptedButtons: Qt.LeftButton
                    onPressed: canvas.beginStroke(mouse.x, mouse.y)
                    onPositionChanged: if (pressed) canvas.continueStroke(mouse.x, mouse.y)
                    onReleased: { canvas.continueStroke(mouse.x, mouse.y); canvas.endStroke() }
                    onCanceled: canvas.endStroke()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            AppButton {
                text: "Папка сохранения"
                onClicked: _backend.chooseFolder()
            }
            Label {
                text: _backend.folderName
                Layout.maximumWidth: 240
                elide: Text.ElideMiddle
                color: "#999999"
                font.pixelSize: 13
                MouseArea { id: pathHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                ToolTip.visible: pathHover.containsMouse
                ToolTip.text: _backend.folder
            }
            Item { Layout.fillWidth: true }
            Rectangle { width: 7; height: 7; radius: 4; color: _backend.hasError ? "#ff6262" : (_backend.dirty ? "#ff791e" : "#a4a4a4") }
            Label {
                Layout.preferredWidth: Math.min(implicitWidth, 440)
                elide: Text.ElideRight
                text: _backend.status
                color: _backend.hasError ? "#ff8484" : "#b9b9b9"
                font.pixelSize: 13
                MouseArea { id: statusHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                ToolTip.visible: statusHover.containsMouse
                ToolTip.text: _backend.hasError ? _backend.status : (_backend.lastFile || "Изменения сохраняются по таймеру")
            }
        }
    }

    Dialog {
        id: clearDialog
        parent: root.contentItem
        anchors.centerIn: parent
        title: "Очистить холст?"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        Label { text: "Текущий рисунок будет удалён с холста." }
        onAccepted: canvas.clearDrawing()
    }
}
