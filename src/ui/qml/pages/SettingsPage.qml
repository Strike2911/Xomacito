import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: settingsController.state
    property var sections: ["General", "Cookies", "Dependencias", "Modelos", "Consola", "Acerca de"]

    ColumnLayout {
        anchors.fill: parent
        spacing: 14
        SectionTitle {
            Layout.fillWidth: true
            eyebrow: "CONFIGURACIÓN"
            title: "Tu espacio de trabajo."
            description: "Apariencia, acceso, componentes y herramientas avanzadas sin reconstruir la pantalla."
            number: "04"
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
            XCard {
                Layout.preferredWidth: 190; Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 6
                    Text { text: "OPCIONES"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1; Layout.leftMargin: 8; Layout.bottomMargin: 6 }
                    Repeater {
                        model: page.sections
                        XButton {
                            required property string modelData
                            Layout.fillWidth: true
                            text: modelData
                            kind: viewState.section === modelData ? "primary" : "ghost"
                            onClicked: settingsController.setValue("section", modelData)
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Text { Layout.fillWidth: true; text: "Xomacito " + appController.version; color: theme.colors.textDim; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter }
                }
            }
            XCard {
                Layout.fillWidth: true; Layout.fillHeight: true
                StackLayout {
                    anchors.fill: parent; anchors.margins: 18; clip: true
                    currentIndex: Math.max(0, page.sections.indexOf(viewState.section))
                    ScrollView { ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: parent.width; sourceComponent: generalPage } }
                    ScrollView { ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: parent.width; sourceComponent: cookiesPage } }
                    ScrollView { ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: parent.width; sourceComponent: dependenciesPage } }
                    ScrollView { ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: parent.width; sourceComponent: modelsPage } }
                    ScrollView { ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: parent.width; sourceComponent: consolePage } }
                    ScrollView { ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: parent.width; sourceComponent: aboutPage } }
                }
            }
        }
        ProgressStrip { Layout.fillWidth: true; visible: viewState.busy || viewState.status.length > 0; value: viewState.progress; status: viewState.status; busy: viewState.busy }
    }

    Component {
        id: generalPage
        ColumnLayout {
            spacing: 14
            SectionTitle { Layout.fillWidth: true; eyebrow: "INTERFAZ"; title: "Clara, rápida y tuya"; description: "Qt Quick mantiene las páginas vivas y anima sólo cambios con significado." }
            GridLayout {
                Layout.fillWidth: true; columns: width > 650 ? 2 : 1; columnSpacing: 14; rowSpacing: 12
                LabeledControl { Layout.fillWidth: true; label: "Apariencia"; XComboBox { objectName: "appearanceCombo"; Layout.fillWidth: true; model: ["Dark", "Light", "System"]; currentIndex: Math.max(0, find(viewState.appearance)); onValueSelected: function(value) { settingsController.setValue("appearance", value) } } }
                LabeledControl {
                    Layout.fillWidth: true
                    label: "Paleta"
                    XComboBox {
                        id: themeCombo
                        objectName: "themeCombo"
                        Layout.fillWidth: true
                        model: theme.availableThemes
                        currentIndex: -1
                        function syncSelection() {
                            var wanted = find(viewState.theme)
                            if (wanted >= 0 && currentIndex !== wanted)
                                currentIndex = wanted
                        }
                        Component.onCompleted: Qt.callLater(syncSelection)
                        onValueSelected: function(value) { settingsController.setValue("theme", value) }
                        Connections {
                            target: settingsController
                            function onStateChanged() { themeCombo.syncSelection() }
                        }
                    }
                }
                XSwitch { text: "Animaciones y transiciones"; checked: viewState.animationsEnabled; onToggled: settingsController.setValue("animationsEnabled", checked) }
                XSwitch { text: "Modo compacto"; checked: viewState.compactMode; onToggled: settingsController.setValue("compactMode", checked) }
                XSwitch { text: "Limpiar títulos descargados"; checked: viewState.cleanTitles; onToggled: settingsController.setValue("cleanTitles", checked) }
                XSwitch { text: "Mantener modelos I.A. en memoria"; checked: viewState.keepAiModels; onToggled: settingsController.setValue("keepAiModels", checked) }
            }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Importar tema"; kind: "secondary"; onClicked: settingsController.importTheme() }
                XButton { text: "Eliminar tema personal"; kind: "danger"; onClicked: settingsController.deleteTheme(viewState.theme) }
                XButton { text: "Abrir carpeta de temas"; kind: "ghost"; onClicked: settingsController.openFolder("themes") }
                Item { Layout.fillWidth: true }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
            SectionTitle { Layout.fillWidth: true; eyebrow: "VECTORES"; title: "Calidad de render"; description: "SVG, PDF, AI, EPS y PS usan estas resoluciones." }
            GridLayout {
                Layout.fillWidth: true; columns: width > 650 ? 2 : 1; columnSpacing: 14; rowSpacing: 12
                LabeledControl { Layout.fillWidth: true; label: "DPI de exportación"; XTextField { Layout.fillWidth: true; text: viewState.vectorDpi; inputMethodHints: Qt.ImhDigitsOnly; onEditingFinished: settingsController.setValue("vectorDpi", Number(text)) } }
                LabeledControl { Layout.fillWidth: true; label: "DPI de previsualización"; XTextField { Layout.fillWidth: true; text: viewState.previewVectorDpi; inputMethodHints: Qt.ImhDigitsOnly; onEditingFinished: settingsController.setValue("previewVectorDpi", Number(text)) } }
                XSwitch { text: "Forzar fondo en vectores"; checked: viewState.vectorForceBackground; onToggled: settingsController.setValue("vectorForceBackground", checked) }
                XSwitch { text: "Usar Inkscape cuando esté disponible"; checked: viewState.inkscapeEnabled; onToggled: settingsController.setValue("inkscapeEnabled", checked) }
                XTextField { Layout.fillWidth: true; text: viewState.inkscapePath; placeholderText: "Ruta de inkscape.exe (opcional)"; onEditingFinished: settingsController.setValue("inkscapePath", text) }
                XButton { text: "Elegir Inkscape"; kind: "secondary"; onClicked: settingsController.chooseInkscape() }
            }
        }
    }

    Component {
        id: cookiesPage
        ColumnLayout {
            spacing: 14
            SectionTitle { Layout.fillWidth: true; eyebrow: "ACCESO"; title: "Cookies bajo tu control"; description: "Úsalas sólo en sitios que requieran sesión. Xomacito no las sube a ningún servidor." }
            LabeledControl { Layout.fillWidth: true; label: "Fuente de cookies"; XComboBox { Layout.fillWidth: true; model: ["No usar", "Chrome", "Edge", "Firefox", "Brave", "Opera", "Vivaldi", "Archivo Manual..."]; currentIndex: Math.max(0, find(viewState.cookiesMode)); onActivated: settingsController.setValue("cookiesMode", currentText) } }
            GridLayout {
                Layout.fillWidth: true; columns: width > 650 ? 2 : 1; columnSpacing: 12; rowSpacing: 12
                LabeledControl { Layout.fillWidth: true; label: "Navegador interno"; XComboBox { Layout.fillWidth: true; model: ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"]; currentIndex: Math.max(0, find(viewState.selectedBrowser)); onActivated: settingsController.setValue("selectedBrowser", currentText) } }
                LabeledControl { Layout.fillWidth: true; label: "Perfil (opcional)"; XTextField { Layout.fillWidth: true; text: viewState.browserProfile; placeholderText: "Default, Profile 1…"; onEditingFinished: settingsController.setValue("browserProfile", text) } }
                XTextField { Layout.fillWidth: true; text: viewState.cookiesPath; placeholderText: "Ruta de cookies.txt"; onEditingFinished: settingsController.setValue("cookiesPath", text) }
                XButton { text: "Elegir cookies.txt"; kind: "secondary"; onClicked: settingsController.chooseCookiesFile() }
            }
            LabeledControl { Layout.fillWidth: true; label: "Enlace para probar"; XTextField { Layout.fillWidth: true; text: viewState.cookieTestUrl; onEditingFinished: settingsController.setValue("cookieTestUrl", text) } }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Probar acceso"; onClicked: settingsController.testCookies() }
                Item { Layout.fillWidth: true }
            }
        }
    }

    Component {
        id: dependenciesPage
        ColumnLayout {
            spacing: 14
            SectionTitle { Layout.fillWidth: true; eyebrow: "MOTOR"; title: "Componentes y versiones"; description: "La revisión rápida es local; la revisión completa consulta versiones nuevas sólo cuando la solicitas." }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Revisión rápida"; kind: "secondary"; onClicked: settingsController.refreshDependencies(false) }
                XButton { text: "Buscar actualizaciones"; onClicked: settingsController.refreshDependencies(true) }
                XButton { text: "Actualizar Xomacito"; kind: "secondary"; onClicked: appController.checkUpdates(true) }
                Item { Layout.fillWidth: true }
                XButton { text: "Abrir bin"; kind: "ghost"; onClicked: settingsController.openFolder("bin") }
            }
            ListView {
                Layout.fillWidth: true; Layout.preferredHeight: Math.max(330, contentHeight); model: settingsController.dependencyModel; spacing: 8; interactive: false
                delegate: Rectangle {
                    required property string key
                    required property string name
                    required property bool installed
                    required property string localVersion
                    required property string latestVersion
                    required property string detail
                    required property string action
                    width: ListView.view.width; height: 67; radius: 11; color: theme.colors.surfaceSoft; border.color: theme.colors.border; border.width: 1
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 11; spacing: 10
                        Rectangle { width: 10; height: 10; radius: 5; color: installed ? theme.colors.success : theme.colors.warning }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 3
                            Text { text: name; color: theme.colors.text; font.weight: Font.DemiBold }
                            Text { text: "Local: " + localVersion + (latestVersion ? "  ·  Nueva: " + latestVersion : ""); color: theme.colors.textMuted; font.pixelSize: 10 }
                        }
                        Text { text: detail; color: theme.colors.textMuted; font.pixelSize: 10 }
                        XButton { compact: true; text: action; enabled: ["ffmpeg", "deno", "poppler", "ytdlp"].indexOf(key) >= 0; onClicked: settingsController.installDependency(key) }
                    }
                }
            }
        }
    }

    Component {
        id: modelsPage
        ColumnLayout {
            spacing: 14
            SectionTitle { Layout.fillWidth: true; eyebrow: "MODELOS"; title: "I.A. y reescalado local"; description: "Descarga sólo los motores que uses y administra el espacio ocupado." }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Preparar rembg"; onClicked: settingsController.downloadModels("rembg") }
                XButton { text: "Preparar todos los escaladores"; kind: "secondary"; onClicked: settingsController.downloadModels("all") }
                XButton { text: "Importar modelo NCNN"; kind: "secondary"; onClicked: settingsController.importUpscaylModel() }
                XButton { text: "Actualizar lista"; kind: "ghost"; onClicked: settingsController.refreshModels() }
                Item { Layout.fillWidth: true }
                XButton { text: "Abrir modelos"; kind: "ghost"; onClicked: settingsController.openFolder("models") }
            }
            ListView {
                Layout.fillWidth: true; Layout.preferredHeight: Math.max(350, contentHeight); model: settingsController.modelModel; spacing: 7; interactive: false
                delegate: Rectangle {
                    required property string name
                    required property string family
                    required property string path
                    required property string size
                    width: ListView.view.width; height: 56; radius: 10; color: theme.colors.surfaceSoft; border.color: theme.colors.border; border.width: 1
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 10
                        Text { text: family.toUpperCase(); color: theme.colors.primary; font.pixelSize: 9; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: name; color: theme.colors.text; elide: Text.ElideMiddle }
                        Text { text: size; color: theme.colors.textMuted; font.pixelSize: 10 }
                        XButton { compact: true; text: "Eliminar"; kind: "danger"; onClicked: settingsController.deleteModel(path) }
                    }
                }
                Text { anchors.centerIn: parent; visible: parent.count === 0; text: "Aún no hay modelos instalados"; color: theme.colors.textMuted }
            }
        }
    }

    Component {
        id: consolePage
        ColumnLayout {
            spacing: 12
            SectionTitle { Layout.fillWidth: true; eyebrow: "CONSOLA"; title: "Herramientas integradas"; description: "FFmpeg, yt-dlp y los motores NCNN comparten el runtime de Xomacito." }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 430; radius: 12; color: theme.colors.backgroundAlt; border.color: theme.colors.border; border.width: 1
                ScrollView {
                    anchors.fill: parent; anchors.margins: 10
                    ScrollBar.vertical: XScrollBar {}
                    TextArea { id: consoleOutput; readOnly: true; text: settingsController.consoleText; color: theme.colors.text; font.family: "Cascadia Mono"; font.pixelSize: 11; wrapMode: viewState.consoleWrap ? TextEdit.WrapAnywhere : TextEdit.NoWrap; background: null; onTextChanged: cursorPosition = length }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                XTextField { id: command; Layout.fillWidth: true; placeholderText: "dp help, ffmpeg -version, yt-dlp --version…"; onAccepted: { settingsController.executeConsole(text); text = "" } }
                XButton { text: "Ejecutar"; enabled: !viewState.consoleBusy; onClicked: { settingsController.executeConsole(command.text); command.text = "" } }
                XButton { text: "Cancelar"; kind: "danger"; enabled: viewState.consoleBusy; onClicked: settingsController.cancelConsole() }
                XButton { text: "Limpiar"; kind: "ghost"; onClicked: settingsController.clearConsole() }
            }
            XSwitch { text: "Ajustar líneas largas"; checked: viewState.consoleWrap; onToggled: settingsController.setValue("consoleWrap", checked) }
        }
    }

    Component {
        id: aboutPage
        ColumnLayout {
            spacing: 16
            SectionTitle { Layout.fillWidth: true; eyebrow: "XOMACITO " + appController.version; title: "Descarga primero. Mejora después."; description: "Una herramienta local de Strike2911 para obtener y preparar contenido sin saltar entre aplicaciones." }
            XCard {
                Layout.fillWidth: true; implicitHeight: 160; cardColor: theme.colors.backgroundAlt
                RowLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 20
                    Image { source: appController.catSource; Layout.preferredWidth: 105; Layout.preferredHeight: 105; fillMode: Image.PreserveAspectFit; mipmap: true }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Gatito del día " + appController.catNumber + "/8"; color: theme.colors.accent; font.pixelSize: 11; font.weight: Font.Bold }
                        Text { text: "Motor Qt Quick + Python"; color: theme.colors.text; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; text: "La interfaz usa render acelerado, páginas persistentes y tareas en segundo plano. Tus archivos se procesan localmente."; color: theme.colors.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 11 }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "GitHub"; onClicked: settingsController.openUrl("https://github.com/Strike2911/Xomacito") }
                XButton { text: "YouTube"; kind: "secondary"; onClicked: settingsController.openUrl("https://www.youtube.com/@ElStrikew") }
                XButton { text: "Ko-fi"; kind: "secondary"; onClicked: settingsController.openUrl("https://ko-fi.com/strikepoint") }
                XButton { text: "Actualizaciones"; kind: "secondary"; onClicked: appController.openReleases() }
                XButton { text: "Buscar nueva versión"; kind: "secondary"; onClicked: appController.checkUpdates(true) }
                XButton { text: "Abrir configuración"; kind: "ghost"; onClicked: settingsController.openFolder("settings") }
                Item { Layout.fillWidth: true }
            }
            Text { Layout.fillWidth: true; text: "Xomacito incluye componentes de código abierto con sus respectivas licencias. © Strike2911."; color: theme.colors.textDim; font.pixelSize: 10; wrapMode: Text.WordWrap }
        }
    }
}
