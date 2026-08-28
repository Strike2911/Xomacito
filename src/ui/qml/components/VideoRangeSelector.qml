import QtQuick
import QtQuick.Controls

Item {
    id: root

    property real duration: 0
    property real inPoint: 0
    property real outPoint: duration
    property url filmstripSource: ""
    property url fallbackSource: ""
    property bool busy: false
    property string errorText: ""
    signal inPointMoved(real value)
    signal outPointMoved(real value)

    function clock(seconds) {
        var total = Math.max(0, Math.floor(Number(seconds) || 0))
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        var secs = total % 60
        return (hours < 10 ? "0" : "") + hours + ":" +
               (minutes < 10 ? "0" : "") + minutes + ":" +
               (secs < 10 ? "0" : "") + secs
    }

    Rectangle {
        anchors.fill: parent
        color: "#090B0F"
        border.color: "#303544"
        border.width: 1
    }
    Image {
        id: filmstripImage
        anchors.fill: parent
        anchors.margins: 2
        source: root.filmstripSource
        fillMode: Image.Stretch
        asynchronous: true
        cache: true
        visible: status === Image.Ready
    }
    Row {
        anchors.fill: parent
        anchors.margins: 2
        visible: !filmstripImage.visible
        Repeater {
            model: 8
            Rectangle {
                width: Math.ceil(parent.width / 8)
                height: parent.height
                color: index % 2 ? "#151923" : "#11151D"
                border.color: "#242A38"
                clip: true
                Image {
                    anchors.fill: parent
                    source: root.fallbackSource
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: Boolean(root.fallbackSource)
                    opacity: 0.82
                }
                Text {
                    anchors.centerIn: parent
                    visible: !root.fallbackSource
                    text: root.busy ? "⋯" : "▧"
                    color: "#667087"
                    font.pixelSize: 17
                }
            }
        }
    }
    Text {
        anchors.centerIn: parent
        visible: !filmstripImage.visible && !root.fallbackSource
        text: root.busy ? "Generando fotogramas…" : (root.errorText || "Preparando video…")
        color: "#D7DAE5"
        font.pixelSize: 10
        font.weight: Font.DemiBold
    }

    Rectangle {
        x: 0
        width: videoRange.leftPadding + videoRange.first.visualPosition * videoRange.availableWidth
        height: parent.height
        color: "#A8090B0F"
    }
    Rectangle {
        x: videoRange.leftPadding + videoRange.second.visualPosition * videoRange.availableWidth
        width: parent.width - x
        height: parent.height
        color: "#A8090B0F"
    }
    Rectangle {
        x: videoRange.leftPadding + videoRange.first.visualPosition * videoRange.availableWidth
        width: Math.max(1, (videoRange.second.visualPosition - videoRange.first.visualPosition) * videoRange.availableWidth)
        height: parent.height
        color: "transparent"
        border.color: "#8D88EB"
        border.width: 2
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 8
        implicitWidth: selectionLabel.implicitWidth + 18
        implicitHeight: 27
        radius: 14
        color: "#DC151820"
        border.color: "#F3F4FA"
        Text {
            id: selectionLabel
            anchors.centerIn: parent
            text: root.clock(root.inPoint) + "  —  " + root.clock(root.outPoint)
            color: "white"
            font.pixelSize: 11
            font.weight: Font.Bold
            font.family: "Consolas"
        }
    }

    RangeSlider {
        id: videoRange
        objectName: "trimVideoRangeSlider"
        anchors.fill: parent
        anchors.leftMargin: 3
        anchors.rightMargin: 3
        from: 0
        to: Math.max(0.05, root.duration)
        stepSize: root.duration > 120 ? 0.1 : 0.02
        snapMode: RangeSlider.SnapOnRelease
        first.value: Math.max(from, Math.min(to, root.inPoint))
        second.value: Math.max(first.value + 0.05, Math.min(to, root.outPoint))
        first.onMoved: root.inPointMoved(first.value)
        second.onMoved: root.outPointMoved(second.value)
        background: Item {}
        first.handle: Rectangle {
            x: videoRange.leftPadding + videoRange.first.visualPosition * (videoRange.availableWidth - width)
            y: videoRange.topPadding + videoRange.availableHeight / 2 - height / 2
            width: 30
            height: Math.max(58, videoRange.height - 8)
            radius: 15
            color: videoRange.first.pressed ? "#D9D7FF" : "#FFFFFF"
            border.color: "#6E68D8"
            border.width: 2
            Rectangle { anchors.centerIn: parent; width: 3; height: 25; radius: 2; color: "#5A56A7" }
        }
        second.handle: Rectangle {
            x: videoRange.leftPadding + videoRange.second.visualPosition * (videoRange.availableWidth - width)
            y: videoRange.topPadding + videoRange.availableHeight / 2 - height / 2
            width: 30
            height: Math.max(58, videoRange.height - 8)
            radius: 15
            color: videoRange.second.pressed ? "#D9D7FF" : "#FFFFFF"
            border.color: "#6E68D8"
            border.width: 2
            Rectangle { anchors.centerIn: parent; width: 3; height: 25; radius: 2; color: "#5A56A7" }
        }
    }

    Row {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        height: 18
        Repeater {
            model: 5
            Text {
                width: parent.width / 5
                text: root.clock(root.duration * index / 4)
                color: "#E8EAF3"
                font.pixelSize: 9
                font.family: "Consolas"
                horizontalAlignment: index === 0 ? Text.AlignLeft : (index === 4 ? Text.AlignRight : Text.AlignHCenter)
                style: Text.Outline
                styleColor: "#99000000"
            }
        }
    }
}
