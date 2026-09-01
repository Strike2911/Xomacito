import QtQuick
import QtQuick.Controls

Item {
    id: root
    property real duration: 0
    property real inPoint: 0
    property real outPoint: duration
    property real playhead: 0
    property real zoomFactor: 1
    property real viewportStart: 0
    readonly property real viewportDuration: duration > 0 ? duration / Math.max(1, zoomFactor) : 0
    readonly property real viewportEnd: Math.min(duration, viewportStart + viewportDuration)
    property url filmstripSource: ""
    property url fallbackSource: ""
    property url waveformSource: ""
    property bool filmstripBusy: false
    property bool waveformBusy: false
    property real interactivePlayhead: playhead
    property bool scrubbing: false
    property real scrubPointerX: width / 2
    property int autoPanDirection: 0
    readonly property real autoPanEdge: Math.min(72, Math.max(42, width * 0.08))
    readonly property int timelineTickCount: width >= 900 ? 8 : 6
    signal inPointMoved(real value)
    signal outPointMoved(real value)
    signal seekRequested(real value)

    implicitHeight: 184

    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value))
    }

    function clock(seconds) {
        var value = Math.max(0, Number(seconds) || 0)
        var hours = Math.floor(value / 3600)
        var minutes = Math.floor((value % 3600) / 60)
        var secs = value % 60
        var secsText = secs.toFixed(2)
        if (secs < 10)
            secsText = "0" + secsText
        return (hours < 10 ? "0" : "") + hours + ":" +
               (minutes < 10 ? "0" : "") + minutes + ":" + secsText
    }

    function timeToX(seconds) {
        if (viewportDuration <= 0)
            return 0
        return (seconds - viewportStart) / viewportDuration * width
    }

    function xToTime(positionX) {
        if (viewportDuration <= 0)
            return 0
        return viewportStart + clamp(positionX / Math.max(1, width), 0, 1) * viewportDuration
    }

    function setZoom(value) {
        var next = clamp(Math.round(Number(value) || 1), 1, 16)
        var center = clamp(root.playhead, 0, root.duration)
        if (center <= 0 && root.outPoint > root.inPoint)
            center = (root.inPoint + root.outPoint) / 2
        zoomFactor = next
        var visible = root.duration / next
        viewportStart = clamp(center - visible / 2, 0, Math.max(0, root.duration - visible))
    }

    function panBy(seconds) {
        viewportStart = clamp(
            viewportStart + Number(seconds || 0),
            0,
            Math.max(0, duration - viewportDuration)
        )
    }

    function sourceCropRect(sourceWidth, sourceHeight) {
        var pixelWidth = Math.max(0, Number(sourceWidth) || 0)
        var pixelHeight = Math.max(0, Number(sourceHeight) || 0)
        if (zoomFactor <= 1 || duration <= 0 || pixelWidth <= 0 || pixelHeight <= 0)
            return Qt.rect(0, 0, 0, 0)
        var start = clamp(viewportStart / duration, 0, 1)
        var end = clamp(viewportEnd / duration, start, 1)
        var sourceX = Math.floor(start * pixelWidth)
        var sourceEnd = Math.min(pixelWidth, Math.ceil(end * pixelWidth))
        return Qt.rect(sourceX, 0, Math.max(1, sourceEnd - sourceX), pixelHeight)
    }

    function requestScrub(value) {
        var bounded = clamp(value, 0, duration)
        interactivePlayhead = bounded
        seekRequested(bounded)
    }

    function requestScrubAtX(positionX) {
        scrubPointerX = positionX
        if (scrubbing && zoomFactor > 1) {
            if (positionX <= autoPanEdge && viewportStart > 0)
                autoPanDirection = -1
            else if (positionX >= width - autoPanEdge && viewportEnd < duration)
                autoPanDirection = 1
            else
                autoPanDirection = 0
        }
        requestScrub(xToTime(clamp(positionX, 0, width)))
    }

    function stopScrubbing() {
        scrubbing = false
        autoPanDirection = 0
    }

    onDurationChanged: {
        zoomFactor = 1
        viewportStart = 0
    }
    onPlayheadChanged: {
        if (!scrubbing)
            interactivePlayhead = playhead
        if (zoomFactor <= 1 || viewportDuration <= 0)
            return
        if (playhead > viewportStart + viewportDuration * 0.88 && playhead < duration) {
            viewportStart = clamp(
                playhead - viewportDuration * 0.82,
                0,
                Math.max(0, duration - viewportDuration)
            )
        } else if (playhead < viewportStart + viewportDuration * 0.10 && playhead > 0) {
            viewportStart = clamp(
                playhead - viewportDuration * 0.12,
                0,
                Math.max(0, duration - viewportDuration)
            )
        }
    }

    Timer {
        id: smoothAutoPan
        interval: 16
        repeat: true
        running: root.scrubbing && root.autoPanDirection !== 0
        onTriggered: {
            var edge = Math.max(1, root.autoPanEdge)
            var depth = root.autoPanDirection < 0
                      ? (edge - Math.max(0, root.scrubPointerX)) / edge
                      : (root.scrubPointerX - (root.width - edge)) / edge
            var strength = root.clamp(depth, 0.12, 1.35)
            var previousStart = root.viewportStart
            root.panBy(root.autoPanDirection * root.viewportDuration * (0.0035 + 0.014 * strength))
            root.requestScrub(root.xToTime(root.clamp(root.scrubPointerX, 0, root.width)))
            if (Math.abs(previousStart - root.viewportStart) < 0.0001)
                root.autoPanDirection = 0
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "#090B10"
        border.color: "#343849"
        clip: true

        Rectangle {
            id: zoomRail
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 26
            color: "#12151C"
        }

        Rectangle {
            id: scrubRail
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: zoomRail.bottom
            height: 26
            color: "#20232B"
            border.color: "#343849"

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 9
                anchors.verticalCenter: parent.verticalCenter
                text: "VISIBLE  " + root.clock(root.viewportStart) + "  —  " + root.clock(root.viewportEnd)
                color: "#AEB5C5"
                font.pixelSize: 9
                font.family: "Consolas"
                font.weight: Font.DemiBold
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.SizeHorCursor
                preventStealing: true
                onPressed: function(mouse) {
                    root.scrubbing = true
                    root.requestScrubAtX(mouse.x)
                }
                onPositionChanged: function(mouse) {
                    if (pressed)
                        root.requestScrubAtX(mouse.x)
                }
                onReleased: function(mouse) {
                    root.requestScrubAtX(mouse.x)
                    root.stopScrubbing()
                }
                onCanceled: root.stopScrubbing()
            }

            Row {
                id: zoomTools
                parent: zoomRail
                anchors.right: parent.right
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                height: 22
                spacing: 5
                z: 20

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "ZOOM"
                    color: "#AEB5C5"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                }
                Rectangle {
                    width: 22; height: 20; radius: 5
                    color: zoomOut.pressed ? "#555B6C" : "#343947"
                    border.color: "#586074"
                    Text { anchors.centerIn: parent; text: "−"; color: "white"; font.pixelSize: 14 }
                    MouseArea {
                        id: zoomOut
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.setZoom(root.zoomFactor - 1)
                    }
                }
                Slider {
                    id: zoomSlider
                    width: 78; height: 20
                    from: 1; to: 16; stepSize: 1
                    value: root.zoomFactor
                    onMoved: root.setZoom(value)
                }
                Rectangle {
                    width: 22; height: 20; radius: 5
                    color: zoomIn.pressed ? "#555B6C" : "#343947"
                    border.color: "#586074"
                    Text { anchors.centerIn: parent; text: "+"; color: "white"; font.pixelSize: 13 }
                    MouseArea {
                        id: zoomIn
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.setZoom(root.zoomFactor + 1)
                    }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 28
                    text: Math.round(root.zoomFactor) + "×"
                    color: "#D8DBE6"
                    font.pixelSize: 10
                    font.family: "Consolas"
                }
            }

        }

        Item {
            id: frames
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: scrubRail.bottom
            height: 76
            clip: true
            Image {
                id: frameProbe
                objectName: "premiereFrameProbe"
                source: root.filmstripSource
                asynchronous: true
                cache: true
                visible: false
            }
            Image {
                id: frameImage
                objectName: "premiereFrameImage"
                anchors.fill: parent
                source: root.filmstripSource
                sourceClipRect: root.sourceCropRect(frameProbe.sourceSize.width, frameProbe.sourceSize.height)
                fillMode: Image.Stretch
                asynchronous: true
                cache: true
                visible: status === Image.Ready
            }
            Row {
                anchors.fill: parent
                visible: !frameImage.visible
                Repeater {
                    model: 12
                    Image {
                        width: Math.ceil(parent.width / 12)
                        height: parent.height
                        source: root.fallbackSource
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        opacity: 0.8
                        Rectangle { anchors.fill: parent; color: "transparent"; border.color: "#242938" }
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                visible: !frameImage.visible && !root.fallbackSource
                text: root.filmstripBusy ? "Preparando fotogramas…" : "Vista de fotogramas"
                color: "#9CA4B8"
                font.pixelSize: 11
            }
        }

        Rectangle {
            id: wave
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: frames.bottom
            anchors.bottom: parent.bottom
            color: "#0B0D15"
            clip: true
            Rectangle { anchors.verticalCenter: parent.verticalCenter; width: parent.width; height: 1; color: "#3B4562" }
            Image {
                id: waveProbe
                objectName: "premiereWaveProbe"
                source: root.waveformSource
                asynchronous: true
                cache: true
                visible: false
            }
            Image {
                id: waveImage
                objectName: "premiereWaveImage"
                anchors.fill: parent
                anchors.margins: 4
                source: root.waveformSource
                sourceClipRect: root.sourceCropRect(waveProbe.sourceSize.width, waveProbe.sourceSize.height)
                fillMode: Image.Stretch
                asynchronous: true
                cache: true
                visible: status === Image.Ready
                opacity: 0.95
            }
            Text {
                anchors.centerIn: parent
                visible: !waveImage.visible
                text: root.waveformBusy ? "Analizando audio…" : "Audio"
                color: "#737C91"
                font.pixelSize: 10
            }
        }

        Item {
            id: timeGrid
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: frames.top
            anchors.bottom: parent.bottom
            z: 3
            Repeater {
                model: root.timelineTickCount + 1
                delegate: Item {
                    required property int index
                    x: Math.round(index / root.timelineTickCount * timeGrid.width)
                    width: 1
                    height: timeGrid.height
                    Rectangle {
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 1
                        color: index === 0 || index === root.timelineTickCount ? "#526078" : "#553B4562"
                    }
                    Text {
                        visible: index > 0 && index < root.timelineTickCount
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        anchors.top: parent.top
                        anchors.topMargin: 4
                        text: root.clock(root.viewportStart + index / root.timelineTickCount * root.viewportDuration)
                        color: "#D1D6E2"
                        font.pixelSize: 8
                        font.family: "Consolas"
                        style: Text.Outline
                        styleColor: "#B0000000"
                    }
                }
            }
        }

        WheelHandler {
            acceptedModifiers: Qt.NoModifier
            onWheel: function(event) {
                if (root.zoomFactor <= 1)
                    return
                var direction = event.angleDelta.y > 0 ? -1 : 1
                root.panBy(direction * root.viewportDuration * 0.08)
            }
        }

        Rectangle {
            x: root.clamp(root.timeToX(root.inPoint), 0, parent.width)
            y: frames.y
            width: Math.max(1, root.clamp(root.timeToX(root.outPoint), 0, parent.width) - x)
            height: parent.height - y
            color: "transparent"
            border.color: "#A29DFF"
            border.width: 1
        }
        Rectangle {
            y: frames.y
            width: root.clamp(root.timeToX(root.inPoint), 0, parent.width)
            height: parent.height - y
            color: "#A8070910"
        }
        Rectangle {
            x: root.clamp(root.timeToX(root.outPoint), 0, parent.width)
            y: frames.y
            width: parent.width - x
            height: parent.height - y
            color: "#A8070910"
        }

        RangeSlider {
            id: timeline
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: scrubRail.bottom
            anchors.bottom: parent.bottom
            from: root.viewportStart
            to: Math.max(from + 0.05, root.viewportEnd)
            stepSize: root.duration > 120 ? 0.1 : 0.02
            snapMode: RangeSlider.SnapOnRelease
            first.value: root.clamp(root.inPoint, from, to)
            second.value: root.clamp(root.outPoint, Math.min(to, first.value + 0.20), to)
            first.onMoved: root.inPointMoved(Math.min(first.value, root.outPoint - 0.20))
            second.onMoved: root.outPointMoved(Math.max(second.value, root.inPoint + 0.20))
            background: Item {}
            first.handle: Item {
                x: root.timeToX(root.inPoint) - width / 2
                y: 2
                width: 14; height: timeline.height - 4
                enabled: root.inPoint >= root.viewportStart && root.inPoint <= root.viewportEnd
                opacity: enabled ? 1 : 0
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 7; height: parent.height; radius: 3.5
                    color: timeline.first.pressed ? "#DAD8FF" : "#FFFFFF"
                    border.color: "#6963D4"; border.width: 1
                    Rectangle { anchors.centerIn: parent; width: 1; height: 24; color: "#56519D" }
                }
            }
            second.handle: Item {
                x: root.timeToX(root.outPoint) - width / 2
                y: 2
                width: 14; height: timeline.height - 4
                enabled: root.outPoint >= root.viewportStart && root.outPoint <= root.viewportEnd
                opacity: enabled ? 1 : 0
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 7; height: parent.height; radius: 3.5
                    color: timeline.second.pressed ? "#DAD8FF" : "#FFFFFF"
                    border.color: "#6963D4"; border.width: 1
                    Rectangle { anchors.centerIn: parent; width: 1; height: 24; color: "#56519D" }
                }
            }
        }

        Item {
            id: playheadMarker
            objectName: "premierePlayhead"
            visible: root.duration > 0
            property real boundedTime: root.clamp(root.interactivePlayhead, 0, root.duration)
            x: root.timeToX(boundedTime) - width / 2
            y: zoomRail.height
            width: 26
            height: parent.height - y
            z: 12

            Canvas {
                id: playheadHead
                anchors.top: parent.top
                anchors.topMargin: 4
                anchors.horizontalCenter: parent.horizontalCenter
                width: 15
                height: 12
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.fillStyle = "#2D9CFF"
                    ctx.beginPath()
                    ctx.moveTo(1, 1)
                    ctx.lineTo(width - 1, 1)
                    ctx.lineTo(width / 2, height - 1)
                    ctx.closePath()
                    ctx.fill()
                }
            }
            Rectangle {
                anchors.top: parent.top
                anchors.topMargin: scrubRail.height
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                width: 2
                color: "#2D9CFF"
            }
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: scrubRail.bottom
            anchors.topMargin: 5
            implicitWidth: rangeText.implicitWidth + 20
            implicitHeight: 25
            radius: 12
            color: "#E0151820"
            border.color: "#E9EAF2"
            z: 8
            visible: root.inPoint >= root.viewportStart && root.outPoint <= root.viewportEnd
            Text {
                id: rangeText
                anchors.centerIn: parent
                text: root.clock(root.inPoint) + "  →  " + root.clock(root.outPoint)
                color: "white"
                font.pixelSize: 11
                font.weight: Font.Bold
                font.family: "Consolas"
            }
        }
    }
}
