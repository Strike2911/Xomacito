import QtQuick
import QtQuick.Controls

Button {
    id: root
    property string kind: "primary"
    property bool compact: false
    property string leadingText: ""
    implicitHeight: compact ? 36 : 44
    implicitWidth: Math.max(compact ? 92 : 120, contentItem.implicitWidth + 30)
    leftPadding: 15
    rightPadding: 15
    font.pixelSize: compact ? 12 : 13
    font.weight: Font.DemiBold
    focusPolicy: Qt.StrongFocus

    function baseColor() {
        if (!enabled) return theme.colors.surfaceSoft
        if (kind === "danger") return theme.colors.error
        if (kind === "ghost") return "transparent"
        if (kind === "secondary") return theme.colors.surfaceRaised
        if (kind === "success") return theme.colors.success
        return theme.colors.primary
    }

    contentItem: Text {
        text: (root.leadingText ? root.leadingText + "  " : "") + root.text
        color: !root.enabled ? theme.colors.textDim : root.kind === "primary" || root.kind === "danger" || root.kind === "success" ? "#FFFFFF" : theme.colors.text
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 11
        color: root.down ? theme.colors.primaryPressed : root.hovered && root.kind === "primary" ? theme.colors.primaryHover : root.baseColor()
        border.width: root.activeFocus || root.kind === "secondary" || root.kind === "ghost" ? 1 : 0
        border.color: root.activeFocus ? theme.colors.accent : theme.colors.border
        Behavior on color { ColorAnimation { duration: settingsController.state.animationsEnabled ? 120 : 0 } }
    }
    scale: down ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: settingsController.state.animationsEnabled ? 90 : 0; easing.type: Easing.OutCubic } }
}
