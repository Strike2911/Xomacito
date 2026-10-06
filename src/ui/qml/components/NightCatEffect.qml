import QtQuick
import QtQuick.Shapes

Item {
    id: root
    property string style: ""
    property bool active: false
    property bool reveal: false
    readonly property bool spike: style === "spike-emerald"
    readonly property bool solar: style === "xomas-solar"
    readonly property bool storm: style === "megas-storm"
    readonly property bool haunted: style === "hola-haunting"
    readonly property color ink: spike ? "#62FFD2" : solar ? "#FFC86B" : storm ? "#A589FF" : "#ED424D"
    visible: spike || solar || storm || haunted
    property real phase: 0
    NumberAnimation on phase { from: 0; to: Math.PI * 2; duration: root.haunted ? 11000 : 16000; loops: Animation.Infinite; running: root.active && root.visible }
    Repeater {
        model: root.solar ? 12 : root.storm ? 8 : 5
        Rectangle {
            required property int index
            readonly property real angle: index * Math.PI * 2 / (root.solar ? 12 : root.storm ? 8 : 5) + root.phase
            x: parent.width/2 + Math.cos(angle) * parent.width * 0.47 - width/2
            y: parent.height/2 + Math.sin(angle) * parent.height * 0.47 - height/2
            width: root.solar ? 2 : root.storm ? 4 : 2
            height: root.solar ? parent.height * 0.10 : root.storm ? 4 : parent.height * 0.19
            radius: root.solar ? 1 : 2
            rotation: root.solar ? angle * 180/Math.PI + 90 : 45
            color: index % 3 ? root.ink : "#FFF2D6"
            opacity: 0.35 + 0.45 * Math.pow(Math.sin(root.phase + index), 2)
        }
    }
    Repeater {
        model: 2
        Rectangle {
            required property int index
            anchors.centerIn: parent
            width: parent.width * (index ? 0.97 : 1.10)
            height: root.storm ? width * 0.52 : width
            radius: width/2
            color: "transparent"
            border.width: 1
            border.color: root.ink
            rotation: (index ? -1 : 1) * (root.phase * 180/Math.PI + 35)
            opacity: root.haunted ? 0.15 : 0.40
        }
    }
    Repeater {
        model: root.storm ? 4 : 0
        Item {
            id: lightning
            required property int index
            readonly property real angle: index * Math.PI / 2 - root.phase * 0.3
            width: Math.max(9, parent.width * 0.06)
            height: parent.height * 0.28
            x: parent.width / 2 + Math.cos(angle) * parent.width * 0.42 - width / 2
            y: parent.height / 2 + Math.sin(angle) * parent.height * 0.42 - height / 2
            rotation: angle * 180 / Math.PI + 90
            opacity: 0.25 + 0.45 * Math.pow(Math.sin(root.phase * 2 + index), 4)
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeColor: "#DBCAFF"; strokeWidth: 1.2; fillColor: "transparent"
                    startX: 0; startY: 0
                    PathLine { x: lightning.width * 0.75; y: lightning.height * 0.38 }
                    PathLine { x: lightning.width * 0.15; y: lightning.height * 0.48 }
                    PathLine { x: lightning.width; y: lightning.height }
                }
            }
        }
    }
    Repeater {
        model: root.solar ? 4 : 0
        Text {
            required property int index
            readonly property real angle: index * Math.PI / 2 + root.phase * 0.4
            x: parent.width / 2 + Math.cos(angle) * parent.width * 0.43 - width / 2
            y: parent.height / 2 + Math.sin(angle) * parent.height * 0.43 - height / 2
            text: "✦"; color: "#FFF1B8"
            font.pixelSize: Math.max(10, parent.height * 0.09)
            opacity: 0.45 + 0.5 * Math.pow(Math.sin(root.phase + index), 2)
            rotation: root.phase * 30
        }
    }
    Repeater {
        model: root.spike ? 6 : 0
        Item {
            required property int index
            readonly property real angle: index * Math.PI / 3 - root.phase
            width: Math.max(5, parent.width * 0.045); height: parent.height * 0.15
            x: parent.width / 2 + Math.cos(angle) * parent.width * 0.44 - width / 2
            y: parent.height / 2 + Math.sin(angle) * parent.height * 0.44 - height / 2
            rotation: angle * 180 / Math.PI + 90
            opacity: 0.45 + 0.5 * Math.pow(Math.sin(root.phase + index), 2)
            Rectangle {
                anchors.centerIn: parent; width: parent.width; height: parent.height
                rotation: 25; radius: 2; color: "#163D35"
                border.width: 1; border.color: "#91FFE0"
            }
            Rectangle { anchors.centerIn: parent; width: 2; height: parent.height * 0.55; color: "#DCFFF5" }
        }
    }
    // A slow eclipse and approaching face; no strobing or sustained camera shake.
    Rectangle {
        anchors.fill: parent
        visible: root.haunted && root.reveal
        radius: 18
        color: "#09030A"
        opacity: 0
        SequentialAnimation on opacity {
            running: root.active && root.haunted && root.reveal
            NumberAnimation { from: 0.95; to: 0.65; duration: 850 }
            NumberAnimation { to: 0; duration: 1400; easing.type: Easing.InCubic }
        }
    }
}
