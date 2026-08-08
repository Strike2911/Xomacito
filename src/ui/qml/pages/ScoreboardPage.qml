import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    signal connectRequested()
    property var viewState: socialController.state
    property var ranking: viewState.leaderboard || []

    function rowAt(index) {
        return index >= 0 && index < ranking.length ? ranking[index] : null
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            ColumnLayout {
                spacing: 1
                Text { text: "COMUNIDAD"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3 }
                Text { text: "La Liga de Xomacito"; color: theme.colors.text; font.pixelSize: 22; font.weight: Font.DemiBold }
                Text { text: "Celebra tu progreso, mantén tu racha y descubre quién domina la colección."; color: theme.colors.textMuted; font.pixelSize: 11 }
            }
            Item { Layout.fillWidth: true }
            XButton { text: viewState.busy ? "Actualizando…" : "Actualizar"; kind: "secondary"; enabled: viewState.configured && !viewState.busy; onClicked: socialController.refresh() }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 104
            Layout.minimumHeight: 104
            Layout.maximumHeight: 104
            spacing: 10

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                cardColor: theme.colors.surfaceRaised
                border.color: viewState.authenticated ? theme.colors.primary : theme.colors.border
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 14
                    Rectangle {
                        width: 62; height: 62; radius: 31
                        color: theme.colors.surfaceSoft
                        border.width: 2; border.color: viewState.authenticated ? theme.colors.primary : theme.colors.border
                        Text { anchors.centerIn: parent; text: viewState.currentRank > 0 ? "#" + viewState.currentRank : "ID"; color: theme.colors.text; font.pixelSize: 19; font.weight: Font.Bold }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 3
                        Text { text: viewState.authenticated ? viewState.username : "Tu lugar en la liga"; color: theme.colors.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Text { text: viewState.authenticated ? "Tu progreso personal" : "Conecta una ID para guardar tu progreso"; color: theme.colors.textMuted; font.pixelSize: 10 }
                        RowLayout {
                            spacing: 12
                            Text { text: "↓ " + (viewState.currentDownloads || 0); color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                            Text { text: "🐱 " + (viewState.currentCats || 0); color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                            Rectangle {
                                visible: (viewState.currentStreak || 0) > 0
                                implicitWidth: streakText.implicitWidth + 14; implicitHeight: 24; radius: 12
                                color: theme.colors.surfaceSoft; border.color: theme.colors.accent
                                Text { id: streakText; anchors.centerIn: parent; text: "🔥 " + (viewState.currentStreak || 0) + " días"; color: theme.colors.accent; font.pixelSize: 10; font.weight: Font.Bold }
                            }
                        }
                    }
                    XButton { visible: !viewState.authenticated; text: "Conectar ID"; onClicked: root.connectRequested() }
                    XButton { visible: viewState.authenticated; text: "Cerrar sesión"; kind: "ghost"; onClicked: socialController.signOut() }
                }
            }

            XCard {
                Layout.preferredWidth: Math.min(430, root.width * 0.38)
                Layout.fillHeight: true
                cardColor: theme.colors.surfaceSoft
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 22
                    ColumnLayout { spacing: 2; Text { text: ranking.length; color: theme.colors.primary; font.pixelSize: 22; font.weight: Font.Bold } Text { text: "JUGADORES"; color: theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.Bold } }
                    Rectangle { width: 1; Layout.fillHeight: true; color: theme.colors.border }
                    ColumnLayout { spacing: 2; Text { text: viewState.activePlayers || 0; color: theme.colors.accent; font.pixelSize: 22; font.weight: Font.Bold } Text { text: "ACTIVOS HOY"; color: theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.Bold } }
                    Rectangle { width: 1; Layout.fillHeight: true; color: theme.colors.border }
                    ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: viewState.communityDownloads || 0; color: theme.colors.text; font.pixelSize: 22; font.weight: Font.Bold } Text { text: "DESCARGAS"; color: theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.Bold } }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            XCard {
                Layout.preferredWidth: Math.min(420, root.width * 0.34)
                Layout.fillHeight: true
                cardColor: theme.colors.surfaceRaised
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 9
                    Text { text: "PODIO DE LA SEMANA"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                    Text { text: "Las leyendas de la comunidad"; color: theme.colors.text; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Repeater {
                        model: Math.min(3, ranking.length)
                        delegate: Rectangle {
                            required property int index
                            property var player: root.rowAt(index)
                            Layout.fillWidth: true; Layout.fillHeight: true
                            radius: 12
                            color: index === 0 ? theme.colors.surfaceSoft : "transparent"
                            border.width: 1; border.color: index === 0 ? theme.colors.accent : theme.colors.border
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 10; spacing: 10
                                Rectangle {
                                    width: 38; height: 38; radius: 19
                                    color: index === 0 ? theme.colors.accent : theme.colors.surfaceSoft
                                    Text { anchors.centerIn: parent; text: index === 0 ? "👑" : "#" + (index + 1); color: index === 0 ? "#111111" : theme.colors.text; font.pixelSize: 13; font.weight: Font.Bold }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 1
                                    RowLayout {
                                        Layout.fillWidth: true; spacing: 6
                                        Text { Layout.fillWidth: true; text: player ? player.username : ""; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideRight }
                                        Text { visible: player && player.streak > 0; text: "🔥 " + (player ? player.streak : 0); color: player && player.activeToday ? theme.colors.accent : theme.colors.textMuted; font.pixelSize: 10; font.weight: Font.Bold }
                                    }
                                    Text { text: player ? player.downloads + " descargas  ·  " + player.cats + " gatos" : ""; color: theme.colors.textMuted; font.pixelSize: 10 }
                                }
                            }
                        }
                    }
                    Text { Layout.fillWidth: true; visible: ranking.length === 0; text: viewState.busy ? "Preparando el podio…" : "La liga espera a sus primeros jugadores."; color: theme.colors.textMuted; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                cardColor: theme.colors.surfaceRaised
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout { spacing: 1; Text { text: "RANKING GLOBAL"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1 } Text { text: "Top 100 · descargas, colección y constancia"; color: theme.colors.textMuted; font.pixelSize: 10 } }
                        Item { Layout.fillWidth: true }
                        Text { text: "🔥 = racha diaria"; color: theme.colors.textMuted; font.pixelSize: 10 }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; spacing: 5; model: ranking
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width; height: 48; radius: 11
                            color: modelData.username === viewState.username ? theme.colors.surfaceSoft : "transparent"
                            border.width: modelData.username === viewState.username ? 1 : 0
                            border.color: theme.colors.primary
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 11; anchors.rightMargin: 11; spacing: 8
                                Text { Layout.preferredWidth: 34; text: "#" + modelData.rank; color: modelData.rank <= 3 ? theme.colors.accent : theme.colors.textMuted; font.pixelSize: 12; font.weight: Font.Bold }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 0
                                    RowLayout {
                                        Layout.fillWidth: true; spacing: 7
                                        Text { text: modelData.username; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideRight }
                                        Rectangle { visible: modelData.username === viewState.username; implicitWidth: 30; implicitHeight: 17; radius: 8; color: theme.colors.primary; Text { anchors.centerIn: parent; text: "TÚ"; color: "#06151a"; font.pixelSize: 8; font.weight: Font.Bold } }
                                        Item { Layout.fillWidth: true }
                                    }
                                    Text { text: "Mejor racha: " + modelData.bestStreak + " días"; color: theme.colors.textMuted; font.pixelSize: 9 }
                                }
                                Rectangle {
                                    visible: modelData.streak > 0
                                    implicitWidth: flameRow.implicitWidth + 14; implicitHeight: 25; radius: 12
                                    color: theme.colors.surfaceSoft; border.color: modelData.activeToday ? theme.colors.accent : theme.colors.border
                                    RowLayout { id: flameRow; anchors.centerIn: parent; spacing: 3; Text { text: "🔥"; font.pixelSize: 12 } Text { text: modelData.streak; color: modelData.activeToday ? theme.colors.accent : theme.colors.textMuted; font.pixelSize: 10; font.weight: Font.Bold } }
                                }
                                Text { Layout.preferredWidth: 72; text: "↓ " + modelData.downloads; color: theme.colors.text; font.pixelSize: 11; horizontalAlignment: Text.AlignRight }
                                Text { Layout.preferredWidth: 62; text: "🐱 " + modelData.cats; color: theme.colors.primary; font.pixelSize: 11; horizontalAlignment: Text.AlignRight }
                            }
                        }
                        Text { anchors.centerIn: parent; visible: parent.count === 0; text: viewState.busy ? "Cargando comunidad…" : "Aún no hay jugadores en el scoreboard."; color: theme.colors.textMuted; font.pixelSize: 11 }
                    }
                }
            }
        }
    }
}
