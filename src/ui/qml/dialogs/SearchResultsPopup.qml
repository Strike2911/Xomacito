import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Popup {
    id: dialog
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(1220, parent ? parent.width - 36 : 1000)
    height: Math.min(780, parent ? parent.height - 36 : 650)
    modal: true; focus: true; padding: 18
    property var state: quickController.state
    property var previewState: quickController.previewController.state
    property bool gridMode: true
    property bool showPreview: Boolean(previewState.open)
    closePolicy: Popup.CloseOnEscape
    background: Rectangle { color: theme.colors.surface; radius: 18; border.color: theme.colors.border }
    onClosed: { quickController.cancelDiscovery(); quickController.previewController.close() }
    onOpened: query.forceActiveFocus()
    function clock(seconds) { return resultPreview.clock(Number(seconds || 0) * 1000) }
    function views(value) {
        if (value >= 1000000) return (value / 1000000).toFixed(1) + " M vistas"
        if (value >= 1000) return (value / 1000).toFixed(1) + " mil vistas"
        return value > 0 ? value + " vistas" : ""
    }

    contentItem: ColumnLayout {
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Buscar medios"; color: theme.colors.text; font.pixelSize: 15; font.weight: Font.DemiBold }
            XButton { text: "×"; implicitWidth: 30; implicitHeight: 28; leftPadding: 4; rightPadding: 4; compact: true; kind: "ghost"; onClicked: dialog.close() }
        }
        RowLayout {
            Layout.fillWidth: true; visible: dialog.state.discoverySource !== "playlist"
            XComboBox { id: searchSource; model: ["YouTube", "SoundCloud"]; currentIndex: Math.max(0, model.indexOf(dialog.state.discoverySource)); Layout.preferredWidth: 132; compact: true }
            XTextField { id: query; Layout.fillWidth: true; text: dialog.state.discoveryQuery; placeholderText: "Busca videos o música y presiona Enter…"; onAccepted: quickController.discover(text, searchSource.currentText) }
            XButton { text: "Buscar"; compact: true; enabled: query.text.trim().length > 0; onClicked: quickController.discover(query.text, searchSource.currentText) }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 6
            Text { Layout.fillWidth: true; text: resultGrid.count + " resultados · " + dialog.state.discoverySelected + " seleccionados"; color: theme.colors.textMuted; font.pixelSize: 11 }
            XButton { text: "Cargar más"; visible: dialog.state.discoveryHasMore; compact: true; enabled: !dialog.state.discovering; kind: "ghost"; onClicked: quickController.loadMoreDiscovery() }
            XButton { text: "Todos"; compact: true; implicitWidth: 64; kind: "ghost"; onClicked: quickController.chooseAllDiscovery(true) }
            XButton { text: "Ninguno"; compact: true; implicitWidth: 80; kind: "ghost"; onClicked: quickController.chooseAllDiscovery(false) }
            XButton { text: dialog.gridMode ? "☷ Lista" : "▦ Cuadrícula"; compact: true; kind: "secondary"; onClicked: dialog.gridMode = !dialog.gridMode }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Item {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 230
                GridView {
                    id: resultGrid; objectName: "searchResultsGrid"; anchors.fill: parent; visible: dialog.gridMode
                    clip: true; model: quickController.discoveryModel
                    cellWidth: width / Math.max(1, Math.floor(width / 225)); cellHeight: cellWidth * 0.5625 + 98
                    delegate: resultCard; ScrollBar.vertical: XScrollBar {}
                }
                ListView {
                    id: resultList; objectName: "searchResultsList"; anchors.fill: parent; visible: !dialog.gridMode
                    clip: true; spacing: 8; model: quickController.discoveryModel
                    delegate: resultCard; ScrollBar.vertical: XScrollBar {}
                }
                Text { visible: resultGrid.count === 0; anchors.centerIn: parent; text: dialog.state.discovering ? "Buscando resultados…" : dialog.state.discoveryQuery ? "No se encontraron resultados." : "Busca videos o música por nombre."; color: theme.colors.textMuted }
                Rectangle { visible: dialog.state.discovering && resultGrid.count === 0; anchors.fill: parent; radius: 12; color: "#A0151821"; BusyIndicator { anchors.centerIn: parent; running: parent.visible } }
            }
            XCard {
                visible: dialog.showPreview; Layout.preferredWidth: Math.min(420, dialog.width * 0.38); Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "VISTA PREVIA"; Layout.fillWidth: true; color: theme.colors.accent; font.pixelSize: 10; font.letterSpacing: 1 }
                        XButton { text: "×"; implicitWidth: 30; leftPadding: 5; rightPadding: 5; compact: true; kind: "ghost"; onClicked: quickController.previewController.close() }
                    }
                    MediaPreview {
                        id: resultPreview; objectName: "searchInteractivePreview"
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 190
                        source: dialog.previewState.source; kind: dialog.previewState.kind
                        title: dialog.previewState.title; poster: dialog.previewState.poster
                        loading: dialog.previewState.busy; externalError: dialog.previewState.error
                        active: dialog.opened && dialog.showPreview; autoPlay: true
                        playerObjectName: "searchPreviewPlayer"
                        onRetryRequested: quickController.previewController.retry()
                    }
                    Text { Layout.fillWidth: true; text: dialog.previewState.title; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                    Text { Layout.fillWidth: true; text: dialog.previewState.detail; color: theme.colors.textDim; font.pixelSize: 10; wrapMode: Text.WordWrap }
                    XButton { Layout.fillWidth: true; text: "Abrir en el sitio"; compact: true; kind: "ghost"; onClicked: quickController.openPreviewSource() }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Ver / doble clic: reproducir · Marca las casillas para descargar"; color: theme.colors.textDim; font.pixelSize: 10; wrapMode: Text.WordWrap }
            XButton { text: "Descargar " + dialog.state.discoverySelected + (dialog.state.discoverySelected === 1 ? " seleccionado" : " seleccionados"); compact: true; enabled: dialog.state.discoverySelected > 0 && !dialog.state.discovering; onClicked: { quickController.enqueueDiscovery(); dialog.close() } }
        }
    }
    Component {
        id: resultCard
        Rectangle {
            id: card
            property bool isGrid: GridView.view !== null
            width: isGrid ? resultGrid.cellWidth - 9 : resultList.width - 5
            height: isGrid ? resultGrid.cellHeight - 9 : 112
            color: model.chosen ? theme.colors.surfaceSoft : hover.containsMouse ? theme.colors.surfaceRaised : theme.colors.background
            radius: 11; border.color: model.chosen || dialog.previewState.pageUrl === model.url && dialog.showPreview ? theme.colors.accent : theme.colors.border
            Behavior on color { ColorAnimation { duration: 120 } }
            MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true; onDoubleClicked: quickController.previewDiscovery(index) }
            Rectangle {
                id: thumb
                x: 7; y: 7; width: card.isGrid ? parent.width - 14 : 148; height: card.isGrid ? width * 9/16 : parent.height - 14
                radius: 7; color: theme.colors.surfaceRaised; clip: true
                Image { anchors.fill: parent; source: model.thumbnail || ""; sourceSize.width: 480; asynchronous: true; fillMode: Image.PreserveAspectCrop }
                Text { anchors.centerIn: parent; visible: !model.thumbnail; text: "▷"; color: theme.colors.accent; font.pixelSize: 26 }
                MouseArea { anchors.fill: parent; onClicked: quickController.previewDiscovery(index) }
                Rectangle {
                    anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 5
                    width: timeText.implicitWidth + 12; height: 20; radius: 4; color: "#DE090B12"
                    Text { id: timeText; anchors.centerIn: parent; text: model.isLive ? "EN VIVO" : dialog.clock(model.duration); color: "white"; font.pixelSize: 10 }
                }
                CheckBox {
                    anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 3; width: 30; height: 30
                    checked: Boolean(model.chosen); onToggled: quickController.chooseDiscovery(index, checked)
                    indicator: Rectangle {
                        x: 4; y: 4; width: 22; height: 22; radius: 5; color: parent.checked ? theme.colors.primary : "#DD11151D"; border.color: parent.checked ? theme.colors.accent : "#ABB4C5"
                        Text { anchors.centerIn: parent; text: parent.parent.checked ? "✓" : ""; color: "white"; font.pixelSize: 16 }
                    }
                }
            }
            Column {
                id: caption
                x: card.isGrid ? 10 : thumb.x + thumb.width + 12; y: card.isGrid ? thumb.y + thumb.height + 8 : 12
                width: card.width - x - 10; spacing: 5
                Text { width: parent.width; text: model.title; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                Text { width: parent.width - 55; text: (model.channel || "") + (model.views ? " · " + dialog.views(model.views) : ""); color: theme.colors.textMuted; font.pixelSize: 10; elide: Text.ElideRight }
            }
            XButton { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 5; text: "Ver ▶"; compact: true; implicitWidth: 60; leftPadding: 6; rightPadding: 6; kind: "ghost"; onClicked: quickController.previewDiscovery(index) }
        }
    }
}
