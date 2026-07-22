import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string label: ""
    property string hint: ""
    property bool compact: false
    default property alias content: holder.data
    spacing: compact ? 4 : 7
    Text { text: root.label; visible: text.length > 0; color: theme.colors.textMuted; font.pixelSize: root.compact ? 10 : 11; font.weight: Font.DemiBold }
    RowLayout { id: holder; Layout.fillWidth: true; spacing: 8 }
    Text { text: root.hint; visible: text.length > 0; color: theme.colors.textDim; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
}
