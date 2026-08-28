import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../components"

Item {
    id: page
    property var viewState: mediaLibraryController.state
    property var selected: viewState.selected || ({})
    // El ancho útil de una ventana 960×720 ronda los 920 px. Mantener una
    // lista cómoda junto al editor evita columnas estrechas y texto ilegible.
    property bool wide: width >= 890
    property bool compactWidth: width < 1120
    property bool dense: height < 760
    property string pendingFolderPath: ""
    property string pendingFolderName: ""
    readonly property color libraryAccent: viewState.rootAccent || theme.colors.primary

    function clock(seconds) {
        var value = Math.max(0, Math.round(Number(seconds || 0)))
        var minutes = Math.floor(value / 60)
        var secs = value % 60
        return String(minutes).padStart(2, "0") + ":" + String(secs).padStart(2, "0")
    }

    function toggleLibraryPreview() {
        var startMs = Math.max(0, Number(viewState.clipIn || 0)) * 1000
        var endMs = Math.max(startMs, Number(viewState.clipOut || 0) * 1000)
        if (player.playbackState === MediaPlayer.PlayingState) {
            player.pause()
            return
        }
        if (player.position < startMs || player.position >= endMs)
            player.position = startMs
        player.play()
    }

    MediaPlayer {
        id: player
        source: selected.kind === "Imagen" ? "" : selected.previewSource || ""
        audioOutput: AudioOutput { id: libraryAudio; volume: 0.75 }
        videoOutput: previewVideo
        onPositionChanged: {
            if (selected.kind !== "Video" || playbackState !== MediaPlayer.PlayingState)
                return
            var startMs = Math.max(0, Number(viewState.clipIn || 0)) * 1000
            var endMs = Math.max(startMs, Number(viewState.clipOut || 0) * 1000)
            if (position < startMs)
                position = startMs
            else if (endMs > startMs && position >= endMs) {
                pause()
                position = startMs
            }
        }
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
            border.color: viewState.rootAccent || theme.colors.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 7
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            spacing: 6
                            Rectangle { width: 8; height: 8; radius: 4; color: viewState.rootAccent || theme.colors.primary }
                            Text { text: "CARPETA VINCULADA"; color: viewState.rootAccent || theme.colors.primary; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                        }
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
                Layout.columnSpan: page.wide ? 4 : 1
                Layout.minimumHeight: 280
                clip: true
                cardColor: libraryDropArea.containsDrag ? theme.colors.surfaceRaised : theme.colors.surface
                border.color: viewState.rootAccent || theme.colors.border
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "RECURSOS"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.Bold }
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
                        compact: false
                        placeholderText: "Buscar nombre, carpeta o metadata…"
                        onTextEdited: mediaLibraryController.setSearchText(text)
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.preferredHeight: childrenRect.height
                        spacing: 5
                        Repeater {
                            model: ["Todos", "Favoritos", "Video", "SFX", "Música", "Imágenes", "Green screen"]
                            Rectangle {
                                required property string modelData
                                readonly property bool active: viewState.categoryFilter === modelData
                                width: filterLabel.implicitWidth + 16
                                height: 32
                                radius: 8
                                color: active ? Qt.rgba(
                                    page.libraryAccent.r,
                                    page.libraryAccent.g,
                                    page.libraryAccent.b, 0.18
                                ) : theme.colors.surfaceSoft
                                border.color: active ? (viewState.rootAccent || theme.colors.primary) : theme.colors.border
                                Text {
                                    id: filterLabel
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: active ? theme.colors.text : theme.colors.textMuted
                                    font.pixelSize: 10
                                    font.weight: active ? Font.Bold : Font.Medium
                                }
                                TapHandler { onTapped: mediaLibraryController.setCategoryFilter(modelData) }
                            }
                        }
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
                            required property string folderColor
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
                            readonly property color accentColor: folderColor || theme.colors.primary
                            width: mediaList.width
                            height: rowType === "folder" ? 46 : 64
                            radius: 9
                            color: rowType === "folder"
                                   ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.11)
                                   : selected.path === path ? theme.colors.surfaceRaised
                                   : hover.hovered ? theme.colors.surfaceSoft : "transparent"
                            border.width: selected.path === path && rowType === "file" ? 2 : 1
                            border.color: selected.path === path && rowType === "file"
                                          ? accentColor : rowType === "folder" ? accentColor : theme.colors.border
                            Rectangle {
                                visible: rowType === "file" && selected.path === path
                                width: 3; radius: 2; color: accentColor
                                anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                                anchors.topMargin: 6; anchors.bottomMargin: 6
                            }
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
                                    color: rowType === "folder"
                                           ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.16)
                                           : theme.colors.backgroundAlt
                                    border.color: rowType === "folder" ? accentColor : "transparent"
                                    clip: true
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
                                        text: rowType === "folder" ? (expanded ? "▾  ▰" : "▸  ▰") : kind === "Video" ? "▶" : kind === "Imagen" ? "▧" : "♫"
                                        color: accentColor; font.pixelSize: rowType === "folder" ? 11 : 14
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Text {
                                        Layout.fillWidth: true
                                        text: rowType === "folder" ? folderName : name
                                        color: theme.colors.text; font.pixelSize: rowType === "folder" ? 12 : 11; font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        visible: rowType === "file"
                                        text: category + " · " + (kind === "Imagen" ? sizeLabel : durationLabel + " · " + sizeLabel)
                                        color: theme.colors.textMuted; font.pixelSize: 10; elide: Text.ElideRight
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
                Layout.columnSpan: page.wide ? 8 : 1
                Layout.minimumHeight: 280
                clip: true
                cardColor: theme.colors.surfaceRaised
                border.color: viewState.selectedFolderColor || theme.colors.border
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { Layout.fillWidth: true; text: selected.name || "Selecciona un archivo"; color: theme.colors.text; font.pixelSize: 17; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { text: selected.kind ? selected.kind + " · " + selected.dimensions + " · " + selected.durationLabel + " · " + selected.sizeLabel : "Vista previa y puntos de corte"; color: theme.colors.textMuted; font.pixelSize: 11 }
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
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: selected.kind === "Video" ? (page.dense ? 190 : 240) : selected.kind === "Audio" ? 92 : 230
                        visible: Boolean(selected.kind)
                        RowLayout {
                            anchors.fill: parent
                            spacing: 10
                            visible: selected.kind === "Video"
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 12; color: "#090B0F"; border.color: theme.colors.border; clip: true
                                VideoOutput { id: previewVideo; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
                                Image {
                                    anchors.fill: parent; anchors.margins: 4
                                    visible: player.playbackState === MediaPlayer.StoppedState && Boolean(selected.thumbnailSource)
                                    source: selected.thumbnailSource || ""
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                }
                                RoundButton {
                                    anchors.centerIn: parent
                                    width: 54; height: 54
                                    text: player.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"
                                    onClicked: page.toggleLibraryPreview()
                                    contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 19; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    background: Rectangle { radius: 27; color: "#C0151820"; border.color: theme.colors.primary; border.width: 2 }
                                }
                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    height: 40
                                    color: "#D90B0D12"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        spacing: 8
                                        Text {
                                            text: page.clock(player.position / 1000) + " / " + (selected.durationLabel || "00:00")
                                            color: "white"
                                            font.pixelSize: 11
                                            font.family: "Consolas"
                                            font.weight: Font.DemiBold
                                        }
                                        Item { Layout.fillWidth: true }
                                        XButton {
                                            compact: true; implicitWidth: 34
                                            text: libraryAudio.volume <= 0 ? "M" : "♪"
                                            kind: "ghost"
                                            onClicked: libraryAudio.volume = libraryAudio.volume > 0 ? 0 : 0.75
                                            ToolTip.visible: hovered
                                            ToolTip.text: libraryAudio.volume <= 0 ? "Activar audio" : "Silenciar"
                                        }
                                        Slider {
                                            Layout.preferredWidth: 74
                                            from: 0; to: 1; stepSize: 0.05
                                            value: libraryAudio.volume
                                            onMoved: libraryAudio.volume = value
                                            ToolTip.visible: hovered
                                            ToolTip.text: "Volumen " + Math.round(value * 100) + "%"
                                        }
                                    }
                                }
                            }
                        }
                        Rectangle {
                            anchors.fill: parent
                            visible: selected.kind === "Audio"
                            radius: 12; color: "#090B0F"; border.color: theme.colors.border
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 16; spacing: 14
                                RoundButton {
                                    width: 52; height: 52
                                    text: player.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"
                                    onClicked: player.playbackState === MediaPlayer.PlayingState ? player.pause() : player.play()
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: selected.name || "Audio"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                                    Text { text: "Escucha y selecciona el fragmento en la onda inferior"; color: theme.colors.textMuted; font.pixelSize: 11 }
                                }
                                Text { text: page.clock(player.position / 1000) + " / " + (selected.durationLabel || "00:00"); color: theme.colors.text; font.pixelSize: 12; font.family: "Consolas" }
                                XButton {
                                    compact: true; implicitWidth: 34
                                    text: libraryAudio.volume <= 0 ? "M" : "♪"
                                    kind: "ghost"
                                    onClicked: libraryAudio.volume = libraryAudio.volume > 0 ? 0 : 0.75
                                }
                                Slider {
                                    Layout.preferredWidth: 90
                                    from: 0; to: 1; stepSize: 0.05
                                    value: libraryAudio.volume
                                    onMoved: libraryAudio.volume = value
                                }
                            }
                        }
                        Image {
                            anchors.fill: parent; anchors.margins: 8
                            visible: selected.kind === "Imagen" && Boolean(selected.previewSource)
                            source: visible ? selected.previewSource : ""
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                        }
                    }
                    PremiereTimeline {
                        objectName: "libraryPremiereTimeline"
                        visible: selected.kind === "Video"
                        Layout.fillWidth: true
                        Layout.preferredHeight: page.dense ? 118 : 146
                        duration: Number(selected.duration || 0)
                        inPoint: Number(viewState.clipIn || 0)
                        outPoint: Number(viewState.clipOut || 0)
                        playhead: Math.max(Number(viewState.clipIn || 0), Math.min(Number(viewState.clipOut || 0), player.position / 1000))
                        filmstripSource: viewState.filmstripSource || ""
                        fallbackSource: selected.thumbnailSource || ""
                        waveformSource: viewState.waveformSource || ""
                        filmstripBusy: Boolean(viewState.filmstripBusy)
                        waveformBusy: Boolean(viewState.waveformBusy)
                        onInPointMoved: function(value) {
                            mediaLibraryController.setValue("clipIn", value)
                            player.pause()
                            player.position = value * 1000
                        }
                        onOutPointMoved: function(value) {
                            mediaLibraryController.setValue("clipOut", value)
                            player.pause()
                            player.position = value * 1000
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
                    WaveformTrimmer {
                        id: libraryTrimmer
                        objectName: "mediaClipRange"
                        visible: selected.kind === "Audio"
                        Layout.fillWidth: true
                        Layout.preferredHeight: page.dense ? 174 : 208
                        compact: page.dense
                        waveformSource: viewState.waveformSource || ""
                        busy: Boolean(viewState.waveformBusy)
                        errorText: viewState.waveformError || ""
                        duration: Number(selected.duration || 0)
                        inPoint: Number(viewState.clipIn || 0)
                        outPoint: Number(viewState.clipOut || 0)
                        onInPointMoved: function(value) { mediaLibraryController.setValue("clipIn", value) }
                        onOutPointMoved: function(value) { mediaLibraryController.setValue("clipOut", value) }
                        onRetryRequested: mediaLibraryController.retryWaveform()
                    }
                    RowLayout {
                        visible: selected.kind === "Video" && !page.dense
                        Layout.fillWidth: true
                        Text { text: "IN  " + page.clock(viewState.clipIn); color: theme.colors.text; font.pixelSize: 12; font.weight: Font.Bold; font.family: "Consolas" }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            implicitWidth: clipLength.implicitWidth + 20; implicitHeight: 30; radius: 15
                            color: theme.colors.surfaceSoft; border.color: theme.colors.border
                            Text { id: clipLength; anchors.centerIn: parent; text: "DURACIÓN  " + page.clock(Math.max(0, viewState.clipOut - viewState.clipIn)); color: theme.colors.text; font.pixelSize: 11; font.weight: Font.DemiBold }
                        }
                        Item { Layout.fillWidth: true }
                        Text { text: "OUT  " + page.clock(viewState.clipOut); color: theme.colors.text; font.pixelSize: 12; font.weight: Font.Bold; font.family: "Consolas" }
                    }
                    RowLayout {
                        visible: selected.kind !== "Imagen"
                        Layout.fillWidth: true; spacing: 8
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: "CARPETA DEL RECORTE"; color: theme.colors.textDim; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                            Text { Layout.fillWidth: true; text: viewState.clipOutputDir || ""; color: theme.colors.textMuted; font.pixelSize: 9; elide: Text.ElideMiddle }
                        }
                        XButton {
                            visible: Boolean(viewState.lastClipPath)
                            text: "Abrir carpeta"
                            compact: true
                            kind: "ghost"
                            onClicked: mediaLibraryController.openClipOutput()
                        }
                        ComboBox {
                            visible: selected.kind === "Video"
                            model: ["Video + audio", "Solo video", "Solo audio"]
                            currentIndex: Math.max(0, model.indexOf(viewState.clipMode))
                            onActivated: mediaLibraryController.setValue("clipMode", currentText)
                            implicitWidth: page.dense ? 118 : 135; implicitHeight: 36
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
                visible: false
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.wide ? 4 : 1
                Layout.minimumHeight: 280
                clip: true
                border.color: viewState.selectedFolderColor || theme.colors.border
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
