import QtQuick
import QtQuick.Controls

TextField {
    id: root
    property bool compact: false
    implicitHeight: compact ? 36 : 44
    leftPadding: compact ? 11 : 14
    rightPadding: compact ? 11 : 14
    color: theme.colors.text
    selectionColor: theme.colors.primary
    selectedTextColor: "white"
    placeholderTextColor: theme.colors.textDim
    font.pixelSize: compact ? 12 : 13
    focusPolicy: Qt.StrongFocus
    background: Rectangle {
        radius: root.compact ? 9 : 11
        color: theme.colors.surfaceSoft
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? theme.colors.primary : theme.colors.border
        Behavior on border.color { ColorAnimation { duration: settingsController.state.animationsEnabled ? 130 : 0 } }
    }
}
