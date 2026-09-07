import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

XCard {
    id: root
    property real value: 0
    property string status: ""
    property bool busy: false
    property bool compact: false
    readonly property real fraction: Math.max(0, Math.min(1, value))
    readonly property bool animate: busy && visible && settingsController.state.animationsEnabled
    property int frame: 0
    implicitHeight: compact ? 78 : 90
    Accessible.role: Accessible.ProgressBar
    Accessible.name: status
    Accessible.description: value < 0 ? "Preparando" : Math.round(fraction * 100) + "%"
    Timer { interval: 140; repeat: true; running: root.animate; onTriggered: root.frame = 1 - root.frame }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 2
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: root.status; color: theme.colors.text; font.pixelSize: 11; elide: Text.ElideRight }
            Text { text: root.value < 0 ? "Preparando…" : Math.round(root.fraction * 100) + "%"; color: root.fraction >= 1 ? theme.colors.success : theme.colors.textMuted; font.pixelSize: 11; font.bold: true }
        }
        Item {
            id: track
            Layout.fillWidth: true
            Layout.fillHeight: true
            readonly property real runnerX: Math.max(0, width - 58) * root.fraction
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 7; radius: 3; color: theme.colors.surfaceSoft }
            Item {
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                width: cat.x + (root.fraction > 0 ? 28 : 0)
                height: 12
                clip: true
                Column {
                    width: parent.width; y: root.animate && root.frame ? 1 : 0
                    Repeater {
                        model: ["#FF647C", "#FFB45B", "#FFE779", "#77DFA1", "#64C7FF", "#AD8BFA"]
                        Rectangle { required property string modelData; width: parent.width; height: 2; color: modelData; opacity: 0.85 }
                    }
                }
            }
            Item {
                id: cat
                objectName: "progressCat"
                x: track.runnerX
                anchors.bottom: parent.bottom
                width: 58; height: 39
                Behavior on x { enabled: settingsController.state.animationsEnabled; NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                Image {
                    anchors.fill: parent
                    source: "../../../../assets/progress/cat-run-1.png"
                    sourceClipRect: Qt.rect(410, 430, 830, 550)
                    fillMode: Image.PreserveAspectFit; smooth: false
                    visible: !root.animate || root.frame === 0
                }
                Image {
                    anchors.fill: parent
                    source: "../../../../assets/progress/cat-run-2.png"
                    sourceClipRect: Qt.rect(200, 340, 1000, 670)
                    fillMode: Image.PreserveAspectFit; smooth: false
                    visible: root.animate && root.frame === 1
                }
            }
        }
    }
}
