import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: downloadController.state
    property var options: downloadController.options
    property bool denseLayout: height < 640

    ColumnLayout {
        anchors.fill: parent
        spacing: page.denseLayout || settingsController.state.compactMode ? 8 : 12

        SectionTitle {
            Layout.fillWidth: true
            eyebrow: "DESCARGA INTELIGENTE"
            title: "Pega. Analiza. Descarga."
            description: "Video, audio, miniaturas y subtítulos con formatos listos para editar."
            number: "01"
            compact: true
        }

        XCard {
            id: sourceCard
            objectName: "downloadSourceCard"
            Layout.fillWidth: true
            implicitHeight: sourceLayout.implicitHeight + (page.denseLayout ? 20 : 26)
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                id: sourceLayout
                anchors.fill: parent
                anchors.margins: page.denseLayout ? 10 : 13
                spacing: page.denseLayout ? 8 : 10
                XTextField {
                    objectName: "downloadUrlField"
                    Layout.fillWidth: true
                    compact: page.denseLayout
                    placeholderText: "Pega un enlace de YouTube, Vimeo, TikTok, Instagram…"
                    text: viewState.url
                    enabled: !viewState.busy && !viewState.localFile
                    onTextEdited: downloadController.setValue("url", text)
                    onAccepted: downloadController.analyze()
                }
                XButton { compact: page.denseLayout; text: "Analizar"; leadingText: "↘"; enabled: !viewState.busy && viewState.url.length > 3; onClicked: downloadController.analyze() }
                XButton { compact: page.denseLayout; text: "Importar"; kind: "secondary"; onClicked: downloadController.chooseLocalFile() }
                XButton { compact: page.denseLayout; text: "Limpiar"; kind: "ghost"; visible: viewState.analyzed || viewState.localFile; onClicked: downloadController.resetSource() }
            }
        }

            GridLayout {
                id: primaryGrid
                objectName: "downloadPrimaryGrid"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                columns: page.width >= 900 ? 2 : 1
                columnSpacing: page.denseLayout ? 10 : 14
                rowSpacing: page.denseLayout ? 10 : 14

                XCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
                    implicitHeight: 0
                    Layout.preferredWidth: 380
                    ColumnLayout {
                        id: previewContent
                        anchors.fill: parent
                        anchors.margins: page.denseLayout ? 10 : 14
                        spacing: page.denseLayout ? 7 : 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: viewState.analyzed ? "ENLACE ANALIZADO ✓" : "VISTA PREVIA"; color: viewState.analyzed ? theme.colors.accent : theme.colors.primary; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                            Item { Layout.fillWidth: true }
                            Text { text: viewState.estimatedSize; color: theme.colors.textMuted; font.pixelSize: 11 }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: page.denseLayout ? 108 : 130
                            radius: 14
                            color: theme.colors.backgroundAlt
                            border.color: theme.colors.border
                            clip: true
                            Image { anchors.fill: parent; anchors.margins: 1; source: viewState.thumbnailSource; fillMode: Image.PreserveAspectFit; asynchronous: true; cache: true }
                            Column {
                                anchors.centerIn: parent
                                visible: !viewState.thumbnailSource
                                spacing: 8
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "▷"; color: theme.colors.primary; font.pixelSize: page.denseLayout ? 25 : 30 }
                                Text { text: viewState.localFile ? "Archivo local" : "La miniatura aparecerá aquí"; color: theme.colors.textMuted; font.pixelSize: page.denseLayout ? 10 : 11 }
                            }
                        }
                        Text { Layout.fillWidth: true; text: viewState.title || "Sin analizar"; color: theme.colors.text; font.pixelSize: page.denseLayout ? 13 : 15; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        RowLayout {
                            Layout.fillWidth: true
                            XButton { Layout.fillWidth: true; compact: true; text: "Guardar miniatura"; kind: "secondary"; enabled: !!viewState.thumbnailSource; onClicked: downloadController.saveThumbnail() }
                            XButton { Layout.fillWidth: true; compact: true; text: "Enviar a cola"; kind: "secondary"; enabled: viewState.url.length > 0; onClicked: downloadController.sendToQueue() }
                        }
                    }
                }

                XCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
                    implicitHeight: 0
                    Layout.preferredWidth: 660
                    ColumnLayout {
                        id: outputContent
                        anchors.fill: parent
                        anchors.margins: page.denseLayout ? 10 : 14
                        spacing: page.denseLayout ? 7 : 10
                        SectionTitle { Layout.fillWidth: true; compact: true; eyebrow: "SALIDA"; title: viewState.localFile ? "Prepara tu archivo" : "Elige cómo descargar"; description: viewState.imagePost ? "Publicación detectada como imagen." : "El motor selecciona combinaciones compatibles y conserva la calidad." }
                        LabeledControl {
                            Layout.fillWidth: true; compact: page.denseLayout; label: "Título de salida"
                            XTextField { Layout.fillWidth: true; compact: page.denseLayout; text: viewState.title; onEditingFinished: downloadController.setValue("title", text) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            LabeledControl {
                                Layout.fillWidth: true; compact: page.denseLayout; label: "Modo"
                                XComboBox { objectName: "downloadModeCombo"; Layout.fillWidth: true; compact: page.denseLayout; model: ["Video+Audio", "Solo Audio"]; currentIndex: Math.max(0, find(viewState.mode)); onActivated: downloadController.setValue("mode", currentText) }
                            }
                            LabeledControl {
                                Layout.fillWidth: true; compact: page.denseLayout; label: viewState.mode === "Solo Audio" ? "Calidad de audio" : "Calidad de video"
                                XComboBox { Layout.fillWidth: true; compact: page.denseLayout; model: viewState.mode === "Solo Audio" ? downloadController.audioChoices : downloadController.videoChoices; currentIndex: Math.max(0, find(viewState.mode === "Solo Audio" ? viewState.selectedAudio : viewState.selectedVideo)); onActivated: downloadController.setValue(viewState.mode === "Solo Audio" ? "selectedAudio" : "selectedVideo", currentText) }
                            }
                        }
                        LabeledControl {
                            Layout.fillWidth: true; compact: page.denseLayout; label: "Preset de conversión"
                            XComboBox { Layout.fillWidth: true; compact: page.denseLayout; model: viewState.mode === "Solo Audio" ? presetStore.audioPresets : presetStore.videoPresets; currentIndex: Math.max(0, find(viewState.preset)); onActivated: downloadController.setValue("preset", currentText) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            XSwitch { text: "Aplicar preset"; checked: options.applyPreset; onToggled: downloadController.setOption("applyPreset", checked) }
                            XSwitch { text: "Mantener original"; checked: options.keepOriginal; enabled: options.applyPreset; onToggled: downloadController.setOption("keepOriginal", checked) }
                            Item { Layout.fillWidth: true }
                            XButton { objectName: "advancedToolsButton"; compact: true; text: "Todas las herramientas"; kind: "secondary"; onClicked: advanced.open() }
                        }
                    }
                }
            }

            Popup {
                id: advanced
                objectName: "advancedToolsPopup"
                parent: Overlay.overlay
                x: Math.round((parent.width - width) / 2)
                y: Math.round((parent.height - height) / 2)
                width: Math.min(1120, parent.width - 28)
                height: Math.min(650, parent.height - 28)
                padding: 16
                modal: true
                focus: true
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: 18; color: theme.colors.surfaceRaised; border.color: theme.colors.primary; border.width: 1 }
                enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: settingsController.state.animationsEnabled ? 150 : 0 } }
                exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: settingsController.state.animationsEnabled ? 120 : 0 } }

                contentItem: ScrollView {
                    id: advancedScroll
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical: XScrollBar {}

                    ColumnLayout {
                        id: advancedContent
                        width: advancedScroll.availableWidth
                        spacing: 12
                        RowLayout {
                            Layout.fillWidth: true
                            SectionTitle { Layout.fillWidth: true; compact: page.denseLayout; eyebrow: "MEJORAS"; title: "Procesamiento sin salir de Xomacito"; description: "Recorta, recodifica, extrae fotogramas o reescala con el mismo flujo."; number: "02" }
                            XButton { compact: true; text: "Cerrar"; kind: "ghost"; onClicked: advanced.close() }
                        }
                    TabBar {
                        id: toolsTabs
                        Layout.fillWidth: true
                        background: Rectangle { radius: 11; color: theme.colors.surfaceSoft }
                        Repeater {
                            model: ["Fragmento", "Subtítulos", "Recodificación", "Fotogramas", "Reescalado"]
                            TabButton {
                                text: modelData
                                contentItem: Text { text: parent.text; color: parent.checked ? theme.colors.text : theme.colors.textMuted; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11; font.weight: parent.checked ? Font.DemiBold : Font.Normal }
                                background: Rectangle { radius: 9; color: parent.checked ? theme.colors.primary : "transparent" }
                            }
                        }
                    }
                    StackLayout {
                        Layout.fillWidth: true
                        currentIndex: toolsTabs.currentIndex

                        GridLayout {
                            columns: advanced.width > 850 ? 4 : 2; rowSpacing: 10; columnSpacing: 10
                            XSwitch { Layout.columnSpan: 2; text: "Activar corte de fragmento"; checked: options.fragmentEnabled; onToggled: downloadController.setOption("fragmentEnabled", checked) }
                            XSwitch { Layout.columnSpan: 2; text: "Corte preciso (más lento)"; checked: options.preciseClip; enabled: options.fragmentEnabled; onToggled: downloadController.setOption("preciseClip", checked) }
                            LabeledControl { Layout.fillWidth: true; label: "Inicio (HH:MM:SS)"; XTextField { Layout.fillWidth: true; text: options.startTime; onEditingFinished: downloadController.setOption("startTime", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Final (HH:MM:SS)"; XTextField { Layout.fillWidth: true; text: options.endTime; onEditingFinished: downloadController.setOption("endTime", text) } }
                            XSwitch { text: "Forzar descarga completa"; checked: options.forceFullDownload; onToggled: downloadController.setOption("forceFullDownload", checked) }
                            XSwitch { text: "Conservar original"; checked: options.keepOriginalOnClip; onToggled: downloadController.setOption("keepOriginalOnClip", checked) }
                        }

                        GridLayout {
                            columns: advanced.width > 850 ? 3 : 1; rowSpacing: 10; columnSpacing: 10
                            XSwitch { text: "Descargar subtítulos"; checked: options.downloadSubtitles; onToggled: downloadController.setOption("downloadSubtitles", checked) }
                            XSwitch { text: "Limpiar subtítulo"; checked: options.cleanSubtitle; onToggled: downloadController.setOption("cleanSubtitle", checked) }
                            XSwitch { text: "Conservar subtítulo completo"; checked: options.keepFullSubtitle; onToggled: downloadController.setOption("keepFullSubtitle", checked) }
                            LabeledControl { Layout.fillWidth: true; label: "Idioma"; XComboBox { Layout.fillWidth: true; model: downloadController.subtitleLanguages; currentIndex: Math.max(0, find(viewState.selectedSubtitleLanguage)); onActivated: downloadController.setValue("selectedSubtitleLanguage", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Formato"; XComboBox { Layout.fillWidth: true; model: downloadController.subtitleFormats; currentIndex: Math.max(0, find(viewState.selectedSubtitleFormat)); onActivated: downloadController.setValue("selectedSubtitleFormat", currentText) } }
                            XButton { Layout.alignment: Qt.AlignBottom; text: "Guardar subtítulo"; kind: "secondary"; onClicked: downloadController.saveSubtitle() }
                        }

                        ColumnLayout {
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                XSwitch { text: "Recodificar video"; checked: options.recodeVideoEnabled; onToggled: downloadController.setOption("recodeVideoEnabled", checked) }
                                XSwitch { text: "Recodificar audio"; checked: options.recodeAudioEnabled; onToggled: downloadController.setOption("recodeAudioEnabled", checked) }
                                XSwitch { text: "Todas las pistas"; checked: options.useAllAudioTracks; onToggled: downloadController.setOption("useAllAudioTracks", checked) }
                            }
                            GridLayout {
                                Layout.fillWidth: true; columns: advanced.width > 850 ? 4 : 2; columnSpacing: 10; rowSpacing: 10
                                LabeledControl { Layout.fillWidth: true; label: "Procesador"; XComboBox { Layout.fillWidth: true; model: ["CPU", "NVIDIA", "AMD", "Intel"]; currentIndex: Math.max(0, find(options.recodeProc)); onActivated: downloadController.setOption("recodeProc", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Códec de video"; XComboBox { Layout.fillWidth: true; model: presetStore.videoCodecs; currentIndex: Math.max(0, find(options.recodeCodecName)); onActivated: downloadController.setOption("recodeCodecName", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Perfil de video"; XComboBox { Layout.fillWidth: true; model: presetStore.profiles("video", options.recodeCodecName); currentIndex: Math.max(0, find(options.recodeProfileName)); onActivated: downloadController.setOption("recodeProfileName", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "FPS forzado"; XTextField { Layout.fillWidth: true; text: options.fpsValue; onEditingFinished: downloadController.setOption("fpsValue", text) } }
                                LabeledControl { Layout.fillWidth: true; label: "Códec de audio"; XComboBox { Layout.fillWidth: true; model: presetStore.audioCodecs; currentIndex: Math.max(0, find(options.recodeAudioCodecName)); onActivated: downloadController.setOption("recodeAudioCodecName", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Perfil de audio"; XComboBox { Layout.fillWidth: true; model: presetStore.profiles("audio", options.recodeAudioCodecName); currentIndex: Math.max(0, find(options.recodeAudioProfileName)); onActivated: downloadController.setOption("recodeAudioProfileName", currentText) } }
                                XSwitch { text: "Forzar FPS"; checked: options.fpsForceEnabled; onToggled: downloadController.setOption("fpsForceEnabled", checked) }
                                XSwitch { text: "Cambiar resolución"; checked: options.resolutionChangeEnabled; onToggled: downloadController.setOption("resolutionChangeEnabled", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Ancho"; XTextField { Layout.fillWidth: true; text: options.resWidth; onEditingFinished: downloadController.setOption("resWidth", text) } }
                                LabeledControl { Layout.fillWidth: true; label: "Alto"; XTextField { Layout.fillWidth: true; text: options.resHeight; onEditingFinished: downloadController.setOption("resHeight", text) } }
                                XSwitch { text: "Mantener proporción"; checked: options.maintainAspect; onToggled: downloadController.setOption("maintainAspect", checked) }
                                XSwitch { text: "No aumentar resolución"; checked: options.noUpscaling; onToggled: downloadController.setOption("noUpscaling", checked) }
                            }
                        }

                        GridLayout {
                            columns: advanced.width > 850 ? 4 : 2; rowSpacing: 10; columnSpacing: 10
                            XSwitch { Layout.columnSpan: 2; text: "Extraer fotogramas"; checked: options.extractFramesEnabled; onToggled: downloadController.setOption("extractFramesEnabled", checked) }
                            XSwitch { Layout.columnSpan: 2; text: "Conservar video original"; checked: options.keepOriginalExtract; onToggled: downloadController.setOption("keepOriginalExtract", checked) }
                            LabeledControl { Layout.fillWidth: true; label: "Tipo"; XComboBox { Layout.fillWidth: true; model: ["Todos los fotogramas", "Fotogramas por segundo"]; currentIndex: Math.max(0, find(options.extractType)); onActivated: downloadController.setOption("extractType", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Formato"; XComboBox { Layout.fillWidth: true; model: ["png", "jpg", "webp"]; currentIndex: Math.max(0, find(options.extractFormat)); onActivated: downloadController.setOption("extractFormat", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "FPS"; XTextField { Layout.fillWidth: true; text: options.extractFps; onEditingFinished: downloadController.setOption("extractFps", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Carpeta"; XTextField { Layout.fillWidth: true; text: options.extractFolderName; onEditingFinished: downloadController.setOption("extractFolderName", text) } }
                        }

                        GridLayout {
                            columns: advanced.width > 850 ? 4 : 2; rowSpacing: 10; columnSpacing: 10
                            XSwitch { Layout.columnSpan: 2; text: "Reescalar video con NCNN"; checked: options.upscaleVideoEnabled; onToggled: downloadController.setOption("upscaleVideoEnabled", checked) }
                            XSwitch { text: "TTA"; checked: options.upscaleTta; onToggled: downloadController.setOption("upscaleTta", checked) }
                            XSwitch { text: "Conservar transparencia"; checked: options.upscaleTransparency; onToggled: downloadController.setOption("upscaleTransparency", checked) }
                            LabeledControl { Layout.fillWidth: true; label: "Motor"; XComboBox { Layout.fillWidth: true; model: ["realesrgan-ncnn-vulkan", "waifu2x-ncnn-vulkan", "srmd-ncnn-vulkan", "realsr-ncnn-vulkan"]; currentIndex: Math.max(0, find(options.upscaleEngine)); onActivated: downloadController.setOption("upscaleEngine", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Modelo"; XTextField { Layout.fillWidth: true; text: options.upscaleModel; onEditingFinished: downloadController.setOption("upscaleModel", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Escala"; XComboBox { Layout.fillWidth: true; model: ["2x", "3x", "4x"]; currentIndex: Math.max(0, find(options.upscaleScale)); onActivated: downloadController.setOption("upscaleScale", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Contenedor"; XComboBox { Layout.fillWidth: true; model: ["Mismo que el original", "MP4", "MOV", "MKV", "WEBM"]; currentIndex: Math.max(0, find(options.upscaleContainer)); onActivated: downloadController.setOption("upscaleContainer", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Tile"; XTextField { Layout.fillWidth: true; text: options.upscaleTile; onEditingFinished: downloadController.setOption("upscaleTile", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Denoise"; XTextField { Layout.fillWidth: true; text: options.upscaleDenoise; onEditingFinished: downloadController.setOption("upscaleDenoise", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Nombre de salida"; XTextField { Layout.fillWidth: true; text: options.upscaleOutputName; onEditingFinished: downloadController.setOption("upscaleOutputName", text) } }
                        }
                    }
                }
            }
            }

        XCard {
            objectName: "downloadFooterCard"
            Layout.fillWidth: true
            implicitHeight: downloadFooter.implicitHeight + (page.denseLayout ? 18 : 24)
            cardColor: theme.colors.surfaceRaised
            ColumnLayout {
                id: downloadFooter
                anchors.fill: parent
                anchors.margins: page.denseLayout ? 9 : 12
                spacing: page.denseLayout ? 7 : 10
                GridLayout {
                    id: footerGrid
                    Layout.fillWidth: true
                    columns: viewState.lastOutput.length > 0 ? 5 : 4
                    columnSpacing: page.denseLayout ? 8 : 10
                    rowSpacing: 8
                    LabeledControl {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 500
                        compact: page.denseLayout
                        label: "Carpeta de salida"
                        XTextField { Layout.fillWidth: true; compact: page.denseLayout; text: viewState.outputPath; onEditingFinished: downloadController.setValue("outputPath", text) }
                    }
                    XButton { Layout.alignment: Qt.AlignBottom; compact: page.denseLayout; text: "Elegir carpeta"; kind: "secondary"; onClicked: downloadController.chooseOutputFolder() }
                    LabeledControl {
                        Layout.fillWidth: true
                        compact: page.denseLayout
                        label: "Límite MB/s"
                        XTextField { Layout.fillWidth: true; compact: page.denseLayout; text: options.speedLimit; onEditingFinished: downloadController.setOption("speedLimit", text) }
                    }
                    XButton {
                        Layout.alignment: Qt.AlignBottom
                        compact: page.denseLayout
                        text: viewState.busy ? "Cancelar" : viewState.localFile ? "Procesar" : "Iniciar descarga"
                        kind: viewState.busy ? "danger" : "primary"
                        enabled: viewState.busy || viewState.analyzed
                        onClicked: viewState.busy ? downloadController.cancel() : downloadController.start()
                    }
                    XButton {
                        id: resultButton
                        Layout.alignment: Qt.AlignBottom
                        compact: page.denseLayout
                        visible: viewState.lastOutput.length > 0
                        text: "Resultado"
                        kind: "secondary"
                        onClicked: downloadController.openOutput()
                    }
                }
            }
        }
        ProgressStrip { objectName: "downloadProgress"; Layout.fillWidth: true; compact: page.denseLayout; value: viewState.progress; status: viewState.status; busy: viewState.busy }
    }
}
