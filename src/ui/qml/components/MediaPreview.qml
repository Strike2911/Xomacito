import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

FocusScope {
    id: root
    property url source: ""
    property url poster: ""
    property url waveform: ""
    property string kind: "Video"
    property string title: ""
    property bool compactControls: true
    property bool loading: false
    property string externalError: ""
    property string playbackError: ""
    property bool autoPlay: false
    property bool active: true
    property bool hasMedia: String(source).length > 0
    property bool temporal: kind !== "Imagen"
    property string playerObjectName: "mediaPreviewPlayer"
    property alias mediaPlayer: playback
    property real zoom: 1
    property bool enlarged: expanded.opened
    property bool scrubbing: false
    property bool resumeAfterScrub: false
    property bool playWhenReady: false
    property bool initialFramePending: false
    property bool frameVisible: false
    signal retryRequested()
    implicitHeight: width * 9 / 16 + 102 + (waveform.toString() ? 44 : 0)

    function clock(ms) {
        var seconds = Math.floor(Math.max(0, ms) / 1000)
        var hours = Math.floor(seconds / 3600)
        return (hours ? hours.toString().padStart(2, "0") + ":" : "") + Math.floor((seconds % 3600) / 60).toString().padStart(2, "0") + ":" + (seconds % 60).toString().padStart(2, "0")
    }
    function play() {
        if (!hasMedia || !temporal) return
        if (playback.mediaStatus === MediaPlayer.LoadingMedia || playback.mediaStatus === MediaPlayer.NoMedia) playWhenReady = true
        else playback.play()
    }
    function pause() { playWhenReady = false; playback.pause() }
    function reload() {
        playback.stop(); playback.source = ""; playbackError = ""; playWhenReady = active
        playback.source = Qt.binding(function() { return root.temporal ? root.source : "" })
    }
    function togglePlay() {
        root.forceActiveFocus()
        if (playback.playbackState === MediaPlayer.PlayingState) pause()
        else play()
    }
    function seek(ms) { playback.position = Math.max(0, Math.min(playback.duration, ms)) }
    function toggleExpand() { expanded.opened ? expanded.close() : expanded.open() }
    function resetView() { zoom = 1; canvas.contentX = 0; canvas.contentY = 0 }
    onSourceChanged: { playbackError = ""; frameVisible = false; resetView(); playWhenReady = autoPlay && active; initialFramePending = hasMedia }
    onActiveChanged: if (!active) { pause(); expanded.close() }
    onVisibleChanged: if (!visible) { pause(); expanded.close() }
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Space) { togglePlay(); event.accepted = true }
        else if (event.key === Qt.Key_Left) { seek(playback.position - 5000); event.accepted = true }
        else if (event.key === Qt.Key_Right) { seek(playback.position + 5000); event.accepted = true }
        else if (event.key === Qt.Key_M) { sound.muted = !sound.muted; event.accepted = true }
        else if (event.key === Qt.Key_F) { toggleExpand(); event.accepted = true }
    }
    MediaPlayer {
        id: playback; objectName: root.playerObjectName
        source: root.temporal ? root.source : ""
        videoOutput: video
        audioOutput: AudioOutput { id: sound; volume: 0.45 }
        loops: repeatButton.checked ? MediaPlayer.Infinite : 1
        onErrorOccurred: function(error, message) { root.playbackError = message; root.playWhenReady = false }
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.LoadedMedia || mediaStatus === MediaPlayer.BufferedMedia) {
                if (root.playWhenReady && root.active) { root.playWhenReady = false; root.initialFramePending = false; play() }
                else if (root.initialFramePending) { root.initialFramePending = false; pause(); position = 0 }
            }
        }
    }
    Connections { target: video.videoSink; function onVideoFrameChanged() { root.frameVisible = true } }
    Item {
        id: body
        parent: expanded.opened ? expandedArea : root
        width: parent.width; height: parent.height
        ColumnLayout {
            anchors.fill: parent; spacing: 6
            Rectangle {
                id: viewport
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 85
                color: "#07090E"; radius: 10; clip: true
                Flickable {
                    id: canvas; anchors.fill: parent; clip: true
                    contentWidth: width * root.zoom; contentHeight: height * root.zoom
                    interactive: root.zoom > 1; boundsBehavior: Flickable.StopAtBounds
                    Item {
                        width: canvas.contentWidth; height: canvas.contentHeight
                        VideoOutput { id: video; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit; visible: root.kind === "Video" && root.hasMedia }
                        Image {
                            anchors.fill: parent; asynchronous: true; fillMode: Image.PreserveAspectFit
                            source: root.kind === "Imagen" ? root.source : !root.hasMedia || root.loading || !root.frameVisible ? root.poster : ""
                            sourceSize.width: root.enlarged ? 1920 : 960
                        }
                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true; preventStealing: false
                            onClicked: if (root.temporal && !root.loading) root.togglePlay()
                            onDoubleClicked: root.toggleExpand()
                            onWheel: function(wheel) {
                                root.zoom = Math.max(1, Math.min(4, root.zoom * (wheel.angleDelta.y > 0 ? 1.2 : 1/1.2)))
                                if (root.zoom === 1) root.resetView()
                                wheel.accepted = true
                            }
                        }
                    }
                }
                Column {
                    anchors.centerIn: parent; width: parent.width - 20; spacing: 9
                    visible: root.kind === "Audio" || (!root.hasMedia && !root.poster.toString())
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.kind === "Audio" ? "♫" : "▷"; font.pixelSize: 34; color: theme.colors.accent }
                    Text { width: parent.width; text: root.kind === "Audio" ? root.title : root.loading ? "Preparando vista previa…" : "Selecciona un medio para explorar"; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; color: theme.colors.textMuted; font.pixelSize: 12 }
                }
                BusyIndicator { anchors.centerIn: parent; running: root.loading || playback.mediaStatus === MediaPlayer.LoadingMedia || playback.mediaStatus === MediaPlayer.StalledMedia; visible: running; width: 44; height: 44 }
                Rectangle {
                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: errorText.implicitHeight + 16
                    color: "#E5151821"; visible: Boolean(root.externalError || root.playbackError)
                    Text { id: errorText; anchors.fill: parent; anchors.margins: 8; text: root.externalError || root.playbackError; color: theme.colors.error; wrapMode: Text.WordWrap; font.pixelSize: 11; maximumLineCount: 4; elide: Text.ElideRight }
                }
                Row {
                    anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 6; spacing: 5
                    XButton { text: Math.round(root.zoom * 100) + "%"; implicitWidth: 48; implicitHeight: 26; leftPadding: 6; rightPadding: 6; compact: true; kind: "secondary"; onClicked: root.resetView(); ToolTip.visible: hovered; ToolTip.text: "Restablecer zoom · Rueda para acercar" }
                    XButton { text: root.enlarged ? "Reducir" : "Ampliar"; implicitWidth: 72; implicitHeight: 26; compact: true; kind: "secondary"; onClicked: root.toggleExpand(); ToolTip.visible: hovered; ToolTip.text: "Ampliar vista (F / doble clic)" }
                }
            }
            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 30; visible: root.waveform.toString().length > 0 && root.temporal
                Image { anchors.fill: parent; source: root.waveform; fillMode: Image.Stretch; asynchronous: true }
                Rectangle { x: parent.width * playback.position / Math.max(1, playback.duration); height: parent.height; width: 2; color: theme.colors.accent }
                MouseArea { anchors.fill: parent; onPressed: function(mouse) { root.scrubbing = true; root.pause(); root.seek(mouse.x / width * playback.duration) }; onPositionChanged: function(mouse) { if (pressed) root.seek(mouse.x / width * playback.duration) }; onReleased: root.scrubbing = false; onCanceled: root.scrubbing = false }
            }
            XSlider {
                id: seekbar; objectName: "mediaPreviewSeek"
                Layout.fillWidth: true; implicitHeight: 16; visible: root.temporal; enabled: root.hasMedia && playback.seekable
                from: 0; to: Math.max(1, playback.duration); value: playback.position
                onPressedChanged: {
                    root.scrubbing = pressed
                    if (pressed) { root.resumeAfterScrub = playback.playbackState === MediaPlayer.PlayingState; root.pause() }
                    else if (root.resumeAfterScrub) root.play()
                }
                onMoved: root.seek(value)
            }
            RowLayout {
                Layout.fillWidth: true; visible: root.temporal; spacing: 4
                XButton { text: playback.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"; implicitWidth: 26; implicitHeight: 26; leftPadding: 3; rightPadding: 3; compact: true; enabled: root.hasMedia; onClicked: root.togglePlay(); ToolTip.visible: hovered; ToolTip.text: "Reproducir / pausar (Espacio)" }
                XButton { id: repeatButton; text: "↻"; implicitWidth: 24; implicitHeight: 26; leftPadding: 3; rightPadding: 3; compact: true; checkable: true; kind: checked ? "primary" : "ghost"; ToolTip.visible: hovered; ToolTip.text: "Repetir" }
                Text { text: root.clock(playback.position) + " / " + root.clock(playback.duration); Layout.fillWidth: true; color: theme.colors.textMuted; font.pixelSize: 10 }
                XComboBox { visible: root.width >= 310 || root.enlarged; model: ["0.5×", "1×", "1.5×", "2×"]; currentIndex: 1; Layout.preferredWidth: 57; implicitHeight: 26; compact: true; onActivated: playback.playbackRate = [0.5, 1, 1.5, 2][currentIndex] }
                XButton { text: sound.muted ? "×♪" : "♪"; implicitWidth: 26; implicitHeight: 26; leftPadding: 2; rightPadding: 2; compact: true; kind: "ghost"; onClicked: sound.muted = !sound.muted; ToolTip.visible: hovered; ToolTip.text: "Silenciar (M)" }
                XSlider { Layout.preferredWidth: root.enlarged ? 100 : 48; implicitHeight: 22; from: 0; to: 1; value: sound.volume; onMoved: { sound.volume = value; sound.muted = false } }
            }
            XButton { visible: Boolean(root.externalError || root.playbackError); text: "Reintentar"; compact: true; implicitHeight: 26; kind: "ghost"; onClicked: { root.playbackError = ""; root.retryRequested() } }

        }
    }
    Popup {
        id: expanded; parent: Overlay.overlay; x: 16; y: 16
        width: parent ? parent.width - 32 : 900; height: parent ? parent.height - 32 : 600
        padding: 14; modal: true; focus: true; closePolicy: Popup.CloseOnEscape
        background: Rectangle { color: theme.colors.surface; radius: 14; border.color: theme.colors.border }
        contentItem: Item { id: expandedArea }
        onClosed: root.forceActiveFocus()
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space) { root.togglePlay(); event.accepted = true }
            else if (event.key === Qt.Key_Left) { root.seek(playback.position - 5000); event.accepted = true }
            else if (event.key === Qt.Key_Right) { root.seek(playback.position + 5000); event.accepted = true }
            else if (event.key === Qt.Key_F) { expanded.close(); event.accepted = true }
            else if (event.key === Qt.Key_M) { sound.muted = !sound.muted; event.accepted = true }
        }
    }
}
