import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: batchController.state
    property var selected: batchController.selected

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        SectionTitle {
            Layout.fillWidth: true
            eyebrow: "COLA DE TRABAJO"
            title: "Muchos archivos. Un solo flujo."
            description: "Analiza enlaces, playlists y carpetas mientras la interfaz sigue respondiendo."
            number: "02"
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: queueInput.implicitHeight + 30
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                id: queueInput
                anchors.fill: parent; anchors.margins: 15; spacing: 9
                XTextField { Layout.fillWidth: true; placeholderText: "Añade un enlace o una playlist"; text: viewState.url; onTextEdited: batchController.setValue("url", text); onAccepted: batchController.analyze() }
                XButton { text: "Añadir enlace"; enabled: !viewState.analyzing && viewState.url.length > 3; onClicked: batchController.analyze() }
                XButton { text: "Archivos"; kind: "secondary"; onClicked: batchController.importLocalFiles() }
                XButton { text: "Carpeta"; kind: "secondary"; onClicked: batchController.importFolder() }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: page.width >= 980 ? 3 : 1
            columnSpacing: 14
            rowSpacing: 14

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.width >= 980 ? 2 : 1
                Layout.minimumHeight: 360
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "TRABAJOS"; color: theme.colors.primary; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Item { Layout.fillWidth: true }
                        XButton { compact: true; text: "Limpiar terminados"; kind: "ghost"; onClicked: batchController.clearFinished() }
                        XButton { compact: true; text: "Reintentar fallos"; kind: "ghost"; onClicked: batchController.resetStatuses() }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        radius: 13; color: theme.colors.backgroundAlt; border.color: theme.colors.border; border.width: 1
                        ListView {
                            id: jobs
                            anchors.fill: parent; anchors.margins: 7; clip: true; spacing: 7
                            model: batchController.model
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property string jobId
                                required property string title
                                required property string status
                                required property string detail
                                required property real progress
                                required property string jobType
                                width: jobs.width
                                height: 72
                                radius: 11
                                color: viewState.selectedJobId === jobId ? theme.colors.surfaceRaised : theme.colors.surface
                                border.width: viewState.selectedJobId === jobId ? 2 : 1
                                border.color: viewState.selectedJobId === jobId ? theme.colors.primary : theme.colors.border
                                MouseArea { anchors.fill: parent; onClicked: batchController.selectJob(jobId) }
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 11; spacing: 10
                                    Rectangle {
                                        width: 38; height: 38; radius: 10
                                        color: status === "COMPLETED" ? theme.colors.success : status === "FAILED" ? theme.colors.error : theme.colors.surfaceSoft
                                        Text { anchors.centerIn: parent; text: jobType === "PLAYLIST" ? "≡" : status === "COMPLETED" ? "✓" : "↓"; color: "white"; font.pixelSize: 17; font.weight: Font.Bold }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 4
                                        Text { Layout.fillWidth: true; text: title; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
                                        Text { Layout.fillWidth: true; text: detail; color: theme.colors.textMuted; font.pixelSize: 10; elide: Text.ElideRight }
                                        ProgressBar {
                                            Layout.fillWidth: true; value: progress
                                            background: Rectangle { implicitHeight: 3; radius: 2; color: theme.colors.surfaceSoft }
                                            contentItem: Rectangle { implicitHeight: 3; width: parent.width * progress; radius: 2; color: theme.colors.primary }
                                        }
                                    }
                                    Text { text: status; color: status === "COMPLETED" ? theme.colors.success : status === "FAILED" ? theme.colors.error : theme.colors.textMuted; font.pixelSize: 10; font.weight: Font.Bold }
                                    XButton { compact: true; text: "×"; kind: "ghost"; implicitWidth: 38; onClicked: batchController.removeJob(jobId) }
                                }
                            }
                            Text { anchors.centerIn: parent; visible: jobs.count === 0; text: "Tu cola está vacía\nAñade enlaces o archivos para comenzar"; color: theme.colors.textMuted; horizontalAlignment: Text.AlignHCenter; lineHeight: 1.4 }
                        }
                    }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 360
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 11
                    SectionTitle { Layout.fillWidth: true; eyebrow: selected.jobId ? "TRABAJO SELECCIONADO" : "AJUSTES GLOBALES"; title: selected.title || "Configura la cola"; description: selected.detail || "Los nuevos elementos heredarán estas opciones." }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical: XScrollBar {}
                        ColumnLayout {
                            width: parent.width
                            spacing: 10
                            LabeledControl {
                                Layout.fillWidth: true; label: "Modo"
                                XComboBox { Layout.fillWidth: true; model: ["Video+Audio", "Solo Audio"]; currentIndex: Math.max(0, find(selected.mode || viewState.globalMode)); onActivated: selected.jobId ? batchController.setSelectedOption("mode", currentText) : batchController.setValue("globalMode", currentText) }
                            }
                            LabeledControl {
                                Layout.fillWidth: true; label: "Calidad"
                                XComboBox { Layout.fillWidth: true; model: ["Mejor Calidad (Auto)", "1080p", "720p", "480p", "Solo Audio (Mejor)"]; currentIndex: Math.max(0, find(viewState.globalQuality)); onActivated: batchController.setValue("globalQuality", currentText) }
                            }
                            XSwitch { text: "Analizar playlists"; checked: viewState.playlistAnalysis; onToggled: batchController.setValue("playlistAnalysis", checked) }
                            XSwitch { text: "Análisis rápido compatible"; checked: viewState.fastMode; enabled: viewState.playlistAnalysis; onToggled: batchController.setValue("fastMode", checked) }
                            XSwitch { text: "Descargar al añadir"; checked: viewState.autoDownload; onToggled: batchController.setValue("autoDownload", checked) }
                            XSwitch { text: "Enviar imágenes al estudio"; checked: viewState.autoSendImages; onToggled: batchController.setValue("autoSendImages", checked) }
                            XSwitch { text: "Recodificar resultados"; checked: selected.jobId ? !!selected.recode : viewState.globalRecode; onToggled: selected.jobId ? batchController.setSelectedOption("recode", checked) : batchController.setValue("globalRecode", checked) }
                            LabeledControl {
                                Layout.fillWidth: true; label: "Preset"
                                XComboBox { Layout.fillWidth: true; model: presetStore.videoPresets; currentIndex: Math.max(0, find(selected.preset || viewState.globalPreset)); onActivated: selected.jobId ? batchController.setSelectedOption("preset", currentText) : batchController.setValue("globalPreset", currentText) }
                            }
                            XSwitch { text: "Mantener originales"; checked: viewState.globalKeepOriginal; onToggled: batchController.setValue("globalKeepOriginal", checked) }
                            XSwitch { text: "Todas las pistas de audio"; checked: viewState.allAudioTracks; onToggled: batchController.setValue("allAudioTracks", checked) }
                            LabeledControl {
                                Layout.fillWidth: true; label: "Conflictos"
                                XComboBox { Layout.fillWidth: true; model: ["Renombrar", "Sobrescribir", "Omitir", "Preguntar"]; currentIndex: Math.max(0, find(viewState.conflictPolicy)); onActivated: batchController.setValue("conflictPolicy", currentText) }
                            }
                            XSwitch { text: "Crear subcarpeta"; checked: viewState.createSubfolder; onToggled: batchController.setValue("createSubfolder", checked) }
                            XTextField { Layout.fillWidth: true; visible: viewState.createSubfolder; text: viewState.subfolderName; placeholderText: "Nombre de la subcarpeta"; onEditingFinished: batchController.setValue("subfolderName", text) }
                            XButton { Layout.fillWidth: true; visible: selected.jobType === "PLAYLIST"; text: "Configurar playlist completa"; kind: "secondary"; onClicked: playlistDialog.openFor(selected.jobId) }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 9
            XTextField { Layout.fillWidth: true; text: viewState.outputPath; onEditingFinished: batchController.setValue("outputPath", text) }
            XButton { text: "Salida"; compact: true; kind: "secondary"; onClicked: batchController.chooseOutputFolder() }
            XButton { text: "Abrir"; compact: true; kind: "ghost"; onClicked: batchController.openOutput() }
            XButton { text: viewState.running ? "Pausar cola" : "Iniciar cola"; kind: viewState.running ? "danger" : "primary"; onClicked: batchController.toggleQueue() }
        }
        ProgressStrip { Layout.fillWidth: true; value: viewState.progress; status: viewState.status; busy: viewState.running || viewState.analyzing }
    }

    Popup {
        id: playlistDialog
        property string jobId: ""
        property var entries: []
        function openFor(id) { jobId = id; entries = batchController.playlistEntries(id); open() }
        anchors.centerIn: parent
        width: Math.min(page.width - 60, 700); height: Math.min(page.height - 70, 620)
        modal: true; focus: true; padding: 0
        background: Rectangle { radius: 18; color: theme.colors.surfaceRaised; border.color: theme.colors.border; border.width: 1 }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 18; spacing: 12
            SectionTitle { Layout.fillWidth: true; eyebrow: "PLAYLIST"; title: "Elementos detectados"; description: "Todos están seleccionados para mantener el flujo rápido." }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: playlistDialog.entries; spacing: 5
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width; height: 43; radius: 8; color: theme.colors.surfaceSoft
                    Text { anchors.fill: parent; anchors.margins: 11; text: (modelData.index + 1) + ". " + modelData.title; color: theme.colors.text; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11 }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Cancelar"; kind: "ghost"; onClicked: playlistDialog.close() }
                Item { Layout.fillWidth: true }
                XButton { text: "Usar todos"; onClicked: { var indices = []; for (var i = 0; i < playlistDialog.entries.length; ++i) indices.push(i); batchController.configurePlaylist(playlistDialog.jobId, indices, viewState.globalMode, viewState.globalQuality); playlistDialog.close() } }
            }
        }
    }
}
