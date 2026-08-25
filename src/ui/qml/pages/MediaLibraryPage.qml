import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../components"

Item {
    id: page
    property var viewState: mediaLibraryController.state
    property var selected: viewState.selected || ({})
    // El ancho útil de una ventana 960×720 ronda los 920 px. Mantener las
    // tres zonas en ese tamaño evita el salto brusco a una columna gigante.
    property bool wide: width >= 890
    property bool compactWidth: width < 1120
    property bool dense: height < 760
    property string pendingFolderPath: ""
    property string pendingFolderName: ""

    function clock(seconds) {
        var value = Math.max(0, Math.round(Number(seconds || 0)))
        var minutes = Math.floor(value / 60)
        var secs = value % 60
        return String(minutes).padStart(2, "0") + ":" + String(secs).padStart(2, "0")
    }

    MediaPlayer {
        id: player
        source: selected.kind === "Imagen" ? "" : selected.previewSource || ""
        audioOutput: AudioOutput { volume: 0.75 }
        videoOutput: previewVideo
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        SectionTitle {
            Layout.fillWidth: true
            compact: page.dense
            eyebrow: "BIBLIOTECA PREMIERE"
            title: "Explora. Recorta. Importa."
            description: "Analiza tus medios, conserva el original y crea sólo el fragmento que necesitas para editar."
            number: "03"
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: page.compactWidth ? 104 : page.dense ? 62 : 72
            cardColor: theme.colors.surfaceRaised
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 7
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text { text: "CARPETA VINCULADA"; color: theme.colors.primary; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                        Text { Layout.fillWidth: true; text: viewState.rootPath; color: theme.colors.text; font.pixelSize: 11; elide: Text.ElideMiddle }
                    }
                    RowLayout {
                        visible: !page.compactWidth
                        spacing: 8
                        XButton { compact: true; text: "Abrir"; kind: "secondary"; onClicked: mediaLibraryController.openLibrary() }
                        XButton { compact: true; text: "Cambiar"; kind: "secondary"; onClicked: mediaLibraryController.chooseLibraryFolder() }
                        XButton { compact: true; text: "Importar carpeta"; onClicked: mediaLibraryController.importFolder() }
                        XButton {
                            compact: true
                            text: "Xomacito Link"
                            kind: viewState.premiereLinkEnabled ? "secondary" : "primary"
                            onClicked: mediaLibraryController.connectPremiere()
                        }
                        XButton {
                            visible: Number(viewState.hiddenFolderCount || 0) > 0
                            compact: true; text: "Restaurar (" + Number(viewState.hiddenFolderCount || 0) + ")"; kind: "ghost"
                            onClicked: mediaLibraryController.restoreHiddenFolders()
                        }
                        XButton { compact: true; text: "Actualizar"; kind: "ghost"; onClicked: mediaLibraryController.refresh() }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: page.compactWidth
                    spacing: 6
                    XButton { Layout.fillWidth: true; compact: true; text: "Abrir"; kind: "secondary"; onClicked: mediaLibraryController.openLibrary() }
                    XButton { Layout.fillWidth: true; compact: true; text: "Cambiar"; kind: "secondary"; onClicked: mediaLibraryController.chooseLibraryFolder() }
                    XButton { Layout.fillWidth: true; compact: true; text: "Importar"; onClicked: mediaLibraryController.importFolder() }
                    XButton {
                        Layout.fillWidth: true
                        compact: true
                        text: "Xomacito Link"
                        kind: viewState.premiereLinkEnabled ? "secondary" : "primary"
                        onClicked: mediaLibraryController.connectPremiere()
                    }
                    XButton {
                        Layout.fillWidth: true; visible: Number(viewState.hiddenFolderCount || 0) > 0
                        compact: true; text: "Restaurar " + Number(viewState.hiddenFolderCount || 0); kind: "ghost"
                        onClicked: mediaLibraryController.restoreHiddenFolders()
                    }
                    XButton { Layout.fillWidth: true; compact: true; text: "Actualizar"; kind: "ghost"; onClicked: mediaLibraryController.refresh() }
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
                id: libraryCard
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.wide ? 3 : 1
                Layout.minimumHeight: 280
                clip: true
                cardColor: libraryDropArea.containsDrag ? theme.colors.surfaceRaised : theme.colors.surface
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "RECURSOS"; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.Bold }
                        Rectangle {
                            implicitWidth: countText.implicitWidth + 14; implicitHeight: 24; radius: 12
                            color: theme.colors.surfaceSoft; border.color: theme.colors.border
                            Text { id: countText; anchors.centerIn: parent; text: (viewState.visibleCount || 0) + " / " + (viewState.itemCount || 0); color: theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.Bold }
                        }
                        Item { Layout.fillWidth: true }
                        Text { text: "EDITORIAL"; color: theme.colors.textDim; font.pixelSize: 8 }
                    }
                    XTextField {
                        Layout.fillWidth: true
                        compact: true
                        placeholderText: "Buscar nombre, carpeta o metadata…"
                        onTextEdited: mediaLibraryController.setSearchText(text)
                    }
                    XComboBox {
                        Layout.fillWidth: true
                        compact: true
                        model: ["Todos", "Favoritos", "Video", "SFX", "Música", "Imágenes", "Green screen"]
                        currentIndex: Math.max(0, find(viewState.categoryFilter || "Todos"))
                        onActivated: mediaLibraryController.setCategoryFilter(currentText)
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                    ListView {
                        id: mediaList
                        objectName: "premiereMediaList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: mediaLibraryController.libraryRowsModel
                        ScrollBar.vertical: XScrollBar {}
                        delegate: Rectangle {
                            required property string rowType
                            required property string folderPath
                            required property string folderName
                            required property int folderCount
                            required property bool expanded
                            required property bool canRemove
                            required property string path
                            required property string name
                            required property string kind
                            required property string durationLabel
                            required property string sizeLabel
                            required property string thumbnailSource
                            required property string category
                            required property bool isFavorite
                            width: mediaList.width
                            height: rowType === "folder" ? 32 : 38
                            radius: 7
                            color: rowType === "folder"
                                   ? theme.colors.surfaceSoft
                                   : selected.path === path ? theme.colors.surfaceRaised
                                   : hover.hovered ? theme.colors.surfaceSoft : "transparent"
                            border.width: selected.path === path && rowType === "file" ? 2 : 1
                            border.color: selected.path === path && rowType === "file"
                                          ? theme.colors.primary : theme.colors.border
                            HoverHandler { id: hover }
                            TapHandler {
                                onTapped: {
                                    if (rowType === "folder") {
                                        mediaLibraryController.toggleFolder(folderPath)
                                    } else {
                                        player.stop()
                                        mediaLibraryController.selectPath(path)
                                    }
                                }
                            }
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 5; spacing: 7
                                Rectangle {
                                    Layout.preferredWidth: rowType === "folder" ? 24 : 42
                                    Layout.fillHeight: true; radius: 6
                                    color: theme.colors.backgroundAlt; clip: true
                                    Image {
                                        anchors.fill: parent
                                        source: rowType === "file" && thumbnailSource ? thumbnailSource : ""
                                        fillMode: Image.PreserveAspectCrop
                                        asynchronous: true
                                        visible: rowType === "file" && thumbnailSource
                                    }
                                    Text {
                                        anchors.centerIn: parent
                                        visible: rowType === "folder" || thumbnailSource === ""
                                        text: rowType === "folder" ? (expanded ? "▾" : "▸") : kind === "Video" ? "▶" : kind === "Imagen" ? "▧" : "♫"
                                        color: theme.colors.primary; font.pixelSize: rowType === "folder" ? 13 : 14
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Text {
                                        Layout.fillWidth: true
                                        text: rowType === "folder" ? folderName : name
                                        color: theme.colors.text; font.pixelSize: 9; font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        visible: rowType === "file"
                                        text: category + " · " + (kind === "Imagen" ? sizeLabel : durationLabel + " · " + sizeLabel)
                                        color: theme.colors.textMuted; font.pixelSize: 7; elide: Text.ElideRight
                                    }
                                }
                                Text { visible: rowType === "folder"; text: folderCount; color: theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.Bold }
                                XButton {
                                    visible: rowType === "file"
                                    compact: true
                                    implicitWidth: 28
                                    text: isFavorite ? "★" : "☆"
                                    kind: "ghost"
                                    ToolTip.visible: hovered
                                    ToolTip.text: isFavorite ? "Quitar de favoritos" : "Añadir a favoritos"
                                    onClicked: mediaLibraryController.toggleFavorite(path)
                                }
                                XButton {
                                    visible: rowType === "folder" && canRemove
                                    compact: true
                                    kind: "ghost"
                                    text: "Quitar"
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Ocultar esta carpeta sin borrar sus archivos"
                                    onClicked: {
                                        page.pendingFolderPath = folderPath
                                        page.pendingFolderName = folderName
                                        removeFolderPopup.open()
                                    }
                                }
                            }
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: mediaList.count === 0 && !viewState.busy
                            text: viewState.itemCount > 0
                                  ? "No hay resultados con este filtro"
                                  : "Arrastra carpetas aquí\no importa una desde el botón superior"
                            color: theme.colors.textMuted
                            horizontalAlignment: Text.AlignHCenter
                            lineHeight: 1.35
                        }
                    }
                }
                DropArea {
                    id: libraryDropArea
                    objectName: "premiereLibraryDropArea"
                    anchors.fill: parent
                    onDropped: function(drop) {
                        if (!drop.hasUrls)
                            return
                        var paths = []
                        for (var index = 0; index < drop.urls.length; ++index)
                            paths.push(drop.urls[index].toString())
                        mediaLibraryController.addDroppedPaths(paths)
                        drop.acceptProposedAction()
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    z: 20
                    visible: libraryDropArea.containsDrag
                    radius: 13
                    color: "#E6141820"
                    border.width: 2
                    border.color: theme.colors.primary
                    Column {
                        anchors.centerIn: parent
                        spacing: 7
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "↓"; color: theme.colors.primary; font.pixelSize: 28; font.weight: Font.Bold }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "SUELTA PARA IMPORTAR"; color: theme.colors.text; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Carpetas o archivos multimedia"; color: theme.colors.textMuted; font.pixelSize: 9 }
                    }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.wide ? 5 : 1
                Layout.minimumHeight: 280
                clip: true
                cardColor: theme.colors.surfaceRaised
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { Layout.fillWidth: true; text: selected.name || "Selecciona un archivo"; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { text: selected.kind ? selected.kind + " · " + selected.dimensions + " · V: " + selected.videoCodec + " · A: " + selected.audioCodec : "Vista previa y puntos de corte"; color: theme.colors.textMuted; font.pixelSize: 9 }
                        }
                        Rectangle {
                            visible: Boolean(selected.kind)
                            implicitWidth: formatText.implicitWidth + 16; implicitHeight: 25; radius: 12
                            color: theme.colors.surfaceSoft; border.color: theme.colors.borderStrong
                            Text { id: formatText; anchors.centerIn: parent; text: selected.kind === "Audio" ? "SALIDA WAV" : selected.kind === "Imagen" ? "LISTA PARA USAR" : "SALIDA MP4"; color: theme.colors.primary; font.pixelSize: 9; font.weight: Font.Bold }
                        }
                        XButton {
                            visible: Boolean(selected.path)
                            compact: true; implicitWidth: 34
                            text: selected.isFavorite ? "★" : "☆"; kind: "ghost"
                            ToolTip.visible: hovered
                            ToolTip.text: selected.isFavorite ? "Quitar de favoritos" : "Añadir a favoritos"
                            onClicked: mediaLibraryController.toggleFavorite(selected.path)
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 135
                        radius: 12; color: "#090B0F"; border.color: theme.colors.border; clip: true
                        VideoOutput { id: previewVideo; anchors.fill: parent; visible: selected.kind !== "Imagen"; fillMode: VideoOutput.PreserveAspectFit }
                        Image {
                            anchors.fill: parent; anchors.margins: 8
                            visible: selected.kind === "Imagen" && Boolean(selected.previewSource)
                            source: visible ? selected.previewSource : ""
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                        }
                        Column {
                            anchors.centerIn: parent
                            visible: !selected.previewSource || selected.kind === "Audio"
                            spacing: 8
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: selected.kind === "Audio" ? "♫" : "▶"; color: theme.colors.primary; font.pixelSize: 34 }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: selected.kind === "Audio" ? "Vista previa de audio" : "Selecciona un archivo"; color: theme.colors.textMuted; font.pixelSize: 11 }
                        }
                        RoundButton {
                            anchors.centerIn: parent
                            visible: Boolean(selected.previewSource) && selected.kind !== "Imagen"
                            width: 48; height: 48
                            text: player.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"
                            onClicked: player.playbackState === MediaPlayer.PlayingState ? player.pause() : player.play()
                            contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { radius: 24; color: "#B8151820"; border.color: theme.colors.primary; border.width: 1 }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 0
                        visible: false
                        radius: 11
                        color: theme.colors.surfaceSoft
                        border.color: theme.colors.border
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 5
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "DETALLES DEL ARCHIVO"; color: theme.colors.primary; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }
                                Item { Layout.fillWidth: true }
                                Text { text: selected.metadataCount ? selected.metadataCount + " etiqueta(s)" : "Sin metadata"; color: theme.colors.textDim; font.pixelSize: 8 }
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: 4
                                columnSpacing: 8
                                rowSpacing: 5
                                Repeater {
                                    model: [
                                        ["FORMATO", selected.formatLabel || "—"],
                                        ["RESOLUCIÓN", selected.dimensions || "—"],
                                        ["TAMAÑO EXACTO", selected.sizeBytesLabel || "—"],
                                        ["DURACIÓN / FPS", selected.durationLabel ? selected.durationLabel + " · " + selected.frameRate : "—"],
                                        ["VIDEO", selected.videoCodec ? selected.videoCodec + " · " + selected.videoProfile : "—"],
                                        ["COLOR / PÍXEL", selected.pixelFormat || "—"],
                                        ["AUDIO", selected.audioCodec ? selected.audioCodec + " · " + selected.sampleRate + " · " + selected.channels : "—"],
                                        ["BITRATE", selected.totalBitrate || "—"]
                                    ]
                                    delegate: ColumnLayout {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Text { Layout.fillWidth: true; text: modelData[0]; color: theme.colors.textDim; font.pixelSize: 7; font.weight: Font.Bold; font.letterSpacing: 0.7 }
                                        Text { Layout.fillWidth: true; text: modelData[1]; color: theme.colors.text; font.pixelSize: 8; elide: Text.ElideRight; ToolTip.visible: detailHover.hovered; ToolTip.text: text; HoverHandler { id: detailHover } }
                                    }
                                }
                            }
                            Text { Layout.fillWidth: true; text: "METADATA · " + (selected.metadataSummary || "Selecciona un archivo"); color: theme.colors.textMuted; font.pixelSize: 8; elide: Text.ElideRight; ToolTip.visible: metadataHover.hovered; ToolTip.text: selected.metadataSummary || ""; HoverHandler { id: metadataHover } }
                            Text { Layout.fillWidth: true; text: selected.path ? "RUTA · " + selected.path : ""; color: theme.colors.textDim; font.pixelSize: 7; elide: Text.ElideMiddle; ToolTip.visible: pathHover.hovered; ToolTip.text: selected.path || ""; HoverHandler { id: pathHover } }
                        }
                    }
                    RowLayout {
                        visible: selected.kind !== "Imagen"
                        Layout.fillWidth: true; spacing: 8
                        Text { text: page.clock(viewState.clipIn); color: theme.colors.text; font.pixelSize: 10; font.weight: Font.Bold }
                        RangeSlider {
                            id: clipRange
                            objectName: "mediaClipRange"
                            Layout.fillWidth: true
                            from: 0
                            to: Math.max(0.01, Number(selected.duration || 0))
                            first.value: Number(viewState.clipIn || 0)
                            second.value: Number(viewState.clipOut || 0)
                            first.onMoved: mediaLibraryController.setValue("clipIn", first.value)
                            second.onMoved: mediaLibraryController.setValue("clipOut", second.value)
                            background: Rectangle {
                                x: clipRange.leftPadding; y: clipRange.topPadding + clipRange.availableHeight / 2 - height / 2
                                width: clipRange.availableWidth; height: 6; radius: 3; color: theme.colors.surfaceSoft
                                Rectangle {
                                    x: clipRange.first.visualPosition * parent.width
                                    width: Math.max(0, (clipRange.second.visualPosition - clipRange.first.visualPosition) * parent.width)
                                    height: parent.height; radius: 3; color: theme.colors.primary
                                }
                            }
                            first.handle: Rectangle { x: clipRange.leftPadding + clipRange.first.visualPosition * (clipRange.availableWidth - width); y: clipRange.topPadding + clipRange.availableHeight / 2 - height / 2; width: 18; height: 18; radius: 9; color: theme.colors.text; border.color: theme.colors.primary; border.width: 4 }
                            second.handle: Rectangle { x: clipRange.leftPadding + clipRange.second.visualPosition * (clipRange.availableWidth - width); y: clipRange.topPadding + clipRange.availableHeight / 2 - height / 2; width: 18; height: 18; radius: 9; color: theme.colors.text; border.color: theme.colors.primary; border.width: 4 }
                        }
                        Text { text: page.clock(viewState.clipOut); color: theme.colors.text; font.pixelSize: 10; font.weight: Font.Bold }
                    }
                    RowLayout {
                        visible: selected.kind !== "Imagen"
                        Layout.fillWidth: true; spacing: 8
                        Text { text: "Fragmento: " + page.clock(Number(viewState.clipOut || 0) - Number(viewState.clipIn || 0)); color: theme.colors.textMuted; font.pixelSize: 10 }
                        Item { Layout.fillWidth: true }
                        ComboBox {
                            visible: selected.kind === "Video"
                            model: ["Video + audio", "Solo video", "Solo audio"]
                            currentIndex: Math.max(0, model.indexOf(viewState.clipMode))
                            onActivated: mediaLibraryController.setValue("clipMode", currentText)
                            implicitWidth: 145; implicitHeight: 36
                            contentItem: Text { leftPadding: 10; text: parent.displayText; color: theme.colors.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 10 }
                            background: Rectangle { radius: 9; color: theme.colors.surfaceSoft; border.color: theme.colors.border }
                        }
                        XButton {
                            text: viewState.busy ? "Procesando…" : "Crear recorte"
                            compact: true
                            enabled: Boolean(selected.path) && !viewState.busy
                            onClicked: mediaLibraryController.createClip()
                        }
                    }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.wide ? 4 : 1
                Layout.minimumHeight: 280
                clip: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: page.dense ? 11 : 16; spacing: page.dense ? 8 : 13
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 3
                            Text { text: "DETALLES DEL ARCHIVO"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                            Text { Layout.fillWidth: true; text: selected.name || "Selecciona un archivo"; color: theme.colors.text; font.pixelSize: page.dense ? 16 : 19; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        }
                        Rectangle {
                            implicitWidth: detailTags.implicitWidth + 16; implicitHeight: 25; radius: 9
                            color: theme.colors.surfaceSoft; border.color: theme.colors.border
                            Text { id: detailTags; anchors.centerIn: parent; text: selected.metadataCount ? selected.metadataCount + " etiqueta(s)" : "Sin metadata"; color: theme.colors.textMuted; font.pixelSize: 9 }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 14; rowSpacing: page.dense ? 8 : 13
                        Repeater {
                            model: [
                                ["FORMATO", selected.formatLabel || "—"],
                                ["RESOLUCIÓN", selected.dimensions || "—"],
                                ["TAMAÑO EXACTO", selected.sizeBytesLabel || "—"],
                                ["DURACIÓN / FPS", selected.durationLabel ? selected.durationLabel + " · " + selected.frameRate : "—"],
                                ["VIDEO", selected.videoCodec ? selected.videoCodec + " · " + selected.videoProfile : "—"],
                                ["COLOR / PÍXEL", selected.pixelFormat || "—"],
                                ["AUDIO", selected.audioCodec ? selected.audioCodec + " · " + selected.sampleRate + " · " + selected.channels : "—"],
                                ["BITRATE", selected.totalBitrate || "—"]
                            ]
                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 3
                                Text { Layout.fillWidth: true; text: modelData[0]; color: theme.colors.textDim; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                                Text { Layout.fillWidth: true; text: modelData[1]; color: theme.colors.text; font.pixelSize: 11; wrapMode: Text.Wrap; maximumLineCount: 2 }
                            }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }
                    Text { text: "METADATA"; color: theme.colors.textDim; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                    Text { Layout.fillWidth: true; text: selected.metadataSummary || "Selecciona un archivo para consultar sus datos técnicos."; color: theme.colors.textMuted; font.pixelSize: 10; lineHeight: 1.2; wrapMode: Text.WordWrap; maximumLineCount: page.dense ? 2 : 4; elide: Text.ElideRight }
                    Text { text: "RUTA COMPLETA"; color: theme.colors.textDim; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                    Text { Layout.fillWidth: true; text: selected.path || "—"; color: theme.colors.textMuted; font.pixelSize: 9; wrapMode: Text.WrapAnywhere; maximumLineCount: page.dense ? 2 : 4; elide: Text.ElideRight }
                    Item { Layout.fillHeight: true }
                    Rectangle {
                        Layout.fillWidth: true; implicitHeight: page.dense ? 42 : 56; radius: 11
                        color: theme.colors.surfaceSoft; border.color: theme.colors.border
                        RowLayout { anchors.fill: parent; anchors.margins: 11; spacing: 10
                            Text { text: "✓"; color: theme.colors.success; font.pixelSize: 18; font.weight: Font.Bold }
                            Text { Layout.fillWidth: true; text: "El original siempre queda intacto; el recorte se guarda aparte."; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                        }
                    }
                }
            }
        }

        ProgressStrip {
            Layout.fillWidth: true
            compact: true
            value: viewState.progress
            status: viewState.status
            busy: viewState.busy
        }
    }

    Popup {
        id: removeFolderPopup
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(500, page.width - 42)
        implicitHeight: removeFolderContent.implicitHeight + 40
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape
        background: Rectangle {
            radius: 17
            color: theme.colors.surfaceRaised
            border.width: 1
            border.color: theme.colors.warning
        }
        contentItem: ColumnLayout {
            id: removeFolderContent
            x: 20
            y: 20
            width: removeFolderPopup.width - 40
            spacing: 13
            Text {
                Layout.fillWidth: true
                text: "¿Quitar esta carpeta?"
                color: theme.colors.text
                font.pixelSize: 19
                font.weight: Font.DemiBold
            }
            Text {
                Layout.fillWidth: true
                text: page.pendingFolderName
                color: theme.colors.primary
                font.pixelSize: 13
                font.weight: Font.Bold
                elide: Text.ElideMiddle
            }
            Text {
                Layout.fillWidth: true
                text: "La carpeta dejará de aparecer en Xomacito, pero sus archivos permanecerán intactos en el disco. Podrás restaurarla desde la barra superior."
                color: theme.colors.textMuted
                font.pixelSize: 12
                lineHeight: 1.25
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                XButton { text: "Cancelar"; kind: "secondary"; onClicked: removeFolderPopup.close() }
                XButton {
                    text: "Quitar de la lista"
                    onClicked: {
                        var target = page.pendingFolderPath
                        removeFolderPopup.close()
                        mediaLibraryController.removeFolder(target)
                    }
                }
            }
        }
    }
}
