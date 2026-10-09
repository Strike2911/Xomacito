import QtQuick

Canvas {
    id: root
    property string name: "background"
    property color color: "white"
    implicitWidth: 24
    implicitHeight: 24
    onNameChanged: requestPaint()
    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset(); c.scale(width / 24, height / 24)
        c.strokeStyle = color; c.fillStyle = color
        c.lineWidth = 1.65; c.lineCap = "round"; c.lineJoin = "round"
        function line(points) {
            c.beginPath(); c.moveTo(points[0], points[1])
            for (var i = 2; i < points.length; i += 2) c.lineTo(points[i], points[i + 1])
            c.stroke()
        }
        if (name === "background") {
            // Subject silhouette, with detached corners representing its background.
            line([3,8,3,3,8,3]); line([16,3,21,3,21,8])
            line([3,16,3,21,8,21]); line([16,21,21,21,21,16])
            c.beginPath(); c.arc(12,9,3,0,Math.PI*2); c.stroke()
            c.beginPath(); c.moveTo(6.5,18); c.bezierCurveTo(6.5,12,17.5,12,17.5,18); c.stroke()
        } else if (name === "upscale") {
            line([14,3,21,3,21,10]); line([21,3,13,11])
            line([10,21,3,21,3,14]); line([3,21,11,13])
            line([4,4,8,4,8,8,4,8,4,4]); line([16,16,20,16,20,20,16,20,16,16])
        } else {
            line([9,3,20,3,20,14]); line([20,3,16,7])
            line([4,7,4,21,17,21,17,10,4,10])
            line([5,18,9,14,12,17,14,15,17,18])
        }
    }
}
