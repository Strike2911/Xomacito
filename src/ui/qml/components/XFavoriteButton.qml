import QtQuick
import QtQuick.Controls

Button {
    id: root
    property bool favorite: false
    property string itemName: ""
    implicitWidth: 34
    implicitHeight: 34
    padding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: (favorite ? "Quitar de favoritos" : "Añadir a favoritos")
                     + (itemName ? ": " + itemName : "")

    contentItem: Text {
        text: root.favorite ? "★" : "☆"
        color: root.favorite ? theme.colors.warning : theme.colors.text
        font.pixelSize: 19
        font.weight: Font.Bold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 9
        color: root.down ? theme.colors.surfaceRaised
                         : root.hovered ? theme.colors.surfaceSoft
                                        : theme.colors.backgroundAlt
        border.width: root.activeFocus || root.hovered ? 2 : 1
        border.color: root.favorite ? theme.colors.warning
                                    : root.activeFocus ? theme.colors.primary
                                                       : theme.colors.borderStrong
    }
    ToolTip.visible: hovered
    ToolTip.delay: 450
    ToolTip.text: favorite ? "Quitar de favoritos" : "Añadir a favoritos"
}
