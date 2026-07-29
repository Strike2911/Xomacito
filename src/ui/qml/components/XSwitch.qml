import QtQuick
import QtQuick.Controls

Switch {
    id: root
    property bool compact: false
    implicitHeight: compact ? 28 : 32
    spacing: compact ? 8 : 10
    focusPolicy: Qt.StrongFocus
    indicator: Rectangle {
        implicitWidth: root.compact ? 38 : 42
        implicitHeight: root.compact ? 22 : 24
        x: root.leftPadding
        y: parent.height / 2 - height / 2
        radius: height / 2
        color: root.checked ? theme.colors.primary : theme.colors.surfaceSoft
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? theme.colors.accent : root.checked ? theme.colors.primary : theme.colors.border
        Rectangle {
            x: root.checked ? parent.width - width - 3 : 3
            anchors.verticalCenter: parent.verticalCenter
            width: root.compact ? 16 : 16
            height: width
            radius: width / 2
            color: "white"
            Behavior on x { NumberAnimation { duration: settingsController.state.animationsEnabled ? 150 : 0; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: Text {
        leftPadding: root.indicator.width + root.spacing
        text: root.text
        color: root.enabled ? theme.colors.text : theme.colors.textDim
        font.pixelSize: root.compact ? 11 : 12
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
    }
}
