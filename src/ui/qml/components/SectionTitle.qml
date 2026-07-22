import QtQuick
import QtQuick.Layouts

RowLayout {
    id: root
    property string eyebrow: ""
    property string title: ""
    property string description: ""
    property string number: ""
    property bool compact: false
    spacing: compact ? 8 : 12
    ColumnLayout {
        Layout.fillWidth: true
        spacing: compact ? 2 : 4
        Text { text: root.eyebrow.toUpperCase(); visible: text.length > 0; color: theme.colors.primary; font.pixelSize: root.compact ? 9 : 10; font.weight: Font.Bold; font.letterSpacing: 1.2 }
        Text { text: root.title; color: theme.colors.text; font.pixelSize: root.compact ? 18 : 21; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Text { text: root.description; visible: text.length > 0 && !root.compact; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
    Text { text: root.number; visible: text.length > 0; color: theme.colors.textDim; font.pixelSize: root.compact ? 10 : 12; Layout.alignment: Qt.AlignTop }
}
