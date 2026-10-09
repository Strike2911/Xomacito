import QtQuick

Item {
    id: root
    property bool active: false
    property int rarity: 1
    property color accent: "#50BFFF"
    property bool haunting: false
    property real progress: 1
    visible: active && rarity >= 3 && progress < 1
    clip: true
    onActiveChanged: { if (active && rarity >= 3) burst.restart(); else { burst.stop(); progress = 1 } }
    NumberAnimation { id: burst; target: root; property: "progress"; from: 0; to: 1; duration: root.rarity >= 5 ? 3000 : 2100; easing.type: Easing.OutQuad }
    Repeater {
        model: root.active && root.rarity >= 3 ? (root.rarity >= 6 ? 72 : root.rarity >= 5 ? 52 : root.rarity >= 4 ? 36 : 22) : 0
        Rectangle {
            property real angle: (index * 137.508) * Math.PI / 180
            property real reach: 0.35 + (index % 9) / 12
            width: root.haunting ? 2 : 3 + index % 4
            height: root.rarity >= 5 ? width * 2 : width
            radius: root.haunting ? 0 : 1
            x: root.width / 2 + Math.cos(angle) * root.width * reach * root.progress
            y: root.height * 0.43 + Math.sin(angle) * root.height * reach * root.progress + root.progress * root.progress * 160
            rotation: index * 31 + root.progress * (root.haunting ? 80 : 480)
            color: root.haunting ? "#A83848" : index % 4 === 0 ? "#FFF1CB" : root.accent
            opacity: Math.min(1, (1 - root.progress) * 3) * (root.haunting ? 0.5 : 0.85)
        }
    }
}
