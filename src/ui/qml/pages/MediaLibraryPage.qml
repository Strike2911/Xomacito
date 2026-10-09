import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../components"

ColumnLayout {
    id: page
    property var viewState: mediaLibraryController.state
    property var selected: viewState.selected || ({})
    property bool hasMedia: Boolean(selected.path)
    property bool temporal: hasMedia && selected.kind !== "Imagen"
    property bool webMode: Boolean(viewState.webMode)
    property string playbackError: ""
    spacing: 10
    onVisibleChanged: if (!visible) inspector.pause()
    function clock(ms) {
        var seconds = Math.floor(ms / 1000)
        return Math.floor(seconds / 60).toString().padStart(2, "0") + ":" + (seconds % 60).toString().padStart(2, "0")
    }
    function sendSelection(timeline) {
        var paths = mediaLibraryController.chosenPaths()
        if (!paths.length && hasMedia) paths = [selected.path]
        premiereController.sendMany(paths, timeline)
    }
    RowLayout {
        Layout.fillWidth: true
        Text { Layout.fillWidth: true; text: "Biblioteca"; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
        XButton { text: "Actualizar"; compact: true; kind: "ghost"; enabled: !page.viewState.busy; onClicked: mediaLibraryController.refresh() }
        XButton { text: premiereController.state.connected ? "Premiere conectado" : "Conectar Premiere"; compact: true; kind: "secondary"; onClicked: mediaLibraryController.connectPremiere() }
    }
    SplitView {
        id: panes; objectName: "mediaBrowserPanes"
        Layout.fillWidth: true; Layout.fillHeight: true; orientation: Qt.Horizontal
        handle: Rectangle {
            implicitWidth: 9; color: "transparent"
            Rectangle { width: 2; height: 32; radius: 1; anchors.centerIn: parent; color: SplitHandle.hovered || SplitHandle.pressed ? theme.colors.accent : theme.colors.border }
        }
        XCard {
            SplitView.preferredWidth: page.width * 0.21; SplitView.minimumWidth: 160
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 10
                Text { text: "Carpetas y colecciones"; Layout.fillWidth: true; elide: Text.ElideRight; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                XButton { Layout.fillWidth: true; text: "+  Indexar carpeta"; compact: true; kind: "secondary"; onClicked: mediaLibraryController.linkFolder() }
                ListView {
                    id: sources; objectName: "librarySources"; Layout.fillWidth: true; Layout.fillHeight: true
                    model: mediaLibraryController.sourceModel; clip: true; spacing: 2
                    ScrollBar.vertical: XScrollBar {}
                    delegate: Rectangle {
                        width: Math.max(0, sources.width - 14); height: model.section ? 38 : 32; radius: 7
                        color: page.viewState.scope === model.key ? theme.colors.surfaceSoft : sourceMouse.containsMouse ? theme.colors.surfaceRaised : "transparent"
                        MouseArea { id: sourceMouse; anchors.fill: parent; hoverEnabled: true; onClicked: mediaLibraryController.setScope(model.key) }
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 5 + model.depth * 10; anchors.rightMargin: 5; spacing: 4
                            Text {
                                text: model.branch ? (model.expanded ? "▾" : "▸") : model.key === "favorites" ? "★" : model.key.indexOf("folder:") === 0 ? "▰" : "◈"
                                color: model.color || theme.colors.accent; font.pixelSize: 13; Layout.preferredWidth: 16
                                MouseArea { anchors.fill: parent; enabled: model.branch; onClicked: mediaLibraryController.toggleSource(model.key) }
                            }
                            Text { Layout.fillWidth: true; text: model.label; elide: Text.ElideRight; color: model.section ? theme.colors.textMuted : theme.colors.text; font.pixelSize: model.section ? 10 : 11; font.weight: model.section ? Font.Bold : Font.Normal }
                            Text { visible: !model.section && model.key.indexOf("web:") !== 0; text: model.count; color: theme.colors.textMuted; font.pixelSize: 11 }
                        }
                    }
                }
                XButton { Layout.fillWidth: true; text: "+  Nueva colección"; compact: true; kind: "ghost"; onClicked: mediaLibraryController.createCollection() }
                XButton { Layout.fillWidth: true; visible: page.viewState.scope.indexOf("collection:") === 0 || (page.viewState.scope.indexOf("folder:") === 0 && page.viewState.scope !== "folder:" + page.viewState.rootPath); text: "Quitar de biblioteca"; compact: true; kind: "ghost"; onClicked: mediaLibraryController.removeSource(); ToolTip.visible: hovered; ToolTip.text: "Conserva los archivos originales" }
                Text { Layout.fillWidth: true; text: page.viewState.itemCount + " archivos indexados"; color: theme.colors.textDim; font.pixelSize: 10 }
                XButton { Layout.fillWidth: true; text: "Carpeta de descargas"; compact: true; kind: "ghost"; enabled: !page.viewState.busy; onClicked: mediaLibraryController.chooseLibraryFolder() }
            }
        }
        XCard {
            SplitView.fillWidth: true; SplitView.minimumWidth: 255
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: page.viewState.scopeTitle; elide: Text.ElideRight; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                    XButton { text: page.viewState.viewMode === "grid" ? "Lista" : "Cuadrícula"; implicitWidth: 92; compact: true; kind: "ghost"; onClicked: mediaLibraryController.setBrowserValue("viewMode", page.viewState.viewMode === "grid" ? "list" : "grid"); ToolTip.visible: hovered; ToolTip.text: "Alternar lista / cuadrícula" }
                }
                XTextField { objectName: "librarySearch"; Layout.fillWidth: true; placeholderText: page.webMode ? "Buscar en " + page.viewState.webProvider + "…" : "Buscar medios…"; text: page.viewState.searchText; onTextEdited: mediaLibraryController.setSearchText(text); onAccepted: if (page.webMode) mediaLibraryController.searchWeb(1) }
                RowLayout {
                    visible: page.webMode; Layout.fillWidth: true; spacing: 5
                    XButton { Layout.fillWidth: true; text: page.viewState.webBusy ? "Buscando…" : "Buscar"; compact: true; enabled: !page.viewState.webBusy && !page.viewState.webNeedsKey; onClicked: mediaLibraryController.searchWeb(1) }
                    XButton { visible: ["Freesound", "Pixabay", "Pexels"].indexOf(page.viewState.webProvider) >= 0; text: "Clave API"; compact: true; kind: "secondary"; onClicked: mediaLibraryController.configureWebKey() }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 4
                    XComboBox { Layout.fillWidth: true; compact: true; model: ["Todos", "Imagen", "Video", "Audio"]; currentIndex: model.indexOf(page.viewState.kindFilter); onActivated: mediaLibraryController.setBrowserValue("kindFilter", currentText) }
                    XComboBox { visible: !page.webMode; Layout.fillWidth: true; compact: true; model: ["Nombre", "Tamaño", "Duración", "Tipo"]; onActivated: mediaLibraryController.setBrowserValue("sortBy", ["name", "sizeBytes", "duration", "extension"][currentIndex]) }
                    XButton { visible: !page.webMode; text: page.viewState.sortDescending ? "↓" : "↑"; compact: true; implicitWidth: 32; leftPadding: 6; rightPadding: 6; kind: "ghost"; onClicked: mediaLibraryController.setBrowserValue("sortDescending", !page.viewState.sortDescending) }
                }
                RowLayout {
                    visible: page.viewState.viewMode === "list"; Layout.fillWidth: true
                    Text { text: "NOMBRE"; Layout.fillWidth: true; color: theme.colors.textDim; font.pixelSize: 9 }
                    Text { text: "TIPO / TAMAÑO"; color: theme.colors.textDim; font.pixelSize: 9 }
                }
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    GridView {
                        id: grid; objectName: "libraryGrid"; anchors.fill: parent; visible: page.viewState.viewMode === "grid"
                        clip: true; model: mediaLibraryController.browserModel
                        cellWidth: width / Math.max(1, Math.floor(width / page.viewState.tileSize)); cellHeight: cellWidth * 0.72 + 52
                        ScrollBar.vertical: XScrollBar {}
                        delegate: mediaDelegate
                        Keys.onPressed: function(event) { if (event.key === Qt.Key_A && event.modifiers & Qt.ControlModifier) { mediaLibraryController.selectAllVisible(); event.accepted = true } }
                    }
                    ListView {
                        id: list; objectName: "libraryFiles"; anchors.fill: parent; visible: page.viewState.viewMode === "list"
                        clip: true; spacing: 4; model: mediaLibraryController.browserModel; delegate: mediaDelegate
                        ScrollBar.vertical: XScrollBar {}
                        Keys.onPressed: function(event) { if (event.key === Qt.Key_A && event.modifiers & Qt.ControlModifier) { mediaLibraryController.selectAllVisible(); event.accepted = true } }
                    }
                    Column {
                        anchors.centerIn: parent; width: parent.width - 24; spacing: 9; visible: grid.count === 0
                        Text { width: parent.width; text: page.webMode ? page.viewState.webProvider : page.viewState.busy ? "Leyendo tus medios…" : "Sin medios"; color: theme.colors.text; font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                        Text { width: parent.width; text: page.webMode ? (page.viewState.webNeedsKey ? "Conecta tu clave API para buscar en este catálogo." : page.viewState.webStatus) : page.viewState.itemCount ? "No hay archivos con estos filtros." : "Indexa una carpeta o arrastra tus archivos aquí."; color: theme.colors.textMuted; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                    }
                    DropArea {
                        anchors.fill: parent
                        onDropped: function(drop) { if (drop.hasUrls) { mediaLibraryController.linkDroppedPaths(drop.urls); drop.acceptProposedAction() } }
                        Rectangle { anchors.fill: parent; radius: 12; visible: parent.containsDrag; color: Qt.rgba(0.1, 0.6, 0.7, 0.18); border.color: theme.colors.accent }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: page.viewState.visibleCount + " medios · " + page.viewState.selectedCount + " seleccionados"; color: theme.colors.textDim; font.pixelSize: 9; Layout.fillWidth: true }
                    XSlider { visible: page.viewState.viewMode === "grid"; Layout.preferredWidth: 75; from: 90; to: 220; value: page.viewState.tileSize; onMoved: mediaLibraryController.setBrowserValue("tileSize", value) }
                }
                RowLayout {
                    visible: page.webMode; Layout.fillWidth: true
                    XButton { text: "Anterior"; compact: true; kind: "ghost"; enabled: page.viewState.webPage > 1 && !page.viewState.webBusy; onClicked: mediaLibraryController.searchWeb(page.viewState.webPage - 1) }
                    Text { text: page.viewState.webPage; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; color: theme.colors.textDim }
                    XButton { text: "Siguiente"; compact: true; kind: "ghost"; enabled: grid.count > 0 && !page.viewState.webBusy; onClicked: mediaLibraryController.searchWeb(page.viewState.webPage + 1) }
                }
                XButton {
                    visible: !page.webMode
                    Layout.fillWidth: true; text: "Organizar selección  ···"; compact: true; kind: "secondary"; enabled: page.viewState.selectedCount > 0
                    onClicked: selectionMenu.open()
                    Menu {
                        id: selectionMenu
                        MenuItem { text: "Nueva colección con la selección"; onTriggered: mediaLibraryController.createCollection() }
                        Instantiator {
                            model: page.viewState.collections || []
                            delegate: MenuItem { text: "Añadir a " + modelData.name; onTriggered: mediaLibraryController.addToCollection(modelData.key) }
                            onObjectAdded: function(index, object) { selectionMenu.insertItem(index + 1, object) }
                            onObjectRemoved: function(index, object) { selectionMenu.removeItem(object) }
                        }
                        MenuItem { text: "Quitar de esta colección"; enabled: page.viewState.scope.indexOf("collection:") === 0; onTriggered: mediaLibraryController.removeFromCollection() }
                        MenuItem { text: "Copiar rutas"; onTriggered: mediaLibraryController.copySelectedPath() }
                        MenuItem { text: "Enviar selección a Premiere"; onTriggered: page.sendSelection(false) }
                    }
                }
            }
        }
        XCard {
            SplitView.preferredWidth: page.width * 0.34; SplitView.minimumWidth: 275
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                Text { text: "Vista previa y detalles"; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                MediaPreview {
                    id: inspector; compactControls: true; objectName: "libraryInteractivePreview"
                    Layout.fillWidth: true; Layout.preferredHeight: Math.min(width * 9 / 16 + 91, Math.max(150, page.height * 0.44)); Layout.minimumHeight: 140
                    playerObjectName: "libraryPreviewPlayer"
                    active: page.visible
                    source: page.hasMedia ? page.selected.previewSource || "" : ""
                    kind: page.selected.kind || "Video"
                    title: page.selected.name || ""
                    poster: page.selected.thumbnailSource || ""
                    waveform: page.webMode ? (page.selected.kind === "Audio" ? page.selected.thumbnailSource || "" : "") : page.viewState.waveformSource || ""
                    onRetryRequested: reload()
                }
                ScrollView {
                    id: details; objectName: "libraryMetadata"; Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 60; contentWidth: availableWidth; clip: true
                    ScrollBar.vertical: XScrollBar {}
                    ColumnLayout {
                        width: Math.max(0, details.availableWidth - 14); spacing: 5
                        Text { Layout.fillWidth: true; text: page.selected.name || "Información técnica"; color: theme.colors.text; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.WrapAnywhere }
                        Text { visible: !page.hasMedia; Layout.fillWidth: true; text: "Explora una carpeta o colección. Usa Ctrl / Shift para seleccionar varios archivos y arrástralos a tu editor."; color: theme.colors.textDim; font.pixelSize: 11; wrapMode: Text.WordWrap }
                        Repeater {
                            model: page.webMode && page.hasMedia ? [["Origen", page.selected.provider], ["Autor", page.selected.creator], ["Licencia", page.selected.license], ["Resolución", page.selected.dimensions], ["Duración", page.selected.durationLabel]] : page.hasMedia ? [
                                ["Formato", page.selected.formatLabel], ["Duración", page.selected.durationLabel],
                                ["Tamaño", page.selected.sizeLabel], ["Resolución", page.selected.dimensions],
                                ["Video", page.selected.videoCodec], ["Fotogramas", page.selected.frameRate],
                                ["Audio", page.selected.audioCodec], ["Muestreo", page.selected.sampleRate],
                                ["Canales", page.selected.channels], ["Bitrate", page.selected.totalBitrate],
                                ["Modificado", page.selected.modified]] : []
                            delegate: RowLayout {
                                Layout.fillWidth: true; spacing: 10
                                Text { text: modelData[0]; Layout.preferredWidth: 82; color: theme.colors.textMuted; font.pixelSize: 11 }
                                Text { text: String(modelData[1] || "—"); Layout.fillWidth: true; color: theme.colors.text; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
                            }
                        }
                        Text { visible: page.hasMedia; text: page.selected.metadataSummary || ""; Layout.fillWidth: true; color: theme.colors.textDim; font.pixelSize: 10; wrapMode: Text.WordWrap }
                        Text { visible: page.hasMedia; text: page.webMode ? page.selected.pageUrl || "" : page.selected.path || ""; Layout.fillWidth: true; color: theme.colors.textDim; font.pixelSize: 9; wrapMode: Text.WrapAnywhere }
                    }
                }
                GridLayout {
                    objectName: "libraryLocalActions"
                    columns: 2; rowSpacing: 6; columnSpacing: 6
                    visible: page.hasMedia && !page.webMode; Layout.fillWidth: true
                    XButton { Layout.fillWidth: true; Layout.preferredWidth: 1; text: "Ubicación"; implicitHeight: 30; compact: true; kind: "ghost"; onClicked: mediaLibraryController.openSelected() }
                    XButton { Layout.fillWidth: true; Layout.preferredWidth: 1; text: "Crear subclip"; implicitHeight: 30; compact: true; kind: "ghost"; enabled: page.temporal; onClicked: { inspector.pause(); trimDialog.open() } }
                    XButton { Layout.fillWidth: true; Layout.preferredWidth: 1; text: "A Premiere"; implicitHeight: 32; compact: true; onClicked: page.sendSelection(false) }
                    XButton { Layout.fillWidth: true; Layout.preferredWidth: 1; text: "Al cabezal"; implicitHeight: 32; compact: true; kind: "secondary"; onClicked: premiereController.send(page.selected.path, true) }
                }
                RowLayout {
                    visible: page.hasMedia && page.webMode; Layout.fillWidth: true; spacing: 5
                    XButton { Layout.fillWidth: true; text: "Ver origen"; compact: true; kind: "ghost"; onClicked: mediaLibraryController.openWebSource() }
                    XButton { Layout.fillWidth: true; text: "Copiar créditos"; compact: true; kind: "ghost"; onClicked: mediaLibraryController.copyWebCredits() }
                }
                RowLayout {
                    visible: page.hasMedia && page.webMode; Layout.fillWidth: true; spacing: 5
                    XButton { Layout.fillWidth: true; text: page.viewState.webDownloading ? "Cancelar" : page.selected.provider === "Freesound" ? "Bajar previa MP3" : "Descargar"; compact: true; onClicked: page.viewState.webDownloading ? mediaLibraryController.cancelWebDownload() : mediaLibraryController.downloadWeb(false) }
                    XButton { text: "A Premiere"; compact: true; kind: "secondary"; enabled: !page.viewState.webDownloading; onClicked: page.viewState.webFile ? premiereController.send(page.viewState.webFile, false) : mediaLibraryController.downloadWeb(true) }
                }
            }
        }
    }
    Text { Layout.fillWidth: true; text: page.webMode ? page.viewState.webStatus : page.viewState.busy ? page.viewState.status : premiereController.state.pending ? premiereController.state.status : page.viewState.visibleCount + " medios"; elide: Text.ElideRight; color: theme.colors.textDim; font.pixelSize: 10 }
    Component {
        id: mediaDelegate
        Rectangle {
            id: tile
            property bool gridMode: GridView.view !== null
            width: gridMode ? grid.cellWidth - 7 : list.width - 14; height: gridMode ? grid.cellHeight - 7 : 58
            radius: 9; color: model.chosen ? theme.colors.surfaceSoft : fileMouse.containsMouse ? theme.colors.surfaceRaised : "transparent"
            border.color: model.chosen ? theme.colors.accent : "transparent"
            Rectangle {
                id: thumb
                x: 6; y: 6; width: tile.gridMode ? parent.width - 12 : 46; height: tile.gridMode ? parent.height - 51 : 46
                radius: 6; color: theme.colors.surfaceRaised; clip: true
                Image { anchors.fill: parent; source: model.thumbnailSource || ""; fillMode: Image.PreserveAspectFit; asynchronous: true; sourceSize.width: 320 }
                Text { anchors.centerIn: parent; visible: !model.thumbnailSource; text: model.kind === "Audio" ? "♫" : "◈"; color: theme.colors.accent; font.pixelSize: 22 }
            }
            Column {
                x: tile.gridMode ? 8 : 60; y: tile.gridMode ? thumb.y + thumb.height + 6 : 10
                width: parent.width - x - 8; spacing: 4
                Text { width: parent.width - (tile.gridMode ? 0 : 85); text: model.name; elide: Text.ElideRight; color: theme.colors.text; font.pixelSize: 11 }
                Text { width: parent.width - (tile.gridMode ? 0 : 85); text: tile.gridMode ? model.extension + " · " + (model.kind === "Imagen" ? model.sizeLabel : model.durationLabel) : model.durationLabel; elide: Text.ElideRight; color: theme.colors.textDim; font.pixelSize: 9 }
            }
            Text { visible: !tile.gridMode; anchors.right: parent.right; anchors.rightMargin: 8; y: 13; width: 78; text: model.extension + "\n" + model.sizeLabel; horizontalAlignment: Text.AlignRight; color: theme.colors.textDim; font.pixelSize: 9; elide: Text.ElideRight }
            MouseArea {
                id: fileMouse; anchors.fill: parent; hoverEnabled: true
                property point downAt
                onPressed: function(mouse) {
                    downAt = Qt.point(mouse.x, mouse.y)
                    if (!model.chosen || mouse.modifiers) mediaLibraryController.chooseItem(model.path, Boolean(mouse.modifiers & Qt.ControlModifier), Boolean(mouse.modifiers & Qt.ShiftModifier))
                    tile.gridMode ? grid.forceActiveFocus() : list.forceActiveFocus()
                }
                onClicked: function(mouse) { if (!mouse.modifiers) mediaLibraryController.chooseItem(model.path, false, false) }
                onDoubleClicked: { mediaLibraryController.chooseItem(model.path, false, false); if (page.temporal) inspector.play() }
                onPositionChanged: function(mouse) { if (pressed && Math.abs(mouse.x - downAt.x) + Math.abs(mouse.y - downAt.y) > 14) { mediaLibraryController.startDrag() } }
            }
            ToolButton {
                anchors.right: parent.right; anchors.top: parent.top; width: 28; height: 28
                visible: !page.webMode && (model.isFavorite || fileMouse.containsMouse || hovered)
                onClicked: mediaLibraryController.toggleFavorite(model.path)
                contentItem: Text { text: model.isFavorite ? "★" : "☆"; color: theme.colors.accent; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter }
                background: Rectangle { radius: 6; color: theme.colors.surfaceRaised }
            }
        }
    }
    Popup {
        id: trimDialog; anchors.centerIn: Overlay.overlay; width: Math.min(820, page.width - 30); height: 390; modal: true; padding: 18
        background: Rectangle { color: theme.colors.surface; radius: 18; border.color: theme.colors.border }
        ColumnLayout {
            anchors.fill: parent; spacing: 12
            Text { text: "Crear subclip · " + (page.selected.name || ""); Layout.fillWidth: true; elide: Text.ElideRight; color: theme.colors.text; font.pixelSize: 17 }
            PremiereTimeline {
                id: timeline; Layout.fillWidth: true; Layout.fillHeight: true
                duration: page.selected.duration || 0; inPoint: page.viewState.clipIn; outPoint: page.viewState.clipOut; playhead: inspector.mediaPlayer.position / 1000
                filmstripSource: page.viewState.filmstripSource; waveformSource: page.viewState.waveformSource; fallbackSource: page.selected.thumbnailSource || ""
                filmstripBusy: page.viewState.filmstripBusy; waveformBusy: page.viewState.waveformBusy
                onSeekRequested: function(value) { inspector.pause(); inspector.mediaPlayer.position = value * 1000 }
                onInPointMoved: function(value) { mediaLibraryController.setValue("clipIn", value); inspector.mediaPlayer.position = value * 1000 }
                onOutPointMoved: function(value) { mediaLibraryController.setValue("clipOut", value); inspector.mediaPlayer.position = value * 1000 }
            }
            XComboBox { Layout.fillWidth: true; model: page.selected.kind === "Audio" ? ["Solo audio"] : ["Video + audio", "Solo video", "Solo audio"]; currentIndex: Math.max(0, model.indexOf(page.viewState.clipMode)); onActivated: mediaLibraryController.setValue("clipMode", currentText) }
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: page.viewState.busy ? page.viewState.status : page.viewState.lastClipPath ? "Subclip guardado en tu biblioteca." : "El original se conserva."; color: theme.colors.textDim; font.pixelSize: 11; wrapMode: Text.WordWrap }
                XButton { text: "Guardar"; compact: true; enabled: !page.viewState.busy; onClicked: mediaLibraryController.createClip() }
                XButton { text: "Cerrar"; compact: true; kind: "ghost"; onClicked: trimDialog.close() }
            }
        }
    }
}
