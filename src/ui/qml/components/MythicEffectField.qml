import QtQuick

Item {
    id: root
    property string animationStyle: ""
    property color effectColor: "#9B5CFF"
    property bool active: false
    property real progress: 1
    property string mode: "reveal"
    readonly property bool arcane: animationStyle === "arcane-mage"
    readonly property bool playera: animationStyle === "playera-prismatic"
    readonly property bool zarking: animationStyle === "zarking-cyber"
    readonly property bool blackbull: animationStyle === "blackbull-noir"
    visible: arcane || playera || zarking || blackbull

    // GATO MAGO: astrolabio arcano, runas y órbitas en sentidos opuestos.
    Item {
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.9
        height: width
        visible: root.arcane
        scale: 0.65 + root.progress * 0.35

        Repeater {
            model: 4
            Rectangle {
                required property int index
                anchors.centerIn: parent
                width: parent.width - index * 46
                height: width
                radius: width / 2
                color: "transparent"
                border.width: index === 0 ? 4 : 2
                border.color: index % 2 ? "#FFE58A" : root.effectColor
                opacity: 0.2 + index * 0.1
                RotationAnimation on rotation {
                    running: root.active
                    from: index % 2 ? 360 : 0
                    to: index % 2 ? 0 : 360
                    duration: 2400 + index * 850
                    loops: Animation.Infinite
                }
            }
        }
        Repeater {
            model: 18
            Text {
                required property int index
                readonly property var glyphs: ["✦", "◇", "✧", "☾", "✶", "✺"]
                text: glyphs[index % glyphs.length]
                color: index % 3 ? root.effectColor : "#FFF2A8"
                font.pixelSize: 13 + index % 3 * 3
                x: parent.width / 2 + Math.cos(index * Math.PI / 9) * (parent.width / 2 - 20) - width / 2
                y: parent.height / 2 + Math.sin(index * Math.PI / 9) * (parent.height / 2 - 20) - height / 2
            }
        }
    }

    // GATO PLAYERA: estallido caricaturesco, confeti y ondas prismáticas.
    Item {
        anchors.fill: parent
        visible: root.playera
        scale: 0.78 + root.progress * 0.22

        Repeater {
            model: 28
            Rectangle {
                required property int index
                readonly property var palette: ["#FFDD42", "#FF6BAA", "#77F4FF", "#A7FF63", "#FFFFFF"]
                width: index % 3 === 0 ? 10 : 6
                height: index % 2 === 0 ? width * 2.5 : width
                radius: 3
                color: palette[index % palette.length]
                rotation: index * 31 + root.progress * 180
                x: parent.width / 2 + Math.cos(index * Math.PI * 2 / 28) * (50 + root.progress * (120 + index % 5 * 18)) - width / 2
                y: parent.height / 2 + Math.sin(index * Math.PI * 2 / 28) * (50 + root.progress * (120 + index % 5 * 18)) - height / 2
                opacity: Math.max(0.12, 1 - root.progress * 0.5)
                SequentialAnimation on scale {
                    running: root.active
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 22 }
                    NumberAnimation { from: 0.55; to: 1.35; duration: 260; easing.type: Easing.OutBack }
                    NumberAnimation { to: 0.7; duration: 360 }
                }
            }
        }
        Repeater {
            model: 3
            Rectangle {
                required property int index
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height) * (0.34 + index * 0.18)
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 5 - index
                border.color: ["#FFDD42", "#FF6BAA", "#77F4FF"][index]
                opacity: 0.55 - index * 0.1
                SequentialAnimation on scale {
                    running: root.active
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 170 }
                    NumberAnimation { from: 0.7; to: 1.18; duration: 720; easing.type: Easing.OutCubic }
                    NumberAnimation { to: 0.7; duration: 1 }
                }
            }
        }
    }

    // GATO ZARKING: portal digital con escáner, nodos y micro-glitches.
    Item {
        anchors.fill: parent
        visible: root.zarking

        Repeater {
            model: 9
            Rectangle {
                required property int index
                x: 0
                y: index * parent.height / 9
                width: parent.width
                height: index % 3 === 0 ? 2 : 1
                color: index % 2 ? "#4B69FF" : "#00E8FF"
                opacity: 0.08 + index % 3 * 0.04
            }
        }
        Rectangle {
            id: scanner
            width: parent.width
            height: 4
            color: "#8AFFFF"
            opacity: 0.72
            y: 0
            SequentialAnimation on y {
                running: root.active
                loops: Animation.Infinite
                NumberAnimation { from: 0; to: root.height - scanner.height; duration: 1180; easing.type: Easing.InOutQuad }
                NumberAnimation { to: 0; duration: 760; easing.type: Easing.InOutQuad }
            }
        }
        Repeater {
            model: 24
            Rectangle {
                required property int index
                width: index % 4 === 0 ? 11 : 6
                height: width
                rotation: 45
                color: index % 3 === 0 ? "#FFFFFF" : index % 2 ? "#00E8FF" : "#596CFF"
                x: (index * 83) % Math.max(1, root.width - width)
                y: (index * 47) % Math.max(1, root.height - height)
                opacity: 0.2 + (index % 4) * 0.16
                SequentialAnimation on opacity {
                    running: root.active
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 31 }
                    NumberAnimation { to: 1; duration: 110 }
                    NumberAnimation { to: 0.12; duration: 240 }
                    PauseAnimation { duration: 350 + index * 13 }
                }
            }
        }
        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.height) * 0.72
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 4
            border.color: "#00E8FF"
            opacity: 0.44
            SequentialAnimation on rotation {
                running: root.active
                loops: Animation.Infinite
                NumberAnimation { from: -4; to: 4; duration: 90 }
                NumberAnimation { to: 0; duration: 70 }
                PauseAnimation { duration: 650 }
            }
        }
    }

    // BLACK BULL: club noir, focos dorados y destellos de gala.
    Item {
        anchors.fill: parent
        visible: root.blackbull
        clip: true

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#00000000" }
                GradientStop { position: 0.5; color: "#331A1000" }
                GradientStop { position: 1; color: "#00000000" }
            }
        }

        Repeater {
            model: 7
            Rectangle {
                required property int index
                width: Math.max(90, root.width * 0.12)
                height: root.height * 1.45
                x: root.width / 2 - width / 2 + (index - 3) * root.width * 0.11
                y: -root.height * 0.22
                rotation: -28 + index * 9
                color: index % 2 ? "#20FFC857" : "#16FFF2B0"
                opacity: 0.06 + (index % 3) * 0.025
                transformOrigin: Item.Bottom
                SequentialAnimation on opacity {
                    running: root.active
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 85 }
                    NumberAnimation { to: 0.16; duration: 540; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 0.045; duration: 760; easing.type: Easing.InOutSine }
                }
            }
        }

        Repeater {
            model: 4
            Rectangle {
                required property int index
                anchors.centerIn: parent
                width: Math.min(root.width, root.height) * (0.3 + index * 0.16)
                height: width
                radius: width / 2
                color: "transparent"
                border.width: index === 0 ? 5 : 2
                border.color: index % 2 ? "#FFF3B5" : "#FFC857"
                opacity: 0.5 - index * 0.08
                scale: 0.72 + root.progress * 0.28
                RotationAnimation on rotation {
                    running: root.active
                    from: index % 2 ? 360 : 0
                    to: index % 2 ? 0 : 360
                    duration: 3300 + index * 880
                    loops: Animation.Infinite
                }
            }
        }

        Repeater {
            model: 30
            Rectangle {
                required property int index
                width: index % 5 === 0 ? 11 : 4 + index % 3 * 2
                height: width
                rotation: 45 + root.progress * 180
                color: index % 4 === 0 ? "#FFFFFF" : index % 2 ? "#FFC857" : "#D99A21"
                x: (index * 89) % Math.max(1, root.width - width)
                y: (index * 53) % Math.max(1, root.height - height)
                opacity: 0.14 + (index % 5) * 0.12
                SequentialAnimation on scale {
                    running: root.active
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 34 }
                    NumberAnimation { from: 0.25; to: 1.45; duration: 300; easing.type: Easing.OutBack }
                    NumberAnimation { to: 0.25; duration: 610 }
                }
            }
        }
    }
}
