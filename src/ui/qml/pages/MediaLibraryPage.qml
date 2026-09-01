import QtQuick

Item {
    Rectangle {
        anchors.centerIn: parent
        width: Math.min(460, parent.width - 40)
        height: 148
        radius: 18
        color: theme.colors.surfaceRaised
        border.color: theme.colors.border

        Column {
            anchors.centerIn: parent
            width: parent.width - 46
            spacing: 10
            Text {
                width: parent.width
                text: "Biblioteca en preparación"
                color: theme.colors.text
                font.pixelSize: 20
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                width: parent.width
                text: "Este espacio está vacío por ahora. Aquí podrás organizar tus archivos en una próxima actualización."
                color: theme.colors.textMuted
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }
}
