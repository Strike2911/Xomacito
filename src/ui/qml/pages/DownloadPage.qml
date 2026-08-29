import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../components"

Item {
    id: page
    property var viewState: downloadController.state
    property var options: downloadController.options
    property bool denseLayout: height < 640
    property bool trimUserMuted: false
    property real trimPendingScrubSeconds: -1

    MediaPlayer {
        id: trimPlayer
        objectName: "downloadTrimPreviewPlayer"
        source: trimPopup.opened
                && (Boolean(viewState.localFile) || Boolean(viewState.trimPreviewFallback))
                ? (viewState.trimPreviewSource || "") : ""
        audioOutput: AudioOutput {
            id: trimAudio
            volume: 0.32
            muted: page.trimUserMuted
        }
        videoOutput: trimPreviewVideo
        onSourceChanged: trimPopup.mediaLoadSeekPending = Boolean(source)
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.LoadedMedia || mediaStatus === MediaPlayer.BufferedMedia) {
                trimPopup.playbackError = ""
                if (trimPopup.mediaLoadSeekPending) {
                    trimPopup.mediaLoadSeekPending = false
                    position = Math.max(0, trimPopup.pendingSeekSeconds - Number(viewState.trimPreviewOffset || 0)) * 1000
                }
            }
        }
        onErrorOccurred: function(_error, errorString) {
            if (!trimPopup.fallbackRequested && !viewState.localFile) {
                trimPopup.fallbackRequested = true
                trimPopup.playbackError = "Preparando una vista previa compatible…"
                downloadController.prepareFallbackTrimPreview()
            } else if (viewState.trimPreviewBusy) {
                trimPopup.playbackError = "Preparando una vista previa compatible…"
            } else {
                trimPopup.playbackError = errorString || "No se pudo abrir esta vista previa."
            }
        }
        onPositionChanged: {
            if (!trimPopup.opened || playbackState !== MediaPlayer.PlayingState)
                return
            var offset = Number(viewState.trimPreviewOffset || 0)
            var globalPosition = position / 1000 + offset
            var endSeconds = Math.max(0, page.clockSeconds(options.endTime))
            if (endSeconds > 0 && globalPosition >= endSeconds) {
                pause()
                position = Math.max(0, endSeconds - offset) * 1000
                trimPopup.pendingSeekSeconds = endSeconds
            }
        }
    }

    Timer {
        id: trimScrubSeekTimer
        interval: 24
        repeat: false
        onTriggered: {
            if (page.trimPendingScrubSeconds < 0)
                return
            var target = page.trimPendingScrubSeconds
            page.trimPendingScrubSeconds = -1
            trimPlayer.position = Math.max(0, target - Number(viewState.trimPreviewOffset || 0)) * 1000
        }
    }

    function clockText(seconds) {
        var total = Math.max(0, Math.floor(Number(seconds) || 0))
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        var secs = total % 60
        return (hours < 10 ? "0" : "") + hours + ":" +
               (minutes < 10 ? "0" : "") + minutes + ":" +
               (secs < 10 ? "0" : "") + secs
    }

    function clockSeconds(value) {
        var match = /^(\d{1,3}):([0-5]\d):([0-5]\d(?:\.\d{1,3})?)$/.exec(String(value).trim())
        if (!match)
            return -1
        return Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3])
    }

    function preciseClockText(seconds) {
        var total = Math.max(0, Number(seconds) || 0)
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        var secs = total % 60
        var secsText = secs.toFixed(2)
        if (secs < 10)
            secsText = "0" + secsText
        return (hours < 10 ? "0" : "") + hours + ":" +
               (minutes < 10 ? "0" : "") + minutes + ":" + secsText
    }

    function setTrimBoundary(optionName, seconds) {
        var bounded = Math.max(0, Math.min(Number(viewState.duration || 0), Number(seconds) || 0))
        downloadController.setOption(optionName, page.preciseClockText(bounded))
        trimPopup.pendingSeekSeconds = bounded
        trimPopup.previewActivated = true
        if (trimPlayer.playbackState === MediaPlayer.PlayingState)
            trimPlayer.pause()
        trimPlayer.position = Math.max(0, bounded - Number(viewState.trimPreviewOffset || 0)) * 1000
    }

    function seekTrimPreview(seconds) {
        var start = Math.max(0, page.clockSeconds(options.startTime))
        var end = Math.max(start, page.clockSeconds(options.endTime))
        var bounded = Math.max(start, Math.min(end, Number(seconds) || 0))
        trimPopup.pendingSeekSeconds = bounded
        trimPopup.previewActivated = true
        trimPlaybackStartDelay.stop()
        if (trimPlayer.playbackState === MediaPlayer.PlayingState)
            trimPlayer.pause()
        page.trimPendingScrubSeconds = bounded
        if (!trimScrubSeekTimer.running)
            trimScrubSeekTimer.start()
    }

    function toggleTrimPreview() {
        if (trimPlayer.playbackState === MediaPlayer.PlayingState) {
            trimPlaybackStartDelay.stop()
            trimPlayer.pause()
            return
        }
        var offsetMs = Number(viewState.trimPreviewOffset || 0) * 1000
        var startMs = Math.max(0, page.clockSeconds(options.startTime) * 1000 - offsetMs)
        var endMs = Math.max(startMs, page.clockSeconds(options.endTime) * 1000 - offsetMs)
        trimPopup.previewActivated = true
        if (trimPlayer.position < startMs || trimPlayer.position >= endMs) {
            trimPlayer.pause()
            trimPlayer.position = startMs
            trimPopup.pendingSeekSeconds = page.clockSeconds(options.startTime)
            trimPopup.playbackSeekRetries = 0
            trimPlaybackStartDelay.restart()
            return
        }
        trimPlayer.play()
    }

    function fragmentMessage() {
        if (!options.fragmentEnabled)
            return "Activa el recorte para elegir un fragmento."
        var start = clockSeconds(options.startTime)
        var end = clockSeconds(options.endTime)
        if (start < 0 || end < 0)
            return "Revisa el formato: usa HH:MM:SS."
        if (end <= start)
            return "El final debe ser posterior al inicio."
        if (viewState.duration > 0 && end > viewState.duration + 0.75)
            return "El final supera la duración del archivo."
        return "Se guardará " + clockText(end - start) + " · de " +
               options.startTime + " a " + options.endTime
    }

    function fragmentReady() {
        if (!options.fragmentEnabled)
            return false
        var start = clockSeconds(options.startTime)
        var end = clockSeconds(options.endTime)
        return start >= 0 && end > start &&
               (viewState.duration <= 0 || end <= viewState.duration + 0.75)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: page.denseLayout || settingsController.state.compactMode ? 8 : 12

        SectionTitle {
            Layout.fillWidth: true
            eyebrow: "DESCARGA INTELIGENTE"
            title: "Pega. Analiza. Descarga."
            description: "Video, audio, miniaturas y subtítulos con formatos listos para editar."
            number: "01"
            compact: true
        }

        XCard {
            id: sourceCard
            objectName: "downloadSourceCard"
            Layout.fillWidth: true
            implicitHeight: sourceLayout.implicitHeight + (page.denseLayout ? 20 : 26)
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                id: sourceLayout
                anchors.fill: parent
                anchors.margins: page.denseLayout ? 10 : 13
                spacing: page.denseLayout ? 8 : 10
                XTextField {
                    objectName: "downloadUrlField"
                    Layout.fillWidth: true
                    compact: page.denseLayout
                    placeholderText: "Pega un enlace de YouTube, Vimeo, TikTok, Instagram…"
                    text: viewState.url
                    enabled: !viewState.busy && !viewState.localFile
                    onTextEdited: downloadController.setValue("url", text)
                    onAccepted: downloadController.analyze()
                }
                XButton { compact: page.denseLayout; text: "Analizar"; leadingText: "↘"; enabled: !viewState.busy && viewState.url.length > 3; onClicked: downloadController.analyze() }
                XButton { compact: page.denseLayout; text: "Importar"; kind: "secondary"; onClicked: downloadController.chooseLocalFile() }
                XButton { compact: page.denseLayout; text: "Limpiar"; kind: "ghost"; visible: viewState.analyzed || viewState.localFile; onClicked: downloadController.resetSource() }
            }
        }

            GridLayout {
                id: primaryGrid
                objectName: "downloadPrimaryGrid"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                columns: page.width >= 900 ? 2 : 1
                columnSpacing: page.denseLayout ? 10 : 14
                rowSpacing: page.denseLayout ? 10 : 14

                XCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
                    implicitHeight: 0
                    Layout.preferredWidth: 380
                    ColumnLayout {
                        id: previewContent
                        anchors.fill: parent
                        anchors.margins: page.denseLayout ? 10 : 14
                        spacing: page.denseLayout ? 7 : 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: viewState.analyzed ? "ENLACE ANALIZADO ✓" : "VISTA PREVIA"; color: viewState.analyzed ? theme.colors.accent : theme.colors.primary; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                            Item { Layout.fillWidth: true }
                            Text { text: viewState.estimatedSize; color: theme.colors.textMuted; font.pixelSize: 11 }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: page.denseLayout ? 108 : 130
                            radius: 14
                            color: theme.colors.backgroundAlt
                            border.color: theme.colors.border
                            clip: true
                            Image { anchors.fill: parent; anchors.margins: 1; source: viewState.thumbnailSource; fillMode: Image.PreserveAspectFit; asynchronous: true; cache: true }
                            Column {
                                anchors.centerIn: parent
                                visible: !viewState.thumbnailSource
                                spacing: 8
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "▷"; color: theme.colors.primary; font.pixelSize: page.denseLayout ? 25 : 30 }
                                Text { text: viewState.localFile ? "Archivo local" : "La miniatura aparecerá aquí"; color: theme.colors.textMuted; font.pixelSize: page.denseLayout ? 10 : 11 }
                            }
                        }
                        Text { Layout.fillWidth: true; text: viewState.title || "Sin analizar"; color: theme.colors.text; font.pixelSize: page.denseLayout ? 13 : 15; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        RowLayout {
                            Layout.fillWidth: true
                            XButton { Layout.fillWidth: true; compact: true; text: "Guardar miniatura"; kind: "secondary"; enabled: !!viewState.thumbnailSource; onClicked: downloadController.saveThumbnail() }
                            XButton {
                                objectName: "openTrimButton"
                                Layout.fillWidth: true
                                compact: true
                                text: options.fragmentEnabled ? "Recorte ✓" : "Recortar"
                                kind: options.fragmentEnabled ? "success" : "secondary"
                                visible: !viewState.imagePost
                                enabled: viewState.analyzed && viewState.duration > 0
                                onClicked: trimPopup.open()
                            }
                            XButton { Layout.fillWidth: true; compact: true; text: "Enviar a cola"; kind: "secondary"; enabled: viewState.url.length > 0; onClicked: downloadController.sendToQueue() }
                        }
                        Text {
                            visible: options.fragmentEnabled
                            Layout.fillWidth: true
                            text: "Fragmento activo · " + options.startTime + " → " + options.endTime
                            color: theme.colors.success
                            font.pixelSize: 9
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }
                    }
                }

                XCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
                    implicitHeight: 0
                    Layout.preferredWidth: 660
                    ColumnLayout {
                        id: outputContent
                        anchors.fill: parent
                        anchors.margins: page.denseLayout ? 10 : 14
                        spacing: page.denseLayout ? 7 : 10
                        SectionTitle { Layout.fillWidth: true; compact: true; eyebrow: "SALIDA"; title: viewState.localFile ? "Prepara tu archivo" : "Elige cómo descargar"; description: viewState.imagePost ? "Publicación detectada como imagen." : "El motor selecciona combinaciones compatibles y conserva la calidad." }
                        LabeledControl {
                            Layout.fillWidth: true; compact: page.denseLayout; label: "Título de salida"
                            XTextField { Layout.fillWidth: true; compact: page.denseLayout; text: viewState.title; onEditingFinished: downloadController.setValue("title", text) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            LabeledControl {
                                Layout.fillWidth: true; compact: page.denseLayout; label: "Modo"
                                XComboBox {
                                    id: modeCombo
                                    objectName: "downloadModeCombo"
                                    Layout.fillWidth: true
                                    compact: page.denseLayout
                                    model: viewState.imagePost ? ["Imágenes"] : ["Video+Audio", "Solo Audio"]
                                    currentIndex: viewState.imagePost ? 0 : (viewState.mode === "Solo Audio" ? 1 : 0)
                                    onActivated: downloadController.setValue("mode", currentText)
                                    Connections {
                                        target: downloadController
                                        function onStateChanged() {
                                            modeCombo.currentIndex = viewState.imagePost ? 0 : (viewState.mode === "Solo Audio" ? 1 : 0)
                                        }
                                    }
                                }
                            }
                            LabeledControl {
                                visible: !viewState.imagePost
                                Layout.fillWidth: true; compact: page.denseLayout; label: viewState.mode === "Solo Audio" ? "Calidad de audio" : "Calidad de video"
                                XComboBox { Layout.fillWidth: true; compact: page.denseLayout; model: viewState.mode === "Solo Audio" ? downloadController.audioChoices : downloadController.videoChoices; currentIndex: Math.max(0, find(viewState.mode === "Solo Audio" ? viewState.selectedAudio : viewState.selectedVideo)); onActivated: downloadController.setValue(viewState.mode === "Solo Audio" ? "selectedAudio" : "selectedVideo", currentText) }
                            }
                        }
                        LabeledControl {
                            visible: !viewState.imagePost
                            Layout.fillWidth: true; compact: page.denseLayout; label: "Preset de conversión"
                            XComboBox { Layout.fillWidth: true; compact: page.denseLayout; model: viewState.mode === "Solo Audio" ? presetStore.audioPresets : presetStore.videoPresets; currentIndex: Math.max(0, find(viewState.preset)); onActivated: downloadController.setValue("preset", currentText) }
                        }
                        LabeledControl {
                            visible: viewState.imagePost
                            Layout.fillWidth: true
                            compact: page.denseLayout
                            label: "Formato de imagen"
                            XComboBox {
                                id: imageFormatCombo
                                Layout.fillWidth: true
                                compact: page.denseLayout
                                model: ["Original", "JPEG", "JPG", "PNG", "WEBP"]
                                currentIndex: Math.max(0, find(viewState.imageFormat || "Original"))
                                onActivated: downloadController.setValue("imageFormat", currentText)
                                Connections {
                                    target: downloadController
                                    function onStateChanged() {
                                        imageFormatCombo.currentIndex = Math.max(0, imageFormatCombo.find(viewState.imageFormat || "Original"))
                                    }
                                }
                            }
                        }
                        RowLayout {
                            visible: !viewState.imagePost
                            Layout.fillWidth: true
                            spacing: 12
                            XSwitch { text: "Aplicar preset"; checked: options.applyPreset; onToggled: downloadController.setOption("applyPreset", checked) }
                            XSwitch { text: "Mantener original"; checked: options.keepOriginal; enabled: options.applyPreset; onToggled: downloadController.setOption("keepOriginal", checked) }
                            XSwitch {
                                objectName: "embedAudioCoverSwitch"
                                visible: viewState.mode === "Solo Audio" && !viewState.localFile
                                text: "Incluir portada"
                                enabled: options.applyPreset && (viewState.preset.indexOf("MP3") >= 0 || viewState.preset.indexOf("AAC") >= 0)
                                checked: options.embedThumbnail
                                onToggled: downloadController.setOption("embedThumbnail", checked)
                                ToolTip.visible: hovered && !enabled
                                ToolTip.text: "Activa un preset MP3 o AAC para incluir la portada."
                            }
                            Item { Layout.fillWidth: true }
                            XButton { objectName: "advancedToolsButton"; compact: true; text: "Ajustes avanzados"; kind: "secondary"; onClicked: advanced.open() }
                        }
                        Text {
                            visible: viewState.imagePost
                            Layout.fillWidth: true
                            text: viewState.imageCount > 1
                                ? viewState.imageCount + " imágenes detectadas · se descargarán todas"
                                : "1 imagen detectada · lista para descargar"
                            color: theme.colors.success
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }

            Popup {
                id: trimPopup
                objectName: "downloadTrimPopup"
                property bool previousEnabled: false
                property string previousStart: "00:00:00"
                property string previousEnd: ""
                property bool previewActivated: false
                property real pendingSeekSeconds: 0
                property string playbackError: ""
                property bool fallbackRequested: false
                property bool mediaLoadSeekPending: false
                property int playbackSeekRetries: 0
                parent: Overlay.overlay
                x: Math.round((parent.width - width) / 2)
                y: Math.round((parent.height - height) / 2)
                width: Math.min(1050, parent.width - 24)
                height: Math.min(800, parent.height - 24)
                padding: 18
                modal: true
                focus: true
                closePolicy: Popup.CloseOnEscape
                background: Rectangle { radius: 18; color: theme.colors.surfaceRaised; border.color: "#6F6AD6"; border.width: 1 }
                onAboutToShow: {
                    previousEnabled = Boolean(options.fragmentEnabled)
                    previousStart = options.startTime
                    previousEnd = options.endTime
                    downloadController.setOption("fragmentEnabled", true)
                    if (page.clockSeconds(options.endTime) <= 0)
                        downloadController.setOption("endTime", page.clockText(viewState.duration))
                    trimWaveformDelay.restart()
                    trimFilmstripDelay.restart()
                    previewActivated = false
                    playbackError = ""
                    fallbackRequested = false
                    mediaLoadSeekPending = false
                    playbackSeekRetries = 0
                    pendingSeekSeconds = Math.max(0, page.clockSeconds(options.startTime))
                    trimPlayer.stop()
                    trimPlayer.position = pendingSeekSeconds * 1000
                    if (!viewState.localFile && viewState.hasVideo) {
                        fallbackRequested = true
                        playbackError = "Preparando una vista previa estable…"
                        downloadController.prepareFallbackTrimPreview()
                    }
                }
                onClosed: {
                    trimPlaybackStartDelay.stop()
                    trimScrubSeekTimer.stop()
                    page.trimPendingScrubSeconds = -1
                    trimPlayer.stop()
                    trimWaveformDelay.stop()
                    trimFilmstripDelay.stop()
                }

                Timer {
                    id: trimWaveformDelay
                    interval: 1400
                    repeat: false
                    onTriggered: downloadController.prepareWaveform()
                }
                Timer {
                    id: trimFilmstripDelay
                    interval: 3200
                    repeat: false
                    onTriggered: downloadController.prepareTrimFilmstrip()
                }
                Timer {
                    id: trimPlaybackStartDelay
                    interval: 90
                    repeat: false
                    onTriggered: {
                        if (!trimPopup.opened)
                            return
                        var offsetMs = Number(viewState.trimPreviewOffset || 0) * 1000
                        var startMs = Math.max(0, page.clockSeconds(options.startTime) * 1000 - offsetMs)
                        if (Math.abs(trimPlayer.position - startMs) > 180 && trimPopup.playbackSeekRetries < 4) {
                            trimPopup.playbackSeekRetries += 1
                            trimPlayer.position = startMs
                            restart()
                            return
                        }
                        trimPopup.playbackSeekRetries = 0
                        trimPlayer.play()
                    }
                }

                contentItem: ColumnLayout {
                    spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text { text: "RECORTADOR"; color: "#8D88EB"; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                            Text { text: "Quédate sólo con lo que necesitas"; color: theme.colors.text; font.pixelSize: 20; font.weight: Font.DemiBold }
                            Text { Layout.fillWidth: true; text: viewState.hasVideo ? "Arrastra las asas blancas sobre los fotogramas y conserva sólo lo que necesitas." : "Arrastra Entrada y Salida sobre la forma de onda."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        }
                        XButton {
                            text: "Cancelar"
                            kind: "ghost"
                            compact: true
                            onClicked: {
                                downloadController.setOption("startTime", trimPopup.previousStart)
                                downloadController.setOption("endTime", trimPopup.previousEnd)
                                downloadController.setOption("fragmentEnabled", trimPopup.previousEnabled)
                                trimPopup.close()
                            }
                        }
                    }

                    Rectangle {
                        id: trimPreviewPanel
                        objectName: "downloadTrimPreview"
                        visible: Boolean(viewState.trimPreviewSource)
                        Layout.fillWidth: true
                        Layout.preferredHeight: viewState.hasVideo ? Math.max(240, trimPopup.height - 520) : 108
                        Layout.minimumHeight: viewState.hasVideo ? 240 : 100
                        radius: 12
                        color: "#050609"
                        border.color: theme.colors.border
                        clip: true

                        VideoOutput {
                            id: trimPreviewVideo
                            anchors.fill: parent
                            anchors.bottomMargin: 46
                            visible: Boolean(viewState.hasVideo)
                            fillMode: VideoOutput.PreserveAspectFit
                        }
                        Image {
                            anchors.fill: trimPreviewVideo
                            visible: Boolean(viewState.hasVideo) && (!trimPopup.previewActivated || trimPlayer.mediaStatus === MediaPlayer.LoadingMedia)
                            source: viewState.thumbnailSource || ""
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            opacity: 0.92
                        }
                        RoundButton {
                            anchors.centerIn: trimPreviewVideo
                            visible: Boolean(viewState.hasVideo)
                                     && !Boolean(viewState.trimPreviewBusy)
                                     && !Boolean(trimPopup.playbackError || viewState.trimPreviewError)
                                     && trimPlayer.playbackState !== MediaPlayer.PlayingState
                            width: 58; height: 58
                            text: "▶"
                            onClicked: page.toggleTrimPreview()
                            contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 20; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { radius: 29; color: "#C9161921"; border.color: "#A29DFF"; border.width: 2 }
                        }
                        Text {
                            anchors.centerIn: trimPreviewVideo
                            visible: Boolean(viewState.trimPreviewBusy)
                                     || Boolean(trimPopup.playbackError || viewState.trimPreviewError)
                            width: Math.min(parent.width - 80, 500)
                            text: viewState.trimPreviewBusy
                                  ? "Preparando una copia ligera para la vista previa…"
                                  : "No se pudo reproducir la vista previa.\n" + (viewState.trimPreviewError || trimPopup.playbackError)
                            color: "#F1F2F7"
                            font.pixelSize: 11
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }
                        XButton {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 50
                            visible: Boolean(trimPopup.playbackError || viewState.trimPreviewError) && !Boolean(viewState.trimPreviewBusy)
                            text: "Preparar vista previa"
                            compact: true
                            onClicked: {
                                trimPopup.playbackError = ""
                                trimPopup.fallbackRequested = true
                                downloadController.prepareFallbackTrimPreview()
                            }
                        }
                        BusyIndicator {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 52
                            running: Boolean(viewState.trimPreviewBusy)
                            visible: running
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: !viewState.hasVideo
                            text: "♫  Vista previa de audio"
                            color: theme.colors.textMuted
                            font.pixelSize: 13
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 46
                            color: "#F011141B"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8
                                XButton {
                                    objectName: "trimPreviewPlayButton"
                                    compact: true; implicitWidth: 40
                                    text: trimPlayer.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"
                                    kind: "ghost"
                                    enabled: Boolean(trimPlayer.source) && !Boolean(viewState.trimPreviewBusy)
                                    onClicked: page.toggleTrimPreview()
                                }
                                Text {
                                    text: page.clockText(trimPlayer.position / 1000 + Number(viewState.trimPreviewOffset || 0)) + "  /  " + page.clockText(viewState.duration || 0)
                                    color: theme.colors.text
                                    font.pixelSize: 12
                                    font.family: "Consolas"
                                    font.weight: Font.DemiBold
                                }
                                Item { Layout.fillWidth: true }
                                XButton {
                                    objectName: "trimVolumeDownButton"
                                    compact: true; implicitWidth: 34; text: "−"; kind: "ghost"
                                    onClicked: trimAudio.volume = Math.max(0, trimAudio.volume - 0.1)
                                }
                                Slider {
                                    objectName: "trimVolumeSlider"
                                    Layout.preferredWidth: 100
                                    from: 0; to: 1; stepSize: 0.05
                                    value: trimAudio.volume
                                    onMoved: trimAudio.volume = value
                                }
                                XButton {
                                    objectName: "trimVolumeUpButton"
                                    compact: true; implicitWidth: 34; text: "+"; kind: "ghost"
                                    onClicked: trimAudio.volume = Math.min(1, trimAudio.volume + 0.1)
                                }
                                XButton {
                                    compact: true; implicitWidth: 38
                                    text: page.trimUserMuted || trimAudio.volume <= 0 ? "M" : "♪"
                                    kind: "ghost"
                                    onClicked: page.trimUserMuted = !page.trimUserMuted
                                }
                            }
                        }
                    }

                    PremiereTimeline {
                        id: trimPremiereTimeline
                        objectName: "trimPremiereTimeline"
                        visible: Boolean(viewState.hasVideo) && Number(viewState.duration || 0) > 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: 184
                        duration: Number(viewState.duration || 0)
                        inPoint: Math.max(0, page.clockSeconds(options.startTime))
                        outPoint: Math.max(0, page.clockSeconds(options.endTime))
                        playhead: trimPlayer.position / 1000 + Number(viewState.trimPreviewOffset || 0)
                        filmstripSource: viewState.trimFilmstripSource || ""
                        fallbackSource: viewState.thumbnailSource || ""
                        waveformSource: viewState.waveformSource || ""
                        filmstripBusy: Boolean(viewState.trimFilmstripBusy)
                        waveformBusy: Boolean(viewState.waveformBusy)
                        onInPointMoved: function(value) { page.setTrimBoundary("startTime", value) }
                        onOutPointMoved: function(value) { page.setTrimBoundary("endTime", value) }
                        onSeekRequested: function(value) { page.seekTrimPreview(value) }
                    }

                    WaveformTrimmer {
                        objectName: "downloadWaveformTrimmer"
                        visible: !viewState.hasVideo && Boolean(viewState.hasAudio)
                        Layout.fillWidth: true
                        Layout.preferredHeight: 190
                        compact: true
                        waveformSource: viewState.waveformSource || ""
                        busy: Boolean(viewState.waveformBusy)
                        errorText: viewState.waveformError || ""
                        duration: Number(viewState.duration || 0)
                        inPoint: Math.max(0, page.clockSeconds(options.startTime))
                        outPoint: Math.max(0, page.clockSeconds(options.endTime))
                        onInPointMoved: function(value) { page.setTrimBoundary("startTime", value) }
                        onOutPointMoved: function(value) { page.setTrimBoundary("endTime", value) }
                        onRetryRequested: downloadController.prepareWaveform()
                    }

                    GridLayout {
                        visible: !viewState.hasVideo
                        Layout.fillWidth: true
                        columns: trimPopup.width > 650 ? 2 : 1
                        columnSpacing: 10
                        rowSpacing: 8
                        LabeledControl {
                            Layout.fillWidth: true
                            label: "Entrada · HH:MM:SS"
                            XTextField { Layout.fillWidth: true; text: options.startTime; onEditingFinished: downloadController.setOption("startTime", text) }
                        }
                        LabeledControl {
                            Layout.fillWidth: true
                            label: "Salida · HH:MM:SS"
                            XTextField { Layout.fillWidth: true; text: options.endTime; onEditingFinished: downloadController.setOption("endTime", text) }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: outputPathColumn.implicitHeight + 20
                        radius: 11
                        color: theme.colors.surfaceSoft
                        border.color: theme.colors.border
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10
                            ColumnLayout {
                                id: outputPathColumn
                                Layout.fillWidth: true
                                spacing: 3
                                Text { text: "CARPETA DE SALIDA"; color: theme.colors.textDim; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 0.9 }
                                Text { Layout.fillWidth: true; text: viewState.effectiveOutputPath; color: theme.colors.text; font.pixelSize: 10; elide: Text.ElideMiddle }
                                Text { Layout.fillWidth: true; text: "Al pulsar Iniciar descarga se generará únicamente este fragmento."; color: theme.colors.textMuted; font.pixelSize: 9; wrapMode: Text.WordWrap }
                            }
                            XButton {
                                objectName: "trimOutputFolderButton"
                                compact: true
                                text: "Cambiar carpeta"
                                kind: "secondary"
                                onClicked: downloadController.chooseOutputFolder()
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        XSwitch { text: "Corte preciso"; checked: options.preciseClip; onToggled: downloadController.setOption("preciseClip", checked) }
                        XSwitch {
                            text: "Conservar archivo completo"
                            checked: options.keepOriginalOnClip
                            onToggled: {
                                downloadController.setOption("keepOriginalOnClip", checked)
                                downloadController.setOption("forceFullDownload", checked)
                            }
                        }
                        Item { Layout.fillWidth: true }
                        XButton {
                            visible: trimPopup.previousEnabled
                            text: "Quitar recorte"
                            compact: true
                            kind: "ghost"
                            onClicked: {
                                downloadController.setOption("fragmentEnabled", false)
                                downloadController.setOption("startTime", "00:00:00")
                                downloadController.setOption("endTime", page.clockText(viewState.duration))
                                trimPopup.close()
                            }
                        }
                        XButton {
                            text: "Usar este fragmento"
                            compact: true
                            kind: "primary"
                            enabled: page.fragmentReady()
                            onClicked: trimPopup.close()
                        }
                    }
                }
            }

            Popup {
                id: advanced
                objectName: "advancedToolsPopup"
                parent: Overlay.overlay
                x: Math.round((parent.width - width) / 2)
                y: Math.round((parent.height - height) / 2)
                width: Math.min(1120, parent.width - 28)
                height: Math.min(650, parent.height - 28)
                padding: 16
                modal: true
                focus: true
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { radius: 18; color: theme.colors.surfaceRaised; border.color: theme.colors.primary; border.width: 1 }
                enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: settingsController.state.animationsEnabled ? 150 : 0 } }
                exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: settingsController.state.animationsEnabled ? 120 : 0 } }

                contentItem: ScrollView {
                    id: advancedScroll
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical: XScrollBar {}

                    ColumnLayout {
                        id: advancedContent
                        width: advancedScroll.availableWidth
                        spacing: 12
                        RowLayout {
                            Layout.fillWidth: true
                            SectionTitle { Layout.fillWidth: true; compact: page.denseLayout; eyebrow: "AJUSTES AVANZADOS"; title: "Herramientas técnicas"; description: "Subtítulos, códecs, fotogramas y reescalado. El recorte está junto a la vista previa."; number: "02" }
                            XButton { compact: true; text: "Cerrar"; kind: "ghost"; onClicked: advanced.close() }
                        }
                    TabBar {
                        id: toolsTabs
                        Layout.fillWidth: true
                        background: Rectangle { radius: 11; color: theme.colors.surfaceSoft }
                        Repeater {
                            model: ["Subtítulos", "Recodificación", "Fotogramas", "Reescalado"]
                            TabButton {
                                text: modelData
                                contentItem: Text { text: parent.text; color: parent.checked ? theme.colors.text : theme.colors.textMuted; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11; font.weight: parent.checked ? Font.DemiBold : Font.Normal }
                                background: Rectangle { radius: 9; color: parent.checked ? theme.colors.primary : "transparent" }
                            }
                        }
                    }
                    StackLayout {
                        Layout.fillWidth: true
                        currentIndex: toolsTabs.currentIndex

                        GridLayout {
                            columns: advanced.width > 850 ? 3 : 1; rowSpacing: 10; columnSpacing: 10
                            XSwitch { text: "Descargar subtítulos"; checked: options.downloadSubtitles; onToggled: downloadController.setOption("downloadSubtitles", checked) }
                            XSwitch { text: "Limpiar subtítulo"; checked: options.cleanSubtitle; onToggled: downloadController.setOption("cleanSubtitle", checked) }
                            XSwitch { text: "Conservar subtítulo completo"; checked: options.keepFullSubtitle; onToggled: downloadController.setOption("keepFullSubtitle", checked) }
                            LabeledControl { Layout.fillWidth: true; label: "Idioma"; XComboBox { Layout.fillWidth: true; model: downloadController.subtitleLanguages; currentIndex: Math.max(0, find(viewState.selectedSubtitleLanguage)); onActivated: downloadController.setValue("selectedSubtitleLanguage", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Formato"; XComboBox { Layout.fillWidth: true; model: downloadController.subtitleFormats; currentIndex: Math.max(0, find(viewState.selectedSubtitleFormat)); onActivated: downloadController.setValue("selectedSubtitleFormat", currentText) } }
                            XButton { Layout.alignment: Qt.AlignBottom; text: "Guardar subtítulo"; kind: "secondary"; onClicked: downloadController.saveSubtitle() }
                        }

                        ColumnLayout {
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                XSwitch { text: "Recodificar video"; checked: options.recodeVideoEnabled; onToggled: downloadController.setOption("recodeVideoEnabled", checked) }
                                XSwitch { text: "Recodificar audio"; checked: options.recodeAudioEnabled; onToggled: downloadController.setOption("recodeAudioEnabled", checked) }
                                XSwitch { text: "Todas las pistas"; checked: options.useAllAudioTracks; onToggled: downloadController.setOption("useAllAudioTracks", checked) }
                            }
                            GridLayout {
                                Layout.fillWidth: true; columns: advanced.width > 850 ? 4 : 2; columnSpacing: 10; rowSpacing: 10
                                LabeledControl { Layout.fillWidth: true; label: "Procesador"; XComboBox { Layout.fillWidth: true; model: ["CPU", "NVIDIA", "AMD", "Intel"]; currentIndex: Math.max(0, find(options.recodeProc)); onActivated: downloadController.setOption("recodeProc", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Códec de video"; XComboBox { Layout.fillWidth: true; model: presetStore.videoCodecs; currentIndex: Math.max(0, find(options.recodeCodecName)); onActivated: downloadController.setOption("recodeCodecName", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Perfil de video"; XComboBox { Layout.fillWidth: true; model: presetStore.profiles("video", options.recodeCodecName); currentIndex: Math.max(0, find(options.recodeProfileName)); onActivated: downloadController.setOption("recodeProfileName", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "FPS forzado"; XTextField { Layout.fillWidth: true; text: options.fpsValue; onEditingFinished: downloadController.setOption("fpsValue", text) } }
                                LabeledControl { Layout.fillWidth: true; label: "Códec de audio"; XComboBox { Layout.fillWidth: true; model: presetStore.audioCodecs; currentIndex: Math.max(0, find(options.recodeAudioCodecName)); onActivated: downloadController.setOption("recodeAudioCodecName", currentText) } }
                                LabeledControl { Layout.fillWidth: true; label: "Perfil de audio"; XComboBox { Layout.fillWidth: true; model: presetStore.profiles("audio", options.recodeAudioCodecName); currentIndex: Math.max(0, find(options.recodeAudioProfileName)); onActivated: downloadController.setOption("recodeAudioProfileName", currentText) } }
                                XSwitch { text: "Forzar FPS"; checked: options.fpsForceEnabled; onToggled: downloadController.setOption("fpsForceEnabled", checked) }
                                XSwitch { text: "Cambiar resolución"; checked: options.resolutionChangeEnabled; onToggled: downloadController.setOption("resolutionChangeEnabled", checked) }
                                LabeledControl { Layout.fillWidth: true; label: "Ancho"; XTextField { Layout.fillWidth: true; text: options.resWidth; onEditingFinished: downloadController.setOption("resWidth", text) } }
                                LabeledControl { Layout.fillWidth: true; label: "Alto"; XTextField { Layout.fillWidth: true; text: options.resHeight; onEditingFinished: downloadController.setOption("resHeight", text) } }
                                XSwitch { text: "Mantener proporción"; checked: options.maintainAspect; onToggled: downloadController.setOption("maintainAspect", checked) }
                                XSwitch { text: "No aumentar resolución"; checked: options.noUpscaling; onToggled: downloadController.setOption("noUpscaling", checked) }
                            }
                        }

                        GridLayout {
                            columns: advanced.width > 850 ? 4 : 2; rowSpacing: 10; columnSpacing: 10
                            XSwitch { Layout.columnSpan: 2; text: "Extraer fotogramas"; checked: options.extractFramesEnabled; onToggled: downloadController.setOption("extractFramesEnabled", checked) }
                            XSwitch { Layout.columnSpan: 2; text: "Conservar video original"; checked: options.keepOriginalExtract; onToggled: downloadController.setOption("keepOriginalExtract", checked) }
                            LabeledControl { Layout.fillWidth: true; label: "Tipo"; XComboBox { Layout.fillWidth: true; model: ["Todos los fotogramas", "Fotogramas por segundo"]; currentIndex: Math.max(0, find(options.extractType)); onActivated: downloadController.setOption("extractType", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Formato"; XComboBox { Layout.fillWidth: true; model: ["png", "jpg", "webp"]; currentIndex: Math.max(0, find(options.extractFormat)); onActivated: downloadController.setOption("extractFormat", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "FPS"; XTextField { Layout.fillWidth: true; text: options.extractFps; onEditingFinished: downloadController.setOption("extractFps", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Carpeta"; XTextField { Layout.fillWidth: true; text: options.extractFolderName; onEditingFinished: downloadController.setOption("extractFolderName", text) } }
                        }

                        GridLayout {
                            columns: advanced.width > 850 ? 4 : 2; rowSpacing: 10; columnSpacing: 10
                            XSwitch { Layout.columnSpan: 2; text: "Reescalar video con NCNN"; checked: options.upscaleVideoEnabled; onToggled: downloadController.setOption("upscaleVideoEnabled", checked) }
                            XSwitch { text: "TTA"; checked: options.upscaleTta; onToggled: downloadController.setOption("upscaleTta", checked) }
                            XSwitch { text: "Conservar transparencia"; checked: options.upscaleTransparency; onToggled: downloadController.setOption("upscaleTransparency", checked) }
                            LabeledControl { Layout.fillWidth: true; label: "Motor"; XComboBox { Layout.fillWidth: true; model: ["realesrgan-ncnn-vulkan", "waifu2x-ncnn-vulkan", "srmd-ncnn-vulkan", "realsr-ncnn-vulkan"]; currentIndex: Math.max(0, find(options.upscaleEngine)); onActivated: downloadController.setOption("upscaleEngine", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Modelo"; XTextField { Layout.fillWidth: true; text: options.upscaleModel; onEditingFinished: downloadController.setOption("upscaleModel", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Escala"; XComboBox { Layout.fillWidth: true; model: ["2x", "3x", "4x"]; currentIndex: Math.max(0, find(options.upscaleScale)); onActivated: downloadController.setOption("upscaleScale", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Contenedor"; XComboBox { Layout.fillWidth: true; model: ["Mismo que el original", "MP4", "MOV", "MKV", "WEBM"]; currentIndex: Math.max(0, find(options.upscaleContainer)); onActivated: downloadController.setOption("upscaleContainer", currentText) } }
                            LabeledControl { Layout.fillWidth: true; label: "Tile"; XTextField { Layout.fillWidth: true; text: options.upscaleTile; onEditingFinished: downloadController.setOption("upscaleTile", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Denoise"; XTextField { Layout.fillWidth: true; text: options.upscaleDenoise; onEditingFinished: downloadController.setOption("upscaleDenoise", text) } }
                            LabeledControl { Layout.fillWidth: true; label: "Nombre de salida"; XTextField { Layout.fillWidth: true; text: options.upscaleOutputName; onEditingFinished: downloadController.setOption("upscaleOutputName", text) } }
                        }
                    }
                }
            }
            }

        XCard {
            objectName: "downloadFooterCard"
            Layout.fillWidth: true
            implicitHeight: downloadFooter.implicitHeight + (page.denseLayout ? 18 : 24)
            cardColor: theme.colors.surfaceRaised
            ColumnLayout {
                id: downloadFooter
                anchors.fill: parent
                anchors.margins: page.denseLayout ? 9 : 12
                spacing: page.denseLayout ? 7 : 10
                RowLayout {
                    id: footerGrid
                    Layout.fillWidth: true
                    spacing: page.denseLayout ? 8 : 10

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 500
                        spacing: page.denseLayout ? 4 : 7
                        Text {
                            text: "Carpeta de salida"
                            color: theme.colors.textMuted
                            font.pixelSize: page.denseLayout ? 10 : 11
                            font.weight: Font.DemiBold
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: page.denseLayout ? 8 : 10
                            XTextField {
                                Layout.fillWidth: true
                                compact: page.denseLayout
                                readOnly: viewState.selectedTag !== "Sin etiqueta"
                                text: viewState.effectiveOutputPath
                                onEditingFinished: {
                                    if (viewState.selectedTag === "Sin etiqueta")
                                        downloadController.setValue("outputPath", text)
                                }
                            }
                            XButton {
                                compact: page.denseLayout
                                text: viewState.selectedTag === "Sin etiqueta" ? "Elegir carpeta" : "Cambiar carpeta"
                                kind: "secondary"
                                onClicked: downloadController.chooseOutputFolder()
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.preferredWidth: page.denseLayout ? 330 : 370
                        spacing: page.denseLayout ? 4 : 7
                        Text {
                            text: "Etiqueta de destino"
                            color: theme.colors.textMuted
                            font.pixelSize: page.denseLayout ? 10 : 11
                            font.weight: Font.DemiBold
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: page.denseLayout ? 8 : 10
                            Rectangle {
                                Layout.preferredWidth: 12
                                Layout.preferredHeight: 12
                                radius: 6
                                color: viewState.selectedTagColor
                            }
                            XComboBox {
                                id: tagCombo
                                Layout.fillWidth: true
                                compact: page.denseLayout
                                model: downloadController.downloadTags
                                currentIndex: Math.max(0, find(viewState.selectedTag))
                                onActivated: downloadController.setValue("selectedTag", currentText)
                                ToolTip.visible: hovered
                                ToolTip.text: "La etiqueta recuerda su color y su carpeta de destino."
                            }
                            XButton {
                                text: "+"
                                compact: true
                                kind: "secondary"
                                onClicked: downloadController.createDownloadTag()
                                ToolTip.visible: hovered
                                ToolTip.text: "Crear etiqueta: nombre, carpeta y color"
                            }
                            XButton {
                                visible: viewState.selectedTag !== "Sin etiqueta"
                                text: "−"
                                compact: true
                                kind: "ghost"
                                onClicked: downloadController.deleteSelectedTag()
                                ToolTip.visible: hovered
                                ToolTip.text: "Eliminar etiqueta"
                            }
                        }
                    }

                    ColumnLayout {
                        spacing: page.denseLayout ? 4 : 7
                        Text {
                            text: "Acción"
                            color: "transparent"
                            font.pixelSize: page.denseLayout ? 10 : 11
                            font.weight: Font.DemiBold
                        }
                        XButton {
                            compact: page.denseLayout
                            text: viewState.busy ? "Cancelar" : viewState.localFile ? "Procesar" : viewState.imagePost ? "Descargar imágenes" : "Iniciar descarga"
                            kind: viewState.busy ? "danger" : "primary"
                            enabled: viewState.busy || viewState.analyzed
                            onClicked: viewState.busy ? downloadController.cancel() : downloadController.start()
                        }
                    }

                    ColumnLayout {
                        visible: viewState.lastOutput.length > 0
                        spacing: page.denseLayout ? 4 : 7
                        Text {
                            text: "Acción"
                            color: "transparent"
                            font.pixelSize: page.denseLayout ? 10 : 11
                            font.weight: Font.DemiBold
                        }
                        XButton {
                            id: resultButton
                            compact: page.denseLayout
                            text: "Resultado"
                            kind: "secondary"
                            onClicked: downloadController.openOutput()
                        }
                    }
                }
            }
        }
        ProgressStrip { objectName: "downloadProgress"; Layout.fillWidth: true; compact: page.denseLayout; value: viewState.progress; status: viewState.status; busy: viewState.busy }
    }
}
