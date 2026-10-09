import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property url originalSource
    property url resultSource
    property bool compareEnabled: true
    readonly property bool ready: compareEnabled && resultSource.toString().length > 0
    property real split: 0.5
    property real zoom: 1
    color: theme.colors.backgroundAlt; radius: 10; clip: true
    function resetView() { zoom = 1; canvas.contentX = 0; canvas.contentY = 0 }
    onOriginalSourceChanged: { split = 0.5; resetView() }
    onResultSourceChanged: { split = 0.5; compareEnabled = true }
    Flickable {
        id: canvas; anchors.fill: parent; clip: true
        contentWidth: width * root.zoom; contentHeight: height * root.zoom
        interactive: root.zoom > 1 && !root.ready; boundsBehavior: Flickable.StopAtBounds
        Item {
            width: canvas.contentWidth; height: canvas.contentHeight
            Canvas {
                anchors.fill: parent
                onWidthChanged: requestPaint(); onHeightChanged: requestPaint()
                onPaint: {
                    var ctx = getContext("2d")
                    for (var y=0; y<height; y+=14) for (var x=0; x<width; x+=14) { ctx.fillStyle = (x/14+y/14)%2 ? "#191C23" : "#16191F"; ctx.fillRect(x,y,14,14) }
                }
            }
            Image { anchors.fill: parent; anchors.margins: 18; source: root.resultSource.toString() ? root.resultSource : root.originalSource; fillMode: Image.PreserveAspectFit; cache: false }
            Item {
                width: parent.width * root.split; height: parent.height; clip: true; visible: root.ready
                Rectangle { anchors.fill: parent; color: theme.colors.backgroundAlt }
                Image { x: 18; y: 18; width: canvas.contentWidth-36; height: canvas.contentHeight-36; source: root.originalSource; fillMode: Image.PreserveAspectFit; cache: false }
            }
            Rectangle { x: parent.width * root.split-1; width: 2; height: parent.height; visible: root.ready; color: theme.colors.accent }
            Rectangle {
                x: Math.max(0, Math.min(parent.width-width, parent.width*root.split-width/2)); anchors.verticalCenter: parent.verticalCenter
                width: 18; height: 36; radius: 6; visible: root.ready; color: theme.colors.primary; border.color: theme.colors.text
                Text { anchors.centerIn: parent; text: "↔"; color: "white"; font.pixelSize: 12 }
            }
            Slider {
                objectName: "imageComparisonSlider"; anchors.fill: parent; visible: root.ready
                from: 0; to: 1; value: root.split; stepSize: 0.01; padding: 0; live: true
                background: Item {} handle: Item { width: 0; height: 0 }
                onMoved: root.split = value; Accessible.name: "Comparar antes y después"
            }
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.NoButton; onWheel: function(wheel) { root.zoom = Math.max(1, Math.min(6, root.zoom * (wheel.angleDelta.y > 0 ? 1.15 : 1/1.15))); if (root.zoom === 1) root.resetView(); wheel.accepted = true } }
        }
    }
    Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 8; width: label.implicitWidth+16; height: 24; radius: 5; color: "#C0181B22"
        Text { id: label; anchors.centerIn: parent; text: root.ready ? "Antes / después" : root.resultSource.toString() ? "Resultado" : "Original"; color: "#ECEEF5"; font.pixelSize: 10 }
    }
    Row { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 8; spacing: 4
        XButton { text: "−"; implicitWidth: 26; implicitHeight: 26; leftPadding: 3; rightPadding: 3; compact: true; kind: "secondary"; onClicked: { root.zoom = Math.max(1, root.zoom/1.25); if (root.zoom === 1) root.resetView() } }
        XButton { text: Math.round(root.zoom*100)+"%"; implicitWidth: 48; implicitHeight: 26; leftPadding: 3; rightPadding: 3; compact: true; kind: "secondary"; onClicked: root.resetView(); ToolTip.visible: hovered; ToolTip.text: "Ajustar a la vista" }
        XButton { text: "+"; implicitWidth: 26; implicitHeight: 26; leftPadding: 3; rightPadding: 3; compact: true; kind: "secondary"; onClicked: root.zoom = Math.min(6, root.zoom*1.25) }
    }
}
