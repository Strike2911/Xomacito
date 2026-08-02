import QtQuick

Item {
    id: root
    property url source
    property int rarity: 1
    property color rarityColor: "#A8B0BC"
    property string animationStyle: "standard"
    property bool animatedEffects: false
    readonly property bool arcaneMage: animationStyle === "arcane-mage"
    readonly property bool playeraPrismatic: animationStyle === "playera-prismatic"
    readonly property bool zarkingCyber: animationStyle === "zarking-cyber"
    readonly property bool blackbullNoir: animationStyle === "blackbull-noir"
    implicitWidth: 64
    implicitHeight: 64

    Rectangle {
        anchors.centerIn: parent
        width: parent.width + (root.rarity >= 6 ? 14 : root.rarity >= 4 ? 8 : 4)
        height: width
        radius: width / 2
        color: "transparent"
        border.width: root.rarity >= 6 ? 4 : root.rarity >= 5 ? 3 : root.rarity >= 3 ? 2 : 1
        border.color: root.rarityColor
        opacity: root.rarity >= 2 ? 0.42 : 0.2
        SequentialAnimation on opacity {
            running: root.animatedEffects && root.rarity >= 2
            loops: Animation.Infinite
            NumberAnimation { to: 0.9; duration: root.rarity >= 6 ? 360 : root.rarity >= 5 ? 620 : 1050; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.32; duration: root.rarity >= 6 ? 360 : root.rarity >= 5 ? 620 : 1050; easing.type: Easing.InOutSine }
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
            duration: root.rarity >= 6 ? 1500 : root.rarity >= 5 ? 2500 : root.rarity >= 4 ? 3800 : 5200
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
        border.width: root.rarity >= 6 ? 4 : root.rarity >= 4 ? 3 : 2

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
        model: root.rarity >= 6 ? 12 : root.rarity >= 5 ? 7 : 0
        Rectangle {
            required property int index
            width: index % 2 ? 3 : 5
            height: width
            radius: width / 2
            color: index % 3 ? root.rarityColor : "#FFFFFF"
            x: root.width / 2 + Math.cos(index * Math.PI * 2 / (root.rarity >= 6 ? 12 : 7)) * (root.width / 2 + 7) - width / 2
            y: root.height / 2 + Math.sin(index * Math.PI * 2 / (root.rarity >= 6 ? 12 : 7)) * (root.height / 2 + 7) - height / 2
            SequentialAnimation on opacity {
                running: root.animatedEffects
                loops: Animation.Infinite
                PauseAnimation { duration: index * 90 }
                NumberAnimation { from: 0.15; to: 1; duration: 420 }
                NumberAnimation { to: 0.12; duration: 540 }
            }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 28
        height: width
        visible: root.arcaneMage
        opacity: root.animatedEffects ? 1 : 0.72

        Repeater {
            model: 6
            Text {
                required property int index
                readonly property var glyphs: ["✦", "◇", "✧", "☾", "✶", "✺"]
                text: glyphs[index]
                color: index % 2 ? "#FFF2A8" : root.rarityColor
                font.pixelSize: index % 2 ? 9 : 12
                x: parent.width / 2 + Math.cos(index * Math.PI / 3) * (parent.width / 2 - 7) - width / 2
                y: parent.height / 2 + Math.sin(index * Math.PI / 3) * (parent.height / 2 - 7) - height / 2
            }
        }

        RotationAnimation on rotation {
            running: root.animatedEffects
            from: 360
            to: 0
            duration: 3200
            loops: Animation.Infinite
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 24
        height: width
        visible: root.playeraPrismatic
        Repeater {
            model: 10
            Rectangle {
                required property int index
                readonly property var palette: ["#FFDD42", "#FF6BAA", "#77F4FF", "#A7FF63"]
                width: index % 2 ? 4 : 7
                height: index % 3 ? width : width * 2
                radius: 2
                color: palette[index % palette.length]
                x: parent.width / 2 + Math.cos(index * Math.PI / 5) * (parent.width / 2 - 5) - width / 2
                y: parent.height / 2 + Math.sin(index * Math.PI / 5) * (parent.height / 2 - 5) - height / 2
                rotation: index * 37
            }
        }
        RotationAnimation on rotation {
            running: root.animatedEffects
            from: 0
            to: 360
            duration: 2200
            loops: Animation.Infinite
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 24
        height: width
        visible: root.zarkingCyber
        Rectangle {
            anchors.centerIn: parent
            width: parent.width
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 2
            border.color: "#00E8FF"
            opacity: 0.7
        }
        Rectangle {
            id: avatarScanner
            width: parent.width * 0.72
            height: 2
            anchors.horizontalCenter: parent.horizontalCenter
            color: "#8AFFFF"
            SequentialAnimation on y {
                running: root.animatedEffects
                loops: Animation.Infinite
                NumberAnimation { from: 8; to: root.height + 16; duration: 820; easing.type: Easing.InOutQuad }
                NumberAnimation { to: 8; duration: 560; easing.type: Easing.InOutQuad }
            }
        }
        Repeater {
            model: 6
            Rectangle {
                required property int index
                width: 5
                height: 5
                rotation: 45
                color: index % 2 ? "#596CFF" : "#00E8FF"
                x: parent.width / 2 + Math.cos(index * Math.PI / 3) * (parent.width / 2 - 5) - width / 2
                y: parent.height / 2 + Math.sin(index * Math.PI / 3) * (parent.height / 2 - 5) - height / 2
            }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 28
        height: width
        visible: root.blackbullNoir

        Repeater {
            model: 12
            Rectangle {
                required property int index
                width: index % 3 === 0 ? 9 : 4
                height: index % 3 === 0 ? 3 : width
                radius: 2
                rotation: index * 30 + 45
                color: index % 2 ? "#FFC857" : "#FFF3B5"
                x: parent.width / 2 + Math.cos(index * Math.PI / 6) * (parent.width / 2 - 5) - width / 2
                y: parent.height / 2 + Math.sin(index * Math.PI / 6) * (parent.height / 2 - 5) - height / 2
            }
        }
        RotationAnimation on rotation {
            running: root.animatedEffects
            from: 0
            to: 360
            duration: 4800
            loops: Animation.Infinite
        }
    }
}
