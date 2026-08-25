import QtQuick

Item {
    id: root
    property url source
    property int rarity: 1
    property color rarityColor: "#A8B0BC"
    property string animationStyle: "standard"
    property bool animatedEffects: false
    property int effectLevel: 0
    readonly property real effectStrength: Math.max(0, Math.min(5, effectLevel)) / 5
    readonly property bool arcaneMage: animationStyle === "arcane-mage"
    readonly property bool playeraPrismatic: animationStyle === "playera-prismatic"
    readonly property bool zarkingCyber: animationStyle === "zarking-cyber"
    readonly property bool blackbullNoir: animationStyle === "blackbull-noir"
    readonly property bool strikeApex: animationStyle === "strike-apex"
    readonly property bool bespokeMythic: arcaneMage || playeraPrismatic || zarkingCyber || blackbullNoir || strikeApex
    readonly property color signatureColor: arcaneMage ? "#B887FF"
                                             : playeraPrismatic ? "#FF7FB7"
                                             : zarkingCyber ? "#00DCEB"
                                             : blackbullNoir ? "#E7B84A"
                                             : strikeApex ? "#FF6A2A" : rarityColor
    implicitWidth: 64
    implicitHeight: 64

    Rectangle {
        id: upgradedAura
        anchors.centerIn: parent
        width: parent.width + 10 + root.effectLevel * 4
        height: width
        radius: width / 2
        visible: root.effectLevel > 0
        color: Qt.rgba(root.signatureColor.r, root.signatureColor.g,
                       root.signatureColor.b, 0.05 + root.effectStrength * 0.07)
        border.width: 2 + Math.floor(root.effectLevel / 2)
        border.color: root.effectLevel >= 5 ? "#FFFFFF" : root.signatureColor
        opacity: 0.66 + root.effectStrength * 0.24

        SequentialAnimation on scale {
            running: root.animatedEffects && root.effectLevel > 0
            loops: Animation.Infinite
            NumberAnimation {
                to: 1.045 + root.effectStrength * 0.035
                duration: Math.max(460, 980 - root.effectLevel * 85)
                easing.type: Easing.InOutSine
            }
            NumberAnimation {
                to: 0.98
                duration: Math.max(460, 980 - root.effectLevel * 85)
                easing.type: Easing.InOutSine
            }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 18 + root.effectLevel * 3
        height: width
        visible: root.effectLevel > 0 && !root.bespokeMythic

        Repeater {
            model: root.effectLevel * 3 + 3
            Rectangle {
                required property int index
                readonly property real orbit: parent.width / 2 - 3
                width: index % 3 === 0 ? 6 : 3 + root.effectLevel * 0.45
                height: width
                radius: width / 2
                color: index % 4 === 0 ? "#FFFFFF" : root.rarityColor
                opacity: 0.52 + (index % 3) * 0.17
                x: parent.width / 2
                    + Math.cos(index * Math.PI * 2 / Math.max(1, root.effectLevel * 3 + 3))
                      * orbit - width / 2
                y: parent.height / 2
                    + Math.sin(index * Math.PI * 2 / Math.max(1, root.effectLevel * 3 + 3))
                      * orbit - height / 2
            }
        }

        RotationAnimation on rotation {
            running: root.animatedEffects && root.effectLevel > 0
            from: 0
            to: 360
            duration: Math.max(1800, 5200 - root.effectLevel * 620)
            loops: Animation.Infinite
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: parent.width + (root.rarity >= 6 ? 14 : root.rarity >= 4 ? 8 : 4)
        height: width
        radius: width / 2
        color: "transparent"
        border.width: root.rarity >= 6 ? 4 : root.rarity >= 5 ? 3 : root.rarity >= 3 ? 2 : 1
        border.color: root.bespokeMythic ? root.signatureColor : root.rarityColor
        opacity: root.rarity >= 2 ? 0.42 : 0.2
        visible: !root.bespokeMythic
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
        visible: root.rarity >= 3 && !root.bespokeMythic
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
        // BLACK BULL ya tiene un avatar circular preparado. Reducirlo otra vez
        // con el margen general hacía que su rostro se viera diminuto.
        width: Math.max(18, parent.width - (root.blackbullNoir ? 0 : 8))
        height: width
        radius: width / 2
        color: "#071824"
        border.color: root.rarityColor
        border.width: (root.rarity >= 6 ? 4 : root.rarity >= 4 ? 3 : 2)
            + (root.effectLevel >= 4 ? 2 : root.effectLevel > 0 ? 1 : 0)
        clip: true

        Image {
            anchors.fill: parent
            anchors.margins: root.blackbullNoir ? 1 : 3
            source: root.source
            fillMode: Image.PreserveAspectFit
            mipmap: true
            smooth: true
            sourceSize.width: Math.max(128, width * 2)
            sourceSize.height: Math.max(128, height * 2)
        }
    }

    Repeater {
        model: root.rarity >= 5 && !root.bespokeMythic ? 7 : 0
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
        opacity: root.animatedEffects ? 0.92 : 0.7

        Repeater {
            model: 2
            Rectangle {
                required property int index
                anchors.centerIn: parent
                width: parent.width - 5 - index * 14
                height: width
                radius: width / 2
                color: "transparent"
                border.width: index === 0 ? 1 : 2
                border.color: index === 0 ? "#7B43C4" : "#E2C4FF"
                opacity: index === 0 ? 0.42 : 0.25
            }
        }

        Repeater {
            model: 5
            Text {
                required property int index
                readonly property var glyphs: ["✦", "◇", "☾", "✶", "✺"]
                text: glyphs[index]
                color: index % 2 ? "#FFF2A8" : root.rarityColor
                font.pixelSize: index % 2 ? 8 : 11
                x: parent.width / 2 + Math.cos(index * Math.PI * 2 / 5) * (parent.width / 2 - 7) - width / 2
                y: parent.height / 2 + Math.sin(index * Math.PI * 2 / 5) * (parent.height / 2 - 7) - height / 2
            }
        }

        RotationAnimation on rotation {
            running: root.animatedEffects
            from: 360
            to: 0
            duration: 6200
            loops: Animation.Infinite
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 24
        height: width
        visible: root.playeraPrismatic
        Repeater {
            model: 8
            Rectangle {
                required property int index
                readonly property var confettiColors: ["#FFD35C", "#FF7FB7", "#77E9F2", "#A8E980"]
                readonly property real baseX: 4 + (index * 19) % Math.max(8, parent.width - 12)
                readonly property real baseY: 5 + (index * 31) % Math.max(8, parent.height - 14)
                width: index % 2 ? 3 : 6
                height: index % 3 ? width * 1.8 : width
                radius: width / 2
                color: confettiColors[index % confettiColors.length]
                x: baseX
                y: baseY
                rotation: index * 29
                opacity: 0.7
                SequentialAnimation on y {
                    running: root.animatedEffects
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 120 }
                    NumberAnimation { from: baseY + 4; to: baseY - 5; duration: 1200 + index * 80; easing.type: Easing.InOutSine }
                    NumberAnimation { to: baseY + 4; duration: 1200 + index * 80; easing.type: Easing.InOutSine }
                }
            }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        clip: true
        visible: root.zarkingCyber
        Rectangle {
            id: avatarScanner
            width: parent.width * 0.82
            height: 1
            anchors.horizontalCenter: parent.horizontalCenter
            color: "#8AFFFF"
            opacity: 0.48
            SequentialAnimation on y {
                running: root.animatedEffects
                loops: Animation.Infinite
                NumberAnimation { from: 5; to: root.height - 6; duration: 1450; easing.type: Easing.InOutQuad }
                NumberAnimation { to: 5; duration: 980; easing.type: Easing.InOutQuad }
            }
        }
        Repeater {
            model: 4
            Item {
                required property int index
                width: 10
                height: 10
                x: index % 2 ? parent.width - width - 2 : 2
                y: index > 1 ? parent.height - height - 2 : 2
                rotation: index * 90
                Rectangle { width: parent.width; height: 1; color: index % 2 ? "#596CFF" : "#00E8FF" }
                Rectangle { width: 1; height: parent.height; color: index % 2 ? "#596CFF" : "#00E8FF" }
                SequentialAnimation on opacity {
                    running: root.animatedEffects; loops: Animation.Infinite
                    PauseAnimation { duration: index * 190 }
                    NumberAnimation { from: 0.28; to: 0.95; duration: 180 }
                    NumberAnimation { to: 0.38; duration: 900 }
                }
            }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 28
        height: width
        visible: root.blackbullNoir

        Repeater {
            model: 3
            Rectangle {
                required property int index
                width: 4
                height: parent.height * 0.42
                radius: 2
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                transformOrigin: Item.Bottom
                rotation: -34 + index * 34
                color: index === 1 ? "#42FFF3B5" : "#32FFC857"
                opacity: 0.3
                SequentialAnimation on opacity {
                    running: root.animatedEffects; loops: Animation.Infinite
                    PauseAnimation { duration: index * 310 }
                    NumberAnimation { to: 0.72; duration: 950; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 0.22; duration: 1250; easing.type: Easing.InOutSine }
                }
            }
        }
        Repeater {
            model: 5
            Text {
                required property int index
                text: index === 2 ? "✦" : "◆"
                color: index % 2 ? "#FFF3B5" : "#E7B84A"
                font.pixelSize: index === 2 ? 11 : 6
                x: index === 0 ? 4 : index === 1 ? parent.width - width - 4 : index === 2 ? parent.width / 2 - width / 2 : index === 3 ? 12 : parent.width - width - 12
                y: index < 2 ? parent.height * 0.48 : index === 2 ? 1 : parent.height - height - 5
                SequentialAnimation on opacity {
                    running: root.animatedEffects; loops: Animation.Infinite
                    PauseAnimation { duration: index * 260 }
                    NumberAnimation { from: 0.2; to: 0.95; duration: 720 }
                    NumberAnimation { to: 0.24; duration: 1280 }
                }
            }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        clip: true
        visible: root.strikeApex
        Repeater {
            model: 12
            Rectangle {
                required property int index
                readonly property real angle: index * Math.PI / 6
                width: index % 4 === 0 ? 6 : 3
                height: width
                radius: width / 2
                color: index % 4 === 0 ? "#FFF7D1" : index % 2 ? "#FFD45C" : "#FF7A38"
                x: parent.width / 2 + Math.cos(angle) * (parent.width / 2 - 5) - width / 2
                y: parent.height / 2 + Math.sin(angle) * (parent.height / 2 - 5) - height / 2
                SequentialAnimation on scale {
                    running: root.animatedEffects
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 115 }
                    NumberAnimation { from: 0.45; to: 1.22; duration: 360; easing.type: Easing.OutCubic }
                    NumberAnimation { to: 0.55; duration: 920; easing.type: Easing.InOutSine }
                }
                SequentialAnimation on opacity {
                    running: root.animatedEffects
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 115 }
                    NumberAnimation { from: 0.28; to: 0.96; duration: 360 }
                    NumberAnimation { to: 0.32; duration: 920 }
                }
            }
        }
    }
}
