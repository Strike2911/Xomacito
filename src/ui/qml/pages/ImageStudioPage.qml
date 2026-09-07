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
    DropArea { anchors.fill: parent; enabled: !root.locked; onDropped: function(drop) { if (drop.hasUrls) imageController.addPaths(drop.urls) } }
    ColumnLayout {
        anchors.fill: parent; spacing: 10
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 2
                Text { text: "ESTUDIO DE IMAGEN"; color: theme.colors.primary; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.2 }
                Text { text: "Tu imagen, lista en unos pasos."; color: theme.colors.text; font.pixelSize: 22; font.weight: Font.DemiBold }
            }
            Item { Layout.fillWidth: true }
            XButton { text: "Importar imágenes"; enabled: !root.locked; onClicked: imageController.importFiles() }
        }
        RowLayout {
            Layout.fillWidth: true
            XTextField { Layout.fillWidth: true; placeholderText: "Pega un enlace de imagen o arrastra tus archivos aquí"; text: root.studio.url; enabled: !root.locked; onTextEdited: imageController.setValue("url", text); onAccepted: imageController.analyzeUrl() }
            XButton { text: "Cargar enlace"; kind: "secondary"; enabled: !root.locked && root.studio.url.length > 0; onClicked: imageController.analyzeUrl() }
            XButton { text: "Pegar"; kind: "secondary"; enabled: !root.locked; onClicked: imageController.paste() }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            XCard {
                Layout.fillWidth: true; Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "01  ·  VISTA PREVIA"; color: theme.colors.textMuted; font.pixelSize: 10; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: root.studio.itemCount + " archivo(s)"; color: theme.colors.primary; font.pixelSize: 10 }
                    }
                    ImageComparison {
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 120
                        originalSource: root.studio.previewSource
                        resultSource: root.studio.resultPreviewSource
                        Column {
                            anchors.centerIn: parent; width: parent.width - 40; spacing: 12
                            visible: !root.studio.previewSource
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "⊕"; font.pixelSize: 44; color: theme.colors.primary }
                            Text { width: parent.width; text: root.studio.itemCount ? "Preparando vista previa…" : "Arrastra una imagen para comenzar"; color: theme.colors.text; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 16; wrapMode: Text.WordWrap }
                            Text { width: parent.width; text: "PNG, JPG, WebP y más · procesamiento local"; color: theme.colors.textMuted; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 11; wrapMode: Text.WordWrap }
                        }
                    }
                    Text { Layout.fillWidth: true; text: root.studio.resultPreviewSource ? "Desliza el separador para comparar el antes y el después." : root.studio.analysisReady ? root.studio.analysisDetail : "El resultado aparecerá aquí al terminar."; color: theme.colors.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                    ListView {
                        Layout.fillWidth: true; Layout.preferredHeight: root.studio.itemCount > 0 ? 46 : 0
                        visible: root.studio.itemCount > 0; orientation: ListView.Horizontal; spacing: 6; clip: true
                        model: imageController.model
                        delegate: XButton {
                            required property int index
                            required property string name
                            text: name; width: 160; compact: true
                            kind: root.studio.selectedIndex === index ? "primary" : "secondary"
                            enabled: !root.locked
                            onClicked: imageController.select(index)
                        }
                    }
                }
            }
            XCard {
                Layout.preferredWidth: Math.max(320, Math.min(420, root.width * 0.37)); Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    ScrollView {
                        id: controlsScroll
                        Layout.fillWidth: true; Layout.fillHeight: true
                        contentWidth: availableWidth; clip: true
                        ScrollBar.vertical: XScrollBar {}
                        ColumnLayout {
                            width: controlsScroll.availableWidth; spacing: 8
                            Text { text: "02  ·  HERRAMIENTA Y MODO"; color: theme.colors.primary; font.pixelSize: 10; font.bold: true }
                            XComboBox { Layout.fillWidth: true; compact: true; model: ["Removedor de fondo", "Mejorar resolución", "Convertir formato"]; currentIndex: Math.max(0, root.tasks.indexOf(root.studio.task)); enabled: !root.locked; onActivated: imageController.setTask(root.tasks[currentIndex]) }
                            XComboBox { Layout.fillWidth: true; compact: true; visible: root.studio.task === "removeBackground"; model: imageController.rembgModels("BiRefNet"); currentIndex: Math.max(0, model.indexOf(root.options.rembgModel)); enabled: !root.locked; onValueSelected: function(value) { imageController.setOption("rembgModel", value) } }
                            LabeledControl {
                                Layout.fillWidth: true; compact: true; label: "Escala"; visible: root.studio.task === "upscaleImage"
                                XComboBox { Layout.fillWidth: true; compact: true; model: ["2", "3", "4"]; currentIndex: Math.max(0, model.indexOf(root.options.upscaleScale)); enabled: !root.locked; onValueSelected: function(value) { imageController.setOption("upscaleScale", value) } }
                            }
                            Text { Layout.fillWidth: true; text: root.studio.recommendation; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                    Text { text: "03  ·  SALIDA"; color: theme.colors.primary; font.pixelSize: 10; font.bold: true }
                    RowLayout {
                        Layout.fillWidth: true
                        LabeledControl {
                            Layout.fillWidth: true; compact: true; label: "Nombre del archivo"
                            XTextField { Layout.fillWidth: true; compact: true; text: imageController.selected.title || ""; placeholderText: "Nombre sin extensión"; enabled: !root.locked && root.studio.itemCount > 0; onEditingFinished: imageController.setSelectedTitle(text) }
                        }
                        LabeledControl {
                            Layout.preferredWidth: 95; compact: true; label: "Formato"
                            XComboBox { Layout.fillWidth: true; compact: true; model: root.studio.task === "removeBackground" ? ["PNG", "WEBP"] : ["PNG", "JPEG", "WEBP", "AVIF", "TIFF", "PDF", "ICO"]; currentIndex: Math.max(0, model.indexOf(root.studio.format)); enabled: !root.locked; onValueSelected: function(value) { imageController.setValue("format", value) } }
                        }
                    }
                    LabeledControl {
                        Layout.fillWidth: true; compact: true; label: "Carpeta de salida"
                        XTextField { Layout.fillWidth: true; compact: true; text: root.studio.outputPath; enabled: !root.locked; onEditingFinished: imageController.setValue("outputPath", text) }
                        XButton { text: "…"; compact: true; kind: "secondary"; enabled: !root.locked; onClicked: imageController.chooseOutputFolder() }
                    }
                    XButton { objectName: "imageStudioStartButton"; Layout.fillWidth: true; compact: true; text: root.studio.busy ? "Cancelar proceso" : "Iniciar · " + root.studio.itemCount + " imagen(es)"; kind: root.studio.busy ? "danger" : "primary"; enabled: root.studio.busy || (!root.locked && root.studio.itemCount > 0); onClicked: root.studio.busy ? imageController.cancel() : imageController.start() }
                    RowLayout {
                        Layout.fillWidth: true
                        XButton { Layout.fillWidth: true; compact: true; text: "Ver resultado"; enabled: !!root.studio.lastOutput; kind: "secondary"; onClicked: imageController.openOutput() }
                        XButton { text: "Vaciar"; compact: true; kind: "ghost"; enabled: !root.locked && root.studio.itemCount > 0; onClicked: imageController.clear() }
                    }
                }
            }
        }
        ProgressStrip { Layout.fillWidth: true; compact: true; value: root.studio.progress; status: root.studio.status; busy: root.locked }
    }
}
