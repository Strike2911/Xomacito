import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: imageController.state
    property var options: imageController.options
    property var selected: imageController.selected

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        SectionTitle {
            Layout.fillWidth: true
            eyebrow: "ESTUDIO DE IMAGEN"
            title: "Más detalle. Menos ruido."
            description: "Convierte, escala, limpia fondos y prepara recursos con procesamiento por lotes."
            number: "03"
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: importBar.implicitHeight + 28
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                id: importBar
                anchors.fill: parent; anchors.margins: 14; spacing: 9
                XButton { text: "Importar archivos"; onClicked: imageController.importFiles() }
                XButton { text: "Importar carpeta"; kind: "secondary"; onClicked: imageController.importFolder() }
                XButton { text: "Pegar"; kind: "secondary"; onClicked: imageController.paste() }
                XTextField { Layout.fillWidth: true; placeholderText: "O pega un enlace para capturar su imagen"; text: viewState.url; onTextEdited: imageController.setValue("url", text); onAccepted: imageController.analyzeUrl() }
                XButton { text: "Analizar"; compact: true; enabled: !viewState.busy && viewState.url.length > 3; onClicked: imageController.analyzeUrl() }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: page.width >= 1060 ? 12 : 1
            columnSpacing: 12
            rowSpacing: 12

            XCard {
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.columnSpan: page.width >= 1060 ? 3 : 1
                Layout.minimumHeight: 390
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "RECURSOS  " + viewState.itemCount; color: theme.colors.primary; font.pixelSize: 11; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        XButton { text: "Vaciar"; compact: true; kind: "ghost"; onClicked: imageController.clear() }
                    }
                    ListView {
                        id: resources
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                        model: imageController.model
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Rectangle {
                            required property string itemId
                            required property string name
                            required property string status
                            required property string preview
                            required property int index
                            width: resources.width; height: 58; radius: 10
                            color: viewState.selectedIndex === index ? theme.colors.surfaceRaised : theme.colors.surfaceSoft
                            border.width: viewState.selectedIndex === index ? 2 : 1
                            border.color: viewState.selectedIndex === index ? theme.colors.primary : theme.colors.border
                            MouseArea { anchors.fill: parent; onClicked: imageController.select(index) }
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 7; spacing: 8
                                Rectangle {
                                    width: 42; height: 42; radius: 8; color: theme.colors.backgroundAlt; clip: true
                                    Image { anchors.fill: parent; source: preview; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                                    Text { anchors.centerIn: parent; visible: !preview; text: "◇"; color: theme.colors.primary }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Text { Layout.fillWidth: true; text: name; color: theme.colors.text; font.pixelSize: 11; elide: Text.ElideMiddle }
                                    Text { text: status; color: status === "COMPLETED" ? theme.colors.success : theme.colors.textMuted; font.pixelSize: 9 }
                                }
                                XButton { compact: true; implicitWidth: 32; text: "×"; kind: "ghost"; onClicked: imageController.remove(index) }
                            }
                        }
                        Text { anchors.centerIn: parent; visible: resources.count === 0; text: "Arrastra, pega o importa\ntus recursos"; color: theme.colors.textMuted; horizontalAlignment: Text.AlignHCenter }
                    }
                }
            }

            XCard {
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.columnSpan: page.width >= 1060 ? 5 : 1
                Layout.minimumHeight: 390
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { text: selected.name || "Previsualización"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { text: selected.detail || "Selecciona un recurso"; color: theme.colors.textMuted; font.pixelSize: 10 }
                        }
                        XButton { compact: true; text: "Quitar"; kind: "ghost"; enabled: viewState.selectedIndex >= 0; onClicked: imageController.removeSelected() }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; radius: 14
                        color: theme.colors.backgroundAlt; border.color: theme.colors.border; border.width: 1; clip: true
                        Image { anchors.fill: parent; anchors.margins: 10; source: viewState.resultPreviewSource || viewState.previewSource; fillMode: Image.PreserveAspectFit; asynchronous: true; smooth: true }
                        Rectangle {
                            anchors.fill: parent; opacity: 0.08
                            gradient: Gradient {
                                GradientStop { position: 0; color: theme.colors.primary }
                                GradientStop { position: 1; color: "transparent" }
                            }
                        }
                        Text { anchors.centerIn: parent; visible: !viewState.previewSource && !viewState.resultPreviewSource; text: "Tu recurso aparecerá aquí"; color: theme.colors.textMuted }
                    }
                    LabeledControl {
                        Layout.fillWidth: true; label: "Nombre de salida"
                        XTextField { Layout.fillWidth: true; text: selected.title || ""; enabled: viewState.selectedIndex >= 0; onEditingFinished: imageController.setSelectedTitle(text) }
                    }
                }
            }

            XCard {
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.columnSpan: page.width >= 1060 ? 4 : 1
                Layout.minimumHeight: 390
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 10
                    Text { text: "AJUSTES DE SALIDA"; color: theme.colors.primary; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                    XComboBox { Layout.fillWidth: true; model: imageController.formats; currentIndex: Math.max(0, find(viewState.format)); onActivated: imageController.setValue("format", currentText) }
                    TabBar {
                        id: optionTabs
                        Layout.fillWidth: true
                        background: Rectangle { radius: 10; color: theme.colors.surfaceSoft }
                        Repeater {
                            model: ["Tamaño", "Lienzo", "Formato", "I.A.", "Video"]
                            TabButton {
                                text: modelData
                                contentItem: Text { text: parent.text; color: parent.checked ? "white" : theme.colors.textMuted; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                background: Rectangle { radius: 8; color: parent.checked ? theme.colors.primary : "transparent" }
                            }
                        }
                    }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical: XScrollBar {}
                        StackLayout {
                            width: parent.width
                            currentIndex: optionTabs.currentIndex
                            ColumnLayout {
                                spacing: 9
                                XSwitch { text: "Cambiar tamaño"; checked: options.resizeEnabled; onToggled: imageController.setOption("resizeEnabled", checked) }
                                RowLayout {
                                    Layout.fillWidth: true
                                    LabeledControl { Layout.fillWidth: true; label: "Ancho"; XTextField { Layout.fillWidth: true; text: options.resizeWidth; onEditingFinished: imageController.setOption("resizeWidth", text) } }
                                    LabeledControl { Layout.fillWidth: true; label: "Alto"; XTextField { Layout.fillWidth: true; text: options.resizeHeight; onEditingFinished: imageController.setOption("resizeHeight", text) } }
                                }
                                XSwitch { text: "Mantener proporción"; checked: options.resizeMaintainAspect; onToggled: imageController.setOption("resizeMaintainAspect", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Interpolación"; XComboBox { Layout.fillWidth: true; model: ["Lanczos (Mejor Calidad)", "Bicúbica", "Bilineal", "Vecino más cercano"]; currentIndex: Math.max(0, find(options.interpolation)); onActivated: imageController.setOption("interpolation", currentText) } }
                                XSwitch { text: "Procesar sólo archivos nuevos"; checked: viewState.processOnlyNew; onToggled: imageController.setValue("processOnlyNew", checked) }
                                XSwitch { text: "Crear subcarpeta"; checked: viewState.createSubfolder; onToggled: imageController.setValue("createSubfolder", checked) }
                                XTextField { Layout.fillWidth: true; visible: viewState.createSubfolder; text: viewState.subfolderName; onEditingFinished: imageController.setValue("subfolderName", text) }
                                LabeledControl { Layout.fillWidth: true; label: "Conflictos"; XComboBox { Layout.fillWidth: true; model: ["Renombrar", "Sobrescribir", "Omitir"]; currentIndex: Math.max(0, find(viewState.conflictPolicy)); onActivated: imageController.setValue("conflictPolicy", currentText) } }
                            }
                            ColumnLayout {
                                spacing: 9
                                XSwitch { text: "Ajustar a un lienzo"; checked: options.canvasEnabled; onToggled: imageController.setOption("canvasEnabled", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Ajuste"; XComboBox { Layout.fillWidth: true; model: ["Sin ajuste", "Cuadrado", "Vertical 9:16", "Horizontal 16:9", "Personalizado"]; currentIndex: Math.max(0, find(options.canvasOption)); onActivated: imageController.setOption("canvasOption", currentText) } }
                                RowLayout {
                                    Layout.fillWidth: true
                                    LabeledControl { Layout.fillWidth: true; label: "Ancho"; XTextField { Layout.fillWidth: true; text: options.canvasWidth; onEditingFinished: imageController.setOption("canvasWidth", text) } }
                                    LabeledControl { Layout.fillWidth: true; label: "Alto"; XTextField { Layout.fillWidth: true; text: options.canvasHeight; onEditingFinished: imageController.setOption("canvasHeight", text) } }
                                }
                                LabeledControl { Layout.fillWidth: true; label: "Margen"; Slider { Layout.fillWidth: true; from: 0; to: 800; stepSize: 10; value: options.canvasMargin; onMoved: imageController.setOption("canvasMargin", value) } }
                                LabeledControl { Layout.fillWidth: true; label: "Posición"; XComboBox { Layout.fillWidth: true; model: ["Centro", "Arriba", "Abajo", "Izquierda", "Derecha"]; currentIndex: Math.max(0, find(options.canvasPosition)); onActivated: imageController.setOption("canvasPosition", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Desbordamiento"; XComboBox { Layout.fillWidth: true; model: ["Reducir hasta que quepa", "Recortar", "Permitir desborde"]; currentIndex: Math.max(0, find(options.canvasOverflow)); onActivated: imageController.setOption("canvasOverflow", currentText) } }
                                XSwitch { text: "Fondo personalizado"; checked: options.backgroundEnabled; onToggled: imageController.setOption("backgroundEnabled", checked) }
                                XComboBox { Layout.fillWidth: true; model: ["Color Sólido", "Gradiente", "Imagen"]; currentIndex: Math.max(0, find(options.backgroundType)); onActivated: imageController.setOption("backgroundType", currentText) }
                                RowLayout {
                                    Layout.fillWidth: true
                                    XButton { Layout.fillWidth: true; text: "Color 1"; kind: "secondary"; onClicked: imageController.setOption("backgroundColor", imageController.chooseColor(options.backgroundColor)) }
                                    XButton { Layout.fillWidth: true; text: "Color 2"; kind: "secondary"; onClicked: imageController.setOption("gradientColor2", imageController.chooseColor(options.gradientColor2)) }
                                }
                                XComboBox { Layout.fillWidth: true; model: ["Horizontal (Izq → Der)", "Vertical (Arriba → Abajo)", "Diagonal"]; currentIndex: Math.max(0, find(options.gradientDirection)); onActivated: imageController.setOption("gradientDirection", currentText) }
                                XButton { Layout.fillWidth: true; text: "Elegir imagen de fondo"; kind: "secondary"; onClicked: imageController.chooseBackgroundImage() }
                            }
                            ColumnLayout {
                                spacing: 9
                                Text { text: "PNG / WEBP / AVIF"; color: theme.colors.text; font.weight: Font.DemiBold }
                                XSwitch { text: "Conservar transparencia PNG"; checked: options.pngTransparency; onToggled: imageController.setOption("pngTransparency", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Compresión PNG: " + options.pngCompression; Slider { Layout.fillWidth: true; from: 0; to: 9; stepSize: 1; value: options.pngCompression; onMoved: imageController.setOption("pngCompression", value) } }
                                LabeledControl { Layout.fillWidth: true; label: "Calidad JPG: " + options.jpgQuality; Slider { Layout.fillWidth: true; from: 1; to: 100; stepSize: 1; value: options.jpgQuality; onMoved: imageController.setOption("jpgQuality", value) } }
                                XComboBox { Layout.fillWidth: true; model: ["4:2:0 (Estándar)", "4:2:2", "4:4:4 (Máxima)"]; currentIndex: Math.max(0, find(options.jpgSubsampling)); onActivated: imageController.setOption("jpgSubsampling", currentText) }
                                XSwitch { text: "JPG progresivo"; checked: options.jpgProgressive; onToggled: imageController.setOption("jpgProgressive", checked) }
                                XSwitch { text: "WEBP sin pérdida"; checked: options.webpLossless; onToggled: imageController.setOption("webpLossless", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Calidad WEBP: " + options.webpQuality; Slider { Layout.fillWidth: true; from: 1; to: 100; stepSize: 1; value: options.webpQuality; onMoved: imageController.setOption("webpQuality", value) } }
                                XSwitch { text: "Transparencia WEBP"; checked: options.webpTransparency; onToggled: imageController.setOption("webpTransparency", checked) }
                                XSwitch { text: "Conservar metadatos WEBP"; checked: options.webpMetadata; onToggled: imageController.setOption("webpMetadata", checked) }
                                XSwitch { text: "AVIF sin pérdida"; checked: options.avifLossless; onToggled: imageController.setOption("avifLossless", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Calidad AVIF: " + options.avifQuality; Slider { Layout.fillWidth: true; from: 1; to: 100; stepSize: 1; value: options.avifQuality; onMoved: imageController.setOption("avifQuality", value) } }
                                XSwitch { text: "Transparencia AVIF"; checked: options.avifTransparency; onToggled: imageController.setOption("avifTransparency", checked) }
                                XSwitch { text: "Combinar en un PDF"; checked: options.pdfCombine; onToggled: imageController.setOption("pdfCombine", checked) }
                                XTextField { Layout.fillWidth: true; text: options.pdfTitle; placeholderText: "Título del PDF"; onEditingFinished: imageController.setOption("pdfTitle", text) }
                                XComboBox { Layout.fillWidth: true; model: ["LZW (Recomendada)", "Deflate", "Sin compresión"]; currentIndex: Math.max(0, find(options.tiffCompression)); onActivated: imageController.setOption("tiffCompression", currentText) }
                                XSwitch { text: "Transparencia TIFF"; checked: options.tiffTransparency; onToggled: imageController.setOption("tiffTransparency", checked) }
                                XSwitch { text: "Transparencia PDF"; checked: options.pdfTransparent; onToggled: imageController.setOption("pdfTransparent", checked) }
                                Text { text: "ICO: 16 · 32 · 48 · 64 · 128 · 256 px"; color: theme.colors.textMuted; font.pixelSize: 10 }
                                RowLayout {
                                    XSwitch { text: "16"; checked: options.ico16; onToggled: imageController.setOption("ico16", checked) }
                                    XSwitch { text: "32"; checked: options.ico32; onToggled: imageController.setOption("ico32", checked) }
                                    XSwitch { text: "48"; checked: options.ico48; onToggled: imageController.setOption("ico48", checked) }
                                }
                                RowLayout {
                                    XSwitch { text: "64"; checked: options.ico64; onToggled: imageController.setOption("ico64", checked) }
                                    XSwitch { text: "128"; checked: options.ico128; onToggled: imageController.setOption("ico128", checked) }
                                    XSwitch { text: "256"; checked: options.ico256; onToggled: imageController.setOption("ico256", checked) }
                                }
                                XSwitch { text: "Compresión BMP RLE"; checked: options.bmpRle; onToggled: imageController.setOption("bmpRle", checked) }
                            }
                            ColumnLayout {
                                spacing: 9
                                XSwitch { text: "Quitar fondo con rembg"; checked: options.rembgEnabled; onToggled: imageController.setOption("rembgEnabled", checked) }
                                XSwitch { text: "Aceleración GPU ONNX"; checked: options.rembgGpu; onToggled: imageController.setOption("rembgGpu", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Familia"; XComboBox { Layout.fillWidth: true; model: imageController.rembgFamilies; currentIndex: Math.max(0, find(options.rembgFamily)); onActivated: imageController.setOption("rembgFamily", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Modelo"; XComboBox { Layout.fillWidth: true; model: imageController.rembgModels(options.rembgFamily); currentIndex: Math.max(0, find(options.rembgModel)); onActivated: imageController.setOption("rembgModel", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Suavizado: " + options.rembgSmooth; Slider { Layout.fillWidth: true; from: 0; to: 20; stepSize: 1; value: options.rembgSmooth; onMoved: imageController.setOption("rembgSmooth", value) } }
                                LabeledControl { Layout.fillWidth: true; label: "Expandir máscara: " + options.rembgExpand; Slider { Layout.fillWidth: true; from: -20; to: 40; stepSize: 1; value: options.rembgExpand; onMoved: imageController.setOption("rembgExpand", value) } }
                                XButton { Layout.fillWidth: true; text: "Abrir modelos rembg"; kind: "secondary"; onClicked: imageController.browseModelFolder() }
                                Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                                XSwitch { text: "Reescalar con NCNN"; checked: options.upscaleEnabled; onToggled: imageController.setOption("upscaleEnabled", checked) }
                                XComboBox { Layout.fillWidth: true; model: ["realesrgan-ncnn-vulkan", "waifu2x-ncnn-vulkan", "srmd-ncnn-vulkan"]; currentIndex: Math.max(0, find(options.upscaleEngine)); onActivated: imageController.setOption("upscaleEngine", currentText) }
                                XTextField { Layout.fillWidth: true; text: options.upscaleModel; placeholderText: "Modelo"; onEditingFinished: imageController.setOption("upscaleModel", text) }
                                XComboBox { Layout.fillWidth: true; model: ["2", "3", "4"]; currentIndex: Math.max(0, find(options.upscaleScale)); onActivated: imageController.setOption("upscaleScale", currentText) }
                                RowLayout {
                                    Layout.fillWidth: true
                                    XTextField { Layout.fillWidth: true; text: options.upscaleDenoise; placeholderText: "Denoise"; onEditingFinished: imageController.setOption("upscaleDenoise", text) }
                                    XTextField { Layout.fillWidth: true; text: options.upscaleTile; placeholderText: "Tile"; onEditingFinished: imageController.setOption("upscaleTile", text) }
                                }
                                XSwitch { text: "TTA"; checked: options.upscaleTta; onToggled: imageController.setOption("upscaleTta", checked) }
                                XButton { Layout.fillWidth: true; text: "Abrir modelos de escalado"; kind: "secondary"; onClicked: imageController.browseUpscaleFolder() }
                            }
                            ColumnLayout {
                                spacing: 9
                                Text { text: "CREAR VIDEO DESDE IMÁGENES"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold }
                                XTextField { Layout.fillWidth: true; text: options.videoTitle; placeholderText: "Nombre del video"; onEditingFinished: imageController.setOption("videoTitle", text) }
                                RowLayout {
                                    Layout.fillWidth: true
                                    XTextField { Layout.fillWidth: true; text: options.videoWidth; placeholderText: "Ancho"; onEditingFinished: imageController.setOption("videoWidth", text) }
                                    XTextField { Layout.fillWidth: true; text: options.videoHeight; placeholderText: "Alto"; onEditingFinished: imageController.setOption("videoHeight", text) }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    XTextField { Layout.fillWidth: true; text: options.videoFps; placeholderText: "FPS"; onEditingFinished: imageController.setOption("videoFps", text) }
                                    XTextField { Layout.fillWidth: true; text: options.videoFrameDuration; placeholderText: "Segundos/foto"; onEditingFinished: imageController.setOption("videoFrameDuration", text) }
                                }
                                XComboBox { Layout.fillWidth: true; model: ["Mantener Tamaño Original", "Ajustar y rellenar", "Recortar al lienzo"]; currentIndex: Math.max(0, find(options.videoFitMode)); onActivated: imageController.setOption("videoFitMode", currentText) }
                                Text { Layout.fillWidth: true; text: "Selecciona .mp4, .mov, .webm o .gif como formato de salida para activar este flujo."; wrapMode: Text.WordWrap; color: theme.colors.textMuted; font.pixelSize: 10 }
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 9
            XTextField { Layout.fillWidth: true; text: viewState.outputPath; onEditingFinished: imageController.setValue("outputPath", text) }
            XButton { compact: true; text: "Salida"; kind: "secondary"; onClicked: imageController.chooseOutputFolder() }
            XButton { compact: true; text: "Abrir"; kind: "ghost"; onClicked: imageController.openOutput() }
            XButton { visible: viewState.lastOutput.length > 0; compact: true; text: "Copiar"; kind: "secondary"; onClicked: imageController.copyResult() }
            XButton { text: viewState.busy ? "Cancelar" : "Procesar " + viewState.itemCount; kind: viewState.busy ? "danger" : "primary"; enabled: viewState.busy || viewState.itemCount > 0; onClicked: viewState.busy ? imageController.cancel() : imageController.start() }
        }
        ProgressStrip { Layout.fillWidth: true; value: viewState.progress; status: viewState.status; busy: viewState.busy }
    }
}
