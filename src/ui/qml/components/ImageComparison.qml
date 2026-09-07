import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property url originalSource
    property url resultSource
    readonly property bool ready: resultSource.toString().length > 0
    property real split: 0.5
    color: theme.colors.backgroundAlt
    radius: 14
    clip: true
    onOriginalSourceChanged: split = 0.5
    onResultSourceChanged: split = 0.5
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            for (var y = 0; y < height; y += 16)
                for (var x = 0; x < width; x += 16) {
                    ctx.fillStyle = (x / 16 + y / 16) % 2 ? "#24272D" : "#1C1F24"
                    ctx.fillRect(x, y, 16, 16)
                }
        }
    }
    Image { anchors.fill: parent; anchors.margins: 12; source: root.ready ? root.resultSource : root.originalSource; fillMode: Image.PreserveAspectFit; cache: false }
    Item {
        width: parent.width * root.split; height: parent.height; clip: true; visible: root.ready
        Rectangle { anchors.fill: parent; color: theme.colors.backgroundAlt }
        Image { x: 12; y: 12; width: root.width - 24; height: root.height - 24; source: root.originalSource; fillMode: Image.PreserveAspectFit; cache: false }
    }
    Text { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 14; text: root.ready ? "ANTES" : "ORIGINAL"; color: "white"; font.pixelSize: 10; font.bold: true; style: Text.Outline; styleColor: "#17191F" }
    Text { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; visible: root.ready; text: "DESPUÉS"; color: "white"; font.pixelSize: 10; font.bold: true; style: Text.Outline; styleColor: "#17191F" }
    Rectangle { x: root.width * root.split - 1; width: 2; height: parent.height; visible: root.ready; color: "white" }
    Rectangle {
        x: Math.max(0, Math.min(root.width - width, root.width * root.split - width / 2))
        anchors.verticalCenter: parent.verticalCenter
        width: 36; height: 36; radius: 18; visible: root.ready
        color: theme.colors.surfaceRaised; border.color: "white"
        Text { anchors.centerIn: parent; text: "↔"; color: "white"; font.pixelSize: 21 }
    }
    Slider {
        objectName: "imageComparisonSlider"
        anchors.fill: parent
        visible: root.ready
        from: 0; to: 1; value: root.split; stepSize: 0.01
        padding: 0; live: true
        background: Item {}
        handle: Item { width: 0; height: 0 }
        onMoved: root.split = value
        Accessible.name: "Comparar antes y después"
        ToolTip.visible: hovered
        ToolTip.text: "Arrastra o usa las flechas para comparar"
    }
}
