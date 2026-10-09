import QtQuick

Item {
    id: root
    property int rarity: 1
    property color accent: "#A8B0BC"
    property string animationStyle: ""
    property bool animated: true
    property int textSize: 20
    readonly property bool haunting: animationStyle === "hola-haunting"
    readonly property color ink: haunting ? "#C97889"
        : animationStyle === "strike-apex" ? "#9BE2FF"
        : animationStyle === "spike-emerald" ? "#6DE5BA"
        : animationStyle === "zarking-cyber" ? "#62D9FF"
        : animationStyle === "xomas-solar" ? "#FFD779"
        : animationStyle === "megas-storm" ? "#BBABFF" : accent
    property real phase: 0
    implicitWidth: label.implicitWidth + 18
    implicitHeight: textSize + 12
    NumberAnimation on phase {
        from: 0; to: 1; duration: root.haunting ? 6000 : 4200
        loops: Animation.Infinite; running: root.visible && root.animated && root.rarity >= 2
    }
    Text {
        id: label; anchors.verticalCenter: parent.verticalCenter
        text: "XOMACITO"; color: Qt.tint(theme.colors.text, Qt.alpha(root.ink, root.haunting ? 0.6 : 0.25))
        font.pixelSize: root.textSize; font.weight: Font.ExtraBold; font.letterSpacing: 1.4
    }
    Rectangle {
        anchors.left: label.left; anchors.bottom: parent.bottom
        width: label.width; height: 2; radius: 1; color: root.ink
        opacity: root.animated && root.rarity >= 2 ? 0.3 + 0.35 * Math.sin(root.phase * Math.PI) : 0.45
        Rectangle {
            visible: root.rarity >= 4 && root.animated
            x: root.phase * (parent.width - width); width: 24; height: 2; radius: 1
            color: root.haunting ? "#EE7C89" : "#FFFFFF"; opacity: Math.sin(root.phase * Math.PI)
        }
    }
    Repeater {
        model: root.rarity >= 6 ? 3 : root.rarity >= 3 ? 1 : 0
        Rectangle {
            width: index === 0 ? 4 : 2; height: width; rotation: 45
            x: label.width + 5 + index * 3
            y: root.height * (0.3 + index * 0.22) + (root.animated ? Math.sin(root.phase * Math.PI * 2 + index) * 2 : 0)
            color: root.ink; opacity: root.animated ? 0.5 + 0.4 * Math.sin(root.phase * Math.PI + index) : 0.7
        }
    }
}
