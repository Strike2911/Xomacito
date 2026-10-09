import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    property var viewState: settingsController.state
    property var sections: ["General", "Cookies", "Dependencias", "Modelos", "Acerca de"]

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

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
                    ScrollView { id: generalScroll; contentWidth: availableWidth; background: Item {} ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: Math.max(0, generalScroll.availableWidth - 14); sourceComponent: generalPage } }
                    ScrollView { id: cookiesScroll; contentWidth: availableWidth; background: Item {} ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: Math.max(0, cookiesScroll.availableWidth - 14); sourceComponent: cookiesPage } }
                    ScrollView { id: dependenciesScroll; contentWidth: availableWidth; background: Item {} ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: Math.max(0, dependenciesScroll.availableWidth - 14); sourceComponent: dependenciesPage } }
                    ScrollView { id: modelsScroll; contentWidth: availableWidth; background: Item {} ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: Math.max(0, modelsScroll.availableWidth - 14); sourceComponent: modelsPage } }
                    ScrollView { id: aboutScroll; contentWidth: availableWidth; background: Item {} ScrollBar.horizontal.policy: ScrollBar.AlwaysOff; ScrollBar.vertical: XScrollBar {} Loader { width: Math.max(0, aboutScroll.availableWidth - 14); sourceComponent: aboutPage } }
                }
            }
        }
        ProgressStrip { Layout.fillWidth: true; visible: viewState.busy; value: viewState.progress; status: viewState.status; busy: viewState.busy }
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
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
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
                            Connections {
                                target: theme
                                function onAvailableThemesChanged() { Qt.callLater(themeCombo.syncSelection) }
                            }
                        }
                        Text {
                            visible: theme.lockedThemeCount > 0
                            text: theme.lockedThemeCount + " paleta" + (theme.lockedThemeCount === 1 ? "" : "s") + " por descubrir · desbloquea gatos de 5★ o 6★"
                            color: theme.colors.textMuted
                            font.pixelSize: 10
                        }
                    }
                }
                XSwitch { text: "Animaciones y transiciones"; checked: viewState.animationsEnabled; onToggled: settingsController.setValue("animationsEnabled", checked) }
                XSwitch { text: "Modo compacto"; checked: viewState.compactMode; onToggled: settingsController.setValue("compactMode", checked) }
                XSwitch { text: "Limpiar títulos descargados"; checked: viewState.cleanTitles; onToggled: settingsController.setValue("cleanTitles", checked) }
                XSwitch {
                    objectName: "openExplorerAfterDownloadSwitch"
                    text: "Abrir Explorador al terminar una descarga"
                    checked: viewState.openExplorerAfterDownload
                    onToggled: settingsController.setValue("openExplorerAfterDownload", checked)
                }
                XSwitch {
                    objectName: "keepRunningInBackgroundSwitch"
                    text: "Mantener Xomacito en segundo plano"
                    checked: viewState.keepRunningInBackground
                    onToggled: settingsController.setValue("keepRunningInBackground", checked)
                    ToolTip.visible: hovered
                    ToolTip.text: "Al cerrar la ventana, Xomacito queda listo en la bandeja para abrir más rápido."
                }
                XSwitch { text: "Mantener modelos I.A. en memoria"; checked: viewState.keepAiModels; onToggled: settingsController.setValue("keepAiModels", checked) }
            }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Importar tema"; kind: "secondary"; onClicked: settingsController.importTheme() }
                XButton { text: "Eliminar tema personal"; kind: "danger"; onClicked: settingsController.deleteTheme(viewState.theme) }
                XButton { text: "Abrir carpeta de temas"; kind: "ghost"; onClicked: settingsController.openFolder("themes") }
                Item { Layout.fillWidth: true }
                XButton {
                    objectName: "repeatGuidedTourButton"
                    text: "Repetir recorrido"
                    kind: "secondary"
                    onClicked: appController.requestGuidedTour()
                }
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
            XCard {
                Layout.fillWidth: true; implicitHeight: tiktokSessionControls.implicitHeight + 28
                ColumnLayout {
                    id: tiktokSessionControls
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; spacing: 10
                    Text { text: viewState.tiktokConnected ? "TikTok conectado" : "Conectar TikTok"; color: theme.colors.text; font.pixelSize: 16; font.bold: true }
                    Text { Layout.fillWidth: true; text: "Importa una vez la sesión exportada desde Brave o Chrome. Después, Xomacito la utiliza automáticamente en TikTok. Si caduca, vuelve a importarla."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    RowLayout {
                        XButton { text: viewState.tiktokConnected ? "Renovar sesión de TikTok" : "Importar sesión de TikTok"; onClicked: settingsController.importTikTokSession() }
                        XButton { visible: viewState.tiktokConnected; text: "Desconectar"; kind: "ghost"; onClicked: settingsController.disconnectTikTokSession() }
                        XButton { text: "Guía de exportación"; kind: "ghost"; onClicked: settingsController.openCookieExportGuide() }
                    }
                }
            }
            LabeledControl { Layout.fillWidth: true; label: "Cookies para otros sitios"; XComboBox { Layout.fillWidth: true; model: ["No usar", "Chrome", "Edge", "Firefox", "Brave", "Opera", "Vivaldi", "Archivo Manual..."]; currentIndex: Math.max(0, find(viewState.cookiesMode)); onActivated: settingsController.setValue("cookiesMode", currentText) } }
            GridLayout {
                Layout.fillWidth: true; columns: width > 650 ? 2 : 1; columnSpacing: 12; rowSpacing: 12
                LabeledControl { Layout.fillWidth: true; label: "Perfil (opcional)"; XTextField { Layout.fillWidth: true; text: viewState.browserProfile; placeholderText: "Default, Profile 1…"; onEditingFinished: settingsController.setValue("browserProfile", text) } }
                XTextField { Layout.fillWidth: true; text: viewState.cookiesPath; placeholderText: "Ruta de cookies.txt"; onEditingFinished: settingsController.setValue("cookiesPath", text) }
                XButton { text: "Elegir cookies.txt"; kind: "secondary"; onClicked: settingsController.chooseCookiesFile() }
            }
            Text { Layout.fillWidth: true; text: "Si Windows no permite leer las cookies de Brave o Chrome, usa Archivo Manual con una exportación local de la sesión del sitio. No compartas ese archivo. El navegador debe poder reproducir el video."; color: theme.colors.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 12 }
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
                    id: dependencyRow
                    required property string key
                    required property string name
                    required property bool installed
                    required property string localVersion
                    required property string latestVersion
                    required property string detail
                    required property string action
                    required property bool updateAvailable
                    width: ListView.view.width; height: 67; radius: 11; color: theme.colors.surfaceSoft; border.color: theme.colors.border; border.width: 1
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 11; spacing: 10
                        Rectangle { width: 10; height: 10; radius: 5; color: updateAvailable || !installed ? theme.colors.warning : theme.colors.success }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 3
                            Text { text: name; color: theme.colors.text; font.weight: Font.DemiBold }
                            Text { text: "Local: " + localVersion + (latestVersion ? "  ·  Disponible: " + latestVersion : ""); color: theme.colors.textMuted; font.pixelSize: 10 }
                        }
                        Text { text: detail; color: theme.colors.textMuted; font.pixelSize: 10 }
                        XButton { compact: true; kind: "secondary"; text: dependencyRow.action; enabled: !page.viewState.busy && ["ffmpeg", "deno", "poppler", "ytdlp", "upscayl"].indexOf(key) >= 0; onClicked: settingsController.installDependency(key) }
                    }
                }
            }
        }
    }

    Component {
        id: modelsPage
        ColumnLayout {
            spacing: 14
            Text { text: "Modelos de inteligencia artificial"; color: theme.colors.text; font.pixelSize: 20; font.weight: Font.DemiBold }
            XSwitch { text: "Mantener modelos cargados en memoria"; checked: viewState.keepAiModels; onToggled: settingsController.setValue("keepAiModels", checked) }
            Text { Layout.fillWidth: true; text: "Reduce el tiempo entre procesos a cambio de mantener la memoria ocupada."; color: theme.colors.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            GridLayout {
                Layout.fillWidth: true; columns: 2; columnSpacing: 10; rowSpacing: 10
                XCard { Layout.fillWidth: true; implicitHeight: 122
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12
                        Text { text: "Eliminación de fondo · BiRefNet"; color: theme.colors.text; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: "Retratos, objetos y bordes finos"; color: theme.colors.textMuted; font.pixelSize: 10 }
                        XButton { Layout.fillWidth: true; text: "Preparar modelos"; compact: true; enabled: !viewState.busy; onClicked: settingsController.downloadModels("rembg") }
                    }
                }
                XCard { Layout.fillWidth: true; implicitHeight: 122
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12
                        Text { text: "Reescalado · Upscayl"; color: theme.colors.text; font.pixelSize: 12 }
                        Text { text: "Fotografía, anime e ilustración"; color: theme.colors.textMuted; font.pixelSize: 10 }
                        XButton { Layout.fillWidth: true; text: "Preparar motor"; compact: true; enabled: !viewState.busy; onClicked: settingsController.downloadModels("Upscayl") }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: "Instalados"; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                XButton { text: "Importar NCNN"; compact: true; kind: "ghost"; onClicked: settingsController.importUpscaylModel() }
                XButton { text: "Actualizar"; compact: true; kind: "ghost"; onClicked: settingsController.refreshModels() }
                XButton { text: "Abrir carpeta"; compact: true; kind: "ghost"; onClicked: settingsController.openFolder("models") }
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
        id: aboutPage
        ColumnLayout {
            spacing: 16
            SectionTitle { Layout.fillWidth: true; eyebrow: "XOMACITO " + appController.version; title: "Descarga primero. Mejora después."; description: "Una herramienta local de Strike2911 para obtener y preparar contenido sin saltar entre aplicaciones." }
            XCard {
                Layout.fillWidth: true; implicitHeight: 160; cardColor: theme.colors.backgroundAlt
                RowLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 20
                    CatAvatar {
                        source: appController.catSource
                        rarity: appController.catRarity
                        rarityColor: appController.catRarityColor
                        animatedEffects: settingsController.state.animationsEnabled
                        Layout.preferredWidth: 105
                        Layout.preferredHeight: 105
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: appController.catRarity + "★ · " + appController.catName; color: appController.catRarityColor; font.pixelSize: 11; font.weight: Font.Bold }
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
