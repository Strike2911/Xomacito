import QtQuick
import QtQuick.Window
import "../wallpaper"
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ScrollView {
    id: page
    property bool advanced: false
    function selectPalette(name) {
        // The published 1.4.7 Python setTheme() also restores wallpaper defaults.
        // Preserve the effective image through its public API until that backend
        // is rebuilt. setWallpaper creates an optimized copy, so the original
        // file remains available even when restoreThemeDefaults clears its key.
        if (name === theme.themeName) return
        var imageUrl = theme.backgroundImage.toString()
        var imageOpacity = theme.backgroundOpacity
        settingsController.setValue("theme", name)
        if (imageUrl) {
            var path = imageUrl.indexOf("file:///") === 0 ? imageUrl.substring(8)
                     : imageUrl.indexOf("file://") === 0 ? imageUrl.substring(5) : imageUrl
            theme.setWallpaper(decodeURIComponent(path))
            theme.setWallpaperOpacity(imageOpacity)
        } else {
            theme.removeWallpaper()
        }
    }
    objectName: "personalizationPage"
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    clip: true
    ScrollBar.vertical: XScrollBar {}
    ColumnLayout {
        width: Math.max(0, page.availableWidth - 12)
        spacing: 12
        XCard {
            visible: page.advanced
            Layout.fillWidth: true; implicitHeight: savedThemesContent.implicitHeight + 32
            ColumnLayout {
                id: savedThemesContent; anchors.fill: parent; anchors.margins: 16; spacing: 10
                Text { text: "MIS TEMAS CUSTOM"; color: theme.colors.text; font.pixelSize: 17 }
                RowLayout {
                    Layout.fillWidth: true
                    XTextField { id: customName; objectName: "customThemeName"; Layout.fillWidth: true; placeholderText: "Nombre del tema"; maximumLength: 80 }
                    XButton { objectName: "saveCustomTheme"; text: "CREAR TEMA CUSTOM"; onClicked: theme.saveCustomTheme(customName.text) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    XComboBox { id: savedThemes; objectName: "savedCustomThemes"; Layout.fillWidth: true; model: theme.customThemes }
                    XButton { text: "Aplicar"; enabled: savedThemes.currentIndex >= 0; onClicked: theme.applyCustomTheme(savedThemes.currentText) }
                    XButton { text: "Eliminar"; kind: "danger"; enabled: savedThemes.currentIndex >= 0; onClicked: theme.deleteCustomTheme(savedThemes.currentText) }
                }
                Text { text: theme.customizationStatus; color: theme.colors.textMuted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
        }
        Text { text: page.advanced ? "Personalización avanzada" : "Temas y fondo"; color: theme.colors.text; font.pixelSize: 21; font.weight: Font.DemiBold }
        RowLayout {
            visible: !page.advanced && theme.customThemes.length > 0
            Layout.fillWidth: true
            XComboBox { id: normalSavedThemes; Layout.fillWidth: true; model: theme.customThemes }
            XButton { text: "Aplicar mi tema"; enabled: normalSavedThemes.currentIndex >= 0; onClicked: theme.applyCustomTheme(normalSavedThemes.currentText) }
        }
        Text { text: "Haz tuyo el espacio de trabajo. Los cambios se guardan automáticamente."; color: theme.colors.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        XCard {
            Layout.fillWidth: true; implicitHeight: paletteContent.implicitHeight + 32
            ColumnLayout {
                id: paletteContent; anchors.fill: parent; anchors.margins: 16; spacing: 12
                Text { text: "Paleta y apariencia"; color: theme.colors.text; font.pixelSize: 17 }
                RowLayout {
                    Layout.fillWidth: true
                    XComboBox { objectName: "themeCombo"; Layout.preferredWidth: Math.min(310, page.width * 0.43); Layout.fillWidth: true; displayText: currentText.replace(/_/g, " ").replace(/\b\w/g, function(c) { return c.toUpperCase() }); model: theme.availableThemes; currentIndex: Math.max(0, theme.availableThemes.indexOf(theme.themeName)); onValueSelected: function(value) { page.selectPalette(value) } }
                    XComboBox { Layout.preferredWidth: 160; model: ["Dark", "Light", "System"]; displayText: ["Oscuro", "Claro", "Sistema"][currentIndex]; currentIndex: Math.max(0, find(theme.appearance)); onValueSelected: function(value) { theme.setAppearance(value) } }
                }
                GridLayout {
                    objectName: "advancedCustomColors"
                    visible: page.advanced
                    Layout.fillWidth: true; columns: page.width > 1000 ? 4 : 3; columnSpacing: 12; rowSpacing: 10
                    Repeater {
                        model: [{key:"primary",label:"Principal"},{key:"accent",label:"Acento"},{key:"background",label:"Fondo"},{key:"surface",label:"Paneles"},{key:"surfaceRaised",label:"Controles"},{key:"text",label:"Texto"},{key:"textMuted",label:"Texto secundario"},{key:"border",label:"Bordes"}]
                        delegate: XButton {
                            required property var modelData
                            Layout.fillWidth: true; implicitHeight: 48; text: "    " + modelData.label; kind: "secondary"
                            onClicked: theme.chooseColor(modelData.key)
                            Rectangle { x: 12; anchors.verticalCenter: parent.verticalCenter; width: 16; height: 16; radius: 4; color: theme.colors[parent.modelData.key]; border.color: theme.colors.textMuted }
                        }
                    }
                }
                RowLayout {
                    visible: page.advanced
                    XButton { visible: page.advanced; text: "Restablecer colores"; kind: "ghost"; onClicked: theme.resetCustomization() }
                    XButton { objectName: "restoreThemeDefaults"; text: "Restaurar tema original"; kind: "secondary"; onClicked: theme.restoreThemeDefaults() }
                }
            }
        }
        XCard {
            Layout.fillWidth: true; implicitHeight: backgroundContent.implicitHeight + 32
            ColumnLayout {
                id: backgroundContent; anchors.fill: parent; anchors.margins: 16; spacing: 12
                Text { text: "Fondo del programa"; color: theme.colors.text; font.pixelSize: 17 }
                GridLayout {
                    Layout.fillWidth: true
                    columns: page.width >= 1000 ? 2 : 1
                    columnSpacing: 24; rowSpacing: 14
                    Rectangle {
                        id: previewArea
                        Layout.fillWidth: true
                        Layout.preferredWidth: 650
                        Layout.preferredHeight: page.width >= 1000 ? 310 : 240
                        color: theme.colors.background
                        radius: 10; clip: true
                        Item {
                            id: viewport
                            readonly property real aspect: page.Window.window ? page.Window.window.width / page.Window.window.height : 16 / 9
                            width: Math.min(parent.width, parent.height * aspect)
                            height: width / aspect
                            anchors.centerIn: parent
                            Rectangle {
                                anchors.fill: parent
                                gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: theme.backgroundImage ? theme.colors.background : theme.gradientColors[0] } GradientStop { position: 1; color: theme.backgroundImage ? theme.colors.backgroundAlt : theme.gradientColors[2] } }
                            }
                            WallpaperImage {
                                objectName: "wallpaperPreview"
                                anchors.fill: parent; source: theme.backgroundImage
                                imageOpacity: theme.backgroundOpacity; interactive: true
                            }
                            Rectangle {
                                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 12
                                height: 26; radius: 6; color: Qt.alpha(theme.colors.surface, 0.9)
                                Text { anchors.centerIn: parent; text: "XOMACITO   ·   Vista previa del encuadre"; color: theme.colors.text; font.pixelSize: 10 }
                            }
                            Rectangle { anchors.fill: parent; color: "transparent"; border.color: theme.colors.border; radius: 6 }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.preferredWidth: 330
                        spacing: 12
                        Text { text: theme.backgroundImage ? "Arrastra la imagen para encuadrarla" : "Elige una imagen para empezar"; color: theme.colors.text; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        RowLayout {
                            XButton {
                                objectName: "chooseWallpaperButton"; text: "Elegir imagen…"; compact: true
                                onClicked: {
                                    var previous = theme.backgroundImage.toString()
                                    theme.chooseWallpaper()
                                    if (theme.backgroundImage.toString() !== previous && theme.backgroundImage) {
                                        theme.setWallpaperOpacity(0.5)
                                        WallpaperLayout.reset()
                                    }
                                }
                            }
                            XButton { text: "Usar degradado"; compact: true; kind: "secondary"; onClicked: theme.removeWallpaper() }
                        }
                        RowLayout {
                            XButton { text: "Otro degradado"; compact: true; kind: "ghost"; visible: !theme.backgroundImage; onClicked: theme.randomizeGradient() }
                            XButton { text: "Rellenar"; compact: true; visible: Boolean(theme.backgroundImage); kind: WallpaperLayout.fit === "cover" ? "primary" : "secondary"; onClicked: WallpaperLayout.fit = "cover" }
                            XButton { text: "Imagen completa"; compact: true; visible: Boolean(theme.backgroundImage); kind: WallpaperLayout.fit === "contain" ? "primary" : "secondary"; onClicked: WallpaperLayout.fit = "contain" }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Opacidad"; color: theme.colors.textMuted; Layout.preferredWidth: 72 }
                            XSlider { objectName: "wallpaperOpacitySlider"; Layout.fillWidth: true; from: 0; to: 1; value: theme.backgroundOpacity; enabled: Boolean(theme.backgroundImage); onMoved: theme.setWallpaperOpacity(value); Accessible.name: "Opacidad de la imagen" }
                            Text { text: Math.round(theme.backgroundOpacity * 100) + "%"; color: theme.colors.text; Layout.preferredWidth: 38 }
                        }
                        RowLayout {
                            Layout.fillWidth: true; enabled: Boolean(theme.backgroundImage)
                            Text { text: "Zoom"; color: theme.colors.textMuted; Layout.preferredWidth: 72 }
                            XSlider { objectName: "wallpaperZoomSlider"; Layout.fillWidth: true; from: 1; to: 3; value: WallpaperLayout.zoom; onMoved: WallpaperLayout.zoom = value; Accessible.name: "Zoom del fondo" }
                            Text { text: Math.round(WallpaperLayout.zoom * 100) + "%"; color: theme.colors.text; Layout.preferredWidth: 38 }
                        }
                        RowLayout {
                            Layout.fillWidth: true; enabled: Boolean(theme.backgroundImage)
                            Text { text: "Horizontal"; color: theme.colors.textMuted; Layout.preferredWidth: 72 }
                            XSlider { objectName: "wallpaperPositionX"; Layout.fillWidth: true; from: 0; to: 1; value: WallpaperLayout.positionX; onMoved: WallpaperLayout.positionX = value; Accessible.name: "Posición horizontal del fondo" }
                        }
                        RowLayout {
                            Layout.fillWidth: true; enabled: Boolean(theme.backgroundImage)
                            Text { text: "Vertical"; color: theme.colors.textMuted; Layout.preferredWidth: 72 }
                            XSlider { objectName: "wallpaperPositionY"; Layout.fillWidth: true; from: 0; to: 1; value: WallpaperLayout.positionY; onMoved: WallpaperLayout.positionY = value; Accessible.name: "Posición vertical del fondo" }
                        }
                        XButton { text: "Restablecer encuadre"; compact: true; kind: "ghost"; enabled: Boolean(theme.backgroundImage); onClicked: WallpaperLayout.reset() }
                    }
                }
                Text { text: "Tu imagen y su encuadre se conservan al cambiar de tema. Las imágenes nuevas empiezan al 50 % de opacidad."; color: theme.colors.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
            }
        }
    }
}
