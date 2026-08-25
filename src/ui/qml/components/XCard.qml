import QtQuick

Rectangle {
    id: root
    property int padding: 20
    property bool elevated: false
    property color cardColor: elevated ? theme.colors.surfaceRaised : theme.colors.surface
    property bool platinumGlow: theme.themeName === "platinum_duality"
    property color platinumGlowColor: "#5267C8"
    property real platinumGlowOpacity: 0.34
    radius: 18
    color: cardColor
    border.width: 1
    border.color: root.platinumGlow ? root.platinumGlowColor : theme.colors.border
    layer.enabled: elevated
    layer.samples: 4

    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: Math.max(2, root.radius - 2)
        color: "transparent"
        border.width: 1
        border.color: root.platinumGlowColor
        opacity: root.platinumGlow ? root.platinumGlowOpacity : 0
    }

    SequentialAnimation on platinumGlowColor {
        running: root.platinumGlow && settingsController.state.animationsEnabled
        loops: Animation.Infinite
        ColorAnimation { from: "#465FAF"; to: "#7657B3"; duration: 1850; easing.type: Easing.InOutSine }
        ColorAnimation { from: "#7657B3"; to: "#465FAF"; duration: 1850; easing.type: Easing.InOutSine }
    }
    SequentialAnimation on platinumGlowOpacity {
        running: root.platinumGlow && settingsController.state.animationsEnabled
        loops: Animation.Infinite
        NumberAnimation { from: 0.2; to: 0.58; duration: 1850; easing.type: Easing.InOutSine }
        NumberAnimation { from: 0.58; to: 0.2; duration: 1850; easing.type: Easing.InOutSine }
    }
}
