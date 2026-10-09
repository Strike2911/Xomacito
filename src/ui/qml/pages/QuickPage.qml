import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../dialogs"

ColumnLayout {
    id: page
    objectName: "quickWorkspace"
    property var viewState: quickController.state
    property bool historyOpen: false
    spacing: 10
    onVisibleChanged: if (!visible) quickController.previewController.close()
    Connections { target: quickController; function onDiscoveryReady() { discoveryPopup.open() } }
    XCard {
        Layout.fillWidth: true; implicitHeight: quickControls.implicitHeight + 24
        ColumnLayout {
            id: quickControls; anchors.fill: parent; anchors.margins: 12; spacing: 8
            RowLayout {
                Layout.fillWidth: true; spacing: 7
                XButton { text: "⌕"; implicitWidth: 36; leftPadding: 6; rightPadding: 6; compact: true; kind: "secondary"; onClicked: discoveryPopup.open(); ToolTip.visible: hovered; ToolTip.text: "Buscar en YouTube o SoundCloud" }
                XTextField {
                    objectName: "quickUrls"; Layout.fillWidth: true; Layout.minimumWidth: 130
                    text: page.viewState.url; placeholderText: "Pega uno o varios enlaces…"
                    onTextEdited: quickController.setValue("url", text)
                    onAccepted: quickController.enqueue()
                }
                XButton { text: page.viewState.ranges.length ? "✂ " + page.viewState.ranges.length : "✂"; implicitWidth: 42; leftPadding: 6; rightPadding: 6; compact: true; kind: page.viewState.ranges.length ? "primary" : "secondary"; onClicked: cutsPopup.open(); ToolTip.visible: hovered; ToolTip.text: "Preparar recortes" }
                XComboBox { Layout.preferredWidth: page.width < 1050 ? 115 : 150; compact: true; model: downloadController.downloadTags; currentIndex: Math.max(0, model.indexOf(page.viewState.selectedTag)); onActivated: quickController.setValue("selectedTag", currentText) }
                XComboBox { Layout.preferredWidth: 110; compact: true; model: ["Video", "Audio"]; currentIndex: model.indexOf(page.viewState.mode); onActivated: quickController.setValue("mode", currentText) }
                XComboBox {
                    Layout.preferredWidth: 128; compact: true
                    model: page.viewState.mode === "Audio" ? ["MP3 128", "MP3 192", "MP3 320", "WAV"] : ["Mejor disponible", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
                    currentIndex: Math.max(0, model.indexOf(page.viewState.mode === "Audio" ? page.viewState.audioFormat : page.viewState.quality))
                    onActivated: quickController.setValue(page.viewState.mode === "Audio" ? "audioFormat" : "quality", currentText)
                }
                XButton { text: page.viewState.playlist ? "Ver lista" : "Descargar"; compact: true; enabled: page.viewState.url.trim().length > 0 && !page.viewState.discovering; onClicked: quickController.enqueue() }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                XSwitch { text: "Lista de reproducción"; checked: page.viewState.playlist; onToggled: quickController.setValue("playlist", checked) }
                XSwitch { text: "Miniatura"; checked: page.viewState.thumbnail; enabled: !page.viewState.thumbnailOnly; onToggled: quickController.setValue("thumbnail", checked) }
                XSwitch { text: "Solo miniatura"; checked: page.viewState.thumbnailOnly; onToggled: quickController.setValue("thumbnailOnly", checked) }
                Item { Layout.fillWidth: true }
                Text { visible: page.viewState.discovering; text: "Buscando…"; color: theme.colors.accent; font.pixelSize: 11 }
                XButton { text: "Postprocesar  ⚙"; compact: true; kind: page.viewState.postprocess || page.viewState.sendPremiere ? "primary" : "ghost"; onClicked: postPopup.open() }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Text { text: "Actividad"; font.pixelSize: 14; font.weight: Font.DemiBold; color: theme.colors.text }
        Text { text: page.viewState.pending + " en espera"; font.pixelSize: 11; color: theme.colors.textDim }
        Item { Layout.fillWidth: true }
        XButton { text: "Historial"; compact: true; kind: page.historyOpen ? "primary" : "ghost"; onClicked: page.historyOpen = !page.historyOpen }
        XButton { text: "Cancelar todo"; compact: true; kind: "ghost"; enabled: page.viewState.running || page.viewState.pending > 0; onClicked: quickController.cancelAll() }
        XButton { text: "Limpiar"; compact: true; kind: "ghost"; onClicked: quickController.clearActivity() }
    }
    RowLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
        XCard {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 100
            ListView {
                id: activity; objectName: "quickActivity"; anchors.fill: parent; anchors.margins: 10; clip: true; spacing: 8
                model: quickController.model; ScrollBar.vertical: XScrollBar {}
                delegate: Rectangle {
                    width: activity.width; height: 100; radius: 12; color: theme.colors.surfaceRaised
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 12
                        Rectangle {
                            Layout.preferredWidth: page.historyOpen && page.width < 1100 ? 66 : 108; Layout.fillHeight: true; radius: 7; color: theme.colors.surface; clip: true
                            Image { anchors.fill: parent; source: model.thumbnail || ""; fillMode: Image.PreserveAspectFit; asynchronous: true; sourceSize.width: 240 }
                            Text { anchors.centerIn: parent; visible: !model.thumbnail; text: model.mode === "Audio" ? "♫" : "↓"; font.pixelSize: 28; color: theme.colors.accent }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: model.title; elide: Text.ElideRight; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                                XButton { visible: ["En cola", "Analizando", "Descargando"].indexOf(model.status) >= 0; text: "Cancelar"; compact: true; kind: "ghost"; implicitWidth: 80; onClicked: quickController.cancel(model.jobId) }
                                XButton { visible: Boolean(model.output); text: "Abrir"; compact: true; implicitWidth: 58; leftPadding: 6; rightPadding: 6; kind: "ghost"; onClicked: quickController.openResult(model.output) }
                                XButton { visible: Boolean(model.output); text: "Pr"; compact: true; implicitWidth: 36; leftPadding: 6; rightPadding: 6; kind: "secondary"; onClicked: quickController.sendToPremiere(model.output); ToolTip.visible: hovered; ToolTip.text: "Enviar a Premiere" }
                                XButton { visible: ["En cola", "Analizando", "Descargando"].indexOf(model.status) < 0; text: "×"; compact: true; implicitWidth: 32; leftPadding: 6; rightPadding: 6; kind: "ghost"; onClicked: quickController.removeJob(model.jobId) }
                            }
                            Rectangle {
                                Layout.fillWidth: true; height: 3; radius: 2; color: theme.colors.border
                                Rectangle { width: parent.width * Math.max(0, Math.min(1, model.progress)); height: 3; radius: 2; color: model.status === "Error" ? theme.colors.error : theme.colors.accent }
                            }
                            Text { Layout.fillWidth: true; text: model.mode + " · " + model.quality + " · " + model.status + " · " + model.detail; elide: Text.ElideRight; color: theme.colors.textDim; font.pixelSize: 10 }
                        }
                    }
                }
                Text { anchors.centerIn: parent; visible: activity.count === 0; text: "Sin descargas"; color: theme.colors.textDim; font.pixelSize: 12 }
            }
        }
        XCard {
            visible: page.historyOpen; Layout.preferredWidth: Math.min(300, page.width * 0.29); Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12
                RowLayout {
                    Text { text: "Historial"; Layout.fillWidth: true; color: theme.colors.text; font.pixelSize: 14 }
                    XButton { text: "×"; implicitWidth: 32; leftPadding: 6; rightPadding: 6; compact: true; kind: "ghost"; onClicked: page.historyOpen = false }
                }
                ListView {
                    id: historyList; objectName: "quickHistory"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 5; model: quickController.historyModel
                    ScrollBar.vertical: XScrollBar {}
                    delegate: Rectangle {
                        width: historyList.width; height: 69; radius: 8; color: theme.colors.surfaceRaised
                        MouseArea { anchors.fill: parent; onClicked: quickController.setValue("url", model.url) }
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 8; spacing: 3
                            Text { Layout.fillWidth: true; text: model.title; elide: Text.ElideRight; color: theme.colors.text; font.pixelSize: 11 }
                            RowLayout {
                                Text { Layout.fillWidth: true; text: model.mode + " · " + model.quality; color: theme.colors.textDim; font.pixelSize: 9 }
                                XButton { text: "Abrir"; compact: true; implicitWidth: 56; leftPadding: 6; rightPadding: 6; kind: "ghost"; onClicked: quickController.openResult(model.output) }
                            }
                        }
                    }
                    Text { anchors.centerIn: parent; visible: historyList.count === 0; text: "Aún no hay descargas."; color: theme.colors.textDim; font.pixelSize: 11 }
                }
                XButton { Layout.fillWidth: true; text: "Borrar historial"; compact: true; kind: "ghost"; onClicked: quickController.clearHistory() }
            }
        }
    }
    XCard {
        Layout.fillWidth: true; implicitHeight: destination.implicitHeight + 22
        ColumnLayout {
            id: destination; anchors.fill: parent; anchors.margins: 11; spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Guardar en"; color: theme.colors.textMuted; font.pixelSize: 11 }
                XTextField { Layout.fillWidth: true; text: page.viewState.outputPath; onEditingFinished: quickController.setValue("outputPath", text) }
                XButton { text: "Elegir"; compact: true; kind: "secondary"; onClicked: quickController.chooseOutputFolder() }
                XButton { text: "Abrir carpeta"; compact: true; kind: "ghost"; onClicked: quickController.openOutputFolder() }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: page.viewState.selectedTag !== "Sin etiqueta" ? "Destino de la etiqueta: " + page.viewState.selectedTag : ""; color: theme.colors.textDim; font.pixelSize: 10 }
                Text { visible: page.viewState.sendPremiere; text: premiereController.state.connected ? "● Premiere conectado" : "○ Premiere sin conectar"; color: theme.colors.textMuted; font.pixelSize: 10 }
                Text { text: Math.round(page.viewState.totalProgress * 100) + "%"; color: theme.colors.accent; font.pixelSize: 10 }
            }
            Rectangle { Layout.fillWidth: true; height: 3; radius: 2; color: theme.colors.border
                Rectangle { width: parent.width * page.viewState.totalProgress; height: 3; radius: 2; color: theme.colors.accent }
            }
        }
    }
    Popup {
        id: postPopup; objectName: "quickPostPopup"; parent: Overlay.overlay; x: Math.max(10, (parent.width - width) / 2); y: Math.max(10, (parent.height - height) / 2)
        width: 480; height: postControls.implicitHeight + 36; modal: true; padding: 18
        background: Rectangle { color: theme.colors.surface; radius: 18; border.color: theme.colors.border }
        ColumnLayout {
            id: postControls; anchors.fill: parent; spacing: 14
            Text { text: "Después de descargar"; color: theme.colors.text; font.pixelSize: 18 }
            XSwitch { text: "Convertir video con un preset"; enabled: page.viewState.mode === "Video"; checked: page.viewState.postprocess; onToggled: quickController.setValue("postprocess", checked) }
            XComboBox { Layout.fillWidth: true; enabled: page.viewState.postprocess && page.viewState.mode === "Video"; model: presetStore.videoPresets; currentIndex: Math.max(0, model.indexOf(page.viewState.preset)); onActivated: quickController.setValue("preset", currentText) }
            XSwitch { text: "Enviar automáticamente a Premiere"; checked: page.viewState.sendPremiere; onToggled: quickController.setValue("sendPremiere", checked) }
            Text { Layout.fillWidth: true; text: "El audio usa el formato seleccionado arriba. Epidemic Sound se guarda automáticamente en WAV de 48 kHz. Para recibir archivos en Premiere, abre Xomacito Link y vincula la carpeta de Biblioteca."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap }
            XButton { Layout.alignment: Qt.AlignRight; text: "Listo"; compact: true; onClicked: postPopup.close() }
        }
    }
    Popup {
        id: cutsPopup; objectName: "quickCutsPopup"; anchors.centerIn: Overlay.overlay; width: 520; height: 400; modal: true; padding: 18
        background: Rectangle { color: theme.colors.surface; radius: 18; border.color: theme.colors.border }
        ColumnLayout {
            anchors.fill: parent; spacing: 12
            Text { text: "Recortar las próximas descargas"; color: theme.colors.text; font.pixelSize: 18 }
            Text { Layout.fillWidth: true; text: "Añade uno o varios tramos en HH:MM:SS. Cada tramo se guarda por separado. Quita los tramos para descargar el archivo completo."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap }
            RowLayout {
                XTextField { id: cutIn; Layout.fillWidth: true; placeholderText: "00:00:00"; text: "00:00:00" }
                Text { text: "→"; color: theme.colors.textMuted }
                XTextField { id: cutOut; Layout.fillWidth: true; placeholderText: "00:00:30" }
                XButton { text: "Añadir"; compact: true; onClicked: quickController.addRange(cutIn.text, cutOut.text) }
            }
            ListView {
                id: cutsList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4; model: page.viewState.ranges
                delegate: RowLayout {
                    width: cutsList.width
                    Text { Layout.fillWidth: true; text: modelData.startTime + " → " + modelData.endTime; color: theme.colors.text; font.pixelSize: 13 }
                    XButton { text: "Quitar"; compact: true; kind: "ghost"; onClicked: quickController.removeRange(index) }
                }
            }
            XButton { Layout.alignment: Qt.AlignRight; text: "Listo"; compact: true; onClicked: cutsPopup.close() }
        }
    }
    SearchResultsPopup {
        id: discoveryPopup
        objectName: "quickDiscoveryPopup"
    }
}
