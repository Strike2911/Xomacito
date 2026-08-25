import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    objectName: "queuePage"
    property var viewState: batchController.state
    property var selected: batchController.selected
    property bool dense: height <= 620 || width <= 1280
    property string expandedPlaylistJobId: ""

    function activateJob(jobId, jobType) {
        if (jobType === "PLAYLIST") {
            expandedPlaylistJobId = expandedPlaylistJobId === jobId ? "" : jobId
        } else {
            expandedPlaylistJobId = ""
        }
        batchController.selectJob(jobId)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: page.dense ? 6 : 10

        SectionTitle {
            Layout.fillWidth: true
            compact: page.dense
            eyebrow: "COLA DE TRABAJO"
            title: "Tu contenido, antes de descargar."
            description: "Revisa cada canción o video, elige su destino y procesa todo sin perder el control."
            number: "02"
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: queueInput.implicitHeight + (page.dense ? 18 : 24)
            cardColor: theme.colors.surfaceRaised
            radius: page.dense ? 14 : 18

            RowLayout {
                id: queueInput
                anchors.fill: parent
                anchors.margins: page.dense ? 9 : 12
                spacing: page.dense ? 7 : 9

                XTextField {
                    Layout.fillWidth: true
                    compact: page.dense
                    placeholderText: "Pega un enlace, una playlist o importa archivos"
                    text: viewState.url
                    onTextEdited: batchController.setValue("url", text)
                    onAccepted: batchController.analyze()
                }
                XButton {
                    text: viewState.analyzing ? "Analizando…" : "Añadir"
                    compact: true
                    enabled: !viewState.analyzing && viewState.url.length > 3
                    onClicked: batchController.analyze()
                }
                XButton {
                    text: "Archivos"
                    compact: true
                    kind: "secondary"
                    onClicked: batchController.importLocalFiles()
                }
                XButton {
                    text: "Carpeta"
                    compact: true
                    kind: "secondary"
                    onClicked: batchController.importFolder()
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: page.width >= 900 ? 5 : 1
            columnSpacing: page.dense ? 8 : 12
            rowSpacing: page.dense ? 8 : 12

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.width >= 900 ? 3 : 1
                Layout.minimumHeight: 240
                radius: page.dense ? 14 : 18

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: page.dense ? 10 : 14
                    spacing: page.dense ? 6 : 9

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "TRABAJOS"
                            color: theme.colors.primary
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            font.letterSpacing: 1
                        }
                        Item { Layout.fillWidth: true }
                        XButton {
                            compact: true
                            text: "Limpiar"
                            kind: "ghost"
                            onClicked: batchController.clearFinished()
                        }
                        XButton {
                            compact: true
                            text: "Reintentar"
                            kind: "ghost"
                            onClicked: batchController.resetStatuses()
                        }
                    }

                    Rectangle {
                        id: jobsFrame
                        Layout.fillWidth: true
                        Layout.fillHeight: !playlistPanel.visible
                        Layout.preferredHeight: playlistPanel.visible
                            ? (page.dense ? 76 : 96) : 1
                        Layout.minimumHeight: playlistPanel.visible
                            ? (page.dense ? 70 : 84) : 130
                        radius: 12
                        color: theme.colors.backgroundAlt
                        border.color: theme.colors.border
                        border.width: 1

                        ListView {
                            id: jobs
                            anchors.fill: parent
                            anchors.margins: 6
                            clip: true
                            spacing: 6
                            model: batchController.model
                            ScrollBar.vertical: XScrollBar {}

                            delegate: Rectangle {
                                id: jobDelegate
                                required property string jobId
                                required property string title
                                required property string status
                                required property string detail
                                required property real progress
                                required property string thumbnail
                                required property string jobType
                                required property int itemCount
                                required property string destinationTag
                                required property string outputFormat

                                width: jobs.width
                                height: page.dense ? 62 : 70
                                radius: 10
                                color: viewState.selectedJobId === jobId
                                    ? theme.colors.surfaceRaised : theme.colors.surface
                                border.width: viewState.selectedJobId === jobId ? 2 : 1
                                border.color: viewState.selectedJobId === jobId
                                    ? theme.colors.primary : theme.colors.border

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: page.activateJob(jobId, jobType)
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: page.dense ? 34 : 38
                                        Layout.preferredHeight: Layout.preferredWidth
                                        radius: 9
                                        color: theme.colors.surfaceSoft
                                        clip: true
                                        Image {
                                            id: jobThumbnail
                                            anchors.fill: parent
                                            source: thumbnail
                                            fillMode: Image.PreserveAspectCrop
                                            asynchronous: true
                                            cache: true
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            visible: jobThumbnail.status !== Image.Ready
                                            text: jobType === "PLAYLIST" ? "≡"
                                                : status === "COMPLETED" ? "✓" : "↓"
                                            color: "white"
                                            font.pixelSize: 16
                                            font.weight: Font.Bold
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Text {
                                            Layout.fillWidth: true
                                            text: title
                                            color: theme.colors.text
                                            font.pixelSize: page.dense ? 12 : 13
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: jobType === "PLAYLIST"
                                                ? itemCount + " elementos · salida " + outputFormat
                                                : detail + (destinationTag !== "Sin etiqueta"
                                                    ? " · " + destinationTag : "")
                                                    + " · salida " + outputFormat
                                            color: theme.colors.textMuted
                                            font.pixelSize: 9
                                            elide: Text.ElideRight
                                        }
                                        ProgressBar {
                                            Layout.fillWidth: true
                                            value: progress
                                            background: Rectangle {
                                                implicitHeight: 3
                                                radius: 2
                                                color: theme.colors.surfaceSoft
                                            }
                                            contentItem: Rectangle {
                                                implicitHeight: 3
                                                width: parent.width * progress
                                                radius: 2
                                                color: theme.colors.primary
                                            }
                                        }
                                    }

                                    Text {
                                        visible: jobType === "PLAYLIST"
                                        text: page.expandedPlaylistJobId === jobId ? "⌃" : "⌄"
                                        color: theme.colors.primary
                                        font.pixelSize: 15
                                        font.weight: Font.Bold
                                    }
                                    Text {
                                        text: status
                                        color: status === "COMPLETED" ? theme.colors.success
                                            : status === "FAILED" ? theme.colors.error
                                            : theme.colors.textMuted
                                        font.pixelSize: 8
                                        font.weight: Font.Bold
                                    }
                                    XButton {
                                        compact: true
                                        text: "×"
                                        kind: "ghost"
                                        implicitWidth: 34
                                        onClicked: batchController.removeJob(jobId)
                                    }
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: jobs.count === 0
                                text: "Tu cola está vacía\nAñade un enlace o importa archivos"
                                color: theme.colors.textMuted
                                horizontalAlignment: Text.AlignHCenter
                                lineHeight: 1.35
                                font.pixelSize: 11
                            }
                        }
                    }

                    Rectangle {
                        id: playlistPanel
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 150
                        visible: selected.jobType === "PLAYLIST"
                            && page.expandedPlaylistJobId === selected.jobId
                        radius: 12
                        color: theme.colors.backgroundAlt
                        border.width: 1
                        border.color: theme.colors.primary
                        clip: true

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 5

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "CONTENIDO"
                                    color: theme.colors.primary
                                    font.pixelSize: 9
                                    font.weight: Font.Bold
                                    font.letterSpacing: 1
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: Number(selected.itemCount || 0) + " de "
                                        + batchController.selectedPlaylistEntriesModel.count()
                                    color: theme.colors.textMuted
                                    font.pixelSize: 9
                                    horizontalAlignment: Text.AlignRight
                                }
                                XButton {
                                    compact: true
                                    text: "Todos"
                                    kind: "ghost"
                                    onClicked: batchController.selectAllPlaylistEntries(true)
                                }
                                XButton {
                                    compact: true
                                    text: "Ninguno"
                                    kind: "ghost"
                                    onClicked: batchController.selectAllPlaylistEntries(false)
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: page.dense ? 54 : 60
                                radius: 11
                                color: theme.colors.surface
                                border.width: 1
                                border.color: playlistCountSlider.activeFocus
                                    ? theme.colors.primary : theme.colors.border

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    anchors.topMargin: 6
                                    anchors.bottomMargin: 6
                                    spacing: 2

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: "ELEGIR CANTIDAD"
                                            color: theme.colors.textMuted
                                            font.pixelSize: 8
                                            font.weight: Font.Bold
                                            font.letterSpacing: 0.7
                                        }
                                        Item { Layout.fillWidth: true }
                                        Rectangle {
                                            implicitWidth: playlistCountLabel.implicitWidth + 14
                                            implicitHeight: 21
                                            radius: 8
                                            color: Qt.rgba(theme.colors.primary.r,
                                                           theme.colors.primary.g,
                                                           theme.colors.primary.b, 0.12)
                                            border.width: 1
                                            border.color: theme.colors.primary
                                            Text {
                                                id: playlistCountLabel
                                                anchors.centerIn: parent
                                                text: Math.round(playlistCountSlider.value) + " de "
                                                    + Number(page.viewState.playlistEntryCount || 0)
                                                color: theme.colors.primary
                                                font.pixelSize: 9
                                                font.weight: Font.Bold
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            text: "0"
                                            color: theme.colors.textMuted
                                            font.pixelSize: 9
                                            font.weight: Font.DemiBold
                                        }
                                        Slider {
                                            id: playlistCountSlider
                                            objectName: "playlistCountSlider"
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 24
                                            from: 0
                                            to: Number(page.viewState.playlistEntryCount || 0)
                                            stepSize: 1
                                            live: true
                                            snapMode: Slider.SnapAlways
                                            enabled: to > 0
                                            focusPolicy: Qt.StrongFocus
                                            onMoved: batchController.setPlaylistSelectionCount(Math.round(value))
                                            function selectFromPosition(pointerX) {
                                                const ratio = Math.max(0, Math.min(1,
                                                    (pointerX - leftPadding) / Math.max(1, availableWidth)))
                                                const requested = Math.round(from + ratio * (to - from))
                                                value = requested
                                                batchController.setPlaylistSelectionCount(requested)
                                            }
                                            Keys.onLeftPressed: function(event) {
                                                batchController.setPlaylistSelectionCount(
                                                    Math.max(0, Number(page.viewState.playlistSelectionCount || 0) - 1))
                                                event.accepted = true
                                            }
                                            Keys.onRightPressed: function(event) {
                                                batchController.setPlaylistSelectionCount(
                                                    Math.min(to, Number(page.viewState.playlistSelectionCount || 0) + 1))
                                                event.accepted = true
                                            }
                                            ToolTip.visible: playlistDragArea.pressed
                                            ToolTip.text: Math.round(value) + " elemento(s) seleccionado(s)"

                                            Binding {
                                                target: playlistCountSlider
                                                property: "value"
                                                value: Number(page.viewState.playlistSelectionCount || 0)
                                            }

                                            background: Rectangle {
                                                x: playlistCountSlider.leftPadding
                                                y: playlistCountSlider.topPadding
                                                    + playlistCountSlider.availableHeight / 2 - height / 2
                                                implicitWidth: 200
                                                implicitHeight: 7
                                                width: playlistCountSlider.availableWidth
                                                height: implicitHeight
                                                radius: height / 2
                                                color: theme.colors.surfaceSoft
                                                Rectangle {
                                                    width: playlistCountSlider.visualPosition * parent.width
                                                    height: parent.height
                                                    radius: parent.radius
                                                    color: playlistCountSlider.enabled
                                                        ? theme.colors.primary : theme.colors.textDim
                                                }
                                            }

                                            handle: Rectangle {
                                                x: playlistCountSlider.leftPadding
                                                    + playlistCountSlider.visualPosition
                                                      * (playlistCountSlider.availableWidth - width)
                                                y: playlistCountSlider.topPadding
                                                    + playlistCountSlider.availableHeight / 2 - height / 2
                                                implicitWidth: playlistDragArea.pressed ? 23 : 19
                                                implicitHeight: implicitWidth
                                                radius: width / 2
                                                color: playlistCountSlider.enabled
                                                    ? theme.colors.primary : theme.colors.textDim
                                                border.width: 3
                                                border.color: theme.colors.backgroundAlt
                                                scale: playlistDragArea.pressed ? 1.12 : 1
                                                Behavior on scale { NumberAnimation { duration: 100 } }
                                            }

                                            MouseArea {
                                                id: playlistDragArea
                                                objectName: "playlistCountDragArea"
                                                anchors.fill: parent
                                                z: 10
                                                enabled: playlistCountSlider.enabled
                                                hoverEnabled: true
                                                preventStealing: true
                                                cursorShape: Qt.PointingHandCursor
                                                onPressed: function(mouse) {
                                                    playlistCountSlider.forceActiveFocus()
                                                    playlistCountSlider.selectFromPosition(mouse.x)
                                                }
                                                onPositionChanged: function(mouse) {
                                                    if (pressed)
                                                        playlistCountSlider.selectFromPosition(mouse.x)
                                                }
                                            }
                                        }
                                        Text {
                                            text: Number(page.viewState.playlistEntryCount || 0)
                                            color: theme.colors.textMuted
                                            font.pixelSize: 9
                                            font.weight: Font.DemiBold
                                        }
                                    }
                                }
                            }

                            ListView {
                                id: playlistEntries
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 4
                                model: batchController.selectedPlaylistEntriesModel
                                boundsBehavior: Flickable.StopAtBounds
                                reuseItems: true
                                cacheBuffer: 300
                                ScrollBar.vertical: XScrollBar {}

                                delegate: Rectangle {
                                    width: playlistEntries.width
                                    height: page.dense ? 42 : 49
                                    radius: 8
                                    color: selected
                                        ? theme.colors.surfaceSoft : theme.colors.surface
                                    border.width: 1
                                    border.color: selected
                                        ? theme.colors.primary : theme.colors.border

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 5
                                        spacing: 7
                                        XSwitch {
                                            compact: true
                                            checked: selected
                                            onToggled: batchController.setPlaylistEntrySelected(
                                                index, checked)
                                        }
                                        Rectangle {
                                            Layout.preferredWidth: page.dense ? 48 : 56
                                            Layout.preferredHeight: page.dense ? 30 : 36
                                            radius: 6
                                            color: theme.colors.surfaceRaised
                                            clip: true
                                            Image {
                                                id: entryThumbnail
                                                anchors.fill: parent
                                                source: thumbnail
                                                fillMode: Image.PreserveAspectCrop
                                                asynchronous: true
                                                cache: true
                                            }
                                            Text {
                                                anchors.centerIn: parent
                                                visible: entryThumbnail.status !== Image.Ready
                                                text: "♪"
                                                color: theme.colors.textMuted
                                                font.pixelSize: 15
                                            }
                                        }
                                        Text {
                                            text: (index + 1) + "."
                                            color: theme.colors.textDim
                                            font.pixelSize: 9
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: title
                                            color: selected
                                                ? theme.colors.text : theme.colors.textMuted
                                            font.pixelSize: page.dense ? 10 : 11
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            XCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.columnSpan: page.width >= 900 ? 2 : 1
                Layout.minimumHeight: 240
                radius: page.dense ? 14 : 18

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: page.dense ? 10 : 14
                    spacing: page.dense ? 7 : 10

                    SectionTitle {
                        Layout.fillWidth: true
                        compact: true
                        eyebrow: selected.jobId
                            ? "TRABAJO SELECCIONADO" : "AJUSTES PARA NUEVOS TRABAJOS"
                        title: selected.title || "Configura la cola"
                        description: selected.detail || "Elige sólo lo esencial; lo técnico está separado."
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        LabeledControl {
                            Layout.fillWidth: true
                            compact: true
                            label: "Formato"
                            XComboBox {
                                Layout.fillWidth: true
                                compact: true
                                model: ["Video+Audio", "Solo Audio"]
                                currentIndex: Math.max(0, find(
                                    selected.mode || viewState.globalMode))
                                onActivated: selected.jobId
                                    ? batchController.setSelectedOption("mode", currentText)
                                    : batchController.setValue("globalMode", currentText)
                            }
                        }
                        LabeledControl {
                            Layout.fillWidth: true
                            compact: true
                            label: "Calidad"
                            XComboBox {
                                Layout.fillWidth: true
                                compact: true
                                model: ["Mejor Calidad (Auto)", "1080p", "720p",
                                    "480p", "Solo Audio (Mejor)"]
                                currentIndex: Math.max(0, find(
                                    selected.quality || viewState.globalQuality))
                                onActivated: selected.jobId
                                    ? batchController.setSelectedOption("quality", currentText)
                                    : batchController.setValue("globalQuality", currentText)
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: !selected.jobId
                        spacing: 8
                        XSwitch {
                            compact: true
                            text: "Detectar playlists"
                            checked: viewState.playlistAnalysis
                            onToggled: batchController.setValue("playlistAnalysis", checked)
                        }
                        XSwitch {
                            compact: true
                            text: "Análisis rápido"
                            checked: viewState.fastMode
                            enabled: viewState.playlistAnalysis
                            onToggled: batchController.setValue("fastMode", checked)
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 38
                        radius: 10
                        color: theme.colors.surfaceRaised
                        border.width: 1
                        border.color: theme.colors.border
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text {
                                Layout.fillWidth: true
                                text: "Opciones avanzadas"
                                color: theme.colors.text
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                text: "›"
                                color: theme.colors.primary
                                font.pixelSize: 18
                                font.weight: Font.Bold
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: advanced.open()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: page.dense ? 48 : 62
                        radius: 10
                        color: theme.colors.backgroundAlt
                        border.width: 1
                        border.color: theme.colors.border
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 8
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: selected.jobId
                                    ? theme.colors.success : theme.colors.primary
                            }
                            Text {
                                Layout.fillWidth: true
                                text: selected.jobId
                                    ? (selected.jobType === "PLAYLIST"
                                        ? Number(selected.itemCount || 0)
                                            + " elementos seleccionados · salida " + selected.outputFormat
                                        : (selected.detail || "Trabajo listo")
                                            + " · salida " + selected.outputFormat)
                                    : "Los nuevos trabajos usarán estos ajustes. La salida se mostrará antes de iniciar."
                                color: theme.colors.textMuted
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: destinationRow.implicitHeight + (page.dense ? 16 : 22)
            cardColor: theme.colors.surfaceRaised
            radius: page.dense ? 14 : 18

            RowLayout {
                id: destinationRow
                anchors.fill: parent
                anchors.margins: page.dense ? 8 : 11
                spacing: page.dense ? 7 : 9

                LabeledControl {
                    Layout.fillWidth: true
                    compact: true
                    label: "Carpeta de salida"
                    hint: page.dense ? "" : (viewState.selectedTag === "Sin etiqueta"
                        ? "Destino general de la cola."
                        : "Esta carpeta pertenece a la etiqueta seleccionada.")
                    XTextField {
                        Layout.fillWidth: true
                        compact: true
                        readOnly: viewState.selectedTag !== "Sin etiqueta"
                        text: viewState.effectiveOutputPath
                        onEditingFinished: {
                            if (!readOnly)
                                batchController.setValue("outputPath", text)
                        }
                    }
                }
                XButton {
                    text: "Elegir carpeta"
                    compact: true
                    kind: "secondary"
                    onClicked: batchController.chooseOutputFolder()
                }
                LabeledControl {
                    Layout.preferredWidth: page.dense ? 210 : 245
                    compact: true
                    label: "Etiqueta de destino"
                    hint: page.dense ? "" : "Color y carpeta se recuerdan."
                    Rectangle {
                        width: 9
                        height: 9
                        radius: 5
                        color: viewState.selectedTagColor
                    }
                    XComboBox {
                        Layout.fillWidth: true
                        compact: true
                        model: batchController.downloadTags
                        currentIndex: Math.max(0, find(viewState.selectedTag))
                        onActivated: batchController.setValue("selectedTag", currentText)
                    }
                }
                XButton {
                    text: "+"
                    compact: true
                    kind: "secondary"
                    implicitWidth: 40
                    onClicked: batchController.createDownloadTag()
                }
                XButton {
                    text: "−"
                    compact: true
                    kind: "ghost"
                    implicitWidth: 40
                    enabled: viewState.selectedTag !== "Sin etiqueta"
                    onClicked: batchController.deleteSelectedTag()
                }
                XButton {
                    text: "Abrir"
                    compact: true
                    kind: "ghost"
                    onClicked: batchController.openOutput()
                }
                XButton {
                    text: viewState.running ? "Pausar cola" : "Iniciar cola"
                    compact: page.dense
                    kind: viewState.running ? "danger" : "primary"
                    onClicked: batchController.toggleQueue()
                }
            }
        }

        ProgressStrip {
            Layout.fillWidth: true
            compact: page.dense
            value: viewState.progress
            status: viewState.status
            busy: viewState.running || viewState.analyzing
        }
    }

    Popup {
        id: advanced
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(650, page.width - 70)
        height: Math.min(480, page.height - 50)
        modal: true
        focus: true
        padding: 16
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            radius: 16
            color: theme.colors.surfaceRaised
            border.width: 1
            border.color: theme.colors.primary
        }
        Overlay.modal: Rectangle {
            color: "#99000912"
        }

        contentItem: ColumnLayout {
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: "Opciones avanzadas"
                        color: theme.colors.text
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: "Sólo cambia lo necesario para este flujo."
                        color: theme.colors.textMuted
                        font.pixelSize: 10
                    }
                }
                XButton {
                    text: "Cerrar"
                    compact: true
                    kind: "ghost"
                    onClicked: advanced.close()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme.colors.border
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical: XScrollBar {}

                ColumnLayout {
                    width: advanced.availableWidth - 8
                    spacing: 8

                    Text {
                        text: selected.jobId ? "ESTE TRABAJO" : "NUEVOS TRABAJOS"
                        color: theme.colors.primary
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        font.letterSpacing: 1
                    }
                    XSwitch {
                        compact: true
                        visible: !selected.jobId
                        text: "Descargar automáticamente al añadir"
                        checked: viewState.autoDownload
                        onToggled: batchController.setValue("autoDownload", checked)
                    }
                    XSwitch {
                        compact: true
                        visible: !selected.jobId
                        text: "Enviar imágenes al Estudio"
                        checked: viewState.autoSendImages
                        onToggled: batchController.setValue("autoSendImages", checked)
                    }
                    XSwitch {
                        compact: true
                        text: "Recodificar resultados"
                        checked: selected.jobId ? !!selected.recode : viewState.globalRecode
                        onToggled: selected.jobId
                            ? batchController.setSelectedOption("recode", checked)
                            : batchController.setValue("globalRecode", checked)
                    }
                    LabeledControl {
                        Layout.fillWidth: true
                        compact: true
                        label: "Preset de conversión"
                        XComboBox {
                            Layout.fillWidth: true
                            compact: true
                            model: (selected.jobId ? selected.mode : viewState.globalMode) === "Solo Audio"
                                ? presetStore.audioPresets : presetStore.videoPresets
                            currentIndex: Math.max(0, find(
                                selected.preset || viewState.globalPreset))
                            onActivated: selected.jobId
                                ? batchController.setSelectedOption("preset", currentText)
                                : batchController.setValue("globalPreset", currentText)
                        }
                    }
                    XSwitch {
                        compact: true
                        text: "Mantener archivos originales"
                        checked: selected.jobId
                            ? !!selected.keepOriginal : viewState.globalKeepOriginal
                        onToggled: selected.jobId
                            ? batchController.setSelectedOption("keepOriginal", checked)
                            : batchController.setValue("globalKeepOriginal", checked)
                    }
                    XSwitch {
                        compact: true
                        text: "Conservar todas las pistas de audio"
                        checked: viewState.allAudioTracks
                        onToggled: batchController.setValue("allAudioTracks", checked)
                    }
                    XSwitch {
                        compact: true
                        visible: (selected.jobId ? selected.mode : viewState.globalMode) === "Solo Audio"
                        text: "Incluir portada en el archivo de audio"
                        checked: selected.jobId
                            ? !!selected.embedAudioCover : !!viewState.globalEmbedAudioCover
                        onToggled: selected.jobId
                            ? batchController.setSelectedOption("embedAudioCover", checked)
                            : batchController.setValue("globalEmbedAudioCover", checked)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: theme.colors.border
                    }
                    Text {
                        text: "ARCHIVOS Y CARPETAS"
                        color: theme.colors.primary
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        font.letterSpacing: 1
                    }
                    LabeledControl {
                        Layout.fillWidth: true
                        compact: true
                        label: "Si el archivo ya existe"
                        XComboBox {
                            Layout.fillWidth: true
                            compact: true
                            model: ["Renombrar", "Sobrescribir", "Omitir", "Preguntar"]
                            currentIndex: Math.max(0, find(viewState.conflictPolicy))
                            onActivated: batchController.setValue("conflictPolicy", currentText)
                        }
                    }
                    XSwitch {
                        compact: true
                        text: "Crear una subcarpeta para este lote"
                        checked: viewState.createSubfolder
                        onToggled: batchController.setValue("createSubfolder", checked)
                    }
                    XTextField {
                        Layout.fillWidth: true
                        compact: true
                        visible: viewState.createSubfolder
                        text: viewState.subfolderName
                        placeholderText: "Nombre de la subcarpeta"
                        onEditingFinished: batchController.setValue("subfolderName", text)
                    }
                }
            }
        }
    }
}
