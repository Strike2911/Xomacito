import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property bool dense: height <= 520

    ColumnLayout {
        anchors.fill: parent
        spacing: root.dense ? 8 : 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 2
                Text {
                    text: "COLECCIÓN GATUNA"
                    color: theme.colors.primary
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    font.letterSpacing: 1.2
                }
                Text {
                    text: "Desbloquea. Colecciona. Equipa."
                    color: theme.colors.text
                    font.pixelSize: root.dense ? 20 : 24
                    font.weight: Font.DemiBold
                }
            }
            Item { Layout.fillWidth: true }
            Rectangle {
                implicitWidth: collectionCount.implicitWidth + 24
                implicitHeight: 30
                radius: 10
                color: theme.colors.surfaceSoft
                border.color: theme.colors.border
                Text {
                    id: collectionCount
                    anchors.centerIn: parent
                    text: catController.state.unlockedCount + " / " + catController.state.totalCount
                    color: theme.colors.text
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                }
            }
        }

        XCard {
            Layout.fillWidth: true
            implicitHeight: root.dense ? 112 : 132
            cardColor: theme.colors.surfaceRaised
            RowLayout {
                anchors.fill: parent
                anchors.margins: root.dense ? 13 : 17
                spacing: root.dense ? 14 : 20

                CatAvatar {
                    Layout.preferredWidth: root.dense ? 78 : 94
                    Layout.preferredHeight: Layout.preferredWidth
                    source: catController.state.equippedSource
                    rarity: catController.state.equippedRarity
                    rarityColor: catController.state.equippedColor
                    animatedEffects: settingsController.state.animationsEnabled
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text {
                        text: "GATO EQUIPADO"
                        color: catController.state.equippedColor
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        font.letterSpacing: 1
                    }
                    Text {
                        Layout.fillWidth: true
                        text: catController.state.equippedName
                        color: theme.colors.text
                        font.pixelSize: root.dense ? 17 : 20
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    Text {
                        text: catController.state.equippedStars
                        color: catController.state.equippedColor
                        font.pixelSize: 15
                        font.letterSpacing: 2
                    }
                }

                Rectangle {
                    Layout.preferredWidth: Math.min(360, Math.max(260, root.width * 0.29))
                    Layout.fillHeight: true
                    radius: 13
                    color: theme.colors.backgroundAlt
                    border.color: theme.colors.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "PRÓXIMA TIRADA"; color: theme.colors.textMuted; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                            Item { Layout.fillWidth: true }
                            Text { text: catController.state.downloadProgress + "/10"; color: theme.colors.accent; font.pixelSize: 10; font.weight: Font.Bold }
                        }
                        ProgressBar {
                            Layout.fillWidth: true
                            value: catController.state.downloadProgressRatio
                        }
                        Text {
                            Layout.fillWidth: true
                            text: catController.state.dailyAvailable
                                  ? "Tu tirada gratis de hoy está lista."
                                  : catController.state.earnedRolls
                                    ? "Tienes " + catController.state.earnedRolls + " tirada(s) acumulada(s)."
                                    : "Cada descarga exitosa suma progreso."
                            color: theme.colors.textMuted
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                    }
                }

                XButton {
                    objectName: "catRollButton"
                    Layout.preferredWidth: root.dense ? 172 : 205
                    text: catController.state.rollButtonText
                    enabled: catController.state.canRoll
                    onClicked: catController.roll()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "TU COLECCIÓN"
                color: theme.colors.text
                font.pixelSize: 12
                font.weight: Font.Bold
                font.letterSpacing: 0.8
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "1★ común   ·   2★ peculiar   ·   3★ raro   ·   4★ épico   ·   5★ legendario"
                color: theme.colors.textMuted
                font.pixelSize: 10
            }
        }

        GridView {
            id: collectionGrid
            objectName: "catCollectionGrid"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: catController.model
            cellWidth: Math.max(150, width / Math.max(1, Math.floor(width / 170)))
            cellHeight: root.dense ? 166 : 184
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: XScrollBar { }

            delegate: Item {
                id: catCard
                required property string catId
                required property string name
                required property url source
                required property int rarity
                required property color rarityColor
                required property string stars
                required property bool unlocked
                required property bool equipped
                required property int duplicateCount
                width: collectionGrid.cellWidth
                height: collectionGrid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: 15
                    color: equipped ? theme.colors.surfaceRaised : theme.colors.surface
                    border.width: equipped ? 2 : 1
                    border.color: equipped ? rarityColor : theme.colors.border

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            CatAvatar {
                                anchors.centerIn: parent
                                width: Math.min(parent.width, parent.height) - 3
                                height: width
                                source: catCard.source
                                rarity: catCard.rarity
                                rarityColor: catCard.rarityColor
                                opacity: catCard.unlocked ? 1 : 0.2
                            }
                            Rectangle {
                                anchors.centerIn: parent
                                visible: !catCard.unlocked
                                width: 34; height: 34; radius: 17
                                color: theme.colors.scrim
                                Text { anchors.centerIn: parent; text: "?"; color: theme.colors.text; font.pixelSize: 18; font.weight: Font.Bold }
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: name
                            color: unlocked ? theme.colors.text : theme.colors.textDim
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: stars; color: rarityColor; font.pixelSize: 10; font.letterSpacing: 1 }
                            Item { Layout.fillWidth: true }
                            Text { visible: duplicateCount > 0; text: "+" + duplicateCount; color: theme.colors.textMuted; font.pixelSize: 9 }
                        }
                        XButton {
                            Layout.fillWidth: true
                            implicitHeight: 29
                            compact: true
                            kind: equipped ? "success" : "secondary"
                            text: equipped ? "Equipado" : unlocked ? "Equipar" : "Bloqueado"
                            enabled: unlocked && !equipped
                            onClicked: catController.equip(catId)
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: revealPopup
        objectName: "catRevealPopup"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(720, root.width - 32)
        height: Math.min(590, root.height - 24)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose
        property var result: ({})
        property real revealProgress: 1
        readonly property int resultRarity: Math.max(1, Math.min(5, Number(result.rarity || 1)))
        readonly property color revealColor: result.rarityColor || theme.colors.primary
        readonly property string rarityTitle: ["", "COMÚN", "PECULIAR", "RARO", "ÉPICO", "LEGENDARIO"][resultRarity]

        function beginReveal() {
            revealProgress = settingsController.state.animationsEnabled ? 0 : 1
            open()
            if (settingsController.state.animationsEnabled)
                revealSequence.restart()
        }

        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 180 }
                NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 260; easing.type: Easing.OutCubic }
            }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 160 } }

        Overlay.modal: Rectangle {
            color: "#D9000710"
        }

        background: Rectangle {
            radius: 26
            color: theme.colors.backgroundAlt
            border.width: revealPopup.resultRarity >= 4 ? 3 : 2
            border.color: revealPopup.revealColor
        }

        SequentialAnimation {
            id: revealSequence
            running: false
            NumberAnimation {
                target: revealPopup
                property: "revealProgress"
                from: 0
                to: 0.48
                duration: revealPopup.resultRarity >= 5 ? 1050 : revealPopup.resultRarity >= 4 ? 860 : 620
                easing.type: Easing.InCubic
            }
            NumberAnimation {
                target: revealPopup
                property: "revealProgress"
                to: 0.66
                duration: 150
                easing.type: Easing.OutExpo
            }
            PauseAnimation { duration: revealPopup.resultRarity >= 4 ? 90 : 40 }
            NumberAnimation {
                target: revealPopup
                property: "revealProgress"
                to: 1
                duration: revealPopup.resultRarity >= 4 ? 560 : 420
                easing.type: Easing.OutBack
            }
        }

        Item {
            id: revealEffects
            anchors.fill: parent
            clip: true

            Rectangle {
                anchors.fill: parent
                radius: 24
                gradient: Gradient {
                    GradientStop { position: 0; color: theme.colors.backgroundAlt }
                    GradientStop { position: 0.52; color: Qt.rgba(revealPopup.revealColor.r, revealPopup.revealColor.g, revealPopup.revealColor.b, revealPopup.resultRarity >= 4 ? 0.15 : 0.08) }
                    GradientStop { position: 1; color: theme.colors.surface }
                }
            }

            Item {
                id: rayField
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height) * 0.94
                height: width
                scale: 0.56 + revealPopup.revealProgress * 0.58
                opacity: 0.08 + revealPopup.resultRarity * 0.035

                Repeater {
                    model: revealPopup.resultRarity >= 5 ? 28 : revealPopup.resultRarity >= 4 ? 22 : 14
                    Rectangle {
                        required property int index
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: parent.height / 2 - height
                        width: index % 3 === 0 ? 5 : 3
                        height: parent.height * (index % 4 === 0 ? 0.48 : 0.39)
                        radius: width / 2
                        color: index % 5 === 0 && revealPopup.resultRarity >= 4 ? "white" : revealPopup.revealColor
                        transformOrigin: Item.Bottom
                        rotation: index * (360 / (revealPopup.resultRarity >= 5 ? 28 : revealPopup.resultRarity >= 4 ? 22 : 14))
                    }
                }

                RotationAnimation on rotation {
                    running: revealPopup.opened && settingsController.state.animationsEnabled
                    from: 0
                    to: 360
                    duration: revealPopup.resultRarity >= 5 ? 10000 : 16000
                    loops: Animation.Infinite
                }
            }

            Repeater {
                model: revealPopup.resultRarity >= 5 ? 30 : revealPopup.resultRarity >= 4 ? 22 : 14
                Rectangle {
                    required property int index
                    property real angle: index * Math.PI * 2 / (revealPopup.resultRarity >= 5 ? 30 : revealPopup.resultRarity >= 4 ? 22 : 14)
                    property real travel: (70 + (index % 6) * 27) * Math.max(0, (revealPopup.revealProgress - 0.42) / 0.58)
                    width: 3 + (index % 3) * 2
                    height: width
                    radius: width / 2
                    color: index % 4 === 0 ? "white" : revealPopup.revealColor
                    opacity: revealPopup.revealProgress < 0.42 ? 0 : Math.max(0.08, 1 - travel / 260)
                    x: revealPopup.width / 2 + Math.cos(angle) * travel - width / 2
                    y: revealPopup.height / 2 + Math.sin(angle) * travel - height / 2
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height) * (0.46 + revealPopup.revealProgress * 0.34)
                height: width
                radius: width / 2
                color: "transparent"
                border.width: revealPopup.resultRarity >= 5 ? 5 : revealPopup.resultRarity >= 4 ? 3 : 2
                border.color: revealPopup.revealColor
                opacity: revealPopup.revealProgress < 0.58 ? 0.7 : 0.18
            }

            Rectangle {
                id: energyCore
                anchors.centerIn: parent
                width: 82 + revealPopup.revealProgress * 86
                height: width
                radius: width / 2
                visible: revealPopup.revealProgress < 0.7
                color: Qt.rgba(revealPopup.revealColor.r, revealPopup.revealColor.g, revealPopup.revealColor.b, 0.28)
                border.width: revealPopup.resultRarity >= 4 ? 5 : 3
                border.color: revealPopup.revealProgress > 0.5 ? "white" : revealPopup.revealColor
                scale: 0.78 + Math.sin(revealPopup.revealProgress * Math.PI * 8) * 0.08

                Text {
                    anchors.centerIn: parent
                    text: revealPopup.resultRarity >= 5 ? "✦" : "★"
                    color: "white"
                    font.pixelSize: parent.width * 0.34
                    opacity: 0.72
                }
            }

            Rectangle {
                anchors.fill: parent
                radius: 24
                color: "white"
                opacity: Math.max(0, 1 - Math.abs(revealPopup.revealProgress - 0.64) * 18)
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.dense ? 14 : 20
            spacing: 6
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: revealPopup.revealProgress < 0.58
                      ? (revealPopup.resultRarity >= 4 ? "UNA PRESENCIA EXTRAORDINARIA…" : "DESCUBRIENDO TU GATO…")
                      : revealPopup.result.isNew ? "¡NUEVO GATO DESBLOQUEADO!" : "GATO REPETIDO · BRILLO +1"
                color: revealPopup.revealProgress < 0.58 ? theme.colors.text : revealPopup.revealColor
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 1.4
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Rectangle {
                    id: revealCard
                    objectName: "catRevealCard"
                    anchors.centerIn: parent
                    width: Math.min(350, parent.width - 18)
                    height: Math.min(350, parent.height - 4)
                    radius: 24
                    color: theme.colors.surfaceRaised
                    border.width: revealPopup.resultRarity >= 5 ? 4 : revealPopup.resultRarity >= 4 ? 3 : 2
                    border.color: revealPopup.revealColor
                    opacity: Math.max(0, Math.min(1, (revealPopup.revealProgress - 0.57) / 0.16))
                    scale: 0.66 + Math.max(0, Math.min(1, (revealPopup.revealProgress - 0.57) / 0.43)) * 0.34
                    rotation: -7 + Math.max(0, Math.min(1, (revealPopup.revealProgress - 0.57) / 0.43)) * 7

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 7
                        radius: 18
                        color: "transparent"
                        border.width: 1
                        border.color: Qt.rgba(revealPopup.revealColor.r, revealPopup.revealColor.g, revealPopup.revealColor.b, 0.5)
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: root.dense ? 12 : 16
                        spacing: root.dense ? 3 : 6
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: revealPopup.rarityTitle
                            color: revealPopup.revealColor
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            font.letterSpacing: 2
                        }
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            CatAvatar {
                                anchors.centerIn: parent
                                width: Math.min(root.dense ? 142 : 176, parent.height - 2)
                                height: width
                                source: revealPopup.result.source || ""
                                rarity: revealPopup.resultRarity
                                rarityColor: revealPopup.revealColor
                                animatedEffects: revealPopup.opened && revealPopup.revealProgress >= 0.66 && settingsController.state.animationsEnabled
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: revealPopup.result.name || ""
                            color: theme.colors.text
                            font.pixelSize: root.dense ? 20 : 25
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: revealPopup.result.stars || ""
                            color: revealPopup.revealColor
                            font.pixelSize: root.dense ? 17 : 21
                            font.letterSpacing: 5
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                opacity: Math.max(0, Math.min(1, (revealPopup.revealProgress - 0.82) / 0.18))
                enabled: revealPopup.revealProgress >= 0.98
                Item { Layout.fillWidth: true }
                XButton {
                    visible: revealPopup.result.isNew === true
                    text: "Equipar ahora"
                    kind: "secondary"
                    onClicked: { catController.equip(revealPopup.result.catId); revealPopup.close() }
                }
                XButton { text: "Continuar"; onClicked: revealPopup.close() }
                Item { Layout.fillWidth: true }
            }
        }
    }

    Connections {
        target: catController
        function onRevealRequested(result) {
            revealPopup.result = result
            revealPopup.beginReveal()
        }
    }
}
