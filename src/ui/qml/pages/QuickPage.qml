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
    spacing: 8
    onVisibleChanged: if (!visible) quickController.previewController.close()
    Connections { target: quickController; function onDiscoveryRequested() { discoveryPopup.open() } }
    XCard {
        Layout.fillWidth: true
        implicitHeight: quickControls.implicitHeight + 20
        radius: 12
        ColumnLayout {
            id: quickControls
            anchors.fill: parent; anchors.margins: 10; spacing: 8
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                XTextField {
                    objectName: "quickUrls"; Layout.fillWidth: true; compact: true
                    text: page.viewState.url
                    placeholderText: "Pega un enlace o escribe para buscar en YouTube…"
                    Accessible.name: "Enlace o búsqueda"
                    onTextEdited: quickController.setValue("url", text)
                    onAccepted: quickController.enqueue()
                }
                XButton {
                    objectName: "quickSubmit"; text: page.viewState.actionLabel
                    compact: true; enabled: page.viewState.inputKind !== "empty" && !page.viewState.discovering
                    onClicked: quickController.enqueue()
                }
                XButton { text: "Buscar medios"; compact: true; kind: "ghost"; onClicked: quickController.openSearch() }
            }
            Flow {
                objectName: "quickOptions"
                Layout.fillWidth: true; spacing: 8
                Repeater {
                    model: [
                        {key: "mode", label: "Formato", size: 150},
                        {key: "quality", label: "Calidad", size: 174},
                        {key: "thumbnailMode", label: "Miniatura", size: 166}
                    ]
                    XComboBox {
                        required property var modelData
                        readonly property string optionKey: modelData.key === "quality" && page.viewState.mode === "Audio" ? "audioFormat" : modelData.key
                        objectName: "quickOption_" + optionKey
                        width: modelData.size; compact: true
                        model: quickController.choices[optionKey]
                        enabled: modelData.key === "thumbnailMode" || !page.viewState.thumbnailOnly
                        currentIndex: Math.max(0, model.indexOf(page.viewState[optionKey]))
                        displayText: modelData.key === "mode" && currentText === "Video" ? "Video + audio" : currentText
                        Accessible.name: modelData.label
                        ToolTip.visible: hovered; ToolTip.text: modelData.label
                        onActivated: quickController.setValue(optionKey, currentText)
                    }
                }
                CheckBox {
                    objectName: "quickPlaylist"; text: "Playlist"; height: 36; width: 100
                    checked: page.viewState.playlist
                    onToggled: quickController.setValue("playlist", checked)
                    indicator: Rectangle {
                        x: 4; y: (parent.height - height) / 2; width: 16; height: 16; radius: 4
                        color: parent.checked ? theme.colors.primary : theme.colors.surfaceSoft
                        border.color: parent.activeFocus ? theme.colors.accent : theme.colors.border
                        Text { anchors.centerIn: parent; text: "✓"; visible: page.viewState.playlist; color: "white"; font.pixelSize: 12 }
                    }
                    contentItem: Text { text: parent.text; leftPadding: 25; verticalAlignment: Text.AlignVCenter; color: theme.colors.textMuted; font.pixelSize: 11 }
                }
                XButton { text: page.viewState.ranges.length ? "Recortes (" + page.viewState.ranges.length + ")" : "Recortar"; compact: true; kind: page.viewState.ranges.length ? "secondary" : "ghost"; onClicked: cutsPopup.open() }
                XButton { text: "Postprocesar"; compact: true; kind: page.viewState.postprocess || page.viewState.sendPremiere ? "secondary" : "ghost"; onClicked: postPopup.open() }
            }
        }
    }
    XCard {
        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 140; radius: 12
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 10; spacing: 8
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Descargas"; compact: true; kind: page.historyOpen ? "ghost" : "secondary"; onClicked: page.historyOpen = false }
                XButton { text: "Historial"; compact: true; kind: page.historyOpen ? "secondary" : "ghost"; onClicked: page.historyOpen = true }
                Text { visible: !page.historyOpen && page.viewState.pending > 0; text: page.viewState.pending + " en cola"; font.pixelSize: 11; color: theme.colors.textDim }
                Item { Layout.fillWidth: true }
                XButton { text: "Cancelar todo"; visible: !page.historyOpen; compact: true; kind: "ghost"; enabled: page.viewState.running || page.viewState.pending > 0; onClicked: quickController.cancelAll() }
                XButton { text: page.historyOpen ? "Borrar historial" : "Limpiar terminadas"; compact: true; kind: "ghost"; onClicked: page.historyOpen ? quickController.clearHistory() : quickController.clearActivity() }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
            ListView {
                id: activity; objectName: "quickActivity"
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                model: page.historyOpen ? quickController.historyModel : quickController.model
                ScrollBar.vertical: XScrollBar {}
                delegate: Rectangle {
                    width: activity.width - 12; height: 80; radius: 8; color: theme.colors.surfaceRaised
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 10
                        Rectangle {
                            Layout.preferredWidth: 96; Layout.fillHeight: true; radius: 6; color: theme.colors.surface; clip: true
                            Image { anchors.fill: parent; source: model.thumbnail || ""; fillMode: Image.PreserveAspectFit; asynchronous: true; sourceSize.width: 192 }
                            Text { anchors.centerIn: parent; visible: !model.thumbnail; text: model.mode; font.pixelSize: 11; color: theme.colors.textDim }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 5
                            Text { Layout.fillWidth: true; text: model.title; elide: Text.ElideRight; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                            Text { Layout.fillWidth: true; text: model.quality + " · " + model.status + (page.historyOpen ? "" : " · " + model.detail); elide: Text.ElideRight; color: model.status === "Error" ? theme.colors.error : theme.colors.textMuted; font.pixelSize: 10 }
                            Rectangle {
                                visible: !page.historyOpen; Layout.fillWidth: true; height: 2; radius: 1; color: theme.colors.border
                                Rectangle { width: parent.width * (model.status === "Completado" ? 1 : Math.max(0, Math.min(1, model.progress))); height: 2; color: theme.colors.accent }
                            }
                        }
                        XButton { visible: ["En cola", "Analizando", "Descargando"].indexOf(model.status) >= 0; text: "Cancelar"; compact: true; kind: "ghost"; onClicked: quickController.cancel(model.jobId) }
                        XButton { visible: Boolean(model.output); text: "Abrir"; compact: true; kind: "ghost"; onClicked: quickController.openResult(model.output) }
                        XButton { visible: Boolean(model.output); text: "Premiere"; compact: true; kind: "secondary"; onClicked: quickController.sendToPremiere(model.output) }
                        XButton { visible: !page.historyOpen && ["En cola", "Analizando", "Descargando"].indexOf(model.status) < 0; text: "Quitar"; compact: true; kind: "ghost"; onClicked: quickController.removeJob(model.jobId) }
                        XButton { visible: page.historyOpen; text: "Reutilizar"; compact: true; kind: "ghost"; onClicked: { quickController.setValue("url", model.url); page.historyOpen = false } }
                    }
                }
                Text { anchors.centerIn: parent; visible: activity.count === 0; text: page.historyOpen ? "Sin historial" : "Aquí aparecerán tus descargas"; color: theme.colors.textDim; font.pixelSize: 12 }
            }
        }
    }
    XCard {
        Layout.fillWidth: true; implicitHeight: destination.implicitHeight + 20; radius: 12
        ColumnLayout {
            id: destination; anchors.fill: parent; anchors.margins: 10; spacing: 6
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Text { text: "Guardar en"; color: theme.colors.textMuted; font.pixelSize: 11 }
                XTextField { objectName: "quickOutput"; Layout.fillWidth: true; compact: true; text: page.viewState.effectiveOutputPath; readOnly: page.viewState.taggedOutput; onEditingFinished: if (!readOnly) quickController.setValue("outputPath", text) }
                XComboBox { Layout.preferredWidth: 150; compact: true; model: downloadController.downloadTags; currentIndex: Math.max(0, model.indexOf(page.viewState.selectedTag)); Accessible.name: "Etiqueta de destino"; onActivated: quickController.setValue("selectedTag", currentText) }
                XButton { text: "Cambiar"; compact: true; kind: "ghost"; enabled: !page.viewState.taggedOutput; onClicked: quickController.chooseOutputFolder() }
                XButton { text: "Abrir carpeta"; compact: true; kind: "ghost"; onClicked: quickController.openOutputFolder() }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: page.viewState.running ? "Descargando · " + Math.round(page.viewState.totalProgress * 100) + "%" : "Listo"; color: theme.colors.textDim; font.pixelSize: 10 }
                Text { visible: page.viewState.sendPremiere; text: premiereController.state.connected ? "Premiere conectado" : "Premiere sin conectar"; color: theme.colors.textMuted; font.pixelSize: 10 }
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
