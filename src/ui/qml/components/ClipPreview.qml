import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

ColumnLayout {
    id: root
    property url source: ""
    property url poster: ""
    property bool audioOnly: false
    property bool muted: false
    property real inPoint: 0
    property real outPoint: 0
    property bool pendingPlay: false
    property string errorText: ""
    property alias mediaPlayer: player
    readonly property bool playing: player.playbackState === MediaPlayer.PlayingState
    spacing: 6

    function pause() { pendingPlay = false; player.pause() }
    function seek(seconds) { pause(); player.position = Math.max(0, seconds * 1000) }
    function beginSelection() {
        pendingPlay = false
        player.position = Math.round(inPoint * 1000)
        player.play()
    }
    function playSelection() {
        if (!String(source).length || outPoint <= inPoint) return
        if (player.mediaStatus === MediaPlayer.LoadingMedia || player.mediaStatus === MediaPlayer.NoMedia) pendingPlay = true
        else beginSelection()
    }
    function enforceEnd() {
        if (playing && player.position >= Math.round(outPoint * 1000)) {
            pause()
            player.position = Math.round(outPoint * 1000)
        }
    }
    onInPointChanged: seek(inPoint)
    onOutPointChanged: pause()
    onVisibleChanged: if (!visible) pause()
    onSourceChanged: { pause(); errorText = "" }
    MediaPlayer {
        id: player; objectName: "clipSelectionPlayer"
        source: root.source
        videoOutput: video
        audioOutput: AudioOutput { volume: 0.45; muted: root.muted }
        onPositionChanged: root.enforceEnd()
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.LoadedMedia || mediaStatus === MediaPlayer.BufferedMedia) {
                if (root.pendingPlay) root.beginSelection()
            }
        }
        onErrorOccurred: function(error, message) { root.pause(); root.errorText = message }
    }
    Timer { interval: 16; repeat: true; running: root.playing; onTriggered: root.enforceEnd() }
    Rectangle {
        Layout.fillWidth: true; Layout.fillHeight: true
        color: "#080A10"; radius: 8; clip: true
        Image { anchors.fill: parent; source: root.poster; fillMode: Image.PreserveAspectFit; visible: root.audioOnly || player.position === 0 }
        VideoOutput { id: video; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit; visible: !root.audioOnly }
        Text { anchors.centerIn: parent; text: "Vista previa de audio"; visible: root.audioOnly; color: theme.colors.text }
    }
    RowLayout {
        Layout.fillWidth: true
        XButton {
            objectName: "playClipSelection"; compact: true
            text: root.playing ? "Pausar" : "Reproducir selección"
            enabled: String(root.source).length > 0 && root.outPoint > root.inPoint && !root.errorText
            onClicked: root.playing ? root.pause() : root.playSelection()
        }
        Text { Layout.fillWidth: true; text: "Solo entre los corchetes"; color: theme.colors.textDim; font.pixelSize: 11 }
    }
    Text { Layout.fillWidth: true; visible: root.errorText.length > 0; text: root.errorText; wrapMode: Text.WordWrap; color: theme.colors.text; font.pixelSize: 11 }
}
