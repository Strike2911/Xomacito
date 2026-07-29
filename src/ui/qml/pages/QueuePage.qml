import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: batchController.state
    property var selected: batchController.selected
    property bool advancedOpen: false

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        SectionTitle {
            Layout.fillWidth: true
            eyebrow: "COLA DE TRABAJO"
            title: "Tu contenido, antes de descargar."
            description: "Revisa cada canción o video, elige su destino y procesa todo sin perder el control."
            number: "02"
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: queueInput.implicitHeight + 28
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                id: queueInput
                anchors.fill: parent
                anchors.margins: 14
                spacing: 9
                XTextField {
                    Layout.fillWidth: true
                    placeholderText: "Pega un enlace, una playlist o importa archivos"
                    text: viewState.url
                    onTextEdited: batchController.setValue("url", text)
                    onAccepted: batchController.analyze()
                }
                XButton {
                    text: viewState.analyzing ? "Analizando…" : "Añadir"
                    enabled: !viewState.analyzing && viewState.url.length > 3
                    onClicked: batchController.analyze()
                }
                XButton { text: "Archivos"; kind: "secondary"; onClicked: batchController.importLocalFiles() }
                XButton { text: "Carpeta"; kind: "secondary"; onClicked: batchController.importFolder() }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: page.width >= 980 ? 5 : 1
            columnSpacing: 12
            rowSpacing: 12

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.width >= 980 ? 2 : 1
                Layout.minimumHeight: 350
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "TRABAJOS"
                            color: theme.colors.primary
                            font.pixelSize: 11
                            font.weight: Font.Bold
                            font.letterSpacing: 1
                        }
                        Item { Layout.fillWidth: true }
                        XButton { compact: true; text: "Limpiar"; kind: "ghost"; onClicked: batchController.clearFinished() }
                        XButton { compact: true; text: "Reintentar"; kind: "ghost"; onClicked: batchController.resetStatuses() }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 13
                        color: theme.colors.backgroundAlt
                        border.color: theme.colors.border
                        border.width: 1
                        ListView {
                            id: jobs
                            anchors.fill: parent
                            anchors.margins: 7
                            clip: true
                            spacing: 7
                            model: batchController.model
                            ScrollBar.vertical: XScrollBar {}
                            delegate: Rectangle {
                                required property string jobId
                                required property string title
                                required property string status
                                required property string detail
                                required property real progress
                                required property string jobType
                                required property int itemCount
                                required property string destinationTag
                                width: jobs.width
                                height: 78
                                radius: 11
                                color: viewState.selectedJobId === jobId ? theme.colors.surfaceRaised : theme.colors.surface
                                border.width: viewState.selectedJobId === jobId ? 2 : 1
                                border.color: viewState.selectedJobId === jobId ? theme.colors.primary : theme.colors.border
                                MouseArea { anchors.fill: parent; onClicked: batchController.selectJob(jobId) }
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 10
                                    Rectangle {
                                        width: 40
                                        height: 40
                                        radius: 10
                                        color: status === "COMPLETED" ? theme.colors.success
                                            : status === "FAILED" ? theme.colors.error : theme.colors.surfaceSoft
                                        Text {
                                            anchors.centerIn: parent
                                            text: jobType === "PLAYLIST" ? "≡" : status === "COMPLETED" ? "✓" : "↓"
                                            color: "white"
                                            font.pixelSize: 18
                                            font.weight: Font.Bold
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Text {
                                            Layout.fillWidth: true
                                            text: title
                                            color: theme.colors.text
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: jobType === "PLAYLIST"
                                                ? itemCount + " elementos · " + destinationTag
                                                : detail + (destinationTag !== "Sin etiqueta" ? " · " + destinationTag : "")
                                            color: theme.colors.textMuted
                                            font.pixelSize: 10
                                            elide: Text.ElideRight
                                        }
                                        ProgressBar {
                                            Layout.fillWidth: true
                                            value: progress
                                            background: Rectangle { implicitHeight: 3; radius: 2; color: theme.colors.surfaceSoft }
                                            contentItem: Rectangle {
                                                implicitHeight: 3
                                                width: parent.width * progress
                                                radius: 2
                                                color: theme.colors.primary
                                            }
                                        }
                                    }
                                    Text {
                                        text: status
                                        color: status === "COMPLETED" ? theme.colors.success
                                            : status === "FAILED" ? theme.colors.error : theme.colors.textMuted
                                        font.pixelSize: 9
                                        font.weight: Font.Bold
                                    }
                                    XButton {
                                        compact: true
                                        text: "×"
                                        kind: "ghost"
                                        implicitWidth: 38
                                        onClicked: batchController.removeJob(jobId)
                                    }
                                }
                            }
                            Text {
                                anchors.centerIn: parent
                                visible: jobs.count === 0
                                text: "Tu cola está vacía\nAñade un enlace o importa archivos"
                                color: theme.colors.textMuted
                                horizontalAlignment: Text.AlignHCenter
                                lineHeight: 1.4
                            }
                        }
                    }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.width >= 980 ? 3 : 1
                Layout.minimumHeight: 350
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    SectionTitle {
                        Layout.fillWidth: true
                        eyebrow: selected.jobId ? "TRABAJO SELECCIONADO" : "AJUSTES PARA NUEVOS TRABAJOS"
                        title: selected.title || "Elige cómo preparar la cola"
                        description: selected.jobType === "PLAYLIST"
                            ? "Revisa su contenido y desmarca lo que no quieras descargar."
                            : selected.detail || "Modo, calidad y análisis. Lo demás queda en Opciones avanzadas."
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        LabeledControl {
                            Layout.fillWidth: true
                            label: "Formato"
                            XComboBox {
                                Layout.fillWidth: true
                                model: ["Video+Audio", "Solo Audio"]
                                currentIndex: Math.max(0, find(selected.mode || viewState.globalMode))
                                onActivated: selected.jobId
                                    ? batchController.setSelectedOption("mode", currentText)
                                    : batchController.setValue("globalMode", currentText)
                            }
                        }
                        LabeledControl {
                            Layout.fillWidth: true
                            label: "Calidad"
                            XComboBox {
                                Layout.fillWidth: true
                                model: ["Mejor Calidad (Auto)", "1080p", "720p", "480p", "Solo Audio (Mejor)"]
                                currentIndex: Math.max(0, find(selected.quality || viewState.globalQuality))
                                onActivated: selected.jobId
                                    ? batchController.setSelectedOption("quality", currentText)
                                    : batchController.setValue("globalQuality", currentText)
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: selected.jobType === "PLAYLIST"
                        spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "CONTENIDO DE LA PLAYLIST"
                                color: theme.colors.primary
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                font.letterSpacing: 1
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: selected.itemCount + " de " + batchController.selectedPlaylistEntries.length
                                color: theme.colors.textMuted
                                font.pixelSize: 10
                            }
                            XButton {
                                compact: true
                                text: "Todos"
                                kind: "ghost"
                                onClicked: batchController.selectAllPlaylistEntries(true)
                            }
                            XButton {
                                compact: true
                                text: "Ninguno"
                                kind: "ghost"
                                onClicked: batchController.selectAllPlaylistEntries(false)
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 145
                            radius: 12
                            color: theme.colors.backgroundAlt
                            border.color: theme.colors.border
                            border.width: 1
                            ListView {
                                id: playlistPreview
                                anchors.fill: parent
                                anchors.margins: 6
                                clip: true
                                spacing: 3
                                model: batchController.selectedPlaylistEntries
                                ScrollBar.vertical: XScrollBar {}
                                delegate: Rectangle {
                                    required property var modelData
                                    width: playlistPreview.width
                                    height: 40
                                    radius: 8
                                    color: modelData.selected ? theme.colors.surfaceRaised : "transparent"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        spacing: 8
                                        XSwitch {
                                            checked: modelData.selected
                                            onToggled: batchController.setPlaylistEntrySelected(modelData.index, checked)
                                        }
                                        Text {
                                            text: (modelData.index + 1) + "."
                                            color: theme.colors.textDim
                                            font.pixelSize: 10
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.title
                                            color: modelData.selected ? theme.colors.text : theme.colors.textMuted
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: !selected.jobId
                        XSwitch {
                            text: "Detectar playlists"
                            checked: viewState.playlistAnalysis
                            onToggled: batchController.setValue("playlistAnalysis", checked)
                        }
                        XSwitch {
                            text: "Análisis rápido"
                            checked: viewState.fastMode
                            enabled: viewState.playlistAnalysis
                            onToggled: batchController.setValue("fastMode", checked)
                        }
                        Item { Layout.fillWidth: true }
                    }

                    XButton {
                        Layout.fillWidth: true
                        text: page.advancedOpen ? "Ocultar opciones avanzadas" : "Opciones avanzadas"
                        kind: "secondary"
                        onClicked: page.advancedOpen = !page.advancedOpen
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: page.advancedOpen
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical: XScrollBar {}
                        ColumnLayout {
                            width: parent.width
                            spacing: 8
                            XSwitch {
                                visible: !selected.jobId
                                text: "Descargar automáticamente al añadir"
                                checked: viewState.autoDownload
                                onToggled: batchController.setValue("autoDownload", checked)
                            }
                            XSwitch {
                                visible: !selected.jobId
                                text: "Enviar imágenes al Estudio"
                                checked: viewState.autoSendImages
                                onToggled: batchController.setValue("autoSendImages", checked)
                            }
                            XSwitch {
                                text: "Recodificar resultados"
                                checked: selected.jobId ? !!selected.recode : viewState.globalRecode
                                onToggled: selected.jobId
                                    ? batchController.setSelectedOption("recode", checked)
                                    : batchController.setValue("globalRecode", checked)
                            }
                            LabeledControl {
                                Layout.fillWidth: true
                                label: "Preset de conversión"
                                XComboBox {
                                    Layout.fillWidth: true
                                    model: presetStore.videoPresets
                                    currentIndex: Math.max(0, find(selected.preset || viewState.globalPreset))
                                    onActivated: selected.jobId
                                        ? batchController.setSelectedOption("preset", currentText)
                                        : batchController.setValue("globalPreset", currentText)
                                }
                            }
                            XSwitch {
                                text: "Mantener archivos originales"
                                checked: selected.jobId ? !!selected.keepOriginal : viewState.globalKeepOriginal
                                onToggled: selected.jobId
                                    ? batchController.setSelectedOption("keepOriginal", checked)
                                    : batchController.setValue("globalKeepOriginal", checked)
                            }
                            XSwitch {
                                text: "Conservar todas las pistas de audio"
                                checked: viewState.allAudioTracks
                                onToggled: batchController.setValue("allAudioTracks", checked)
                            }
                            LabeledControl {
                                Layout.fillWidth: true
                                label: "Si el archivo ya existe"
                                XComboBox {
                                    Layout.fillWidth: true
                                    model: ["Renombrar", "Sobrescribir", "Omitir", "Preguntar"]
                                    currentIndex: Math.max(0, find(viewState.conflictPolicy))
                                    onActivated: batchController.setValue("conflictPolicy", currentText)
                                }
                            }
                            XSwitch {
                                text: "Crear una subcarpeta para este lote"
                                checked: viewState.createSubfolder
                                onToggled: batchController.setValue("createSubfolder", checked)
                            }
                            XTextField {
                                Layout.fillWidth: true
                                visible: viewState.createSubfolder
                                text: viewState.subfolderName
                                placeholderText: "Nombre de la subcarpeta"
                                onEditingFinished: batchController.setValue("subfolderName", text)
                            }
                        }
                    }
                    Item { Layout.fillHeight: !page.advancedOpen && selected.jobType !== "PLAYLIST" }
                }
            }
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: destinationRow.implicitHeight + 24
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                id: destinationRow
                anchors.fill: parent
                anchors.margins: 12
                spacing: 9
                LabeledControl {
                    Layout.fillWidth: true
                    label: "Carpeta de salida"
                    hint: viewState.selectedTag === "Sin etiqueta"
                        ? "Destino general de la cola."
                        : "Esta carpeta pertenece a la etiqueta seleccionada."
                    XTextField {
                        Layout.fillWidth: true
                        compact: true
                        readOnly: viewState.selectedTag !== "Sin etiqueta"
                        text: viewState.effectiveOutputPath
                        onEditingFinished: {
                            if (!readOnly)
                                batchController.setValue("outputPath", text)
                        }
                    }
                }
                XButton { text: "Elegir carpeta"; compact: true; kind: "secondary"; onClicked: batchController.chooseOutputFolder() }
                LabeledControl {
                    Layout.preferredWidth: 245
                    label: "Etiqueta de destino"
                    hint: "Color y carpeta se recuerdan."
                    Rectangle { width: 10; height: 10; radius: 5; color: viewState.selectedTagColor }
                    XComboBox {
                        Layout.fillWidth: true
                        compact: true
                        model: batchController.downloadTags
                        currentIndex: Math.max(0, find(viewState.selectedTag))
                        onActivated: batchController.setValue("selectedTag", currentText)
                    }
                }
                XButton { text: "+"; compact: true; kind: "secondary"; implicitWidth: 44; onClicked: batchController.createDownloadTag() }
                XButton {
                    text: "−"
                    compact: true
                    kind: "ghost"
                    implicitWidth: 44
                    enabled: viewState.selectedTag !== "Sin etiqueta"
                    onClicked: batchController.deleteSelectedTag()
                }
                XButton { text: "Abrir"; compact: true; kind: "ghost"; onClicked: batchController.openOutput() }
                XButton {
                    text: viewState.running ? "Pausar cola" : "Iniciar cola"
                    kind: viewState.running ? "danger" : "primary"
                    onClicked: batchController.toggleQueue()
                }
            }
        }

        ProgressStrip {
            Layout.fillWidth: true
            value: viewState.progress
            status: viewState.status
            busy: viewState.running || viewState.analyzing
        }
    }
}
