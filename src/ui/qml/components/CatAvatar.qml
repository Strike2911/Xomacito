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
    // El retrato de Zane ocupa casi todo el lienzo cuadrado. Un inset mayor
    // mantiene incluso el hocico y el pelaje dentro del aro circular.
    readonly property bool zanePortrait: source.toString().indexOf("cat-5a99d9f019f0-avatar.webp") >= 0
    readonly property bool bespokeMythic: arcaneMage || playeraPrismatic || zarkingCyber || blackbullNoir || strikeApex
    readonly property color signatureColor: arcaneMage ? "#B887FF"
                                             : playeraPrismatic ? "#FF7FB7"
                                             : zarkingCyber ? "#00DCEB"
                                             : blackbullNoir ? "#E7B84A"
                                             : strikeApex ? "#8476E8" : rarityColor
    implicitWidth: 64
    implicitHeight: 64

    // A single fine halo leaves the portrait readable at inventory sizes.
    readonly property bool motionActive: animatedEffects && visible
    Rectangle {
        anchors.centerIn: parent
        width: parent.width + 6 + root.effectStrength * 4
        height: width
        radius: width / 2
        color: Qt.alpha(root.signatureColor, 0.025 + root.effectStrength * 0.025)
        border.width: 1
        border.color: Qt.alpha(root.signatureColor, 0.22 + root.effectStrength * 0.18)
        visible: root.effectLevel > 0 || root.rarity >= 3
        SequentialAnimation on opacity {
            running: root.motionActive && (root.effectLevel > 0 || root.rarity >= 3)
            loops: Animation.Infinite
            NumberAnimation { from: 0.55; to: 0.9; duration: 2400; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.55; duration: 2400; easing.type: Easing.InOutSine }
        }
    }
    Item {
        anchors.centerIn: parent
        width: parent.width + 8
        height: width
        visible: !root.bespokeMythic && (root.rarity >= 3 || root.effectLevel > 0)
        Repeater {
            model: root.effectLevel >= 4 ? 3 : 2
            Rectangle {
                required property int index
                width: index === 0 ? 2.5 : 1.5
                height: width
                radius: width / 2
                color: index === 0 ? "#F5F0DE" : root.signatureColor
                opacity: index === 0 ? 0.7 : 0.4
                x: parent.width / 2 + Math.cos(index * 2.4) * (parent.width / 2) - width / 2
                y: parent.height / 2 + Math.sin(index * 2.4) * (parent.height / 2) - height / 2
            }
        }
        RotationAnimation on rotation {
            running: root.motionActive && !root.bespokeMythic && (root.rarity >= 3 || root.effectLevel > 0)
            from: 0; to: 360; duration: 14000; loops: Animation.Infinite
        }
    }

    Rectangle {
        id: avatarFrame
        objectName: "catAvatarFrame"
        anchors.centerIn: parent
        // BLACK BULL ya tiene un avatar circular preparado. Reducirlo otra vez
        // con el margen general hacía que su rostro se viera diminuto.
        width: Math.max(18, parent.width - (root.blackbullNoir ? 0 : 8))
        height: width
        radius: width / 2
        color: "#071824"
        border.color: root.rarityColor
        border.width: root.rarity >= 5 ? 1.5 : 1
        clip: true

        Image {
            objectName: "catAvatarImage"
            anchors.fill: parent
            anchors.margins: root.blackbullNoir ? 1 : root.zanePortrait ? avatarFrame.width * 0.15 : 3
            source: root.source
            fillMode: Image.PreserveAspectFit
            mipmap: true
            smooth: true
            sourceSize.width: Math.max(128, width * 2)
            sourceSize.height: Math.max(128, height * 2)
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 12
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
            running: root.motionActive && root.arcaneMage
            from: 360
            to: 0
            duration: 14000
            loops: Animation.Infinite
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 10
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
                    running: root.motionActive && root.playeraPrismatic
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
                running: root.motionActive && root.zarkingCyber
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
                    running: root.motionActive && root.zarkingCyber; loops: Animation.Infinite
                    PauseAnimation { duration: index * 190 }
                    NumberAnimation { from: 0.28; to: 0.95; duration: 180 }
                    NumberAnimation { to: 0.38; duration: 900 }
                }
            }
        }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width + 12
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
                    running: root.motionActive && root.blackbullNoir; loops: Animation.Infinite
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
                    running: root.motionActive && root.blackbullNoir; loops: Animation.Infinite
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

        QtObject { id: strikeOrbit; property real phase: 0 }
        NumberAnimation {
            target: strikeOrbit; property: "phase"; from: 0; to: Math.PI * 2
            duration: 16000; loops: Animation.Infinite
            running: root.motionActive && root.strikeApex
        }

        Repeater {
            model: 2
            Rectangle {
                required property int index
                anchors.centerIn: parent
                width: parent.width * (index === 0 ? 0.82 : 0.96)
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 1
                border.color: index === 0 ? "#776DE2" : "#E4CB82"
                opacity: index === 0 ? 0.32 : 0.18
                scale: 0.98 + Math.sin(strikeOrbit.phase * 2 + index * 1.7) * 0.018
            }
        }

        Repeater {
            model: 8
            Text {
                required property int index
                readonly property real angle: index * Math.PI * 2 / 8 + strikeOrbit.phase * (index % 2 ? -0.42 : 0.28)
                readonly property real orbit: parent.width * (index % 3 === 0 ? 0.46 : 0.41)
                text: index % 5 === 0 ? "✦" : index % 3 === 0 ? "✧" : "·"
                color: index % 5 === 0 ? "#FFF2C2" : index % 2 ? "#9D8DFF" : "#74B7FF"
                font.pixelSize: index % 5 === 0 ? 8 : index % 3 === 0 ? 6 : 10
                font.weight: Font.Bold
                x: parent.width / 2 + Math.cos(angle) * orbit - width / 2
                y: parent.height / 2 + Math.sin(angle) * orbit - height / 2
                opacity: 0.42 + (Math.sin(strikeOrbit.phase * 3 + index) + 1) * 0.26
                scale: 0.8 + (Math.sin(strikeOrbit.phase * 2 + index * 0.7) + 1) * 0.12
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 1
            text: "✦"
            color: "#FFFFFF"
            font.pixelSize: 10
            opacity: 0.7 + Math.sin(strikeOrbit.phase * 3) * 0.25
        }
    }
}
