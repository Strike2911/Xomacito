import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: imageController.state
    property var options: imageController.options
    property var selected: imageController.selected
    property bool wide: width >= 1040
    property bool dense: height < 760

    function taskTitle() {
        if (viewState.task === "removeBackground") return "Quitar fondo"
        if (viewState.task === "upscaleImage") return "Mejorar imagen"
        if (viewState.task === "upscaleVideo") return "Mejorar video"
        return "Convertir y preparar"
    }
    function processLabel() {
        if (viewState.busy) return "Cancelar"
        if (viewState.task === "removeBackground") return "Quitar fondo · " + viewState.itemCount
        if (viewState.task === "upscaleImage") return "Mejorar imágenes · " + viewState.itemCount
        if (viewState.task === "upscaleVideo") return "Mejorar videos · " + viewState.itemCount
        return "Convertir · " + viewState.itemCount
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        SectionTitle {
            Layout.fillWidth: true
            compact: page.dense
            eyebrow: "ESTUDIO DE IMAGEN"
            title: "¿Qué quieres hacer?"
            description: "Elige una tarea y Xomacito prepara los ajustes recomendados. Los controles técnicos siguen disponibles."
            number: "03"
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: page.dense ? 58 : 70
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8
                Repeater {
                    model: [
                        { key: "removeBackground", label: "Quitar fondo", hint: "PNG transparente" },
                        { key: "upscaleImage", label: "Mejorar imagen", hint: "Más detalle" },
                        { key: "upscaleVideo", label: "Mejorar video", hint: "2× o 4×" },
                        { key: "convert", label: "Convertir", hint: "Tamaño y formato" }
                    ]
                    delegate: Button {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        hoverEnabled: true
                        onClicked: imageController.setTask(modelData.key)
                        contentItem: Column {
                            anchors.centerIn: parent
                            spacing: 2
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.label
                                color: viewState.task === modelData.key ? "#FFFFFF" : theme.colors.text
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.hint
                                color: viewState.task === modelData.key ? "#DDFBFF" : theme.colors.textMuted
                                font.pixelSize: 9
                            }
                        }
                        background: Rectangle {
                            radius: 12
                            color: viewState.task === modelData.key ? theme.colors.primary : parent.hovered ? theme.colors.surfaceSoft : "transparent"
                            border.width: viewState.task === modelData.key || parent.activeFocus ? 2 : 1
                            border.color: viewState.task === modelData.key ? theme.colors.accent : theme.colors.border
                            Behavior on color { ColorAnimation { duration: settingsController.state.animationsEnabled ? 130 : 0 } }
                        }
                    }
                }
            }
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: page.dense ? 54 : 64
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                XButton {
                    text: viewState.task === "upscaleVideo" ? "Importar videos" : "Importar imágenes"
                    onClicked: imageController.importFiles()
                }
                XButton { text: "Carpeta"; compact: true; kind: "secondary"; onClicked: imageController.importFolder() }
                XButton { text: "Pegar"; compact: true; kind: "secondary"; visible: viewState.task !== "upscaleVideo"; onClicked: imageController.paste() }
                XTextField {
                    Layout.fillWidth: true
                    visible: viewState.task !== "upscaleVideo"
                    placeholderText: "Pega un enlace para capturar su imagen"
                    text: viewState.url
                    onTextEdited: imageController.setValue("url", text)
                    onAccepted: imageController.analyzeUrl()
                }
                XButton {
                    text: "Analizar"
                    compact: true
                    visible: viewState.task !== "upscaleVideo"
                    enabled: !viewState.busy
                    onClicked: imageController.analyzeUrl()
                }
                Text {
                    Layout.fillWidth: true
                    visible: viewState.task === "upscaleVideo"
                    text: "MP4, MOV, MKV, WEBM o AVI · el resultado se guarda como MP4 compatible"
                    color: theme.colors.textMuted
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: page.wide ? 12 : 1
            columnSpacing: 10
            rowSpacing: 10

            XCard {
                id: filesCard
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.wide ? 3 : 1
                Layout.minimumHeight: page.dense ? 230 : 278
                cardColor: fileDropArea.containsDrag ? theme.colors.surfaceRaised : theme.colors.surface
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "ARCHIVOS  " + viewState.itemCount; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Item { Layout.fillWidth: true }
                        XButton { text: "Vaciar"; compact: true; kind: "ghost"; onClicked: imageController.clear() }
                    }
                    ListView {
                        id: resources
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 6
                        model: imageController.model
                        ScrollBar.vertical: XScrollBar {}
                        delegate: Rectangle {
                            required property string name
                            required property string status
                            required property string preview
                            required property string mediaType
                            required property int index
                            width: resources.width
                            height: 54
                            radius: 10
                            color: viewState.selectedIndex === index ? theme.colors.surfaceRaised : theme.colors.surfaceSoft
                            border.width: viewState.selectedIndex === index ? 2 : 1
                            border.color: viewState.selectedIndex === index ? theme.colors.primary : theme.colors.border
                            MouseArea { anchors.fill: parent; onClicked: imageController.select(index) }
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 8
                                Rectangle {
                                    width: 42; height: 42; radius: 8
                                    color: theme.colors.backgroundAlt
                                    clip: true
                                    Image { anchors.fill: parent; source: preview; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                                    Text { anchors.centerIn: parent; visible: !preview; text: mediaType === "video" ? "▶" : "◇"; color: theme.colors.primary }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    Text { Layout.fillWidth: true; text: name; color: theme.colors.text; font.pixelSize: 10; elide: Text.ElideMiddle }
                                    Text { text: status === "COMPLETED" ? "Listo" : "Pendiente"; color: status === "COMPLETED" ? theme.colors.success : theme.colors.textMuted; font.pixelSize: 9 }
                                }
                                XButton { compact: true; implicitWidth: 30; text: "×"; kind: "ghost"; onClicked: imageController.remove(index) }
                            }
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: resources.count === 0
                            text: viewState.task === "upscaleVideo" ? "Arrastra videos aquí" : "Arrastra imágenes aquí"
                            color: theme.colors.textMuted
                        }
                    }
                }
                DropArea {
                    id: fileDropArea
                    objectName: "imageStudioDropArea"
                    anchors.fill: parent
                    onDropped: function(drop) {
                        if (!drop.hasUrls)
                            return
                        var paths = []
                        for (var index = 0; index < drop.urls.length; ++index)
                            paths.push(drop.urls[index].toString())
                        imageController.addPaths(paths)
                        drop.acceptProposedAction()
                    }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.wide ? 4 : 1
                Layout.minimumHeight: page.dense ? 230 : 278
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            Text { Layout.fillWidth: true; text: selected.name || "Vista previa"; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { text: viewState.resultPreviewSource ? "RESULTADO" : "ORIGINAL"; color: viewState.resultPreviewSource ? theme.colors.success : theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.Bold }
                        }
                        XButton { compact: true; text: "Quitar"; kind: "ghost"; enabled: viewState.selectedIndex >= 0; onClicked: imageController.removeSelected() }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 14
                        color: theme.colors.backgroundAlt
                        border.color: theme.colors.border
                        border.width: 1
                        clip: true
                        Image {
                            anchors.fill: parent
                            anchors.margins: 8
                            source: viewState.resultPreviewSource || viewState.previewSource
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            smooth: true
                        }
                        Text { anchors.centerIn: parent; visible: !viewState.previewSource && !viewState.resultPreviewSource; text: "Tu recurso aparecerá aquí"; color: theme.colors.textMuted }
                    }
                    XTextField {
                        Layout.fillWidth: true
                        placeholderText: "Nombre del resultado"
                        text: selected.title || ""
                        enabled: viewState.selectedIndex >= 0
                        onEditingFinished: imageController.setSelectedTitle(text)
                    }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.wide ? 5 : 1
                Layout.minimumHeight: page.dense ? 230 : 278
                cardColor: theme.colors.surfaceRaised
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: page.dense ? 11 : 14
                    spacing: page.dense ? 6 : 9
                    Text { text: "TAREA SELECCIONADA"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                    Text { text: page.taskTitle(); color: theme.colors.text; font.pixelSize: page.dense ? 17 : 20; font.weight: Font.DemiBold }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 0
                        Layout.preferredHeight: 1
                        clip: true
                        currentIndex: viewState.task === "removeBackground" ? 0 : viewState.task === "upscaleImage" ? 1 : viewState.task === "upscaleVideo" ? 2 : 3

                        ColumnLayout {
                            spacing: page.dense ? 6 : 8
                            Text { Layout.fillWidth: true; visible: !page.dense; text: "Detecta el sujeto y crea una transparencia real. Ideal para miniaturas, productos y recursos de edición."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                LabeledControl {
                                    Layout.fillWidth: true
                                    compact: page.dense
                                    label: "Tipo de imagen"
                                    XComboBox {
                                        Layout.fillWidth: true
                                        compact: page.dense
                                        model: ["Automático · BiRefNet Lite", "Máxima precisión · BiRefNet", "Retrato", "Bordes difíciles"]
                                        onActivated: {
                                            imageController.setOption("rembgFamily", "BiRefNet (Next-Gen 2024)")
                                            imageController.setOption("rembgModel", currentIndex === 1 ? "General (Estándar)" : currentIndex === 2 ? "Portrait (Retratos)" : currentIndex === 3 ? "DIS (Bordes Finos/Complejo)" : "General Lite (Rápido)")
                                        }
                                    }
                                }
                                LabeledControl {
                                    Layout.preferredWidth: 120
                                    compact: page.dense
                                    label: "Salida"
                                    XComboBox { Layout.fillWidth: true; compact: page.dense; model: ["PNG", "WEBP"]; currentIndex: Math.max(0, find(viewState.format)); onActivated: imageController.setValue("format", currentText) }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; implicitHeight: page.dense ? 34 : 44; radius: 10
                                color: theme.colors.surfaceSoft; border.color: theme.colors.border
                                Text { anchors.fill: parent; anchors.margins: page.dense ? 7 : 10; text: page.dense ? "✓ Transparencia real · ✓ Bordes afinados" : "✓ Fondo transparente\n✓ Bordes afinados automáticamente"; color: theme.colors.success; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter }
                            }
                        }

                        ColumnLayout {
                            spacing: page.dense ? 6 : 8
                            Text { Layout.fillWidth: true; visible: !page.dense; text: "Aumenta resolución con modelos elegidos según el contenido; no necesitas conocer nombres técnicos."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                LabeledControl {
                                    Layout.fillWidth: true; compact: page.dense; label: "Contenido"
                                    XComboBox { Layout.fillWidth: true; compact: page.dense; model: imageController.upscaleProfiles; currentIndex: Math.max(0, find(viewState.upscaleProfile)); onActivated: imageController.setUpscaleProfile(currentText) }
                                }
                                LabeledControl {
                                    Layout.preferredWidth: 150; compact: page.dense; label: "Aumento"
                                    XComboBox { Layout.fillWidth: true; compact: page.dense; model: ["2× · recomendado", "4× · máximo detalle"]; onActivated: imageController.setOption("upscaleScale", currentIndex === 0 ? "2" : "4") }
                                }
                            }
                            LabeledControl {
                                Layout.fillWidth: true
                                compact: page.dense
                                label: "Formato final"
                                XComboBox { Layout.fillWidth: true; compact: page.dense; model: ["PNG", "JPG", "WEBP"]; currentIndex: Math.max(0, find(viewState.format)); onActivated: imageController.setValue("format", currentText) }
                            }
                        }

                        ColumnLayout {
                            spacing: page.dense ? 6 : 8
                            Text { Layout.fillWidth: true; visible: !page.dense; text: "Mejora cada fotograma, conserva el audio y entrega un MP4 listo para editores."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                LabeledControl {
                                    Layout.fillWidth: true; compact: page.dense; label: "Tipo de video"
                                    XComboBox {
                                        Layout.fillWidth: true; compact: page.dense
                                        model: ["Video real", "Animación / anime", "Rápido"]
                                        onActivated: imageController.setUpscaleProfile(currentIndex === 1 ? "Video animado" : currentIndex === 2 ? "Rápido" : "Foto real")
                                    }
                                }
                                LabeledControl {
                                    Layout.preferredWidth: 160; compact: page.dense; label: "Aumento"
                                    XComboBox { Layout.fillWidth: true; compact: page.dense; model: ["2× · recomendado", "4× · máxima resolución"]; onActivated: imageController.setOption("upscaleScale", currentIndex === 0 ? "2" : "4") }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; implicitHeight: page.dense ? 38 : 48; radius: 10
                                color: theme.colors.surfaceSoft; border.color: theme.colors.border
                                Text { anchors.fill: parent; anchors.margins: 8; text: page.dense ? "MP4 · H.264 · audio conservado" : "MP4 · H.264 · audio conservado\nEl tiempo depende de la duración y la GPU."; color: theme.colors.textMuted; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter }
                            }
                        }

                        ColumnLayout {
                            spacing: 8
                            Text { Layout.fillWidth: true; text: "Cambia formato, dimensiones o lienzo sin activar inteligencia artificial."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            LabeledControl {
                                Layout.fillWidth: true
                                label: "Formato final"
                                XComboBox { Layout.fillWidth: true; model: imageController.formats; currentIndex: Math.max(0, find(viewState.format)); onActivated: imageController.setValue("format", currentText) }
                            }
                            XSwitch { text: "Cambiar tamaño"; checked: options.resizeEnabled; onToggled: imageController.setOption("resizeEnabled", checked) }
                            RowLayout {
                                Layout.fillWidth: true
                                XTextField { Layout.fillWidth: true; placeholderText: "Ancho"; text: options.resizeWidth; onEditingFinished: imageController.setOption("resizeWidth", text) }
                                XTextField { Layout.fillWidth: true; placeholderText: "Alto"; text: options.resizeHeight; onEditingFinished: imageController.setOption("resizeHeight", text) }
                            }
                            XSwitch { text: "Mantener proporción"; checked: options.resizeMaintainAspect; onToggled: imageController.setOption("resizeMaintainAspect", checked) }
                        }
                    }

                    XButton {
                        Layout.fillWidth: true
                        text: "Opciones de resultado"
                        compact: page.dense
                        kind: "secondary"
                        onClicked: advanced.open()
                    }
                }
            }
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: page.dense ? 66 : 76
            RowLayout {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 8
                LabeledControl {
                    Layout.fillWidth: true
                    compact: page.dense
                    label: "Carpeta de salida"
                    XTextField { Layout.fillWidth: true; compact: page.dense; text: viewState.outputPath; onEditingFinished: imageController.setValue("outputPath", text) }
                }
                XButton { text: "Elegir"; compact: true; kind: "secondary"; onClicked: imageController.chooseOutputFolder() }
                XButton { text: "Abrir"; compact: true; kind: "ghost"; onClicked: imageController.openOutput() }
                XButton {
                    text: page.processLabel()
                    implicitWidth: 175
                    compact: page.dense
                    kind: viewState.busy ? "danger" : "primary"
                    enabled: viewState.busy || viewState.itemCount > 0
                    onClicked: viewState.busy ? imageController.cancel() : imageController.start()
                }
            }
        }
        ProgressStrip { Layout.fillWidth: true; compact: page.dense; value: viewState.progress; status: viewState.status; busy: viewState.busy }
    }

    Popup {
        id: advanced
        parent: Overlay.overlay
        anchors.centerIn: parent
            width: Math.min(760, Math.max(360, page.width - 32))
            height: Math.min(560, Math.max(380, page.height - 36))
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 18; color: theme.colors.surfaceRaised; border.width: 1; border.color: theme.colors.border }
        contentItem: ColumnLayout {
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: "Opciones de resultado"; color: theme.colors.text; font.pixelSize: 18; font.weight: Font.DemiBold }
                XButton { text: "Cerrar"; compact: true; kind: "ghost"; onClicked: advanced.close() }
            }
            Text { Layout.fillWidth: true; text: "La configuracion recomendada funciona sin tocar nada mas. Abre una seccion solo si buscas un resultado especifico."; color: theme.colors.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            TabBar {
                id: advancedTabs
                Layout.fillWidth: true
                background: Rectangle { radius: 10; color: theme.colors.surfaceSoft }
                Repeater {
                    model: ["Tamano", "Lienzo", "Formato", "Mejora IA", "Video"]
                    TabButton {
                        text: modelData
                        width: advancedTabs.width / 5
                        contentItem: Text { text: parent.text; color: parent.checked ? "#FFFFFF" : theme.colors.textMuted; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        background: Rectangle { radius: 8; color: parent.checked ? theme.colors.primary : "transparent" }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: advancedGuide.implicitHeight + 16
                radius: 9
                color: theme.colors.surfaceSoft
                border.width: 1
                border.color: theme.colors.border
                Text {
                    id: advancedGuide
                    anchors.fill: parent
                    anchors.margins: 8
                    color: theme.colors.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    text: [
                        "Tamano: ajusta dimensiones y que hacer si ya existe un archivo.",
                        "Lienzo: prepara proporcion, margen y fondo para una composicion.",
                        "Formato: controla transparencia, compresion y calidad de salida.",
                        "Mejora IA: amplia detalles. Empieza con 2x para un resultado estable.",
                        "Video: crea una secuencia desde imagenes. Para ampliar video usa Mejorar video."
                    ][advancedTabs.currentIndex]
                }
            }
            ScrollView {
                id: advancedScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical: XScrollBar {}
                StackLayout {
                    width: advancedScroll.availableWidth - 4
                    currentIndex: advancedTabs.currentIndex

                    ColumnLayout {
                        spacing: 10
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
                        LabeledControl { Layout.fillWidth: true; label: "Si el archivo existe"; XComboBox { Layout.fillWidth: true; model: ["Renombrar", "Sobrescribir", "Omitir"]; currentIndex: Math.max(0, find(viewState.conflictPolicy)); onActivated: imageController.setValue("conflictPolicy", currentText) } }
                    }

                    ColumnLayout {
                        spacing: 10
                        XSwitch { text: "Ajustar a un lienzo"; checked: options.canvasEnabled; onToggled: imageController.setOption("canvasEnabled", checked) }
                        LabeledControl { Layout.fillWidth: true; label: "Proporción"; XComboBox { Layout.fillWidth: true; model: ["Sin ajuste", "Cuadrado", "Vertical 9:16", "Horizontal 16:9", "Personalizado"]; currentIndex: Math.max(0, find(options.canvasOption)); onActivated: imageController.setOption("canvasOption", currentText) } }
                        RowLayout {
                            Layout.fillWidth: true
                            LabeledControl { Layout.fillWidth: true; label: "Ancho"; XTextField { Layout.fillWidth: true; text: options.canvasWidth; onEditingFinished: imageController.setOption("canvasWidth", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Alto"; XTextField { Layout.fillWidth: true; text: options.canvasHeight; onEditingFinished: imageController.setOption("canvasHeight", text) } }
                        }
                        LabeledControl { Layout.fillWidth: true; label: "Margen: " + options.canvasMargin + " px"; Slider { Layout.fillWidth: true; from: 0; to: 800; stepSize: 10; value: options.canvasMargin; onMoved: imageController.setOption("canvasMargin", value) } }
                        LabeledControl { Layout.fillWidth: true; label: "Posición"; XComboBox { Layout.fillWidth: true; model: ["Centro", "Arriba", "Abajo", "Izquierda", "Derecha"]; currentIndex: Math.max(0, find(options.canvasPosition)); onActivated: imageController.setOption("canvasPosition", currentText) } }
                        XSwitch { text: "Fondo personalizado"; checked: options.backgroundEnabled; onToggled: imageController.setOption("backgroundEnabled", checked) }
                        XComboBox { Layout.fillWidth: true; model: ["Color Sólido", "Gradiente", "Imagen"]; currentIndex: Math.max(0, find(options.backgroundType)); onActivated: imageController.setOption("backgroundType", currentText) }
                        RowLayout {
                            Layout.fillWidth: true
                            XButton { Layout.fillWidth: true; text: "Color principal"; kind: "secondary"; onClicked: imageController.setOption("backgroundColor", imageController.chooseColor(options.backgroundColor)) }
                            XButton { Layout.fillWidth: true; text: "Segundo color"; kind: "secondary"; onClicked: imageController.setOption("gradientColor2", imageController.chooseColor(options.gradientColor2)) }
                        }
                        XButton { Layout.fillWidth: true; text: "Elegir imagen de fondo"; kind: "secondary"; onClicked: imageController.chooseBackgroundImage() }
                    }

                    ColumnLayout {
                        spacing: 10
                        LabeledControl { Layout.fillWidth: true; label: "Formato de salida"; XComboBox { Layout.fillWidth: true; model: imageController.formats; currentIndex: Math.max(0, find(viewState.format)); onActivated: imageController.setValue("format", currentText) } }
                        XSwitch { text: "Conservar transparencia PNG"; checked: options.pngTransparency; onToggled: imageController.setOption("pngTransparency", checked) }
                        LabeledControl { Layout.fillWidth: true; label: "Compresión PNG: " + options.pngCompression; Slider { Layout.fillWidth: true; from: 0; to: 9; stepSize: 1; value: options.pngCompression; onMoved: imageController.setOption("pngCompression", value) } }
                        LabeledControl { Layout.fillWidth: true; label: "Calidad JPG: " + options.jpgQuality; Slider { Layout.fillWidth: true; from: 1; to: 100; stepSize: 1; value: options.jpgQuality; onMoved: imageController.setOption("jpgQuality", value) } }
                        XSwitch { text: "JPG progresivo"; checked: options.jpgProgressive; onToggled: imageController.setOption("jpgProgressive", checked) }
                        XSwitch { text: "WEBP sin pérdida"; checked: options.webpLossless; onToggled: imageController.setOption("webpLossless", checked) }
                        LabeledControl { Layout.fillWidth: true; label: "Calidad WEBP: " + options.webpQuality; Slider { Layout.fillWidth: true; from: 1; to: 100; stepSize: 1; value: options.webpQuality; onMoved: imageController.setOption("webpQuality", value) } }
                        XSwitch { text: "Combinar en un PDF"; checked: options.pdfCombine; onToggled: imageController.setOption("pdfCombine", checked) }
                        XTextField { Layout.fillWidth: true; text: options.pdfTitle; placeholderText: "Título del PDF"; onEditingFinished: imageController.setOption("pdfTitle", text) }
                    }

                    ColumnLayout {
                        spacing: 10
                        Text { text: "Quitar background"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                        XSwitch { text: "Quitar fondo"; checked: options.rembgEnabled; onToggled: imageController.setOption("rembgEnabled", checked) }
                        XSwitch { text: "Aceleración GPU"; checked: options.rembgGpu; onToggled: imageController.setOption("rembgGpu", checked) }
                        LabeledControl { Layout.fillWidth: true; label: "Familia"; XComboBox { Layout.fillWidth: true; model: imageController.rembgFamilies; currentIndex: Math.max(0, find(options.rembgFamily)); onActivated: imageController.setOption("rembgFamily", currentText) } }
                        LabeledControl { Layout.fillWidth: true; label: "Modelo"; XComboBox { Layout.fillWidth: true; model: imageController.rembgModels(options.rembgFamily); currentIndex: Math.max(0, find(options.rembgModel)); onActivated: imageController.setOption("rembgModel", currentText) } }
                        LabeledControl { Layout.fillWidth: true; label: "Suavizado de borde: " + options.rembgSmooth; Slider { Layout.fillWidth: true; from: 0; to: 20; stepSize: 1; value: options.rembgSmooth; onMoved: imageController.setOption("rembgSmooth", value) } }
                        LabeledControl { Layout.fillWidth: true; label: "Expandir máscara: " + options.rembgExpand; Slider { Layout.fillWidth: true; from: -20; to: 40; stepSize: 1; value: options.rembgExpand; onMoved: imageController.setOption("rembgExpand", value) } }
                        Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                        Text { text: "Mejora con IA"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; text: "Usala solo si quieres ampliar una imagen. La escala 2x es la opcion mas estable."; wrapMode: Text.WordWrap; color: theme.colors.textMuted; font.pixelSize: 10 }
                        XSwitch { text: "Activar mejora con IA (recomendado: 2x)"; checked: options.upscaleEnabled; onToggled: imageController.setOption("upscaleEnabled", checked) }
                        LabeledControl { Layout.fillWidth: true; label: "Perfil de mejora"; XComboBox { Layout.fillWidth: true; model: imageController.upscaleModels; currentIndex: Math.max(0, find(options.upscaleModel)); onActivated: { imageController.setOption("upscaleEngine", "Upscayl"); imageController.setOption("upscaleModel", currentText) } } }
                        LabeledControl { Layout.fillWidth: true; label: "Aumento"; XComboBox { Layout.fillWidth: true; model: ["2", "3", "4"]; currentIndex: Math.max(0, find(options.upscaleScale)); onActivated: imageController.setOption("upscaleScale", currentText) } }
                        RowLayout {
                            Layout.fillWidth: true
                            LabeledControl { Layout.fillWidth: true; label: "Nivel de limpieza"; XTextField { Layout.fillWidth: true; text: options.upscaleDenoise; onEditingFinished: imageController.setOption("upscaleDenoise", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Uso de memoria (GPU)"; XTextField { Layout.fillWidth: true; text: options.upscaleTile; onEditingFinished: imageController.setOption("upscaleTile", text) } }
                        }
                        XSwitch { text: "Priorizar detalle (tarda mas)"; checked: options.upscaleTta; onToggled: imageController.setOption("upscaleTta", checked) }
                    }

                    ColumnLayout {
                        spacing: 10
                        Text { text: "Crear video desde imágenes"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; text: "Este flujo crea una secuencia. Para reescalar un video, usa la tarea “Mejorar video” de la pantalla principal."; wrapMode: Text.WordWrap; color: theme.colors.textMuted; font.pixelSize: 10 }
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
                    }
                }
            }
        }
    }
}
