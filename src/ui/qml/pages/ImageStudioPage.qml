import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    readonly property var studio: imageController.state
    readonly property var options: imageController.options
    readonly property bool locked: studio.busy || studio.previewBusy
    readonly property var tasks: ["removeBackground", "upscaleImage", "convert"]
    function manageModels() { settingsController.setValue("section", "Modelos"); settingsController.refreshModels(); appController.setPage(6) }
    DropArea { anchors.fill: parent; enabled: !root.locked; onDropped: function(drop) { if (drop.hasUrls) imageController.addPaths(drop.urls) } }
    ColumnLayout {
        anchors.fill: parent; spacing: 8
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Text { text: "Nombre"; color: theme.colors.textMuted; font.pixelSize: 11 }
            XTextField { Layout.fillWidth: true; compact: true; text: imageController.selected.title || ""; placeholderText: "Nombre de salida"; enabled: !root.locked && root.studio.itemCount > 0; onEditingFinished: imageController.setSelectedTitle(text) }
            XButton { text: "Enlace"; compact: true; kind: "ghost"; onClicked: linkPopup.open(); enabled: !root.locked }
            XButton { text: "Comparar"; compact: true; kind: preview.compareEnabled ? "primary" : "ghost"; enabled: !!root.studio.resultPreviewSource; onClicked: preview.compareEnabled = !preview.compareEnabled }
            XButton { text: "Copiar"; compact: true; kind: "ghost"; enabled: !!root.studio.lastOutput; onClicked: imageController.copyResult() }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
            ColumnLayout {
                Layout.preferredWidth: 40; Layout.minimumWidth: 40; Layout.maximumWidth: 40; Layout.fillHeight: true; spacing: 6
                Repeater {
                    model: [{icon:"background", label:"Eliminar fondo con IA"}, {icon:"upscale", label:"Reescalar con IA"}, {icon:"convert", label:"Convertir y redimensionar"}]
                    XButton {
                        id: toolButton
                        required property int index
                        required property var modelData
                        Layout.fillWidth: true; implicitWidth: 40; implicitHeight: 40; leftPadding: 4; rightPadding: 4
                        kind: root.studio.task === root.tasks[index] ? "primary" : "ghost"; enabled: !root.locked
                        contentItem: Item {
                            StudioIcon { anchors.centerIn: parent; width: 23; height: 23; name: toolButton.modelData.icon; color: toolButton.currentForegroundColor; opacity: toolButton.enabled ? 1 : 0.4 }
                        }
                        ToolTip.visible: hovered; ToolTip.text: modelData.label; Accessible.name: modelData.label
                        onClicked: imageController.setTask(root.tasks[index])
                    }
                }
                Item { Layout.fillHeight: true }
                XButton { text: "↺"; implicitWidth: 40; leftPadding: 4; rightPadding: 4; compact: true; kind: "ghost"; onClicked: preview.resetView(); ToolTip.visible: hovered; ToolTip.text: "Ajustar imagen a la vista" }
            }
            ImageComparison {
                id: preview; objectName: "imageStudioCanvas"
                Layout.fillWidth: true; Layout.preferredWidth: root.width * 0.65; Layout.minimumWidth: 200; Layout.fillHeight: true; Layout.minimumHeight: 160
                originalSource: root.studio.previewSource; resultSource: root.studio.resultPreviewSource
                Text { anchors.centerIn: parent; visible: !root.studio.previewSource; text: root.studio.itemCount ? "Cargando…" : "Arrastra imágenes aquí"; color: theme.colors.textMuted; font.pixelSize: 14 }
                Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 8; width: imageSize.implicitWidth + 16; height: 24; radius: 5; color: "#C0181B22"; visible: root.studio.analysisReady
                    Text { id: imageSize; anchors.centerIn: parent; text: (root.studio.analysis.width || "") + " × " + (root.studio.analysis.height || "") + " px"; color: "#ECEEF5"; font.pixelSize: 10 }
                }
            }
            XCard {
                Layout.preferredWidth: Math.min(350, Math.max(285, root.width * 0.28)); Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { Layout.fillWidth: true; text: "Imágenes"; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Text { text: root.studio.itemCount + " archivos"; color: theme.colors.textMuted; font.pixelSize: 10 }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 4
                        XButton { Layout.fillWidth: true; implicitWidth: 65; leftPadding: 5; rightPadding: 5; text: "Archivos"; compact: true; implicitHeight: 30; kind: "secondary"; enabled: !root.locked; onClicked: imageController.importFiles() }
                        XButton { Layout.fillWidth: true; implicitWidth: 65; leftPadding: 5; rightPadding: 5; text: "Carpeta"; compact: true; implicitHeight: 30; kind: "secondary"; enabled: !root.locked; onClicked: imageController.importFolder() }
                        XButton { Layout.fillWidth: true; implicitWidth: 56; leftPadding: 5; rightPadding: 5; text: "Pegar"; compact: true; implicitHeight: 30; kind: "secondary"; enabled: !root.locked; onClicked: imageController.paste() }
                        XButton { text: "×"; implicitWidth: 28; leftPadding: 4; rightPadding: 4; compact: true; implicitHeight: 30; kind: "ghost"; enabled: !root.locked; onClicked: imageController.clear(); ToolTip.visible: hovered; ToolTip.text: "Vaciar lista" }
                    }
                    ListView {
                        id: files; objectName: "studioFiles"; Layout.fillWidth: true; Layout.preferredHeight: root.height > 630 ? 125 : 85; clip: true; spacing: 3; model: imageController.model
                        ScrollBar.vertical: XScrollBar {}
                        delegate: Rectangle {
                            required property int index
                            required property string name
                            required property string status
                            required property string preview
                            width: files.width - 14; height: 37; radius: 5; color: root.studio.selectedIndex === index ? theme.colors.surfaceSoft : "transparent"
                            RowLayout { anchors.fill: parent; anchors.margins: 4; spacing: 7
                                Image { source: preview; Layout.preferredWidth: 28; Layout.preferredHeight: 28; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                Text { text: name; Layout.fillWidth: true; elide: Text.ElideMiddle; color: theme.colors.text; font.pixelSize: 11 }
                                Text { text: status === "COMPLETED" ? "Listo" : "Pendiente"; color: theme.colors.textMuted; font.pixelSize: 9 }
                            }
                            MouseArea { anchors.fill: parent; enabled: !root.locked; onClicked: imageController.select(index) }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                    ScrollView {
                        id: toolScroll; Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {}
                        ColumnLayout {
                            width: Math.max(0, toolScroll.availableWidth - 14); spacing: 8; enabled: !root.locked
                            Text { text: root.studio.task === "removeBackground" ? "Eliminar fondo con IA" : root.studio.task === "upscaleImage" ? "Reescalar con IA" : "Redimensionar"; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                            XSwitch { visible: root.studio.task === "removeBackground"; text: "Aceleración por GPU"; checked: root.options.rembgGpu; onToggled: imageController.setOption("rembgGpu", checked) }
                            LabeledControl { Layout.fillWidth: true; compact: true; label: "Motor"; visible: root.studio.task !== "convert"
                                XComboBox { Layout.fillWidth: true; compact: true; model: root.studio.task === "removeBackground" ? imageController.rembgFamilies : ["Upscayl"]; onActivated: imageController.setOption(root.studio.task === "removeBackground" ? "rembgFamily" : "upscaleEngine", currentText) }
                            }
                            LabeledControl { Layout.fillWidth: true; compact: true; label: "Modelo"; visible: root.studio.task !== "convert"
                                XComboBox { Layout.fillWidth: true; compact: true; model: root.studio.task === "removeBackground" ? imageController.rembgModels(root.options.rembgFamily) : imageController.upscaleModels; currentIndex: Math.max(0, model.indexOf(root.studio.task === "removeBackground" ? root.options.rembgModel : root.options.upscaleModel)); onActivated: imageController.setOption(root.studio.task === "removeBackground" ? "rembgModel" : "upscaleModel", currentText) }
                            }
                            RowLayout {
                                Layout.fillWidth: true; visible: root.studio.task !== "convert"
                                XButton { Layout.fillWidth: true; text: "Administrar"; objectName: "studioManageModels"; compact: true; kind: "secondary"; onClicked: root.manageModels() }
                                XButton { Layout.fillWidth: true; text: "Probar"; compact: true; kind: "ghost"; enabled: root.studio.itemCount > 0; onClicked: imageController.preparePreview() }
                            }
                            LabeledControl { Layout.fillWidth: true; compact: true; label: "Suavizado · " + root.options.rembgSmooth + " px"; visible: root.studio.task === "removeBackground"
                                XSlider { Layout.fillWidth: true; from: 0; to: 20; stepSize: 1; value: root.options.rembgSmooth; onMoved: imageController.setOption("rembgSmooth", value) }
                            }
                            LabeledControl { Layout.fillWidth: true; compact: true; label: "Expandir / contraer · " + root.options.rembgExpand + " px"; visible: root.studio.task === "removeBackground"
                                XSlider { Layout.fillWidth: true; from: -20; to: 20; stepSize: 1; value: root.options.rembgExpand; onMoved: imageController.setOption("rembgExpand", value) }
                            }
                            RowLayout { Layout.fillWidth: true; visible: root.studio.task === "upscaleImage"
                                LabeledControl { Layout.fillWidth: true; compact: true; label: "Escala"
                                    XComboBox { Layout.fillWidth: true; compact: true; model: ["2", "3", "4"]; currentIndex: Math.max(0, model.indexOf(root.options.upscaleScale)); onActivated: imageController.setOption("upscaleScale", currentText) }
                                }
                                LabeledControl { Layout.fillWidth: true; compact: true; label: "Tile · 0 = auto"
                                    XTextField { Layout.fillWidth: true; compact: true; text: root.options.upscaleTile; validator: IntValidator { bottom: 0; top: 4096 } onEditingFinished: if (acceptableInput) imageController.setOption("upscaleTile", text) }
                                }
                            }
                            LabeledControl { Layout.fillWidth: true; compact: true; label: "Potencia"; visible: root.studio.task === "upscaleImage"
                                XComboBox { Layout.fillWidth: true; compact: true; model: imageController.performanceProfiles; currentIndex: Math.max(0, model.indexOf(root.options.performanceProfile)); onActivated: imageController.setPerformanceProfile(currentText) }
                            }
                            XSwitch { visible: root.studio.task === "upscaleImage"; text: "TTA · mayor calidad, más lento"; checked: root.options.upscaleTta; onToggled: imageController.setOption("upscaleTta", checked) }
                            XSwitch { visible: root.studio.task === "convert"; text: "Cambiar dimensiones"; checked: root.options.resizeEnabled; onToggled: imageController.setOption("resizeEnabled", checked) }
                            RowLayout { visible: root.studio.task === "convert"; Layout.fillWidth: true; enabled: root.options.resizeEnabled
                                XTextField { Layout.fillWidth: true; compact: true; placeholderText: "Ancho"; text: root.options.resizeWidth; validator: IntValidator { bottom: 1; top: 32768 } onEditingFinished: if (acceptableInput) imageController.setOption("resizeWidth", text) }
                                Text { text: "×"; color: theme.colors.textMuted }
                                XTextField { Layout.fillWidth: true; compact: true; placeholderText: "Alto"; text: root.options.resizeHeight; validator: IntValidator { bottom: 1; top: 32768 } onEditingFinished: if (acceptableInput) imageController.setOption("resizeHeight", text) }
                            }
                            XSwitch { visible: root.studio.task === "convert"; text: "Mantener proporción"; checked: root.options.resizeMaintainAspect; onToggled: imageController.setOption("resizeMaintainAspect", checked) }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                    Text { text: "Formato de salida"; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                    XComboBox { objectName: "studioOutputFormat"; Layout.fillWidth: true; compact: true; model: imageController.stillFormats; currentIndex: Math.max(0, model.indexOf(root.studio.format)); enabled: !root.locked; onActivated: imageController.setValue("format", currentText) }
                    Text { visible: root.studio.format === "No Convertir" || root.studio.format === "SVG"; Layout.fillWidth: true; text: root.studio.format === "SVG" ? "SVG con imagen incrustada; conserva los píxeles." : "Conserva el formato original. Entradas no reexportables se guardan en PNG."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 6
            Text { text: "Si existe"; color: theme.colors.textMuted; font.pixelSize: 10 }
            XComboBox { Layout.preferredWidth: 114; compact: true; model: ["Renombrar", "Omitir", "Sobrescribir"]; currentIndex: model.indexOf(root.studio.conflictPolicy); enabled: !root.locked; onActivated: imageController.setValue("conflictPolicy", currentText) }
            XTextField { Layout.fillWidth: true; compact: true; text: root.studio.outputPath; enabled: !root.locked; onEditingFinished: imageController.setValue("outputPath", text) }
            XButton { text: "…"; implicitWidth: 32; leftPadding: 4; rightPadding: 4; compact: true; kind: "secondary"; enabled: !root.locked; onClicked: imageController.chooseOutputFolder(); ToolTip.visible: hovered; ToolTip.text: "Carpeta de salida" }
            XButton { text: "Resultado"; compact: true; kind: "ghost"; enabled: !!root.studio.lastOutput; onClicked: imageController.openOutput() }
            XButton { objectName: "imageStudioStartButton"; compact: true; text: root.studio.busy ? "Cancelar" : "Procesar · " + root.studio.itemCount; kind: root.studio.busy ? "danger" : "primary"; enabled: root.studio.busy || (!root.locked && root.studio.itemCount > 0); onClicked: root.studio.busy ? imageController.cancel() : imageController.start() }
        }
        RowLayout {
            Layout.fillWidth: true; visible: root.locked || root.studio.progress > 0; spacing: 8
            Text { Layout.fillWidth: true; text: root.studio.status; color: theme.colors.textMuted; font.pixelSize: 10; elide: Text.ElideRight }
            ProgressBar { Layout.preferredWidth: 130; implicitHeight: 5; value: root.studio.progress }
            Text { text: Math.round(root.studio.progress * 100) + "%"; color: theme.colors.textMuted; font.pixelSize: 10 }
        }
    }
    Popup {
        id: linkPopup; anchors.centerIn: Overlay.overlay; width: Math.min(650, root.width - 30); height: 120; modal: true; padding: 16
        background: Rectangle { color: theme.colors.surface; radius: 12; border.color: theme.colors.border }
        ColumnLayout { anchors.fill: parent
            Text { text: "Importar desde un enlace"; color: theme.colors.text; font.pixelSize: 14 }
            RowLayout { Layout.fillWidth: true
                XTextField { Layout.fillWidth: true; text: root.studio.url; placeholderText: "https://…"; onTextEdited: imageController.setValue("url", text); onAccepted: { imageController.analyzeUrl(); linkPopup.close() } }
                XButton { text: "Importar"; compact: true; enabled: root.studio.url.length > 0 && !root.locked; onClicked: { imageController.analyzeUrl(); linkPopup.close() } }
            }
        }
    }
}
