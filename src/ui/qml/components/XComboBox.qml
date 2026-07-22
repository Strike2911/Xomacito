import QtQuick
import QtQuick.Controls

ComboBox {
    id: root
    property bool selectionReady: false
    property bool compact: false
    signal valueSelected(string value)
    implicitHeight: compact ? 36 : 42
    leftPadding: compact ? 11 : 13
    rightPadding: 34
    font.pixelSize: compact ? 11 : 12
    focusPolicy: Qt.StrongFocus
    Component.onCompleted: selectionReady = true
    onActivated: root.valueSelected(root.currentText)
    onCurrentIndexChanged: {
        // Algunos estilos personalizados de ComboBox actualizan currentIndex
        // sin emitir activated. Reemitirlo aquí garantiza que ratón, teclado y
        // delegado personalizado ejecuten el controlador asociado.
        if (selectionReady && currentIndex >= 0)
            root.valueSelected(root.currentText)
    }
    contentItem: Text {
        text: root.displayText
        color: root.enabled ? theme.colors.text : theme.colors.textDim
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Text {
        text: "⌄"
        color: theme.colors.primary
        font.pixelSize: 17
        rightPadding: 12
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
    }
    background: Rectangle {
        radius: 10
        color: theme.colors.surfaceSoft
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? theme.colors.primary : theme.colors.border
    }
    popup: Popup {
        y: root.height + 5
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 330)
        padding: 4
        background: Rectangle { radius: 12; color: theme.colors.surfaceRaised; border.color: theme.colors.border; border.width: 1 }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }
    delegate: ItemDelegate {
        required property var model
        required property int index
        width: root.width - 8
        height: 38
        highlighted: root.highlightedIndex === index
        contentItem: Text { text: root.textAt(index); color: theme.colors.text; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; font.pixelSize: 12 }
        background: Rectangle { radius: 8; color: highlighted ? theme.colors.primary : "transparent" }
        onClicked: {
            root.currentIndex = index
            root.activated(index)
            root.popup.close()
        }
    }
}
