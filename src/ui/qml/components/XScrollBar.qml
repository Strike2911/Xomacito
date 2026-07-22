import QtQuick
import QtQuick.Controls

ScrollBar {
    id: root
    orientation: Qt.Vertical
    policy: ScrollBar.AsNeeded
    implicitWidth: 11
    padding: 2
    anchors.top: parent.top
    anchors.right: parent.right
    anchors.bottom: parent.bottom

    contentItem: Rectangle {
        implicitWidth: 7
        radius: width / 2
        color: root.pressed ? theme.colors.primary : root.hovered ? theme.colors.borderStrong : theme.colors.border
        opacity: root.active || root.hovered ? 0.95 : 0.55
        Behavior on color { ColorAnimation { duration: 120 } }
        Behavior on opacity { NumberAnimation { duration: 140 } }
    }
    background: Rectangle {
        radius: width / 2
        color: theme.colors.backgroundAlt
        opacity: 0.72
    }
}
