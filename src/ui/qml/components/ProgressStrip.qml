import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

XCard {
    id: root
    property real value: 0
    property string status: ""
    property bool busy: false
    property bool compact: false
    implicitHeight: compact ? 48 : 68
    RowLayout {
        anchors.fill: parent
        anchors.margins: root.compact ? 9 : 14
        spacing: root.compact ? 9 : 14
        Rectangle {
            width: 8; height: 8; radius: 4
            color: root.busy ? theme.colors.accent : root.value >= 1 ? theme.colors.success : theme.colors.primary
            SequentialAnimation on opacity {
                running: root.busy && settingsController.state.animationsEnabled
                loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 520 }
                NumberAnimation { to: 1; duration: 520 }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: root.compact ? 4 : 8
            Text { text: root.status; color: theme.colors.text; font.pixelSize: root.compact ? 11 : 12; elide: Text.ElideRight; Layout.fillWidth: true }
            ProgressBar {
                Layout.fillWidth: true
                value: Math.max(0, root.value)
                indeterminate: root.value < 0
                background: Rectangle { implicitHeight: 5; radius: 3; color: theme.colors.surfaceSoft }
                contentItem: Item {
                    implicitHeight: 5
                    Rectangle { width: parent.width * Math.max(0, Math.min(1, root.value)); height: parent.height; radius: 3; color: theme.colors.primary; Behavior on width { NumberAnimation { duration: 180 } } }
                }
            }
        }
        Text { text: root.value >= 0 ? Math.round(root.value * 100) + "%" : "•••"; color: theme.colors.textMuted; font.pixelSize: 11 }
    }
}
