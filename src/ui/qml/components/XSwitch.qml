import QtQuick
import QtQuick.Controls

Switch {
    id: root
    implicitHeight: 32
    spacing: 10
    focusPolicy: Qt.StrongFocus
    indicator: Rectangle {
        implicitWidth: 42
        implicitHeight: 24
        x: root.leftPadding
        y: parent.height / 2 - height / 2
        radius: 12
        color: root.checked ? theme.colors.primary : theme.colors.surfaceSoft
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? theme.colors.accent : root.checked ? theme.colors.primary : theme.colors.border
        Rectangle {
            x: root.checked ? parent.width - width - 4 : 4
            anchors.verticalCenter: parent.verticalCenter
            width: 16; height: 16; radius: 8
            color: "white"
            Behavior on x { NumberAnimation { duration: settingsController.state.animationsEnabled ? 150 : 0; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: Text {
        leftPadding: root.indicator.width + root.spacing
        text: root.text
        color: root.enabled ? theme.colors.text : theme.colors.textDim
        font.pixelSize: 12
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
    }
}
