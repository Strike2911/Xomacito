import QtQuick
import "../wallpaper"

Item {
    id: root
    property alias source: picture.source
    property real imageOpacity: 0.5
    property bool interactive: false
    readonly property real imageWidth: picture.width
    readonly property real imageHeight: picture.height
    clip: true
    Image {
        id: picture
        readonly property real factor: implicitWidth > 0 && implicitHeight > 0
            ? (WallpaperLayout.fit === "contain"
               ? Math.min(root.width / implicitWidth, root.height / implicitHeight)
               : Math.max(root.width / implicitWidth, root.height / implicitHeight)) : 1
        width: implicitWidth * factor * WallpaperLayout.zoom
        height: implicitHeight * factor * WallpaperLayout.zoom
        x: (root.width - width) * (width <= root.width ? 0.5 : WallpaperLayout.positionX)
        y: (root.height - height) * (height <= root.height ? 0.5 : WallpaperLayout.positionY)
        opacity: root.imageOpacity
        sourceSize.width: 2560
        asynchronous: true
        cache: true
        fillMode: Image.Stretch
    }
    MouseArea {
        anchors.fill: parent
        enabled: root.interactive && picture.status === Image.Ready
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property real previousX: 0
        property real previousY: 0
        onPressed: function(mouse) { previousX = mouse.x; previousY = mouse.y }
        onPositionChanged: function(mouse) {
            if (!pressed) return
            if (picture.width > root.width + 1)
                WallpaperLayout.positionX = Math.max(0, Math.min(1, WallpaperLayout.positionX + (mouse.x - previousX) / (root.width - picture.width)))
            if (picture.height > root.height + 1)
                WallpaperLayout.positionY = Math.max(0, Math.min(1, WallpaperLayout.positionY + (mouse.y - previousY) / (root.height - picture.height)))
            previousX = mouse.x
            previousY = mouse.y
        }
    }
}
