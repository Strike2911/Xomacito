import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: imageController.state
    property var options: imageController.options
    property var selected: imageController.selected
    property bool dense: height < 760
    property real comparePosition: 0.5

    function taskDescription() {
        if (viewState.task === "removeBackground") return "Crea un PNG o WEBP transparente con bordes limpios."
        if (viewState.task === "upscaleImage") return "Amplía fotografías e ilustraciones con un modelo elegido para su contenido."
        if (viewState.task === "upscaleVideo") return "Aumenta la resolución del video y conserva su pista de audio."
        return "Cambia formato, dimensiones o lienzo sin alterar innecesariamente la imagen."
    }

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
    function rembgHint() {
        if (options.rembgModel === "Personas y retratos") return "Optimizado para rostro, cabello y silueta humana."
        if (options.rembgModel === "Cabello y bordes finos") return "Conserva mechones, transparencias parciales y contornos complejos."
        if (options.rembgModel === "Objetos y productos") return "Más detalle para productos, fotografía y objetos completos."
        return "La opción más ágil para imágenes generales y lotes grandes."
    }
    function performanceHint() {
        if (options.performanceProfile === "Priorizar calidad") return "Más detalle; puede tardar más y usar más memoria."
        if (options.performanceProfile === "Priorizar velocidad") return "Menos espera y consumo para equipos modestos."
        return "Xomacito adapta CPU, GPU y memoria al archivo."
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        SectionTitle {
            Layout.fillWidth: true
            compact: page.dense
            eyebrow: "ESTUDIO"
            title: "Prepara tus imágenes"
            description: "Elige una tarea, añade tus archivos y revisa una muestra antes de procesarlos."
            number: "03"
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: page.dense ? 54 : 62
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 4
                Repeater {
                    model: [
                        { key: "removeBackground", icon: "◇", label: "Quitar fondo", hint: "Transparencia" },
                        { key: "upscaleImage", icon: "↗", label: "Mejorar imagen", hint: "Más detalle" },
                        { key: "upscaleVideo", icon: "▶", label: "Mejorar video", hint: "2× o 4×" },
                        { key: "convert", icon: "⇄", label: "Convertir", hint: "Formato y tamaño" }
                    ]
                    delegate: Button {
                        id: taskButton
                        required property var modelData
                        property bool selectedTask: viewState.task === modelData.key
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        hoverEnabled: true
                        onClicked: imageController.setTask(modelData.key)
                        contentItem: RowLayout {
                            spacing: 7
                            Text {
                                text: modelData.icon
                                color: taskButton.selectedTask ? "#FFFFFF" : theme.colors.textMuted
                                font.pixelSize: 14
                                font.weight: Font.Bold
                                Layout.leftMargin: 4
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    color: taskButton.selectedTask ? "#FFFFFF" : theme.colors.text
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    visible: !page.dense
                                    text: modelData.hint
                                    color: taskButton.selectedTask ? "#EAF1FF" : theme.colors.textMuted
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                            }
                        }
                        background: Rectangle {
                            radius: 10
                            color: parent.selectedTask ? theme.colors.primary : parent.hovered ? theme.colors.surfaceSoft : "transparent"
                            border.width: parent.activeFocus ? 2 : 0
                            border.color: theme.colors.accent
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                height: 2
                                radius: 1
                                visible: taskButton.selectedTask
                                color: theme.colors.primary
                            }
                            Behavior on color { ColorAnimation { duration: settingsController.state.animationsEnabled ? 130 : 0 } }
                        }
                    }
                }
            }
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: page.dense ? 50 : 56
            RowLayout {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 7
                XButton {
                    text: viewState.task === "upscaleVideo" ? "Añadir videos" : "Añadir archivos"
                    leadingText: "+"
                    compact: true
                    onClicked: imageController.importFiles()
                }
                XButton { text: "Carpeta"; leadingText: "▣"; compact: true; kind: "secondary"; onClicked: imageController.importFolder() }
                XButton { text: "Pegar"; compact: true; kind: "ghost"; visible: viewState.task !== "upscaleVideo"; onClicked: imageController.paste() }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: viewState.task !== "upscaleVideo"
                    radius: 10
                    color: theme.colors.surfaceSoft
                    border.width: 1
                    border.color: theme.colors.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 4
                        spacing: 6
                        Text { text: "↗"; color: theme.colors.textMuted; font.pixelSize: 12 }
                        XTextField {
                            Layout.fillWidth: true
                            compact: true
                            placeholderText: "Pega aquí el enlace de una imagen"
                            text: viewState.url
                            background: Item {}
                            onTextEdited: imageController.setValue("url", text)
                            onAccepted: imageController.analyzeUrl()
                        }
                        XButton {
                            text: "Importar enlace"
                            compact: true
                            kind: "secondary"
                            enabled: !viewState.busy && viewState.url.length > 0
                            onClicked: imageController.analyzeUrl()
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: viewState.task === "upscaleVideo"
                    text: "MP4, MOV, MKV, WEBM o AVI"
                    color: theme.colors.textMuted
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            XCard {
                id: filesCard
                Layout.fillHeight: true
                Layout.minimumWidth: 190
                Layout.preferredWidth: Math.min(250, page.width * 0.18)
                Layout.maximumWidth: 260
                Layout.minimumHeight: page.dense ? 270 : 310
                clip: true
                cardColor: fileDropArea.containsDrag ? theme.colors.surfaceRaised : theme.colors.surface
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "ARCHIVOS"; color: theme.colors.text; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                        Rectangle {
                            implicitWidth: Math.max(22, fileCount.implicitWidth + 12)
                            implicitHeight: 22
                            radius: 11
                            color: theme.colors.primarySoft
                            Text { id: fileCount; anchors.centerIn: parent; text: viewState.itemCount; color: theme.colors.primary; font.pixelSize: 9; font.weight: Font.Bold }
                        }
                        Item { Layout.fillWidth: true }
                        XButton { text: "Vaciar"; compact: true; kind: "ghost"; visible: viewState.itemCount > 0; onClicked: imageController.clear() }
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
                        Column {
                            anchors.centerIn: parent
                            visible: resources.count === 0
                            width: Math.max(130, resources.width - 26)
                            spacing: 7
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 44; height: 44; radius: 22
                                color: "transparent"
                                border.width: 1
                                border.color: theme.colors.primary
                                Text { anchors.centerIn: parent; text: "+"; color: theme.colors.primary; font.pixelSize: 23; font.weight: Font.Light }
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: viewState.task === "upscaleVideo" ? "Añade tus videos" : "Añade tus archivos"
                                color: theme.colors.text
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                            }
                            Text {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: "También puedes arrastrarlos aquí"
                                color: theme.colors.textMuted
                                font.pixelSize: 9
                                wrapMode: Text.WordWrap
                            }
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
                Layout.minimumWidth: 360
                Layout.minimumHeight: page.dense ? 270 : 310
                clip: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            Text { text: "Vista previa"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                            Text { Layout.fillWidth: true; text: selected.name || "Selecciona un archivo para comenzar"; color: theme.colors.textMuted; font.pixelSize: 9; elide: Text.ElideMiddle }
                        }
                        XButton { compact: true; text: "Quitar"; kind: "ghost"; enabled: viewState.selectedIndex >= 0; onClicked: imageController.removeSelected() }
                    }
                    Rectangle {
                        id: previewSurface
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 14
                        color: theme.colors.backgroundAlt
                        border.color: theme.colors.border
                        border.width: 1
                        clip: true
                        Image {
                            id: originalPreview
                            anchors.fill: parent
                            anchors.margins: 8
                            source: viewState.previewSource
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            smooth: true
                        }
                        Item {
                            anchors.fill: parent
                            anchors.margins: 8
                            visible: !!viewState.resultPreviewSource
                            Item {
                                width: Math.max(0, page.comparePosition * parent.width)
                                height: parent.height
                                clip: true
                                Image {
                                    width: parent.parent.width
                                    height: parent.height
                                    source: viewState.resultPreviewSource
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    smooth: true
                                }
                            }
                            Rectangle {
                                x: Math.max(0, Math.min(parent.width - 2, page.comparePosition * parent.width - 1))
                                width: 2; height: parent.height
                                color: theme.colors.accent
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 26; height: 34; radius: 9
                                    color: theme.colors.primary
                                    border.color: theme.colors.text
                                    border.width: 1
                                    Text { anchors.centerIn: parent; text: "↔"; color: "#FFFFFF"; font.pixelSize: 12; font.weight: Font.Bold }
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.SizeHorCursor
                                preventStealing: true
                                function updateCompare(mouseX) { page.comparePosition = Math.max(0, Math.min(1, mouseX / Math.max(1, width))) }
                                onPressed: function(mouse) { updateCompare(mouse.x) }
                                onPositionChanged: function(mouse) { if (pressed) updateCompare(mouse.x) }
                            }
                        }
                        Rectangle {
                            anchors.left: parent.left; anchors.top: parent.top
                            anchors.margins: 14
                            visible: !!viewState.resultPreviewSource && page.comparePosition > 0.05
                            implicitWidth: resultLabel.implicitWidth + 16; implicitHeight: resultLabel.implicitHeight + 8
                            radius: 8; color: theme.colors.primary; opacity: 0.94
                            Text { id: resultLabel; anchors.centerIn: parent; text: "RESULTADO"; color: "#FFFFFF"; font.pixelSize: 9; font.weight: Font.Bold }
                        }
                        Rectangle {
                            anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 14
                            visible: !!viewState.resultPreviewSource && page.comparePosition < 0.95
                            implicitWidth: originalLabel.implicitWidth + 16; implicitHeight: originalLabel.implicitHeight + 8
                            radius: 8; color: theme.colors.surfaceRaised; opacity: 0.94
                            Text { id: originalLabel; anchors.centerIn: parent; text: "ORIGINAL"; color: theme.colors.text; font.pixelSize: 9; font.weight: Font.Bold }
                        }
                        Column {
                            anchors.centerIn: parent
                            visible: !viewState.previewSource && !viewState.resultPreviewSource
                            spacing: 8
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 50; height: 50; radius: 25
                                color: theme.colors.surfaceSoft
                                border.width: 1
                                border.color: theme.colors.border
                                Text { anchors.centerIn: parent; text: "▧"; color: theme.colors.primary; font.pixelSize: 22 }
                            }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Aquí verás el resultado"; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Selecciona un archivo de la lista"; color: theme.colors.textMuted; font.pixelSize: 9 }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        visible: viewState.selectedIndex >= 0
                        spacing: 7
                        XButton {
                            Layout.fillWidth: true
                            text: viewState.previewBusy ? "Preparando muestra…" : viewState.resultPreviewSource ? "Actualizar vista previa" : "Preparar vista previa"
                            kind: "secondary"
                            compact: true
                            enabled: !viewState.busy
                            onClicked: imageController.preparePreview()
                        }
                        XButton { visible: !!viewState.resultPreviewSource; compact: true; text: "Original"; kind: "ghost"; onClicked: page.comparePosition = 0 }
                        XButton { visible: !!viewState.resultPreviewSource; compact: true; text: "50 / 50"; kind: "ghost"; onClicked: page.comparePosition = 0.5 }
                        XButton { visible: !!viewState.resultPreviewSource; compact: true; text: "Resultado"; kind: "ghost"; onClicked: page.comparePosition = 1 }
                    }
                }
            }

            XCard {
                Layout.fillHeight: true
                Layout.minimumWidth: 310
                Layout.preferredWidth: Math.min(420, page.width * 0.31)
                Layout.maximumWidth: 430
                Layout.minimumHeight: page.dense ? 270 : 310
                clip: true
                cardColor: theme.colors.surfaceRaised
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: page.dense ? 11 : 14
                    spacing: page.dense ? 6 : 9
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            Text { text: "AJUSTES"; color: theme.colors.primary; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }
                            Text { Layout.fillWidth: true; text: page.taskTitle(); color: theme.colors.text; font.pixelSize: page.dense ? 17 : 19; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        }
                        Rectangle {
                            implicitWidth: 132
                            implicitHeight: 32
                            radius: 9
                            color: theme.colors.surfaceSoft
                            border.width: 1
                            border.color: theme.colors.border
                            Column {
                                anchors.centerIn: parent
                                width: parent.width - 14
                                spacing: 0
                                Text { width: parent.width; text: "MOTOR LOCAL"; color: theme.colors.primary; font.pixelSize: 7; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                                Text { width: parent.width; text: viewState.hardwareLabel; color: theme.colors.textMuted; font.pixelSize: 8; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: !page.dense
                        text: page.taskDescription()
                        color: theme.colors.textMuted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 0
                        Layout.preferredHeight: 1
                        clip: true
                        currentIndex: viewState.task === "removeBackground" ? 0 : viewState.task === "upscaleImage" ? 1 : viewState.task === "upscaleVideo" ? 2 : 3

                        ColumnLayout {
                            spacing: page.dense ? 6 : 8
                            Text { Layout.fillWidth: true; visible: !page.dense; text: "Xomacito analiza el contenido y elige el recorte adecuado. Puedes cambiar el enfoque si buscas un borde concreto."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                LabeledControl {
                                    Layout.fillWidth: true
                                    compact: page.dense
                                    label: "Enfoque del recorte"
                                    XComboBox {
                                        Layout.fillWidth: true
                                        compact: page.dense
                                        model: imageController.rembgModels(options.rembgFamily)
                                        currentIndex: Math.max(0, find(options.rembgModel))
                                        onActivated: imageController.setOption("rembgModel", currentText)
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
                                Layout.fillWidth: true; implicitHeight: page.dense ? 34 : 46; radius: 10
                                color: theme.colors.surfaceSoft; border.color: theme.colors.primary
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: page.dense ? 7 : 10; spacing: 7
                                    Text { text: "✦"; color: theme.colors.primary; font.pixelSize: 13; font.weight: Font.Bold }
                                    Text { Layout.fillWidth: true; text: page.rembgHint(); color: theme.colors.text; font.pixelSize: 9; wrapMode: Text.WordWrap; verticalAlignment: Text.AlignVCenter }
                                }
                            }
                        }

                        ColumnLayout {
                            spacing: page.dense ? 6 : 8
                            Text { Layout.fillWidth: true; visible: !page.dense; text: "Xomacito analiza el archivo y elige un modelo local para foto, compresión o ilustración."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
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
                            Text { Layout.fillWidth: true; text: viewState.outputEstimate; color: theme.colors.primary; font.pixelSize: 9; elide: Text.ElideRight }
                        }

                        ColumnLayout {
                            spacing: page.dense ? 6 : 8
                            Text { Layout.fillWidth: true; visible: !page.dense; text: "Mejora cada fotograma con la GPU, conserva el audio y entrega un MP4 listo para editores."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                LabeledControl {
                                    Layout.fillWidth: true; compact: page.dense; label: "Tipo de video"
                                    XComboBox {
                                        Layout.fillWidth: true; compact: page.dense
                                        model: ["Video real", "Animación / anime"]
                                        onActivated: imageController.setUpscaleProfile(currentIndex === 1 ? "Video animado" : "Foto real")
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
                                Text { anchors.fill: parent; anchors.margins: 8; text: page.dense ? "MP4 · audio conservado" : "MP4 · audio conservado\nModo por fotogramas: rápido, pero no inventa movimiento entre cuadros."; color: theme.colors.textMuted; font.pixelSize: 9; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap }
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

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: page.dense ? 28 : 50
                        radius: 10
                        color: theme.colors.primarySoft
                        visible: viewState.analysisReady
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: page.dense ? 6 : 8
                            spacing: 7
                            Text { text: "✦"; color: theme.colors.primary; font.pixelSize: page.dense ? 12 : 15; font.weight: Font.Bold }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Text { Layout.fillWidth: true; text: page.dense ? viewState.recommendation : viewState.analysisTitle; color: theme.colors.text; font.pixelSize: page.dense ? 8 : 9; font.weight: Font.DemiBold; elide: Text.ElideRight }
                                Text { Layout.fillWidth: true; visible: !page.dense; text: viewState.recommendation; color: theme.colors.textMuted; font.pixelSize: 8; elide: Text.ElideRight }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: !viewState.analysisReady
                        text: "✦ Añade un archivo y elegiré el ajuste recomendado."
                        color: theme.colors.textMuted
                        font.pixelSize: 8
                        elide: Text.ElideRight
                    }
                    XTextField {
                        Layout.fillWidth: true
                        compact: true
                        visible: viewState.selectedIndex >= 0
                        placeholderText: "Nombre del resultado (opcional)"
                        text: selected.title || ""
                        onEditingFinished: imageController.setSelectedTitle(text)
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: page.dense ? 60 : 74
                        radius: 11
                        color: theme.colors.surfaceSoft
                        border.width: 1
                        border.color: theme.colors.border
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 8
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text { text: "Procesamiento"; color: theme.colors.text; font.pixelSize: 10; font.weight: Font.DemiBold }
                                Text { Layout.fillWidth: true; visible: !page.dense; text: page.performanceHint(); color: theme.colors.textMuted; font.pixelSize: 8; elide: Text.ElideRight }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Repeater {
                                        model: imageController.performanceProfiles
                                        delegate: Button {
                                            id: performanceButton
                                            required property string modelData
                                            property bool selectedProfile: options.performanceProfile === modelData
                                            Layout.fillWidth: true
                                            implicitHeight: 27
                                            text: modelData === "Automático" ? "Auto" : modelData === "Priorizar calidad" ? "Calidad" : "Velocidad"
                                            hoverEnabled: true
                                            onClicked: imageController.setPerformanceProfile(modelData)
                                            contentItem: Text { text: parent.text; color: performanceButton.selectedProfile ? "#FFFFFF" : theme.colors.textMuted; font.pixelSize: 8; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle {
                                                radius: 7
                                                color: performanceButton.selectedProfile ? theme.colors.primary : performanceButton.hovered ? theme.colors.surfaceRaised : "transparent"
                                                border.width: 1
                                                border.color: performanceButton.selectedProfile ? theme.colors.primary : theme.colors.border
                                            }
                                        }
                                    }
                                }
                            }
                            XButton {
                                text: "Ajustes de salida"
                                compact: true
                                kind: "secondary"
                                Layout.alignment: Qt.AlignVCenter
                                onClicked: advanced.open()
                            }
                        }
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
        width: Math.min(860, Math.max(420, page.width - 32))
        height: Math.min(620, Math.max(440, page.height - 30))
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 18; color: theme.colors.surfaceRaised; border.width: 1; border.color: theme.colors.border }
        contentItem: ColumnLayout {
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    width: 42; height: 42; radius: 12
                    color: theme.colors.surfaceSoft
                    border.width: 1; border.color: theme.colors.primary
                    Text { anchors.centerIn: parent; text: "⚙"; color: theme.colors.primary; font.pixelSize: 18 }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1
                    Text { text: "Configura la salida"; color: theme.colors.text; font.pixelSize: 19; font.weight: Font.DemiBold }
                    Text { Layout.fillWidth: true; text: "Los ajustes recomendados ya están activos. Cambia sólo lo que necesites."; color: theme.colors.textMuted; font.pixelSize: 10; elide: Text.ElideRight }
                }
                XButton { text: "Cerrar"; compact: true; kind: "ghost"; onClicked: advanced.close() }
            }
            TabBar {
                id: advancedTabs
                Layout.fillWidth: true
                implicitHeight: 54
                spacing: 6
                background: Item {}
                Repeater {
                    model: [
                        { icon: "↔", label: "Tamaño" },
                        { icon: "▣", label: "Lienzo" },
                        { icon: "◇", label: "Formato" },
                        { icon: "✦", label: "Mejora IA" },
                        { icon: "▶", label: "Video" }
                    ]
                    TabButton {
                        id: advancedTab
                        width: (advancedTabs.width - 24) / 5
                        hoverEnabled: true
                        contentItem: RowLayout {
                            spacing: 6
                            Text { text: modelData.icon; color: advancedTab.checked ? "#FFFFFF" : theme.colors.primary; font.pixelSize: 12; font.weight: Font.Bold }
                            Text { Layout.fillWidth: true; text: modelData.label; color: advancedTab.checked ? "#FFFFFF" : theme.colors.text; font.pixelSize: 10; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        }
                        background: Rectangle {
                            radius: 10
                            color: advancedTab.checked ? theme.colors.primary : advancedTab.hovered ? theme.colors.surfaceSoft : theme.colors.surface
                            border.width: 1
                            border.color: advancedTab.checked ? theme.colors.primary : theme.colors.border
                        }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: advancedGuide.implicitHeight + 16
                radius: 9
                color: theme.colors.surfaceSoft
                border.width: 1
                border.color: theme.colors.primary
                Text {
                    id: advancedGuide
                    anchors.fill: parent
                    anchors.margins: 8
                    color: theme.colors.text
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    text: [
                        "Tamaño · Define dimensiones y decide qué hacer si ya existe un archivo.",
                        "Lienzo · Prepara proporción, margen y fondo para una composición.",
                        "Formato · Controla transparencia, compresión y calidad de salida.",
                        "Mejora IA · Amplía detalles. Empieza con 2× para un resultado estable.",
                        "Video · Crea una secuencia desde imágenes. Para ampliar video usa Mejorar video."
                    ][advancedTabs.currentIndex]
                }
            }
            ScrollView {
                id: advancedScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                leftPadding: 14
                rightPadding: 14
                topPadding: 12
                bottomPadding: 12
                background: Rectangle {
                    radius: 12
                    color: theme.colors.surface
                    border.width: 1
                    border.color: theme.colors.border
                }
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
                        Text { text: "Quitar fondo"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                        XSwitch { text: "Quitar fondo"; checked: options.rembgEnabled; onToggled: imageController.setOption("rembgEnabled", checked) }
                        XSwitch { text: "Preferir GPU (si está disponible)"; checked: options.rembgGpu; onToggled: imageController.setOption("rembgGpu", checked) }
                        LabeledControl { Layout.fillWidth: true; label: "Enfoque de recorte"; XComboBox { Layout.fillWidth: true; model: imageController.rembgModels(options.rembgFamily); currentIndex: Math.max(0, find(options.rembgModel)); onActivated: imageController.setOption("rembgModel", currentText) } }
                        LabeledControl { Layout.fillWidth: true; label: "Suavizado de borde: " + options.rembgSmooth; Slider { Layout.fillWidth: true; from: 0; to: 20; stepSize: 1; value: options.rembgSmooth; onMoved: imageController.setOption("rembgSmooth", value) } }
                        LabeledControl { Layout.fillWidth: true; label: "Expandir máscara: " + options.rembgExpand; Slider { Layout.fillWidth: true; from: -20; to: 40; stepSize: 1; value: options.rembgExpand; onMoved: imageController.setOption("rembgExpand", value) } }
                        Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                        Text { text: "Mejora con IA"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; text: "Úsala sólo si quieres ampliar una imagen. La escala 2× es la opción más estable."; wrapMode: Text.WordWrap; color: theme.colors.textMuted; font.pixelSize: 10 }
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
