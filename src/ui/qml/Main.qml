import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: window
    width: 1280
    height: 860
    minimumWidth: 960
    minimumHeight: 700
    visible: true
    title: "Xomacito " + appController.version
    color: theme.colors.background
    property bool denseWindow: height <= 760

    property var updateInfo: ({})
    property string dialogRequestId: ""
    property var dialogOptions: []

    background: Item {
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: theme.colors.background }
                GradientStop { position: 1; color: theme.colors.backgroundAlt }
            }
        }
        Rectangle {
            width: 480; height: 480; radius: 240
            x: -210 + Math.sin(motion.phase) * 34
            y: -260 + Math.cos(motion.phase) * 22
            color: theme.colors.primary
            opacity: 0.07
        }
        Rectangle {
            width: 360; height: 360; radius: 180
            x: parent.width - 160 + Math.cos(motion.phase * 0.8) * 28
            y: parent.height - 220 + Math.sin(motion.phase * 0.8) * 25
            color: theme.colors.accent
            opacity: 0.045
        }
        QtObject { id: motion; property real phase: 0 }
        NumberAnimation {
            target: motion; property: "phase"; from: 0; to: Math.PI * 2
            duration: 18000; loops: Animation.Infinite
            running: settingsController.state.animationsEnabled
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: settingsController.state.compactMode || window.denseWindow ? 10 : 14
        spacing: settingsController.state.compactMode || window.denseWindow ? 8 : 12

        XCard {
            Layout.fillWidth: true
            implicitHeight: window.denseWindow ? 62 : settingsController.state.compactMode ? 68 : 78
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                anchors.fill: parent
                anchors.margins: window.denseWindow ? 9 : 11
                spacing: window.denseWindow ? 10 : 13
                Rectangle {
                    Layout.preferredWidth: window.denseWindow ? 44 : settingsController.state.compactMode ? 48 : 54
                    Layout.preferredHeight: Layout.preferredWidth
                    radius: width / 2
                    color: theme.colors.backgroundAlt
                    border.color: theme.colors.primary
                    border.width: 2
                    Image {
                        anchors.fill: parent
                        anchors.margins: 4
                        source: appController.catSource
                        fillMode: Image.PreserveAspectFit
                        mipmap: true
                        smooth: true
                    }
                    SequentialAnimation on scale {
                        loops: Animation.Infinite
                        running: settingsController.state.animationsEnabled
                        NumberAnimation { to: 1.025; duration: 1800; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 1; duration: 1800; easing.type: Easing.InOutSine }
                    }
                }
                ColumnLayout {
                    spacing: 2
                    Text { text: "XOMACITO"; color: theme.colors.text; font.pixelSize: window.denseWindow ? 17 : settingsController.state.compactMode ? 18 : 20; font.weight: Font.Bold; font.letterSpacing: 0.5 }
                    Text { text: "Analiza, descarga y prepara contenido"; color: theme.colors.textMuted; font.pixelSize: 10 }
                }
                Item { Layout.fillWidth: true }
                ColumnLayout {
                    spacing: window.denseWindow ? 3 : 5; Layout.alignment: Qt.AlignVCenter
                    Rectangle {
                        Layout.alignment: Qt.AlignRight; implicitWidth: engineText.implicitWidth + 20; implicitHeight: window.denseWindow ? 20 : 23; radius: height / 2
                        color: theme.colors.surfaceSoft; border.color: theme.colors.border; border.width: 1
                        Text { id: engineText; anchors.centerIn: parent; text: "MOTOR " + appController.version; color: theme.colors.primary; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 0.6 }
                    }
                    Rectangle {
                        Layout.alignment: Qt.AlignRight; implicitWidth: catText.implicitWidth + 20; implicitHeight: window.denseWindow ? 20 : 23; radius: height / 2
                        color: theme.colors.backgroundAlt; border.color: theme.colors.border; border.width: 1
                        Text { id: catText; anchors.centerIn: parent; text: "GATITO DEL DÍA  " + appController.catNumber + "/8"; color: theme.colors.text; font.pixelSize: 8; font.weight: Font.DemiBold }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: window.denseWindow ? 40 : 46
            radius: 14
            color: theme.colors.surface
            border.color: theme.colors.border
            border.width: 1
            RowLayout {
                anchors.fill: parent; anchors.margins: 6; spacing: 6
                Repeater {
                    model: appController.pages
                    Button {
                        required property string modelData
                        required property int index
                        Layout.fillWidth: true
                        Layout.maximumWidth: 220
                        implicitHeight: window.denseWindow ? 30 : 34
                        text: modelData
                        font.pixelSize: 12
                        font.weight: appController.page === index ? Font.DemiBold : Font.Normal
                        focusPolicy: Qt.StrongFocus
                        onClicked: appController.setPage(index)
                        contentItem: Text { text: parent.text; color: appController.page === index ? "white" : theme.colors.textMuted; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font: parent.font }
                        background: Rectangle {
                            radius: 10
                            color: appController.page === index ? theme.colors.primary : parent.hovered ? theme.colors.surfaceSoft : "transparent"
                            border.width: parent.activeFocus ? 1 : 0
                            border.color: theme.colors.accent
                            Behavior on color { ColorAnimation { duration: settingsController.state.animationsEnabled ? 140 : 0 } }
                        }
                    }
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    visible: appController.updateState.downloading || appController.updateState.checking
                    implicitWidth: updateMini.implicitWidth + 22; implicitHeight: 32; radius: 10
                    color: theme.colors.surfaceSoft
                    Text { id: updateMini; anchors.centerIn: parent; text: appController.updateState.downloading ? Math.round(appController.updateState.progress * 100) + "%" : "BUSCANDO…"; color: theme.colors.accent; font.pixelSize: 9; font.weight: Font.Bold }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            StackLayout {
                id: pages
                anchors.fill: parent
                currentIndex: appController.page
                Item { DownloadPage { anchors.fill: parent } }
                Item { QueuePage { anchors.fill: parent } }
                Item { ImageStudioPage { anchors.fill: parent } }
                Item { SettingsPage { anchors.fill: parent } }
            }
        }
    }

    Popup {
        id: toast
        property string toastKind: "info"
        property string toastTitle: ""
        property string toastMessage: ""
        x: window.width - width - 26
        y: 26
        width: Math.min(430, window.width - 52)
        implicitHeight: toastBody.implicitHeight + 28
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 170 }
            NumberAnimation { property: "y"; from: 5; duration: 200; easing.type: Easing.OutCubic }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 140 } }
        background: Rectangle { radius: 14; color: theme.colors.surfaceRaised; border.width: 1; border.color: toast.toastKind === "error" ? theme.colors.error : toast.toastKind === "success" ? theme.colors.success : theme.colors.primary }
        RowLayout {
            id: toastBody
            width: toast.width - 28; x: 14; y: 14; spacing: 11
            Rectangle { width: 10; height: 10; radius: 5; color: toast.toastKind === "error" ? theme.colors.error : toast.toastKind === "success" ? theme.colors.success : theme.colors.primary }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Text { Layout.fillWidth: true; text: toast.toastTitle; color: theme.colors.text; font.pixelSize: 13; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; text: toast.toastMessage; visible: text.length > 0; color: theme.colors.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            }
            XButton { compact: true; implicitWidth: 34; text: "×"; kind: "ghost"; onClicked: toast.close() }
        }
        Timer { interval: 4800; running: toast.opened; onTriggered: toast.close() }
    }

    Popup {
        id: updatePopup
        anchors.centerIn: parent
        width: Math.min(650, window.width - 70)
        implicitHeight: updatePopupContent.implicitHeight + 44
        modal: true; focus: true; padding: 0
        closePolicy: Popup.NoAutoClose
        background: Rectangle { radius: 20; color: theme.colors.surfaceRaised; border.color: theme.colors.primary; border.width: 1 }
        ColumnLayout {
            id: updatePopupContent
            x: 22; y: 22; width: updatePopup.width - 44; spacing: 14
            Text { text: "NUEVA VERSIÓN"; color: theme.colors.accent; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.2 }
            Text { Layout.fillWidth: true; text: "Xomacito " + (window.updateInfo.latest_version || ""); color: theme.colors.text; font.pixelSize: 25; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
            Text { Layout.fillWidth: true; text: window.updateInfo.release_notes || "Hay mejoras y correcciones listas para instalar."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap; maximumLineCount: 14; elide: Text.ElideRight }
            ProgressBar { Layout.fillWidth: true; visible: appController.updateState.downloading; value: appController.updateState.progress; indeterminate: value < 0 }
            Text { Layout.fillWidth: true; visible: appController.updateState.downloading; text: appController.updateState.status; color: theme.colors.textMuted; font.pixelSize: 11 }
            RowLayout {
                Layout.fillWidth: true
                XButton { text: "Ahora no"; kind: "ghost"; enabled: !appController.updateState.downloading; onClicked: { appController.declineUpdate(); updatePopup.close() } }
                Item { Layout.fillWidth: true }
                XButton { text: appController.updateState.downloading ? "Descargando…" : "Actualizar ahora"; enabled: !appController.updateState.downloading; onClicked: appController.acceptUpdate() }
            }
        }
    }

    Popup {
        id: noticePopup
        objectName: "releaseNoticePopup"
        anchors.centerIn: parent
        width: Math.min(760, window.width - 48)
        implicitHeight: noticePopupContent.implicitHeight + 36
        modal: true; focus: true; padding: 0
        closePolicy: Popup.NoAutoClose
        property var noticeInfo: ({})
        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220 }
                NumberAnimation { property: "scale"; from: 0.94; to: 1; duration: 260; easing.type: Easing.OutBack }
            }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 150 } }
        background: Rectangle {
            radius: 22
            color: theme.colors.surfaceRaised
            border.color: theme.colors.primary
            border.width: 1
        }
        ColumnLayout {
            id: noticePopupContent
            x: 18; y: 18; width: noticePopup.width - 36; spacing: 12

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 154
                radius: 17
                clip: true
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: theme.colors.backgroundAlt }
                    GradientStop { position: 1; color: theme.colors.primary }
                }

                Rectangle {
                    width: 210; height: 210; radius: 105
                    x: parent.width - 112; y: -92
                    color: theme.colors.accent; opacity: 0.16
                }
                Rectangle {
                    width: 150; height: 150; radius: 75
                    x: parent.width - 225; y: 92
                    color: theme.colors.background; opacity: 0.2
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 18

                    Rectangle {
                        Layout.preferredWidth: 82; Layout.preferredHeight: 82
                        radius: 41
                        color: theme.colors.background
                        border.color: "#FFE35A"
                        border.width: 3
                        Image {
                            anchors.fill: parent
                            anchors.margins: 6
                            source: appController.catSource
                            fillMode: Image.PreserveAspectFit
                            mipmap: true; smooth: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            text: noticePopup.noticeInfo.eyebrow || "ACTUALIZACIÓN INSTALADA"
                            color: theme.colors.accent
                            font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.4
                        }
                        Text {
                            Layout.fillWidth: true
                            text: noticePopup.noticeInfo.title || "Xomacito"
                            color: "white"
                            font.pixelSize: 30; font.weight: Font.Bold
                            wrapMode: Text.WordWrap
                        }
                        Item {
                            Layout.fillWidth: true
                            implicitHeight: 34
                            Text {
                                id: dowpSplash
                                objectName: "dowpSplash"
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                text: noticePopup.noticeInfo.subtitle || ""
                                color: "#FFE35A"
                                font.family: "Bahnschrift SemiBold"
                                font.pixelSize: 19
                                font.weight: Font.Black
                                font.letterSpacing: 0.5
                                rotation: -2.5
                                transformOrigin: Item.Center
                                SequentialAnimation on scale {
                                    loops: Animation.Infinite
                                    running: noticePopup.opened && settingsController.state.animationsEnabled
                                    NumberAnimation { to: 1.045; duration: 720; easing.type: Easing.InOutSine }
                                    NumberAnimation { to: 1; duration: 720; easing.type: Easing.InOutSine }
                                }
                            }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 6; Layout.rightMargin: 6
                text: noticePopup.noticeInfo.message || "Gracias por actualizar Xomacito."
                color: theme.colors.textMuted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 6; Layout.rightMargin: 6
                columns: noticePopup.width >= 650 ? 2 : 1
                columnSpacing: 9; rowSpacing: 8
                Repeater {
                    model: noticePopup.noticeInfo.highlights || []
                    Rectangle {
                        required property string modelData
                        Layout.fillWidth: true
                        implicitHeight: highlightText.implicitHeight + 22
                        radius: 11
                        color: theme.colors.surfaceSoft
                        border.color: theme.colors.border
                        border.width: 1
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 10; spacing: 9
                            Rectangle { width: 7; height: 7; radius: 3.5; color: theme.colors.accent }
                            Text {
                                id: highlightText
                                Layout.fillWidth: true
                                text: modelData
                                color: theme.colors.text
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 6; Layout.rightMargin: 6
                implicitHeight: thanksContent.implicitHeight + 22
                radius: 13
                color: theme.colors.backgroundAlt
                border.color: theme.colors.accent
                border.width: 1
                ColumnLayout {
                    id: thanksContent
                    x: 11; y: 11; width: parent.width - 22; spacing: 8
                    Text {
                        text: "PRINCIPALES CONTRIBUYENTES DE IDEAS"
                        color: theme.colors.accent
                        font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.preferredHeight: childrenRect.height
                        spacing: 7
                        Repeater {
                            model: noticePopup.noticeInfo.contributors || []
                            Rectangle {
                                required property string modelData
                                width: contributorName.implicitWidth + 24
                                height: 28
                                radius: 9
                                color: theme.colors.surfaceRaised
                                border.color: theme.colors.border
                                Text {
                                    id: contributorName
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: theme.colors.text
                                    font.pixelSize: 11; font.weight: Font.DemiBold
                                }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: noticePopup.noticeInfo.closing || ""
                        color: theme.colors.textMuted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                XButton { text: "¡A descargar!"; onClicked: noticePopup.close() }
            }
        }
    }

    Popup {
        id: dialogPopup
        anchors.centerIn: parent
        width: Math.min(560, window.width - 70)
        implicitHeight: dialogPopupContent.implicitHeight + 42
        modal: true; focus: true; padding: 0
        property string dialogKind: "question"
        property string dialogTitle: ""
        property string dialogMessage: ""
        property string defaultValue: ""
        closePolicy: Popup.NoAutoClose
        background: Rectangle { radius: 18; color: theme.colors.surfaceRaised; border.color: theme.colors.border; border.width: 1 }
        ColumnLayout {
            id: dialogPopupContent
            x: 21; y: 21; width: dialogPopup.width - 42; spacing: 14
            Text { Layout.fillWidth: true; text: dialogPopup.dialogTitle; color: theme.colors.text; font.pixelSize: 19; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
            Text { Layout.fillWidth: true; text: dialogPopup.dialogMessage; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap }
            XTextField { id: dialogInput; Layout.fillWidth: true; visible: dialogPopup.dialogKind === "input"; text: dialogPopup.defaultValue }
            RowLayout {
                Layout.fillWidth: true
                Repeater {
                    model: window.dialogOptions.length ? window.dialogOptions : [dialogPopup.defaultValue || "Aceptar"]
                    XButton {
                        required property string modelData
                        text: modelData
                        kind: index === 0 ? "primary" : "secondary"
                        onClicked: { var answer = dialogPopup.dialogKind === "input" ? dialogInput.text : modelData; dialogBroker.respond(window.dialogRequestId, answer); dialogPopup.close() }
                    }
                }
            }
        }
    }

    Connections {
        target: appController
        function onToastRequested(kind, title, message) { toast.toastKind = kind; toast.toastTitle = title; toast.toastMessage = message; toast.open() }
        function onUpdatePromptRequested(info) { window.updateInfo = info; updatePopup.open() }
        function onReleaseNoticeRequested(info) { noticePopup.noticeInfo = info; noticePopup.open() }
    }
    Connections {
        target: dialogBroker
        function onRequested(requestId, kind, title, message, options, defaultValue) { window.dialogRequestId = requestId; window.dialogOptions = options; dialogPopup.dialogKind = kind; dialogPopup.dialogTitle = title; dialogPopup.dialogMessage = message; dialogPopup.defaultValue = defaultValue; dialogInput.text = defaultValue; dialogPopup.open() }
    }
}
