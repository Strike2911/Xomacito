import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property int section: 0
    property bool dense: height <= 520
    readonly property bool revealOpen: revealPopup.opened
    signal revealFinished()
    readonly property var cats: catController.state
    property string search: ""
    property int rarityFilter: 0
    onSearchChanged: catController.setInventoryFilter(search, rarityFilter)
    onRarityFilterChanged: catController.setInventoryFilter(search, rarityFilter)

    ColumnLayout {
        anchors.fill: parent; spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 3
                Text { text: "PERSONALIZACIÓN"; color: theme.colors.primary; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.2 }
                Text { text: root.section === 0 ? "Una caja. Un nuevo compañero." : "Tu colección, a tu manera."; color: theme.colors.text; font.pixelSize: 24; font.weight: Font.DemiBold }
            }
            Item { Layout.fillWidth: true }
            XCard {
                implicitWidth: 168; implicitHeight: 58; cardColor: theme.colors.surfaceRaised
                Column {
                    anchors.centerIn: parent; spacing: 2
                    Text { text: root.cats.wallet || "$0.00"; color: theme.colors.success; font.pixelSize: 23; font.bold: true }
                    Text { text: "SALDO VIRTUAL"; color: theme.colors.textMuted; font.pixelSize: 9; font.letterSpacing: 1 }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            XButton { objectName: "catBoxesTab"; text: "Cajas"; kind: root.section === 0 ? "primary" : "secondary"; onClicked: root.section = 0 }
            XButton { objectName: "catInventoryTab"; text: "Mis gatos · " + root.cats.ownedCount; kind: root.section === 1 ? "primary" : "secondary"; onClicked: root.section = 1 }
            Item { Layout.fillWidth: true }
            XButton {
                objectName: "catSkipAnimationToggle"
                text: checked ? "✓ Omitir animación" : "Omitir animación"
                checkable: true; checked: root.cats.skipAnimation || false
                kind: checked ? "primary" : "ghost"
                onClicked: catController.setSkipAnimation(checked)
                Accessible.description: "Conservar esta preferencia para todas las aperturas"
            }
            Text { text: "10 descargas válidas = $1.00 virtual"; color: theme.colors.textMuted; font.pixelSize: 11 }
        }
        XCard {
            Layout.fillWidth: true; implicitHeight: 86; cardColor: theme.colors.surfaceRaised
            RowLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 16
                CatAvatar { Layout.preferredWidth: 60; Layout.preferredHeight: 60; source: root.cats.equippedSource; rarity: root.cats.equippedRarity; rarityColor: root.cats.equippedColor; animationStyle: root.cats.equippedAnimationStyle; effectLevel: root.cats.equippedEffectLevel; animatedEffects: settingsController.state.animationsEnabled }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: "GATO EQUIPADO"; color: theme.colors.textMuted; font.pixelSize: 9; font.bold: true }
                    Text { text: root.cats.equippedName; color: theme.colors.text; font.pixelSize: 16; font.bold: true }
                    Text { text: root.cats.equippedStars; color: root.cats.equippedColor; font.pixelSize: 11 }
                }
                ColumnLayout {
                    Layout.preferredWidth: Math.min(330, root.width * 0.3); spacing: 6
                    Text { text: "PRÓXIMO $1.00  ·  " + root.cats.downloadProgress + "/10"; color: theme.colors.textMuted; font.pixelSize: 10; font.bold: true }
                    Rectangle {
                        Layout.fillWidth: true; height: 6; radius: 3; color: theme.colors.backgroundAlt
                        Rectangle { width: parent.width * root.cats.downloadProgressRatio; height: parent.height; radius: 3; color: theme.colors.primary }
                    }
                    Text { text: "Faltan " + root.cats.downloadsUntilRoll + " descargas válidas"; color: theme.colors.textMuted; font.pixelSize: 10 }
                }
                ColumnLayout {
                    spacing: 3
                    Text { text: root.cats.ownedUniqueCount + " especies · " + root.cats.ownedCount + " gatos"; color: theme.colors.text; font.pixelSize: 12 }
                    Text { text: "Valor de colección: " + root.cats.inventoryValue; color: theme.colors.success; font.pixelSize: 11 }
                }
            }
        }

        ScrollView {
            id: boxesScroll
            visible: root.section === 0
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: availableWidth; clip: true
            ColumnLayout {
                width: boxesScroll.availableWidth; spacing: 14
                Text { text: "ELIGE TU CAJA"; color: theme.colors.text; font.pixelSize: 12; font.bold: true; font.letterSpacing: 1 }
                GridLayout {
                    Layout.fillWidth: true; columns: root.width < 1000 ? 2 : 4; columnSpacing: 12; rowSpacing: 12
                    Repeater {
                        model: root.cats.boxes || []
                        delegate: XCard {
                            id: boxCard
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 300
                            border.color: boxCard.modelData.color
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 16; spacing: 10
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: boxCard.modelData.id === "daily" ? "CADA DÍA" : "1 GATO POR CAJA"; color: theme.colors.textMuted; font.pixelSize: 9; font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    Text { text: boxCard.modelData.price; color: boxCard.modelData.color; font.pixelSize: 18; font.bold: true }
                                }
                                Item {
                                    Layout.fillWidth: true; Layout.preferredHeight: 78
                                    Rectangle {
                                        anchors.centerIn: parent; width: 96; height: 64; radius: 9
                                        color: Qt.alpha(boxCard.modelData.color, 0.13); border.color: boxCard.modelData.color; border.width: 2
                                        Rectangle { x: -5; y: -4; width: parent.width + 10; height: 16; radius: 5; color: Qt.darker(boxCard.modelData.color, 1.7); border.color: boxCard.modelData.color }
                                        Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 18; height: parent.height; color: Qt.alpha(boxCard.modelData.color, 0.25) }
                                        Text { anchors.centerIn: parent; anchors.verticalCenterOffset: 4; text: "✦"; color: boxCard.modelData.color; font.pixelSize: 32 }
                                    }
                                }
                                Text { Layout.fillWidth: true; text: boxCard.modelData.name; color: theme.colors.text; font.pixelSize: 19; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                                Text { Layout.fillWidth: true; Layout.fillHeight: true; text: boxCard.modelData.odds; color: theme.colors.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
                                XButton {
                                    objectName: boxCard.modelData.id === "daily" ? "catRollButton" : "catBox_" + boxCard.modelData.id
                                    Layout.fillWidth: true
                                    text: boxCard.modelData.available ? "Abrir · " + boxCard.modelData.price : boxCard.modelData.id === "daily" ? "Vuelve mañana" : "Saldo insuficiente"
                                    enabled: boxCard.modelData.available
                                    onClicked: catController.openBox(boxCard.modelData.id)
                                }
                            }
                        }
                    }
                }
                Text { Layout.fillWidth: true; text: "Cada apertura entrega un gato; pueden salir repetidos. Vende copias para ahorrar para otras cajas. Los precios son virtuales, sin compras ni retiros de dinero real."; color: theme.colors.textMuted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; text: "Nueva temporada: tus gatos anteriores se convirtieron en " + (root.cats.resetCredit || "$0.00") + " virtuales. Conservas tu historial y recibes un compañero inicial gratis."; color: theme.colors.textDim; font.pixelSize: 11; wrapMode: Text.WordWrap }
            }
        }
        RowLayout {
            visible: root.section === 1; Layout.fillWidth: true
            XTextField { Layout.fillWidth: true; placeholderText: "Buscar entre mis gatos…"; onTextEdited: root.search = text }
            XComboBox { Layout.preferredWidth: 190; model: ["Todas las rarezas", "1★ Común", "2★ Peculiar", "3★ Raro", "4★ Épico", "5★ Legendario", "6★ Mítico"]; onActivated: root.rarityFilter = currentIndex }
            Text { text: collectionGrid.count + " especies"; color: theme.colors.textMuted; font.pixelSize: 11 }
        }
        GridView {
            id: collectionGrid
            objectName: "catCollectionGrid"
            visible: root.section === 1
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            model: catController.inventoryModel
            cellWidth: width / Math.max(1, Math.floor(width / 190)); cellHeight: 248
            ScrollBar.vertical: XScrollBar {}
            Text { anchors.centerIn: parent; visible: collectionGrid.count === 0; text: "No hay gatos que coincidan con tu búsqueda."; color: theme.colors.textMuted }
            delegate: Item {
                id: catCard
                required property var model
                readonly property var modelData: model
                readonly property bool onScreen: root.visible && root.section === 1 && y + height >= collectionGrid.contentY && y <= collectionGrid.contentY + collectionGrid.height
                width: collectionGrid.cellWidth; height: collectionGrid.cellHeight
                XCard {
                    anchors.fill: parent; anchors.margins: 5; border.color: catCard.modelData.equipped ? catCard.modelData.rarityColor : theme.colors.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: catCard.modelData.stars; color: catCard.modelData.rarityColor; font.pixelSize: 10 }
                            Item { Layout.fillWidth: true }
                            Text { text: "×" + catCard.modelData.quantity; color: theme.colors.text; font.pixelSize: 12; font.bold: true }
                        }
                        CatAvatar { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 80; Layout.preferredHeight: 80; source: catCard.modelData.source; rarity: catCard.modelData.rarity; rarityColor: catCard.modelData.rarityColor; animationStyle: catCard.modelData.animationStyle; effectLevel: catCard.modelData.effectLevel; animatedEffects: catCard.onScreen && !revealPopup.opened && settingsController.state.animationsEnabled }
                        Text { Layout.fillWidth: true; text: catCard.modelData.name; color: theme.colors.text; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.alignment: Qt.AlignHCenter; text: catCard.modelData.price + " / gato"; color: theme.colors.success; font.pixelSize: 12 }
                        XButton { Layout.fillWidth: true; compact: true; implicitHeight: 28; text: catCard.modelData.equipped ? "Equipado" : "Equipar"; kind: "secondary"; enabled: !catCard.modelData.equipped; onClicked: catController.equip(catCard.modelData.catId) }
                        XButton { Layout.fillWidth: true; compact: true; implicitHeight: 28; text: "Vender 1 · " + catCard.modelData.price; kind: "ghost"; enabled: catCard.modelData.canSell; onClicked: catController.sellCat(catCard.modelData.catId) }
                    }
                }
            }
        }
        Text { visible: root.section === 1; Layout.fillWidth: true; text: "La última copia de tu gato equipado se conserva. Equipa otro para venderlo. Las auras y los descubrimientos se mantienen."; color: theme.colors.textMuted; font.pixelSize: 10 }
    }

    Popup {
        id: revealPopup
        objectName: "catRevealPopup"
        parent: Overlay.overlay; anchors.centerIn: parent
        width: Math.min(900, parent ? parent.width - 32 : 850)
        height: Math.min(530, parent ? parent.height - 32 : 500)
        modal: true; focus: true; padding: 22
        closePolicy: Popup.NoAutoClose
        property var result: ({})
        property real travel: 0
        readonly property bool done: travel >= 0.999
        readonly property bool resultCanSell: (root.cats.inventoryItems || []).some(function(cat) { return cat.catId === revealPopup.result.catId && cat.canSell })
        onClosed: { spin.stop(); catController.finishOpening(); root.revealFinished() }
        background: Rectangle { radius: 22; color: theme.colors.backgroundAlt; border.color: revealPopup.result.rarityColor || theme.colors.primary; border.width: 2 }
        function reveal(value) {
            result = value
            travel = 0
            open()
            if (settingsController.state.animationsEnabled && !root.cats.skipAnimation && value.reel && value.reel.length)
                spin.restart()
            else {
                travel = 1
                catController.finishOpening()
            }
        }
        NumberAnimation { id: spin; target: revealPopup; property: "travel"; from: 0; to: 1; duration: 4400; easing.type: Easing.OutQuint; onFinished: catController.finishOpening() }
        MythicEffectField {
            anchors.fill: parent
            animationStyle: revealPopup.result.animationStyle || ""
            effectColor: revealPopup.result.rarityColor || theme.colors.primary
            active: revealPopup.opened && revealPopup.done
            progress: revealPopup.travel
            mode: "reveal"
            opacity: 0.3
        }
        ColumnLayout {
            anchors.fill: parent; spacing: 14
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: revealPopup.done ? "Tu nuevo compañero" : "Abriendo " + (revealPopup.result.boxName || "regalo") + "…"; color: theme.colors.text; font.pixelSize: 22; font.bold: true }
                XButton {
                    objectName: "catRevealSkipToggle"
                    text: checked ? "✓ Omitir animación" : "Omitir animación"
                    checkable: true; checked: root.cats.skipAnimation || false
                    kind: checked ? "primary" : "ghost"
                    onClicked: {
                        catController.setSkipAnimation(checked)
                        if (checked) { spin.stop(); revealPopup.travel = 1; catController.finishOpening() }
                    }
                }
            }
            Rectangle {
                id: reelViewport
                Layout.fillWidth: true; Layout.preferredHeight: 152; visible: (revealPopup.result.reel || []).length > 0; clip: true; radius: 12; color: theme.colors.surface
                Row {
                    x: reelViewport.width / 2 - (2 + (Number(revealPopup.result.winningIndex || 34) - 2) * revealPopup.travel) * 146 - 69
                    y: 9; spacing: 8
                    Repeater {
                        model: revealPopup.result.reel || []
                        Rectangle {
                            required property var modelData
                            width: 138; height: 134; radius: 10; color: theme.colors.surfaceRaised
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 4; color: modelData.rarityColor }
                            Column {
                                anchors.centerIn: parent; width: parent.width - 12; spacing: 5
                                Image { anchors.horizontalCenter: parent.horizontalCenter; width: 78; height: 78; source: modelData.source; fillMode: Image.PreserveAspectFit }
                                Text { width: parent.width; text: modelData.name; color: theme.colors.text; font.pixelSize: 9; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.price; color: modelData.rarityColor; font.pixelSize: 11 }
                            }
                        }
                    }
                }
                Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 3; height: parent.height; color: "#FFD75E" }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "▼"; color: "#FFD75E"; font.pixelSize: 21 }
            }
            RowLayout {
                objectName: "catRevealCard"
                Layout.fillWidth: true; Layout.fillHeight: true; opacity: revealPopup.done ? 1 : 0
                CatAvatar { Layout.preferredWidth: 100; Layout.preferredHeight: 100; source: revealPopup.result.source || ""; rarity: Number(revealPopup.result.rarity || 1); rarityColor: revealPopup.result.rarityColor || theme.colors.primary; animationStyle: revealPopup.result.animationStyle || "standard"; effectLevel: Number(revealPopup.result.effectLevel || 0); animatedEffects: revealPopup.done && settingsController.state.animationsEnabled }
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: revealPopup.result.isNew ? "NUEVO DESCUBRIMIENTO" : "OTRA COPIA PARA TU COLECCIÓN"; color: revealPopup.result.rarityColor || theme.colors.primary; font.pixelSize: 10; font.bold: true }
                    Text { Layout.fillWidth: true; text: revealPopup.result.name || ""; color: theme.colors.text; font.pixelSize: 24; font.bold: true; elide: Text.ElideRight }
                    Text { text: (revealPopup.result.stars || "") + "   ·   " + (revealPopup.result.price || ""); color: revealPopup.result.rarityColor || theme.colors.primary; font.pixelSize: 16 }
                }
            }
            RowLayout {
                Layout.fillWidth: true; enabled: revealPopup.done
                XButton { text: "Vender · " + (revealPopup.result.price || ""); kind: "success"; enabled: revealPopup.resultCanSell; onClicked: { if (catController.sellCat(revealPopup.result.catId)) revealPopup.close() } }
                Item { Layout.fillWidth: true }
                XButton { objectName: "catRevealEquipButton"; text: "Equipar ahora"; kind: "secondary"; onClicked: { catController.equip(revealPopup.result.catId); revealPopup.close() } }
                XButton { objectName: "catRevealContinueButton"; text: "Conservar"; onClicked: revealPopup.close() }
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
        function onRevealRequested(result) { revealPopup.reveal(result) }
        function onEquippedRequested(result) { equipCelebration.celebrate(result) }
    }
}
