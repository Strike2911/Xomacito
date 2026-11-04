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
    spacing: 14
    onVisibleChanged: if (!visible) quickController.previewController.close()
    Connections { target: quickController; function onDiscoveryRequested() { discoveryPopup.open() } }
    XCard {
        Layout.fillWidth: true
        implicitHeight: quickControls.implicitHeight + 28
        radius: 12
        cardColor: theme.backgroundImage ? Qt.alpha(theme.colors.surface, 0.96) : theme.colors.surface
        ColumnLayout {
            id: quickControls
            anchors.fill: parent; anchors.margins: 14; spacing: 14
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                XTextField {
                    objectName: "quickUrls"; Layout.fillWidth: true
                    text: page.viewState.url
                    placeholderText: "Pega un enlace o busca un video…"
                    Accessible.name: "Enlace o búsqueda"
                    onTextEdited: quickController.setValue("url", text)
                    onAccepted: quickController.enqueue()
                }
                XButton {
                    objectName: "quickSubmit"; text: page.viewState.actionLabel
                    implicitWidth: 114
                    enabled: page.viewState.inputKind !== "empty" && !page.viewState.discovering
                    onClicked: quickController.enqueue()
                }
                XButton { text: "Buscar"; compact: true; kind: "ghost"; ToolTip.visible: hovered; ToolTip.text: "Buscar medios"; onClicked: quickController.openSearch() }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Flow {
                    objectName: "quickOptions"
                    Layout.fillWidth: true; spacing: 12
                    Repeater {
                        model: [
                            {key: "mode", label: "Formato", size: 150},
                            {key: "quality", label: "Calidad", size: 164},
                            {key: "thumbnailMode", label: "Miniatura", size: 164}
                        ]
                        Column {
                            id: optionField
                            required property var modelData
                            readonly property string optionKey: modelData.key === "quality" && page.viewState.mode === "Audio" ? "audioFormat" : modelData.key
                            width: modelData.size
                            spacing: 6
                            Text { text: optionField.modelData.label; color: theme.colors.textMuted; font.pixelSize: 11 }
                            XComboBox {
                                objectName: "quickOption_" + optionField.optionKey
                                width: parent.width; compact: true
                                model: quickController.choices[optionField.optionKey]
                                enabled: optionField.optionKey === "thumbnailMode" || !page.viewState.thumbnailOnly
                                currentIndex: Math.max(0, model.indexOf(page.viewState[optionField.optionKey]))
                                displayText: optionField.optionKey === "mode" && currentText === "Video" ? "Video + audio" : currentText
                                Accessible.name: optionField.modelData.label
                                onActivated: quickController.setValue(optionField.optionKey, currentText)
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.alignment: Qt.AlignBottom
                    spacing: 4
                    CheckBox {
                        objectName: "quickPlaylist"; text: "Playlist"; implicitHeight: 36; implicitWidth: 88
                        checked: page.viewState.playlist
                        onToggled: quickController.setValue("playlist", checked)
                        indicator: Rectangle {
                            x: 4; y: (parent.height - height) / 2; width: 15; height: 15; radius: 4
                            color: parent.checked ? theme.colors.primary : theme.colors.surfaceSoft
                            border.color: parent.activeFocus ? theme.colors.accent : theme.colors.border
                            Text { anchors.centerIn: parent; text: "✓"; visible: page.viewState.playlist; color: theme.colors.onPrimary; font.pixelSize: 11 }
                        }
                        contentItem: Text { text: parent.text; leftPadding: 25; verticalAlignment: Text.AlignVCenter; color: theme.colors.textMuted; font.pixelSize: 11 }
                    }
                    XButton { text: page.viewState.ranges.length ? "Recortes (" + page.viewState.ranges.length + ")" : "Recortar"; compact: true; kind: page.viewState.ranges.length ? "secondary" : "ghost"; onClicked: cutsPopup.open() }
                    XButton { text: page.viewState.videoDelivery === "Premiere · alta calidad" ? "Premiere ✓" : "Destino / convertir"; compact: true; kind: page.viewState.postprocess || page.viewState.sendPremiere ? "secondary" : "ghost"; onClicked: postPopup.open() }
                }
            }
            Text { Layout.fillWidth: true; visible: page.viewState.postprocess; text: "La descarga se convertirá con el preset seleccionado."; color: theme.colors.textMuted; font.pixelSize: 11 }
        }
    }
    XCard {
        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 140; radius: 12
        cardColor: theme.backgroundImage ? Qt.alpha(theme.colors.surface, 0.18) : theme.colors.surface
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 10
            RowLayout {
                Layout.fillWidth: true
                WorkspaceTab { text: "Descargas"; selected: !page.historyOpen; onClicked: page.historyOpen = false }
                WorkspaceTab { text: "Historial"; selected: page.historyOpen; onClicked: page.historyOpen = true }
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
                            MouseArea {
                                anchors.fill: parent; cursorShape: Qt.OpenHandCursor
                                property point pressedAt
                                property bool started: false
                                onPressed: function(mouse) { pressedAt = Qt.point(mouse.x, mouse.y); started = false }
                                onPositionChanged: function(mouse) {
                                    if (pressed && !started && Math.abs(mouse.x - pressedAt.x) + Math.abs(mouse.y - pressedAt.y) >= Qt.styleHints.startDragDistance) {
                                        started = true
                                        transferController.startDrag(model.outputs && model.outputs.length ? model.outputs : [model.output || model.url])
                                    }
                                }
                            }
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
                        FileDragHandle { paths: model.outputs && model.outputs.length ? model.outputs : (model.output ? [model.output] : []); label: "Arrastrar" }
                        XButton { visible: Boolean(model.output); text: "Abrir"; compact: true; kind: "ghost"; onClicked: quickController.openResult(model.output) }
                        XButton { visible: !page.historyOpen && ["En cola", "Analizando", "Descargando"].indexOf(model.status) < 0; text: "Quitar"; compact: true; kind: "ghost"; onClicked: quickController.removeJob(model.jobId) }
                        XButton { visible: page.historyOpen; text: "Reutilizar"; compact: true; kind: "ghost"; onClicked: { quickController.setValue("url", model.url); page.historyOpen = false } }
                    }
                }
                Column {
                    anchors.centerIn: parent
                    width: Math.min(400, parent.width - 32)
                    spacing: 8
                    visible: activity.count === 0
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: page.historyOpen ? "↺" : "↓"; color: theme.colors.primary; opacity: 0.75; font.pixelSize: 34 }
                    Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: page.historyOpen ? "Todavía no hay historial" : "Todo listo para tu próxima descarga"; color: theme.colors.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: page.historyOpen ? "Tus archivos completados aparecerán aquí." : "Pega un enlace arriba para comenzar."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap }
                }
            }
        }
    }
    XCard {
        Layout.fillWidth: true; implicitHeight: destination.implicitHeight + 24; radius: 12
        ColumnLayout {
            id: destination; anchors.fill: parent; anchors.margins: 12; spacing: 6
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Text { text: "Destino"; color: theme.colors.textMuted; font.pixelSize: 11 }
                XTextField { objectName: "quickOutput"; Layout.fillWidth: true; compact: true; text: page.viewState.effectiveOutputPath; readOnly: page.viewState.taggedOutput; onEditingFinished: if (!readOnly) quickController.setValue("outputPath", text) }
                XComboBox { Layout.preferredWidth: 142; compact: true; model: downloadController.downloadTags; currentIndex: Math.max(0, model.indexOf(page.viewState.selectedTag)); Accessible.name: "Etiqueta de destino"; onActivated: quickController.setValue("selectedTag", currentText) }
                XButton { text: "Cambiar"; compact: true; kind: "ghost"; enabled: !page.viewState.taggedOutput; onClicked: quickController.chooseOutputFolder() }
                XButton { text: "Abrir carpeta"; compact: true; kind: "ghost"; onClicked: quickController.openOutputFolder() }
            }
            RowLayout {
                Layout.fillWidth: true
                visible: page.viewState.running
                Text { Layout.fillWidth: true; text: page.viewState.running ? "Descargando · " + Math.round(page.viewState.totalProgress * 100) + "%" : "Listo"; color: theme.colors.textDim; font.pixelSize: 10 }
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
            LabeledControl {
                Layout.fillWidth: true; label: "Destino del video"
                visible: page.viewState.mode === "Video"
                XComboBox {
                    objectName: "quickVideoDelivery"; Layout.fillWidth: true
                    model: ["Original · sin convertir", "Premiere · alta calidad"]
                    currentIndex: Math.max(0, model.indexOf(page.viewState.videoDelivery))
                    onActivated: quickController.setValue("videoDelivery", currentText)
                }
            }
            Text {
                Layout.fillWidth: true; wrapMode: Text.WordWrap; color: theme.colors.textMuted; font.pixelSize: 12
                visible: page.viewState.mode === "Video"
                text: page.viewState.videoDelivery === "Premiere · alta calidad"
                    ? "AV1/VP9 se preparan al terminar. Conserva resolución, FPS y original; convertir tarda y crea otro archivo."
                    : "El original puede usar AV1/VP9. Elige Premiere · alta calidad para editarlo en Premiere."
            }
            XSwitch { text: "Enviar automáticamente a Premiere"; checked: page.viewState.sendPremiere; onToggled: quickController.setValue("sendPremiere", checked) }
            XSwitch { text: "Convertir video con un preset"; enabled: page.viewState.mode === "Video"; checked: page.viewState.postprocess; onToggled: quickController.setValue("postprocess", checked) }
            XComboBox { Layout.fillWidth: true; enabled: page.viewState.postprocess && page.viewState.mode === "Video"; model: presetStore.videoPresets; currentIndex: Math.max(0, model.indexOf(page.viewState.preset)); onActivated: quickController.setValue("preset", currentText) }
            Text { Layout.fillWidth: true; text: "El audio usa el formato seleccionado arriba. Epidemic Sound se guarda automáticamente en WAV de 48 kHz. Arrastra los archivos descargados hacia tu editor o una carpeta."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap }
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
