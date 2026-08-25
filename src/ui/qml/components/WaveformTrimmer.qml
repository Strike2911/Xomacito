import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property url waveformSource: ""
    property bool busy: false
    property string errorText: ""
    property real duration: 0
    property real from: 0
    property real to: duration
    property real inPoint: 0
    property real outPoint: duration
    property bool compact: false
    signal inPointMoved(real value)
    signal outPointMoved(real value)
    signal retryRequested()

    implicitHeight: root.compact ? 142 : 174

    function clock(seconds) {
        var total = Math.max(0, Number(seconds) || 0)
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        var secs = Math.floor(total % 60)
        return (hours < 10 ? "0" : "") + hours + ":" +
               (minutes < 10 ? "0" : "") + minutes + ":" +
               (secs < 10 ? "0" : "") + secs
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: root.compact ? 5 : 7

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "FORMA DE ONDA"
                color: theme.colors.textDim
                font.pixelSize: 9
                font.weight: Font.Bold
                font.letterSpacing: 1
            }
            Text {
                Layout.fillWidth: true
                text: "Las zonas planas indican silencio"
                color: theme.colors.textMuted
                font.pixelSize: 9
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: waveArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: root.compact ? 82 : 104
            radius: 11
            color: "#090B12"
            border.color: theme.colors.border
            clip: true

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width
                height: 1
                color: "#34405C"
                opacity: 0.7
            }
            Image {
                anchors.fill: parent
                anchors.margins: 7
                source: root.waveformSource
                visible: status === Image.Ready
                fillMode: Image.Stretch
                asynchronous: true
                cache: true
                opacity: 0.92
            }
            Rectangle {
                x: 0
                width: trimRange.leftPadding + trimRange.first.visualPosition * trimRange.availableWidth
                height: parent.height
                color: "#B0090B12"
            }
            Rectangle {
                x: trimRange.leftPadding + trimRange.second.visualPosition * trimRange.availableWidth
                width: parent.width - x
                height: parent.height
                color: "#B0090B12"
            }
            Rectangle {
                x: trimRange.leftPadding + trimRange.first.visualPosition * trimRange.availableWidth
                width: Math.max(1, (trimRange.second.visualPosition - trimRange.first.visualPosition) * trimRange.availableWidth)
                height: parent.height
                color: "transparent"
                border.color: "#7D77E8"
                border.width: 1
                opacity: 0.78
            }

            Column {
                anchors.centerIn: parent
                visible: !root.waveformSource || root.busy || Boolean(root.errorText)
                spacing: 4
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.busy ? "Generando forma de onda…" : root.errorText ? "Forma de onda no disponible" : "Preparando audio…"
                    color: theme.colors.textMuted
                    font.pixelSize: 10
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: Boolean(root.errorText)
                    text: "Reintentar"
                    color: theme.colors.primary
                    font.pixelSize: 9
                    font.underline: retryMouse.containsMouse
                    MouseArea { id: retryMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.retryRequested() }
                }
            }

            RangeSlider {
                id: trimRange
                anchors.fill: parent
                anchors.leftMargin: 3
                anchors.rightMargin: 3
                from: root.from
                to: Math.max(0.05, root.to)
                stepSize: root.duration > 120 ? 0.25 : 0.05
                snapMode: RangeSlider.SnapOnRelease
                first.value: Math.max(from, Math.min(to, root.inPoint))
                second.value: Math.max(first.value + 0.05, Math.min(to, root.outPoint))
                first.onMoved: root.inPointMoved(first.value)
                second.onMoved: root.outPointMoved(second.value)
                background: Item {}
                first.handle: Rectangle {
                    x: trimRange.leftPadding + trimRange.first.visualPosition * (trimRange.availableWidth - width)
                    y: trimRange.topPadding + trimRange.availableHeight / 2 - height / 2
                    width: 24; height: 32; radius: 8
                    color: trimRange.first.pressed ? "#A7A2FF" : "#F0F1FA"
                    border.color: "#6E68D8"; border.width: 3
                    Rectangle { anchors.centerIn: parent; width: 2; height: 13; radius: 1; color: "#4E4A93" }
                }
                second.handle: Rectangle {
                    x: trimRange.leftPadding + trimRange.second.visualPosition * (trimRange.availableWidth - width)
                    y: trimRange.topPadding + trimRange.availableHeight / 2 - height / 2
                    width: 24; height: 32; radius: 8
                    color: trimRange.second.pressed ? "#A7A2FF" : "#F0F1FA"
                    border.color: "#6E68D8"; border.width: 3
                    Rectangle { anchors.centerIn: parent; width: 2; height: 13; radius: 1; color: "#4E4A93" }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: (root.compact ? "IN  " : "ENTRADA  ") + root.clock(root.inPoint); color: theme.colors.text; font.pixelSize: 10; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Rectangle {
                implicitWidth: fragmentText.implicitWidth + 18
                implicitHeight: 24
                radius: 12
                color: theme.colors.surfaceSoft
                border.color: theme.colors.border
                Text { id: fragmentText; anchors.centerIn: parent; text: "FRAGMENTO  " + root.clock(Math.max(0, root.outPoint - root.inPoint)); color: theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.DemiBold }
            }
            Item { Layout.fillWidth: true }
            Text { text: (root.compact ? "OUT  " : "SALIDA  ") + root.clock(root.outPoint); color: theme.colors.text; font.pixelSize: 10; font.weight: Font.DemiBold }
        }
    }
}
