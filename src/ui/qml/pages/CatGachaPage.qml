import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property bool dense: height <= 520
    readonly property bool revealOpen: revealPopup.opened
    signal revealFinished()

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
                    text: catController.state.isPlatinum
                        ? "Colección completa. Mejora sus auras."
                        : "Desbloquea. Colecciona. Equipa."
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
                    animationStyle: catController.state.equippedAnimationStyle
                    effectLevel: catController.state.equippedEffectLevel
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
                    Text {
                        visible: Number(catController.state.equippedEffectLevel || 0) > 0
                        text: "AURA " + catController.state.equippedEffectLevel
                            + " · " + String(catController.state.equippedEffectName || "").toUpperCase()
                        color: catController.state.equippedColor
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        font.letterSpacing: 1
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
                            text: catController.state.isPlatinum
                                  ? "Cada gato repetido mejora su aura hasta nivel 5."
                                  : catController.state.dailyAvailable
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
                text: "1★ común  ·  2★ peculiar  ·  3★ raro  ·  4★ épico  ·  5★ legendario  ·  6★ mítico"
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
                required property string animationStyle
                required property bool unlocked
                required property bool equipped
                required property int duplicateCount
                required property int effectLevel
                required property string effectName
                width: collectionGrid.cellWidth
                height: collectionGrid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: 15
                    color: equipped ? theme.colors.surfaceRaised : theme.colors.surface
                    border.width: equipped || effectLevel > 0 ? 2 : 1
                    border.color: equipped || effectLevel > 0 ? rarityColor : theme.colors.border

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
                                animationStyle: catCard.animationStyle
                                effectLevel: catCard.effectLevel
                                animatedEffects: catCard.unlocked
                                    && settingsController.state.animationsEnabled
                                    && catCard.effectLevel > 0
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
                            Rectangle {
                                visible: effectLevel > 0
                                implicitWidth: auraLabel.implicitWidth + 12
                                implicitHeight: 20
                                radius: 7
                                color: Qt.rgba(rarityColor.r, rarityColor.g, rarityColor.b, 0.14)
                                border.width: 1
                                border.color: rarityColor
                                Text {
                                    id: auraLabel
                                    anchors.centerIn: parent
                                    text: "AURA " + effectLevel
                                    color: rarityColor
                                    font.pixelSize: 8
                                    font.weight: Font.Bold
                                    font.letterSpacing: 0.5
                                }
                                ToolTip.visible: auraBadgeMouse.containsMouse
                                ToolTip.text: effectName + " · " + duplicateCount
                                    + " repetido(s)"
                                MouseArea {
                                    id: auraBadgeMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }
                            }
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
        // El premio puede abrirse desde cualquier pestaña. La pestaña de
        // Personalización mide 0x0 mientras está inactiva, pero el overlay global no.
        readonly property real overlayWidth: parent && parent.width > 0 ? parent.width : 760
        readonly property real overlayHeight: parent && parent.height > 0 ? parent.height : 640
        readonly property bool compactLayout: height <= 500
        width: Math.max(320, Math.min(720, overlayWidth - 32))
        height: Math.max(390, Math.min(590, overlayHeight - 24))
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose
        onClosed: root.revealFinished()
        property var result: ({})
        property real revealProgress: 1
        readonly property int resultRarity: Math.max(1, Math.min(6, Number(result.rarity || 1)))
        readonly property color revealColor: result.animationStyle === "strike-apex"
                                             ? "#8476E8" : result.rarityColor || theme.colors.primary
        readonly property string animationStyle: result.animationStyle || ""
        readonly property string rarityTitle: resultRarity < 6
                                                ? ["", "COMÚN", "PECULIAR", "RARO", "ÉPICO", "LEGENDARIO"][resultRarity]
                                                : animationStyle === "strike-apex"
                                                  ? "MÍTICO SUPREMO"
                                                : animationStyle === "playera-prismatic"
                                                  ? "MÍTICO PRISMÁTICO"
                                                  : animationStyle === "zarking-cyber"
                                                    ? "MÍTICO CIBERNÉTICO"
                                                    : animationStyle === "blackbull-noir"
                                                      ? "MÍTICO BLACK BULL"
                                                    : "MÍTICO ARCANO"
        readonly property bool arcaneMage: result.animationStyle === "arcane-mage"
        readonly property bool strikeApex: result.animationStyle === "strike-apex"
        readonly property bool mythicCat: resultRarity >= 6

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
            border.width: revealPopup.resultRarity >= 6 ? 5 : revealPopup.resultRarity >= 4 ? 3 : 2
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
                duration: revealPopup.strikeApex ? 1450 : revealPopup.mythicCat ? 1650 : revealPopup.resultRarity >= 5 ? 1050 : revealPopup.resultRarity >= 4 ? 860 : 620
                easing.type: Easing.InCubic
            }
            NumberAnimation {
                target: revealPopup
                property: "revealProgress"
                to: 0.66
                duration: 150
                easing.type: Easing.OutExpo
            }
            PauseAnimation { duration: revealPopup.strikeApex ? 180 : revealPopup.mythicCat ? 220 : revealPopup.resultRarity >= 4 ? 90 : 40 }
            NumberAnimation {
                target: revealPopup
                property: "revealProgress"
                to: 1
                duration: revealPopup.strikeApex ? 760 : revealPopup.mythicCat ? 860 : revealPopup.resultRarity >= 4 ? 560 : 420
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
                    GradientStop { position: 0.52; color: Qt.rgba(revealPopup.revealColor.r, revealPopup.revealColor.g, revealPopup.revealColor.b, revealPopup.arcaneMage ? 0.28 : revealPopup.resultRarity >= 4 ? 0.15 : 0.08) }
                    GradientStop { position: 1; color: theme.colors.surface }
                }
            }

            MythicEffectField {
                anchors.fill: parent
                animationStyle: revealPopup.animationStyle
                effectColor: revealPopup.revealColor
                active: revealPopup.opened && settingsController.state.animationsEnabled
                progress: revealPopup.revealProgress
                mode: "reveal"
            }

            Item {
                id: rayField
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height) * 0.94
                height: width
                visible: !revealPopup.strikeApex
                scale: 0.56 + revealPopup.revealProgress * 0.58
                opacity: 0.08 + revealPopup.resultRarity * 0.035

                Repeater {
                    model: revealPopup.strikeApex ? 24 : revealPopup.resultRarity >= 6 ? 36 : revealPopup.resultRarity >= 5 ? 28 : revealPopup.resultRarity >= 4 ? 22 : 14
                    Rectangle {
                        required property int index
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: parent.height / 2 - height
                        width: index % 3 === 0 ? 5 : 3
                        height: parent.height * (index % 4 === 0 ? 0.48 : 0.39)
                        radius: width / 2
                        color: index % 5 === 0 && revealPopup.resultRarity >= 4 ? "white" : revealPopup.revealColor
                        transformOrigin: Item.Bottom
                        rotation: index * (360 / (revealPopup.strikeApex ? 24 : revealPopup.resultRarity >= 6 ? 36 : revealPopup.resultRarity >= 5 ? 28 : revealPopup.resultRarity >= 4 ? 22 : 14))
                    }
                }

                RotationAnimation on rotation {
                    running: revealPopup.opened && settingsController.state.animationsEnabled
                    from: 0
                    to: 360
                    duration: revealPopup.arcaneMage ? 5200 : revealPopup.resultRarity >= 5 ? 10000 : 16000
                    loops: Animation.Infinite
                }
            }

            Item {
                id: strikeRevealCosmos
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height) * 0.96
                height: width
                visible: revealPopup.strikeApex
                opacity: Math.min(1, revealPopup.revealProgress * 2.4)
                property real phase: 0

                NumberAnimation on phase {
                    running: revealPopup.opened && settingsController.state.animationsEnabled
                    from: 0; to: Math.PI * 2; duration: 9000; loops: Animation.Infinite
                }

                Repeater {
                    model: 4
                    Rectangle {
                        required property int index
                        anchors.centerIn: parent
                        width: parent.width * (0.28 + index * 0.18) * (0.72 + revealPopup.revealProgress * 0.28)
                        height: width
                        radius: width / 2
                        color: "transparent"
                        border.width: index === 0 ? 4 : 2
                        border.color: index === 0 ? "#F3F1FF" : index === 1 ? "#8C7AE8" : index === 2 ? "#67B3F0" : "#E7CA82"
                        opacity: Math.max(0.12, 0.7 - index * 0.13)
                        scale: 1 + Math.sin(strikeRevealCosmos.phase * 2 + index) * 0.018
                    }
                }

                Repeater {
                    model: 30
                    Text {
                        required property int index
                        readonly property real angle: index * Math.PI * 2 / 30 + strikeRevealCosmos.phase * (index % 2 ? -0.18 : 0.25)
                        readonly property real radiusValue: parent.width * (0.22 + (index % 5) * 0.055) * Math.max(0.3, revealPopup.revealProgress)
                        text: index % 7 === 0 ? "✦" : index % 4 === 0 ? "✧" : "·"
                        color: index % 7 === 0 ? "#FFF0B7" : index % 2 ? "#A695FF" : "#78C4FF"
                        font.pixelSize: index % 7 === 0 ? 16 : index % 4 === 0 ? 11 : 15
                        font.weight: Font.Bold
                        x: parent.width / 2 + Math.cos(angle) * radiusValue - width / 2
                        y: parent.height / 2 + Math.sin(angle) * radiusValue - height / 2
                        opacity: 0.25 + (Math.sin(strikeRevealCosmos.phase * 3 + index * 0.8) + 1) * 0.34
                    }
                }

                Text {
                    anchors.centerIn: parent
                    text: "✦"
                    color: "#FFFFFF"
                    font.pixelSize: 52 + revealPopup.revealProgress * 30
                    opacity: Math.max(0, 0.82 - revealPopup.revealProgress)
                    scale: 0.5 + revealPopup.revealProgress * 0.8
                }
            }

            Repeater {
                model: revealPopup.strikeApex ? 22 : revealPopup.resultRarity >= 6 ? 36 : revealPopup.resultRarity >= 5 ? 30 : revealPopup.resultRarity >= 4 ? 22 : 14
                Rectangle {
                    required property int index
                    property real angle: index * Math.PI * 2 / (revealPopup.strikeApex ? 22 : revealPopup.resultRarity >= 6 ? 36 : revealPopup.resultRarity >= 5 ? 30 : revealPopup.resultRarity >= 4 ? 22 : 14)
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
                border.width: revealPopup.resultRarity >= 6 ? 7 : revealPopup.resultRarity >= 5 ? 5 : revealPopup.resultRarity >= 4 ? 3 : 2
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
                    text: revealPopup.resultRarity >= 6 ? "✺" : revealPopup.resultRarity >= 5 ? "✦" : "★"
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

            Item {
                id: arcanePortal
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height) * 0.88
                height: width
                visible: revealPopup.arcaneMage
                opacity: Math.min(1, revealPopup.revealProgress * 2.2)

                Repeater {
                    model: 3
                    Rectangle {
                        required property int index
                        anchors.centerIn: parent
                        width: parent.width - index * 46
                        height: width
                        radius: width / 2
                        color: "transparent"
                        border.width: index === 0 ? 3 : 2
                        border.color: index === 1 ? "#FFF2A8" : revealPopup.revealColor
                        opacity: 0.2 + index * 0.12
                        RotationAnimation on rotation {
                            running: revealPopup.opened && settingsController.state.animationsEnabled
                            from: index % 2 ? 360 : 0
                            to: index % 2 ? 0 : 360
                            duration: 3300 + index * 900
                            loops: Animation.Infinite
                        }
                    }
                }

                Repeater {
                    model: 12
                    Text {
                        required property int index
                        readonly property var glyphs: ["✦", "◇", "✧", "☾", "✶", "✺"]
                        text: glyphs[index % glyphs.length]
                        color: index % 3 === 0 ? "#FFF2A8" : revealPopup.revealColor
                        font.pixelSize: index % 2 ? 14 : 20
                        font.weight: Font.Bold
                        x: parent.width / 2 + Math.cos(index * Math.PI / 6) * (parent.width / 2 - 24) - width / 2
                        y: parent.height / 2 + Math.sin(index * Math.PI / 6) * (parent.height / 2 - 24) - height / 2
                        SequentialAnimation on opacity {
                            running: revealPopup.opened && settingsController.state.animationsEnabled
                            loops: Animation.Infinite
                            PauseAnimation { duration: index * 65 }
                            NumberAnimation { from: 0.18; to: 1; duration: 380 }
                            NumberAnimation { to: 0.2; duration: 620 }
                        }
                    }
                }

                RotationAnimation on rotation {
                    running: revealPopup.opened && settingsController.state.animationsEnabled
                    from: 0
                    to: 360
                    duration: 14000
                    loops: Animation.Infinite
                }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: revealPopup.compactLayout ? 14 : 20
            spacing: 6
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: revealPopup.revealProgress < 0.58
                      ? (revealPopup.animationStyle === "strike-apex"
                         ? "EL UNIVERSO SE DETIENE… STRIKE HA LLEGADO"
                         : revealPopup.animationStyle === "arcane-mage"
                         ? "EL FIRMAMENTO RESPONDE AL GATO MAGO…"
                         : revealPopup.animationStyle === "playera-prismatic"
                           ? "¡EL CAOS PRISMÁTICO ESTÁ DESPERTANDO!"
                            : revealPopup.animationStyle === "zarking-cyber"
                              ? "SINCRONIZANDO EL NÚCLEO ZARKING…"
                              : revealPopup.animationStyle === "blackbull-noir"
                                ? "LAS LUCES DEL CLUB BLACK BULL SE ENCIENDEN…"
                              : revealPopup.resultRarity >= 4 ? "UNA PRESENCIA EXTRAORDINARIA…" : "DESCUBRIENDO TU GATO…")
                      : revealPopup.result.isNew
                        ? "¡NUEVO GATO DESBLOQUEADO!"
                        : "¡AURA MEJORADA! · NIVEL " + Number(revealPopup.result.effectLevel || 1)
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
                    width: Math.min(380, parent.width - 18)
                    height: Math.min(380, parent.height - 4)
                    radius: 24
                    color: theme.colors.surfaceRaised
                    border.width: revealPopup.resultRarity >= 6 ? 6 : revealPopup.resultRarity >= 5 ? 4 : revealPopup.resultRarity >= 4 ? 3 : 2
                    border.color: revealPopup.revealColor
                    opacity: Math.max(0, Math.min(1, (revealPopup.revealProgress - 0.57) / 0.16))
                    readonly property real entrance: Math.max(0, Math.min(1, (revealPopup.revealProgress - 0.57) / 0.43))
                    scale: (revealPopup.strikeApex ? 0.82 : 0.66) + entrance * (revealPopup.strikeApex ? 0.18 : 0.34)
                    rotation: revealPopup.strikeApex ? 0 : -7 + entrance * 7
                    layer.enabled: revealPopup.strikeApex

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
                        anchors.margins: revealPopup.compactLayout ? 12 : 16
                        spacing: revealPopup.compactLayout ? 3 : 6
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
                                width: Math.min(revealPopup.compactLayout ? 132 : 176, parent.height - 2)
                                height: width
                                source: revealPopup.result.source || ""
                                rarity: revealPopup.resultRarity
                                rarityColor: revealPopup.revealColor
                                animationStyle: revealPopup.result.animationStyle || "standard"
                                effectLevel: Number(revealPopup.result.effectLevel || 0)
                                animatedEffects: revealPopup.opened && revealPopup.revealProgress >= 0.66 && settingsController.state.animationsEnabled
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: revealPopup.result.name || ""
                            color: theme.colors.text
                            font.pixelSize: revealPopup.compactLayout ? 20 : 25
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: revealPopup.result.stars || ""
                            color: revealPopup.revealColor
                            font.pixelSize: revealPopup.compactLayout ? 17 : 21
                            font.letterSpacing: 5
                        }
                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: auraUpgradeText.implicitWidth + 22
                            Layout.preferredHeight: revealPopup.result.effectUpgraded === true ? 28 : 0
                            visible: revealPopup.result.effectUpgraded === true
                            radius: 10
                            color: Qt.rgba(revealPopup.revealColor.r, revealPopup.revealColor.g,
                                           revealPopup.revealColor.b, 0.16)
                            border.width: 1
                            border.color: revealPopup.revealColor
                            Text {
                                id: auraUpgradeText
                                anchors.centerIn: parent
                                text: "✦ AURA " + Number(revealPopup.result.effectLevel || 1)
                                    + " · " + String(revealPopup.result.effectName || "DESTELLO").toUpperCase()
                                color: revealPopup.revealColor
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                font.letterSpacing: 0.8
                            }
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
                    objectName: "catRevealEquipButton"
                    visible: revealPopup.result.isNew === true
                    text: "Equipar ahora"
                    kind: "secondary"
                    onClicked: { revealPopup.close(); catController.equip(revealPopup.result.catId) }
                }
                XButton { objectName: "catRevealContinueButton"; text: "Continuar"; onClicked: revealPopup.close() }
                Item { Layout.fillWidth: true }
            }
        }
    }

    Item {
        id: equipCelebration
        objectName: "catEquipCelebration"
        anchors.fill: parent
        z: 500
        visible: opacity > 0
        opacity: 0
        property var result: ({})
        property real pulseScale: 0.5
        readonly property bool arcaneMage: result.animationStyle === "arcane-mage"
        readonly property bool playeraPrismatic: result.animationStyle === "playera-prismatic"
        readonly property bool zarkingCyber: result.animationStyle === "zarking-cyber"
        readonly property bool blackbullNoir: result.animationStyle === "blackbull-noir"
        readonly property bool strikeApex: result.animationStyle === "strike-apex"
        readonly property bool mythicCat: Number(result.rarity || 1) >= 6
        readonly property color effectColor: result.rarityColor || theme.colors.primary
        readonly property string equipTitle: strikeApex
                                                ? "CORONA SUPREMA ACTIVADA"
                                                : arcaneMage
                                                ? "PACTO ARCANO COMPLETADO"
                                                : playeraPrismatic
                                                  ? "¡FIESTA PRISMÁTICA ACTIVADA!"
                                                  : zarkingCyber
                                                    ? "NÚCLEO ZARKING SINCRONIZADO"
                                                    : blackbullNoir
                                                      ? "BLACK BULL ENTRA AL CLUB"
                                                    : "GATO EQUIPADO"

        function celebrate(value) {
            result = value
            if (!settingsController.state.animationsEnabled)
                return
            opacity = 0
            pulseScale = 0.5
            equipSequence.restart()
        }

        Rectangle {
            anchors.fill: parent
            color: equipCelebration.strikeApex
                   ? "#EB170400"
                   : equipCelebration.arcaneMage
                   ? "#D90A001A"
                   : equipCelebration.playeraPrismatic
                     ? "#D91D0A2D"
                     : equipCelebration.zarkingCyber
                       ? "#E0000718"
                       : equipCelebration.blackbullNoir ? "#EB100900" : "#A8000710"
        }

        MythicEffectField {
            anchors.fill: parent
            animationStyle: equipCelebration.result.animationStyle || ""
            effectColor: equipCelebration.effectColor
            active: equipCelebration.visible
            progress: equipCelebration.pulseScale
            mode: "equip"
        }

        Item {
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.height) * (equipCelebration.mythicCat ? 0.54 : 0.4)
            height: width
            scale: equipCelebration.pulseScale

            Repeater {
                model: equipCelebration.arcaneMage ? 3 : 1
                Rectangle {
                    required property int index
                    anchors.centerIn: parent
                    width: parent.width - index * 42
                    height: width
                    radius: width / 2
                    color: "transparent"
                    border.width: equipCelebration.arcaneMage ? 4 - index : 2
                    border.color: index === 1 ? "#FFF2A8" : equipCelebration.effectColor
                    opacity: 0.38 + index * 0.12
                    RotationAnimation on rotation {
                        running: equipCelebration.visible && equipCelebration.arcaneMage
                        from: index % 2 ? 360 : 0
                        to: index % 2 ? 0 : 360
                        duration: 1800 + index * 650
                        loops: Animation.Infinite
                    }
                }
            }

            Repeater {
                model: equipCelebration.arcaneMage ? 18 : 8
                Text {
                    required property int index
                    readonly property var glyphs: ["✦", "◇", "✧", "☾", "✶", "✺"]
                    text: glyphs[index % glyphs.length]
                    color: index % 3 ? equipCelebration.effectColor : "#FFF2A8"
                    font.pixelSize: equipCelebration.arcaneMage ? 16 + index % 3 * 3 : 11
                    x: parent.width / 2 + Math.cos(index * Math.PI * 2 / (equipCelebration.arcaneMage ? 18 : 8))
                       * (parent.width / 2 - 12) - width / 2
                    y: parent.height / 2 + Math.sin(index * Math.PI * 2 / (equipCelebration.arcaneMage ? 18 : 8))
                       * (parent.height / 2 - 12) - height / 2
                }
            }

            CatAvatar {
                anchors.centerIn: parent
                width: equipCelebration.mythicCat ? 150 : 104
                height: width
                source: equipCelebration.result.source || ""
                rarity: Number(equipCelebration.result.rarity || 1)
                rarityColor: equipCelebration.effectColor
                animationStyle: equipCelebration.result.animationStyle || "standard"
                effectLevel: Number(equipCelebration.result.effectLevel || 0)
                animatedEffects: equipCelebration.visible
            }
        }

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: root.dense ? 36 : 54
            spacing: 5
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: equipCelebration.equipTitle
                color: equipCelebration.arcaneMage ? "#FFF2A8" : equipCelebration.effectColor
                font.pixelSize: equipCelebration.mythicCat ? 18 : 13
                font.weight: Font.Bold
                font.letterSpacing: 2
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: equipCelebration.result.name || ""
                color: theme.colors.text
                font.pixelSize: equipCelebration.mythicCat ? 28 : 20
                font.weight: Font.Bold
            }
        }

        SequentialAnimation {
            id: equipSequence
            ParallelAnimation {
                NumberAnimation {
                    target: equipCelebration
                    property: "opacity"
                    from: 0
                    to: 1
                    duration: equipCelebration.mythicCat ? 360 : 180
                }
                NumberAnimation {
                    target: equipCelebration
                    property: "pulseScale"
                    from: 0.5
                    to: 1
                    duration: equipCelebration.strikeApex ? 1450 : equipCelebration.playeraPrismatic ? 760 : equipCelebration.zarkingCyber ? 620 : equipCelebration.blackbullNoir ? 1120 : equipCelebration.arcaneMage ? 980 : 420
                    easing.type: equipCelebration.playeraPrismatic
                                 ? Easing.OutBounce
                                 : equipCelebration.zarkingCyber
                                   ? Easing.OutExpo
                                   : equipCelebration.blackbullNoir
                                     ? Easing.OutQuint
                                     : equipCelebration.arcaneMage ? Easing.OutElastic : Easing.OutBack
                }
            }
            PauseAnimation { duration: equipCelebration.mythicCat ? 1250 : 500 }
            NumberAnimation {
                target: equipCelebration
                property: "opacity"
                to: 0
                duration: equipCelebration.mythicCat ? 520 : 260
            }
        }
    }

    Connections {
        target: catController
        function onRevealRequested(result) {
            revealPopup.result = result
            revealPopup.beginReveal()
        }
        function onEquippedRequested(result) {
            equipCelebration.celebrate(result)
        }
    }
}
