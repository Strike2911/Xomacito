import QtQuick

Rectangle {
    id: root
    property int padding: 20
    property bool elevated: false
    property color cardColor: elevated ? theme.colors.surfaceRaised : theme.colors.surface
    radius: 18
    color: cardColor
    border.width: 1
    border.color: theme.colors.border
    layer.enabled: elevated
    layer.samples: 4
}
