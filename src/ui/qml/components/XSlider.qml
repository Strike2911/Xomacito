import QtQuick
import QtQuick.Controls

Slider {
    id: control
    implicitHeight: 24
    leftPadding: 7
    rightPadding: 7
    background: Rectangle {
        x: control.leftPadding; y: (control.height - height) / 2
        width: control.availableWidth; height: 3; radius: 2; color: theme.colors.border
        Rectangle { width: control.visualPosition * parent.width; height: parent.height; radius: 2; color: theme.colors.accent }
    }
    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: (control.height - height) / 2
        width: 10; height: 10; radius: 5
        color: control.pressed ? theme.colors.primary : theme.colors.text
        border.width: 1; border.color: theme.colors.primary
        Behavior on color { ColorAnimation { duration: 100 } }
    }
}
