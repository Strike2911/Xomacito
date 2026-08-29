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
    readonly property color currentBackgroundColor: !enabled ? theme.colors.surfaceSoft
                                                        : down ? pressedColor()
                                                        : hovered ? hoverColor()
                                                        : baseColor()

    function baseColor() {
        if (!enabled) return theme.colors.surfaceSoft
        if (kind === "danger") return theme.colors.error
        if (kind === "ghost") return "transparent"
        if (kind === "secondary") return theme.colors.surfaceRaised
        if (kind === "success") return theme.colors.success
        return theme.colors.primary
    }

    function hoverColor() {
        if (kind === "primary") return theme.colors.primaryHover
        if (kind === "danger") return Qt.darker(theme.colors.error, 1.08)
        if (kind === "success") return Qt.darker(theme.colors.success, 1.08)
        if (kind === "ghost") return theme.colors.surfaceSoft
        return Qt.lighter(theme.colors.surfaceRaised, 1.08)
    }

    function pressedColor() {
        if (kind === "danger") return Qt.darker(theme.colors.error, 1.18)
        if (kind === "success") return Qt.darker(theme.colors.success, 1.18)
        if (kind === "ghost") return theme.colors.surfaceRaised
        if (kind === "secondary") return Qt.darker(theme.colors.surfaceRaised, 1.08)
        return theme.colors.primaryPressed
    }

    function contrastText(backgroundColor) {
        var luminance = 0.2126 * backgroundColor.r
                      + 0.7152 * backgroundColor.g
                      + 0.0722 * backgroundColor.b
        return luminance > 0.62 ? "#17202A" : "#FFFFFF"
    }

    function foregroundColor() {
        if (!enabled || kind === "primary" || kind === "danger" || kind === "success")
            return contrastText(currentBackgroundColor)
        return theme.colors.text
    }

    contentItem: Text {
        text: (root.leadingText ? root.leadingText + "  " : "") + root.text
        color: root.foregroundColor()
        opacity: root.enabled ? 1 : 0.68
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 11
        color: root.currentBackgroundColor
        border.width: root.activeFocus || root.kind === "secondary" || root.kind === "ghost" ? 1 : 0
        border.color: root.activeFocus ? theme.colors.accent : theme.colors.border
        Behavior on color { ColorAnimation { duration: settingsController.state.animationsEnabled ? 120 : 0 } }
    }
    scale: down ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: settingsController.state.animationsEnabled ? 90 : 0; easing.type: Easing.OutCubic } }
}
