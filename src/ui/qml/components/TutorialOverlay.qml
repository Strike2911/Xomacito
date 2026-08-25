import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: tutorial
    objectName: "guidedTutorialOverlay"
    x: 0
    y: 0
    width: parent ? parent.width : 1280
    height: parent ? parent.height : 720
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose

    property var steps: []
    property int stepIndex: 0
    property bool pageOnly: false
    property var currentStep: steps.length > stepIndex ? steps[stepIndex] : ({})
    property bool navigationTarget: currentStep.target === "navigation"
    property real focusX: 10
    property real focusY: navigationTarget ? Math.max(76, Math.min(90, height * 0.112)) : Math.max(128, Math.min(145, height * 0.19))
    property real focusWidth: Math.max(0, width - 20)
    property real focusHeight: navigationTarget ? 48 : Math.max(125, Math.min(160, height * 0.215))

    signal pageRequested(int page)
    signal finished()
    signal skipped()

    function animateStep() {
        coachCard.opacity = 0
        coachCard.scale = 0.965
        coachCard.entranceOffset = 10
        stepEntrance.restart()
    }

    function selectStep(index) {
        stepIndex = Math.max(0, Math.min(steps.length - 1, index))
        if (currentStep.page >= 0)
            pageRequested(currentStep.page)
        animateStep()
    }

    function startFull() {
        pageOnly = false
        stepIndex = 0
        tutorial.visible = true
        selectStep(0)
    }

    function startPage(pageIndex) {
        pageOnly = true
        var wanted = Math.max(1, Math.min(steps.length - 1, Number(pageIndex) + 1))
        stepIndex = wanted
        tutorial.visible = true
        selectStep(wanted)
    }

    function advance() {
        if (pageOnly || stepIndex >= steps.length - 1) {
            tutorial.visible = false
            finished()
            return
        }
        selectStep(stepIndex + 1)
    }

    function back() {
        if (!pageOnly && stepIndex > 0)
            selectStep(stepIndex - 1)
    }

    function omit() {
        tutorial.visible = false
        skipped()
    }

    onOpened: animateStep()
    Keys.onEscapePressed: function(event) { omit(); event.accepted = true }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 180; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: 140; easing.type: Easing.InCubic }
    }
    background: Rectangle { color: "transparent" }

    contentItem: Item {
        Rectangle { x: 0; y: 0; width: parent.width; height: tutorial.focusY; color: "#B0000000" }
        Rectangle { x: 0; y: tutorial.focusY; width: tutorial.focusX; height: tutorial.focusHeight; color: "#B0000000" }
        Rectangle { x: tutorial.focusX + tutorial.focusWidth; y: tutorial.focusY; width: Math.max(0, parent.width - x); height: tutorial.focusHeight; color: "#B0000000" }
        Rectangle { x: 0; y: tutorial.focusY + tutorial.focusHeight; width: parent.width; height: Math.max(0, parent.height - y); color: "#B0000000" }

        Rectangle {
            x: tutorial.focusX
            y: tutorial.focusY
            width: tutorial.focusWidth
            height: tutorial.focusHeight
            radius: 14
            color: "transparent"
            border.width: 2
            border.color: theme.colors.primary
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                running: tutorial.visible && settingsController.state.animationsEnabled
                NumberAnimation { from: 1; to: 0.55; duration: 800; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1; duration: 800; easing.type: Easing.InOutSine }
            }
        }

        Rectangle {
            id: coachCard
            objectName: "guidedTutorialCoachCard"
            property real entranceOffset: 0
            width: Math.min(520, tutorial.width - 48)
            implicitHeight: coachContent.implicitHeight + 36
            x: Math.max(18, Math.min(tutorial.width - width - 18, tutorial.focusX + tutorial.focusWidth / 2 - width / 2))
            y: Math.min(tutorial.height - height - 18, tutorial.focusY + tutorial.focusHeight + 18 + entranceOffset)
            radius: 18
            color: theme.colors.surfaceRaised
            border.width: 1
            border.color: theme.colors.primary

            Rectangle {
                width: 18; height: 18; rotation: 45
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.top
                color: theme.colors.surfaceRaised
                border.width: 1
                border.color: theme.colors.primary
            }
            Rectangle {
                width: 30; height: 12
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                color: theme.colors.surfaceRaised
            }

            ColumnLayout {
                id: coachContent
                x: 18; y: 18; width: coachCard.width - 36
                spacing: 11

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Rectangle {
                        width: 34; height: 34; radius: 10
                        color: theme.colors.surfaceSoft
                        border.color: theme.colors.borderStrong
                        Text { anchors.centerIn: parent; text: tutorial.currentStep.icon || "→"; color: theme.colors.primary; font.pixelSize: 16; font.weight: Font.Bold }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: tutorial.pageOnly ? "GUÍA DEL APARTADO" : "RECORRIDO RÁPIDO"; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                        Text { Layout.fillWidth: true; text: tutorial.currentStep.title || "Xomacito"; color: theme.colors.text; font.pixelSize: 21; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
                    }
                    Text { text: (tutorial.stepIndex + 1) + " / " + tutorial.steps.length; color: theme.colors.textDim; font.pixelSize: 12; font.weight: Font.Bold }
                }

                Text {
                    Layout.fillWidth: true
                    text: tutorial.currentStep.message || ""
                    color: theme.colors.textMuted
                    font.pixelSize: 14
                    lineHeight: 1.3
                    wrapMode: Text.WordWrap
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    Repeater {
                        model: tutorial.currentStep.actions || []
                        delegate: RowLayout {
                            required property string modelData
                            required property int index
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle {
                                width: 25; height: 25; radius: 8
                                color: theme.colors.surfaceSoft
                                Text { anchors.centerIn: parent; text: index + 1; color: theme.colors.primary; font.pixelSize: 10; font.weight: Font.Bold }
                            }
                            Text { Layout.fillWidth: true; text: modelData; color: theme.colors.text; font.pixelSize: 13; wrapMode: Text.WordWrap }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: theme.colors.border }

                RowLayout {
                    Layout.fillWidth: true
                    XButton { compact: true; text: tutorial.pageOnly ? "Cerrar" : "Omitir"; kind: "ghost"; font.pixelSize: 14; onClicked: tutorial.omit() }
                    Item { Layout.fillWidth: true }
                    XButton { compact: true; visible: !tutorial.pageOnly && tutorial.stepIndex > 0; text: "Anterior"; kind: "secondary"; font.pixelSize: 14; onClicked: tutorial.back() }
                    XButton {
                        compact: true
                        font.pixelSize: 14
                        text: tutorial.pageOnly || tutorial.stepIndex >= tutorial.steps.length - 1 ? "Entendido" : "Siguiente"
                        onClicked: tutorial.advance()
                    }
                }
            }

            ParallelAnimation {
                id: stepEntrance
                NumberAnimation { target: coachCard; property: "opacity"; to: 1; duration: 180; easing.type: Easing.OutCubic }
                NumberAnimation { target: coachCard; property: "scale"; to: 1; duration: 240; easing.type: Easing.OutBack }
                NumberAnimation { target: coachCard; property: "entranceOffset"; to: 0; duration: 220; easing.type: Easing.OutCubic }
            }
        }
    }
}
