pragma Singleton
import QtCore

Settings {
    category: "WallpaperLayout"
    property real positionX: 0.5
    property real positionY: 0.5
    property real zoom: 1.0
    property string fit: "cover"
    function reset() {
        positionX = 0.5
        positionY = 0.5
        zoom = 1.0
        fit = "cover"
    }
}
