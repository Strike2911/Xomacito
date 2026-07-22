import QtQuick

Item {
    id: root
    property url source
    property int rarity: 1
    property color rarityColor: "#A8B0BC"
    property bool animatedEffects: false
    implicitWidth: 64
    implicitHeight: 64

    Rectangle {
        anchors.centerIn: parent
        width: parent.width + (root.rarity >= 4 ? 8 : 4)
        height: width
        radius: width / 2
        color: "transparent"
        border.width: root.rarity >= 5 ? 3 : root.rarity >= 3 ? 2 : 1
        border.color: root.rarityColor
        opacity: root.rarity >= 2 ? 0.42 : 0.2
        SequentialAnimation on opacity {
            running: root.animatedEffects && root.rarity >= 2
            loops: Animation.Infinite
            NumberAnimation { to: 0.9; duration: root.rarity >= 5 ? 620 : 1050; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.32; duration: root.rarity >= 5 ? 620 : 1050; easing.type: Easing.InOutSine }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 12
        height: width
        visible: root.rarity >= 3
        Rectangle {
            width: root.rarity >= 5 ? 6 : 4
            height: width
            radius: width / 2
            color: root.rarityColor
            anchors.horizontalCenter: parent.horizontalCenter
            y: 0
        }
        Rectangle {
            visible: root.rarity >= 4
            width: root.rarity >= 5 ? 5 : 4
            height: width
            radius: width / 2
            color: root.rarity >= 5 ? "#FFFFFF" : root.rarityColor
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height - height
        }
        RotationAnimation on rotation {
            running: root.animatedEffects
            from: 0; to: 360
            duration: root.rarity >= 5 ? 2500 : root.rarity >= 4 ? 3800 : 5200
            loops: Animation.Infinite
        }
    }

    Rectangle {
        id: avatarFrame
        anchors.centerIn: parent
        width: Math.max(18, parent.width - 8)
        height: width
        radius: width / 2
        color: "#071824"
        border.color: root.rarityColor
        border.width: root.rarity >= 4 ? 3 : 2

        Image {
            anchors.fill: parent
            anchors.margins: 3
            source: root.source
            fillMode: Image.PreserveAspectFit
            mipmap: true
            smooth: true
            sourceSize.width: Math.max(128, width * 2)
            sourceSize.height: Math.max(128, height * 2)
        }
    }

    Repeater {
        model: root.rarity >= 5 ? 7 : 0
        Rectangle {
            required property int index
            width: index % 2 ? 3 : 5
            height: width
            radius: width / 2
            color: index % 3 ? root.rarityColor : "#FFFFFF"
            x: root.width / 2 + Math.cos(index * Math.PI * 2 / 7) * (root.width / 2 + 7) - width / 2
            y: root.height / 2 + Math.sin(index * Math.PI * 2 / 7) * (root.height / 2 + 7) - height / 2
            SequentialAnimation on opacity {
                running: root.animatedEffects
                loops: Animation.Infinite
                PauseAnimation { duration: index * 90 }
                NumberAnimation { from: 0.15; to: 1; duration: 420 }
                NumberAnimation { to: 0.12; duration: 540 }
            }
        }
    }
}
