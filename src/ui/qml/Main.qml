import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: window
    width: 1280
    height: 720
    minimumWidth: 960
    minimumHeight: 680
    visible: true
    title: "Xomacito " + appController.version
    color: theme.colors.background
    property bool denseWindow: height <= 760

    property var updateInfo: ({})
    property string dialogRequestId: ""
    property var dialogOptions: []
    property bool pendingSmoothMotionPromo: false
    property bool pendingSocialOnboarding: false
    property bool pendingRecoveryEmailRequirement: false
    property bool pendingGuidedTutorial: false
    property bool pendingZaneBirthday: false
    property var zaneBirthdayInfo: ({})
    property int tutorialQuietTicks: 0
    property var tutorialSteps: [
        {
            "page": 0, "target": "navigation", "icon": "↔",
            "title": "Tu mapa de trabajo",
            "message": "Cada pestaña conserva lo que estabas haciendo. Puedes moverte entre tareas sin perder enlaces, selecciones ni ajustes.",
            "actions": ["Descarga o prepara contenido desde la primera pestaña.", "Usa Guía cuando quieras repasar sólo el apartado abierto."]
        },
        {
            "page": 0, "target": "page", "icon": "↓",
            "title": "Descarga con el formato claro",
            "message": "Pega un enlace o importa un archivo. Xomacito analiza el contenido antes de habilitar la descarga y te dice el formato final.",
            "actions": ["Elige Video+Audio o Sólo audio.", "Ajusta calidad y un preset compatible con ese modo.", "Revisa la salida anunciada y pulsa Iniciar descarga."]
        },
        {
            "page": 1, "target": "page", "icon": "☷",
            "title": "Colas sin sorpresas",
            "message": "Analiza una lista para ver miniaturas y elegir exactamente qué elementos se procesarán.",
            "actions": ["Mueve Elegir cantidad desde 0 hasta el total.", "Activa o desactiva elementos individuales.", "Confirma modo, preset y formato antes de iniciar la cola."]
        },
        {
            "page": 2, "target": "page", "icon": "▣",
            "title": "Biblioteca para edición",
            "message": "Aquí reúnes y revisas material de edición sin alterar los originales.",
            "actions": ["Arrastra archivos o carpetas sobre la lista.", "Pliega carpetas y selecciona un archivo para ver todos sus datos.", "Marca el fragmento necesario y crea un recorte independiente."]
        },
        {
            "page": 3, "target": "page", "icon": "◇",
            "title": "Estudio",
            "message": "Prepara imágenes, vectores y fotogramas con una vista previa antes de exportar.",
            "actions": ["Añade los archivos que quieras procesar.", "Escoge la herramienta y sus ajustes.", "Comprueba la vista previa y abre la salida al terminar."]
        },
        {
            "page": 4, "target": "page", "icon": "★",
            "title": "Colección gatuna",
            "message": "Las descargas generan tiradas. Los duplicados mejoran progresivamente el efecto visual de cada gato.",
            "actions": ["Usa tus tiradas para desbloquear gatos.", "Equipa el que acompañará toda la interfaz.", "Completa la colección y mejora a tus favoritos."]
        },
        {
            "page": 5, "target": "page", "icon": "#",
            "title": "Comunidad y progreso",
            "message": "El Scoreboard resume tus descargas, colección y constancia frente a la comunidad.",
            "actions": ["Conecta tu cuenta para sincronizar el progreso.", "Revisa tu racha y posición.", "Añade un correo real para recuperar la cuenta de forma segura."]
        },
        {
            "page": 6, "target": "page", "icon": "⚙",
            "title": "Ajusta Xomacito a tu flujo",
            "message": "Strike es el tema inicial. Aquí administras apariencia, cookies, componentes y rendimiento.",
            "actions": ["Cambia apariencia o paleta cuando quieras.", "Comprueba las dependencias desde su sección.", "Pulsa Repetir recorrido para volver a esta guía completa."]
        }
    ]

    onClosing: function(close) {
        close.accepted = false
        if (settingsController.state.keepRunningInBackground && appController.trayAvailable) {
            window.hide()
            appController.notifyRunningInBackground()
        } else {
            appController.quitApplication()
        }
    }

    function finishReleaseNotice() {
        pendingSmoothMotionPromo = Boolean(noticePopup.noticeInfo.smoothMotionPromotion)
        noticePopup.close()
        if (pendingSmoothMotionPromo)
            smoothMotionDelay.restart()
    }

    function requestSocialOnboarding() {
        pendingSocialOnboarding = true
        tryOpenSocialOnboarding()
    }

    function requestZaneBirthday(info) {
        zaneBirthdayInfo = info || ({})
        pendingZaneBirthday = true
        zaneBirthdayGate.restart()
    }

    function tryOpenZaneBirthday() {
        if (!pendingZaneBirthday || zaneBirthdayPopup.opened)
            return
        if (updatePopup.opened || noticePopup.opened || platinumPopup.opened
                || smoothMotionPopup.opened || catGachaPage.revealOpen
                || socialOnboardingPopup.opened || recoveryEmailPopup.opened
                || dialogPopup.opened || tutorialOverlay.opened) {
            zaneBirthdayGate.restart()
            return
        }
        pendingZaneBirthday = false
        zaneBirthdayPopup.open()
    }

    function tryOpenSocialOnboarding() {
        if (!pendingSocialOnboarding || socialOnboardingPopup.opened)
            return
        if (updatePopup.opened || noticePopup.opened || platinumPopup.opened
                || smoothMotionPopup.opened || pendingSmoothMotionPromo
                || smoothMotionDelay.running || catGachaPage.revealOpen
                || recoveryEmailPopup.opened || pendingRecoveryEmailRequirement
                || tutorialOverlay.opened || zaneBirthdayPopup.opened || pendingZaneBirthday)
            return
        socialOnboardingDelay.restart()
    }

    function requestRecoveryEmailRequirement() {
        pendingRecoveryEmailRequirement = true
        tryOpenRecoveryEmailRequirement()
    }

    function tryOpenRecoveryEmailRequirement() {
        if (!pendingRecoveryEmailRequirement || recoveryEmailPopup.opened
                || !socialController.state.authenticated)
            return
        if (updatePopup.opened || noticePopup.opened || platinumPopup.opened
                || smoothMotionPopup.opened || pendingSmoothMotionPromo
                || smoothMotionDelay.running || catGachaPage.revealOpen
                || tutorialOverlay.opened || zaneBirthdayPopup.opened || pendingZaneBirthday)
            return
        recoveryEmailDelay.restart()
    }

    function tutorialBlocked() {
        return updatePopup.visible || noticePopup.visible || platinumPopup.visible
                || smoothMotionPopup.visible || socialOnboardingPopup.visible
                || recoveryEmailPopup.visible || dialogPopup.visible
                || zaneBirthdayPopup.visible
                || pendingSmoothMotionPromo || smoothMotionDelay.running
                || pendingSocialOnboarding || socialOnboardingDelay.running
                || pendingRecoveryEmailRequirement || recoveryEmailDelay.running
                || pendingZaneBirthday || zaneBirthdayGate.running
                || catGachaPage.revealOpen
                || !window.active
    }

    function requestGuidedTutorial() {
        pendingGuidedTutorial = true
        tutorialQuietTicks = 0
        tutorialGate.restart()
    }

    function tryOpenGuidedTutorial() {
        if (!pendingGuidedTutorial)
            return
        if (tutorialBlocked()) {
            tutorialQuietTicks = 0
            tutorialGate.restart()
            return
        }
        tutorialQuietTicks += 1
        if (tutorialQuietTicks < 4) {
            tutorialGate.restart()
            return
        }
        pendingGuidedTutorial = false
        tutorialQuietTicks = 0
        tutorialOverlay.startFull()
    }

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
            visible: appController.catRarity < 6
        }
        Rectangle {
            width: 360; height: 360; radius: 180
            x: parent.width - 160 + Math.cos(motion.phase * 0.8) * 28
            y: parent.height - 220 + Math.sin(motion.phase * 0.8) * 25
            color: theme.colors.accent
            opacity: 0.045
            visible: appController.catRarity < 6
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 7
            radius: 20
            color: "transparent"
            border.width: 1
            border.color: Math.sin(motion.phase) > 0 ? "#6558B5" : "#4769B0"
            opacity: theme.themeName === "platinum_duality"
                     ? 0.26 + (Math.sin(motion.phase * 2) + 1) * 0.15 : 0
            Behavior on border.color { ColorAnimation { duration: 900 } }
        }
        MythicEffectField {
            anchors.fill: parent
            animationStyle: appController.catAnimationStyle
            effectColor: appController.catRarityColor
            active: appController.catRarity >= 6 && settingsController.state.animationsEnabled
            progress: 0.72
            mode: "background"
            visible: appController.catRarity >= 6
            opacity: appController.catAnimationStyle === "zarking-cyber"
                     ? 0.19
                     : appController.catAnimationStyle === "blackbull-noir" ? 0.2
                     : appController.catAnimationStyle === "strike-apex" ? 0.18 : 0.14
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
                CatAvatar {
                    Layout.preferredWidth: window.denseWindow ? 44 : settingsController.state.compactMode ? 48 : 54
                    Layout.preferredHeight: Layout.preferredWidth
                    source: appController.catSource
                    rarity: appController.catRarity
                    rarityColor: appController.catRarityColor
                    animationStyle: appController.catAnimationStyle
                    effectLevel: appController.catEffectLevel
                    animatedEffects: settingsController.state.animationsEnabled
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
                XButton {
                    objectName: "guidedTutorialButton"
                    compact: true
                    kind: "secondary"
                    text: "?  Guía"
                    Accessible.name: "Abrir la guía de " + appController.pages[appController.page]
                    ToolTip.visible: hovered
                    ToolTip.text: "Explica las herramientas de esta pestaña"
                    onClicked: tutorialOverlay.startPage(appController.page)
                }
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
                        Text { id: catText; anchors.centerIn: parent; text: appController.catRarity + "★  " + appController.catName; color: appController.catRarityColor; font.pixelSize: 8; font.weight: Font.DemiBold }
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
                objectName: "navigationBar"
                anchors.fill: parent; anchors.margins: 6; spacing: 6
                Repeater {
                    model: appController.pages
                    Button {
                        id: navigationButton
                        required property string modelData
                        required property int index
                        objectName: "navButton" + index
                        property int pendingCatRolls: index === 4 ? Number(catController.state.earnedRolls || 0) : 0
                        property bool showRollBadge: index === 4 && pendingCatRolls > 0
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: 1
                        implicitHeight: window.denseWindow ? 30 : 34
                        text: modelData
                        font.pixelSize: 12
                        font.weight: appController.page === index ? Font.DemiBold : Font.Normal
                        focusPolicy: Qt.StrongFocus
                        Accessible.name: modelData + (pendingCatRolls > 0 ? ". " + pendingCatRolls + " tirada" + (pendingCatRolls === 1 ? "" : "s") + " disponible" + (pendingCatRolls === 1 ? "" : "s") : "")
                        onClicked: appController.setPage(index)
                        contentItem: Text { text: parent.text; color: appController.page === index ? "white" : theme.colors.textMuted; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font: parent.font }
                        background: Rectangle {
                            radius: 10
                            color: appController.page === index ? theme.colors.primary : parent.hovered ? theme.colors.surfaceSoft : "transparent"
                            border.width: parent.activeFocus ? 1 : 0
                            border.color: theme.colors.accent
                            Behavior on color { ColorAnimation { duration: settingsController.state.animationsEnabled ? 140 : 0 } }
                        }

                        Rectangle {
                            id: rollBadgeHalo
                            anchors.centerIn: rollBadge
                            width: rollBadge.width
                            height: rollBadge.height
                            radius: height / 2
                            color: "transparent"
                            border.width: 2
                            border.color: "#F23F42"
                            opacity: 0
                            scale: 0.7
                            visible: rollBadge.visible
                            z: 9
                        }

                        Rectangle {
                            id: rollBadge
                            objectName: "catRollBadge"
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.rightMargin: 7
                            anchors.topMargin: -3
                            width: Math.max(19, rollBadgeText.implicitWidth + 9)
                            height: 19
                            radius: height / 2
                            color: "#F23F42"
                            border.width: 2
                            border.color: appController.page === index ? theme.colors.primary : theme.colors.surface
                            visible: navigationButton.showRollBadge
                            z: 10
                            property int navIndex: index
                            property int count: navigationButton.pendingCatRolls
                            property int observedCount: 0
                            property bool observationReady: false

                            Component.onCompleted: {
                                observedCount = navigationButton.pendingCatRolls
                                observationReady = true
                            }
                            onVisibleChanged: {
                                if (!visible) {
                                    scale = 1
                                    rollBadgeHalo.opacity = 0
                                }
                            }
                            Connections {
                                target: catController
                                function onStateChanged() {
                                    var nextCount = navigationButton.pendingCatRolls
                                    if (rollBadge.observationReady && nextCount > rollBadge.observedCount && settingsController.state.animationsEnabled)
                                        badgeUnlockAnimation.restart()
                                    rollBadge.observedCount = nextCount
                                }
                            }

                            Text {
                                id: rollBadgeText
                                anchors.centerIn: parent
                                text: navigationButton.pendingCatRolls > 99 ? "99+" : String(navigationButton.pendingCatRolls)
                                color: "white"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                            }

                            SequentialAnimation {
                                id: badgeUnlockAnimation
                                ParallelAnimation {
                                    SequentialAnimation {
                                        NumberAnimation { target: rollBadge; property: "scale"; from: 1; to: 1.28; duration: 120; easing.type: Easing.OutQuad }
                                        NumberAnimation { target: rollBadge; property: "scale"; to: 0.93; duration: 90; easing.type: Easing.InOutQuad }
                                        NumberAnimation { target: rollBadge; property: "scale"; to: 1; duration: 170; easing.type: Easing.OutBack }
                                    }
                                    ParallelAnimation {
                                        NumberAnimation { target: rollBadgeHalo; property: "scale"; from: 0.7; to: 2.1; duration: 380; easing.type: Easing.OutCubic }
                                        NumberAnimation { target: rollBadgeHalo; property: "opacity"; from: 0.8; to: 0; duration: 380; easing.type: Easing.OutCubic }
                                    }
                                }
                            }

                            ToolTip.visible: navigationButton.hovered
                            ToolTip.text: navigationButton.pendingCatRolls + " tirada" + (navigationButton.pendingCatRolls === 1 ? " disponible" : "s disponibles")
                            ToolTip.delay: 450
                        }
                    }
                }
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
                Item { MediaLibraryPage { anchors.fill: parent } }
                Item { ImageStudioPage { anchors.fill: parent } }
                Item {
                    CatGachaPage {
                        id: catGachaPage
                        anchors.fill: parent
                        onRevealFinished: {
                            window.tryOpenRecoveryEmailRequirement()
                            window.tryOpenSocialOnboarding()
                        }
                    }
                }
                Item { ScoreboardPage { anchors.fill: parent; onConnectRequested: socialOnboardingPopup.open() } }
                Item { SettingsPage { anchors.fill: parent } }

                Connections {
                    target: appController
                    function onPageChanged() {
                        if (settingsController.state.animationsEnabled)
                            pageArrival.restart()
                    }
                }
                ParallelAnimation {
                    id: pageArrival
                    NumberAnimation { target: pages; property: "opacity"; from: 0.62; to: 1; duration: 260; easing.type: Easing.OutCubic }
                    NumberAnimation { target: pages; property: "scale"; from: 0.992; to: 1; duration: 340; easing.type: Easing.OutCubic }
                }
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
        onClosed: {
            window.tryOpenRecoveryEmailRequirement()
            window.tryOpenSocialOnboarding()
        }
        background: Rectangle { radius: 20; color: theme.colors.surfaceRaised; border.color: theme.colors.primary; border.width: 1 }
        ColumnLayout {
            id: updatePopupContent
            x: 22; y: 22; width: updatePopup.width - 44; spacing: 14
            Text { text: "ACTUALIZACIÓN"; color: theme.colors.accent; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.2 }
            // La revisión usada por el actualizador nunca forma parte del
            // nombre que ve el usuario. La edición pública viene del programa.
            Text { Layout.fillWidth: true; text: "Xomacito " + appController.version; color: theme.colors.text; font.pixelSize: 25; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
            Text { Layout.fillWidth: true; text: "- Arreglo de bugs de la versión 1.0."; color: theme.colors.textMuted; font.pixelSize: 12; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
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

    Timer {
        id: zaneBirthdayGate
        interval: 180
        repeat: false
        onTriggered: window.tryOpenZaneBirthday()
    }

    Popup {
        id: zaneBirthdayPopup
        objectName: "zaneBirthdayPopup"
        anchors.centerIn: parent
        width: Math.min(620, window.width - 48)
        implicitHeight: birthdayContent.implicitHeight + 44
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose
        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220 }
                NumberAnimation { property: "scale"; from: 0.9; to: 1; duration: 360; easing.type: Easing.OutBack }
            }
        }
        onClosed: {
            window.tryOpenRecoveryEmailRequirement()
            window.tryOpenSocialOnboarding()
            if (window.pendingGuidedTutorial)
                tutorialGate.restart()
        }
        background: Rectangle {
            radius: 24
            color: theme.colors.surfaceRaised
            border.color: "#FFD75E"
            border.width: 2
        }
        ColumnLayout {
            id: birthdayContent
            x: 22; y: 22; width: zaneBirthdayPopup.width - 44
            spacing: 14

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "CELEBRACIÓN ESPECIAL · 26 DE AGOSTO"
                color: "#FFD75E"
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 1.2
            }
            CatAvatar {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 154
                Layout.preferredHeight: 154
                source: (window.zaneBirthdayInfo.cat || {}).source || ""
                rarity: 5
                rarityColor: "#FFD75E"
                animationStyle: "standard"
                animatedEffects: zaneBirthdayPopup.opened && settingsController.state.animationsEnabled
            }
            Text {
                Layout.fillWidth: true
                text: window.zaneBirthdayInfo.title || "¡Feliz cumpleaños, Zane!"
                horizontalAlignment: Text.AlignHCenter
                color: theme.colors.text
                font.pixelSize: 29
                font.weight: Font.Bold
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: window.zaneBirthdayInfo.message || "10 rolleos y PERRO ZANE 5★ para celebrar."
                horizontalAlignment: Text.AlignHCenter
                color: theme.colors.textMuted
                font.pixelSize: 14
                lineHeight: 1.18
                wrapMode: Text.WordWrap
            }
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                implicitWidth: rewardText.implicitWidth + 30
                implicitHeight: 38
                radius: 12
                color: theme.colors.surfaceSoft
                border.color: "#FFD75E"
                Text {
                    id: rewardText
                    anchors.centerIn: parent
                    text: "+10 ROLLEOS · PERRO ZANE 5★"
                    color: "#FFD75E"
                    font.pixelSize: 13
                    font.weight: Font.Bold
                }
            }
            XButton {
                Layout.alignment: Qt.AlignHCenter
                text: "Recibir regalo"
                onClicked: zaneBirthdayPopup.close()
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

                    CatAvatar {
                        Layout.preferredWidth: 82; Layout.preferredHeight: 82
                        source: appController.catSource
                        rarity: appController.catRarity
                        rarityColor: "#FFE35A"
                        animationStyle: appController.catAnimationStyle
                        effectLevel: appController.catEffectLevel
                        animatedEffects: noticePopup.opened && settingsController.state.animationsEnabled
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
                                id: releaseSplash
                                objectName: "releaseSplash"
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
                XButton {
                    objectName: "releaseNoticeContinueButton"
                    text: "¡A descargar!"
                    onClicked: window.finishReleaseNotice()
                }
            }
        }
    }

    Timer {
        id: platinumDelay
        interval: 190
        repeat: false
        onTriggered: platinumPopup.open()
    }

    Popup {
        id: platinumPopup
        objectName: "platinumCelebrationPopup"
        x: 0
        y: 0
        width: window.width
        height: window.height
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape
        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 260 }
        }
        exit: Transition {
            NumberAnimation { property: "opacity"; to: 0; duration: 220 }
        }
        onOpened: {
            platinumCardAnimation.restart()
            appController.playPlatinumCelebration()
        }
        onClosed: {
            if (window.pendingSmoothMotionPromo)
                smoothMotionDelay.restart()
            else
                window.tryOpenRecoveryEmailRequirement()
        }

        background: Rectangle {
            color: "#E6000712"
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#B51D0B3A" }
                    GradientStop { position: 0.5; color: "#B5032532" }
                    GradientStop { position: 1; color: "#B52E123D" }
                }
            }
        }

        contentItem: Item {
            clip: true

            QtObject {
                id: confettiMotion
                property real phase: 0
            }
            NumberAnimation {
                target: confettiMotion
                property: "phase"
                from: 0
                to: 1
                duration: 4200
                loops: Animation.Infinite
                running: platinumPopup.opened && settingsController.state.animationsEnabled
            }

            Repeater {
                model: 76
                Rectangle {
                    required property int index
                    property var confettiColors: [
                        "#20D8E8", "#9CFF57", "#FFE35A", "#FF5FE7",
                        "#FF6B6B", "#7B8DFF", "#FFFFFF"
                    ]
                    x: ((index * 73) % 101) / 100 * (platinumPopup.width - width)
                    y: -70 + (
                        ((index * 97) + confettiMotion.phase * (platinumPopup.height + 140))
                        % (platinumPopup.height + 140)
                    )
                    width: 6 + (index % 4) * 2
                    height: index % 3 === 0 ? width : width * 2.1
                    radius: index % 4 === 0 ? width / 2 : 2
                    color: confettiColors[index % confettiColors.length]
                    opacity: 0.92
                    rotation: ((index * 37) % 180) + confettiMotion.phase * 720
                    visible: platinumPopup.opened
                }
            }

            Rectangle {
                id: platinumHaloOuter
                anchors.centerIn: platinumCard
                width: platinumCard.width + 110
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 2
                border.color: "#66FFE35A"
                opacity: 0.55
                SequentialAnimation on scale {
                    running: platinumPopup.opened && settingsController.state.animationsEnabled
                    loops: Animation.Infinite
                    NumberAnimation { from: 0.86; to: 1.05; duration: 1250; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 0.86; duration: 1250; easing.type: Easing.InOutSine }
                }
            }

            Rectangle {
                anchors.centerIn: platinumCard
                width: platinumCard.width + 44
                height: width
                radius: width / 2
                color: "transparent"
                border.width: 3
                border.color: "#669CFF57"
                opacity: 0.72
                SequentialAnimation on rotation {
                    running: platinumPopup.opened && settingsController.state.animationsEnabled
                    loops: Animation.Infinite
                    NumberAnimation { from: 0; to: 360; duration: 9000 }
                }
            }

            Rectangle {
                id: platinumCard
                objectName: "platinumCelebrationCard"
                anchors.centerIn: parent
                width: Math.min(650, platinumPopup.width - 54)
                height: Math.min(520, platinumPopup.height - 54)
                radius: 28
                color: theme.colors.surfaceRaised
                border.width: 2
                border.color: "#FFE35A"
                scale: 1

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 7
                    radius: 22
                    color: "transparent"
                    border.width: 1
                    border.color: "#339CFF57"
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 10

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "✦  COLECCIÓN COMPLETA  ✦"
                        color: "#9CFF57"
                        font.pixelSize: 11
                        font.weight: Font.Bold
                        font.letterSpacing: 1.6
                    }
                    Text {
                        objectName: "platinumCelebrationTitle"
                        Layout.fillWidth: true
                        text: "¡PLATINASTE XOMACITO!"
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: platinumPopup.width < 700 ? 25 : 31
                        font.weight: Font.Black
                        font.letterSpacing: 0.5
                        wrapMode: Text.WordWrap
                    }

                    Item {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.min(330, platinumCard.width - 86)
                        Layout.preferredHeight: Math.min(215, platinumCard.height * 0.43)

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width + 10
                            height: parent.height + 10
                            rotation: -1.7
                            radius: 13
                            color: "#FF5FE7"
                            opacity: 0.34
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width + 7
                            height: parent.height + 8
                            rotation: 1.4
                            radius: 13
                            color: "#20D8E8"
                            opacity: 0.48
                        }
                        Rectangle {
                            anchors.fill: parent
                            radius: 11
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: "#C92857" }
                                GradientStop { position: 0.48; color: "#761C69" }
                                GradientStop { position: 1; color: "#2763D7" }
                            }
                            border.width: 2
                            border.color: "#FFE35A"
                            clip: true
                            Text {
                                anchors.centerIn: parent
                                text: "★  XOMACITO  ★"
                                color: "white"
                                font.pixelSize: 30
                                font.weight: Font.Black
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Todos los gatos forman parte de tu colección."
                        color: "#FFE35A"
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Desbloqueaste el tema exclusivo PLATINUM DUALITY."
                        color: theme.colors.textMuted
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    Item { Layout.fillHeight: true; Layout.minimumHeight: 2 }
                    XButton {
                        Layout.alignment: Qt.AlignHCenter
                        implicitWidth: 190
                        text: "Equipar tema exclusivo"
                        onClicked: {
                            theme.setTheme("platinum_duality")
                            platinumPopup.close()
                        }
                    }
                }
            }

            SequentialAnimation {
                id: platinumCardAnimation
                ParallelAnimation {
                    NumberAnimation {
                        target: platinumCard
                        property: "scale"
                        from: 0.62
                        to: 1.06
                        duration: settingsController.state.animationsEnabled ? 520 : 0
                        easing.type: Easing.OutBack
                    }
                    NumberAnimation {
                        target: platinumCard
                        property: "opacity"
                        from: 0
                        to: 1
                        duration: settingsController.state.animationsEnabled ? 300 : 0
                    }
                }
                NumberAnimation {
                    target: platinumCard
                    property: "scale"
                    to: 1
                    duration: settingsController.state.animationsEnabled ? 190 : 0
                    easing.type: Easing.OutCubic
                }
            }
        }
    }

    Timer {
        id: smoothMotionDelay
        interval: 220
        repeat: false
        onTriggered: smoothMotionPopup.open()
    }

    Timer {
        id: socialOnboardingDelay
        interval: 240
        repeat: false
        onTriggered: {
            if (updatePopup.opened || noticePopup.opened || platinumPopup.opened
                    || smoothMotionPopup.opened || window.pendingSmoothMotionPromo
                    || smoothMotionDelay.running || catGachaPage.revealOpen
                    || tutorialOverlay.opened)
                return
            window.pendingSocialOnboarding = false
            socialOnboardingPopup.open()
        }
    }

    Timer {
        id: recoveryEmailDelay
        interval: 220
        repeat: false
        onTriggered: {
            if (!socialController.state.authenticated
                    || !socialController.state.needsRecoveryEmail
                    || tutorialOverlay.opened)
                return
            window.pendingRecoveryEmailRequirement = false
            recoveryEmailPopup.open()
        }
    }

    Timer {
        id: tutorialGate
        interval: 500
        repeat: false
        onTriggered: window.tryOpenGuidedTutorial()
    }

    Popup {
        id: smoothMotionPopup
        objectName: "smoothMotionPromotionPopup"
        anchors.centerIn: parent
        width: Math.min(820, window.width - 36)
        height: Math.min(620, window.height - 30)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose
        onOpened: window.pendingSmoothMotionPromo = false
        onClosed: {
            window.tryOpenRecoveryEmailRequirement()
            window.tryOpenSocialOnboarding()
        }

        enter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 260 }
                NumberAnimation { property: "scale"; from: 0.93; to: 1; duration: 420; easing.type: Easing.OutBack }
            }
        }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 180 } }

        Overlay.modal: Rectangle { color: "#E900050E" }
        background: Rectangle {
            radius: 28
            color: "#07111F"
            border.width: 2
            border.color: "#168CFF"
            Rectangle {
                anchors.fill: parent
                anchors.margins: 7
                radius: 22
                color: "transparent"
                border.width: 1
                border.color: "#3349B9FF"
            }
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: window.denseWindow ? 18 : 24
            spacing: window.denseWindow ? 9 : 13

            RowLayout {
                Layout.fillWidth: true
                spacing: 14
                CatAvatar {
                    objectName: "smoothMotionBlackBullAvatar"
                    Layout.preferredWidth: window.denseWindow ? 76 : 86
                    Layout.preferredHeight: Layout.preferredWidth
                    source: appController.catSourceForId("cat-cf837ae651c8")
                    rarity: 6
                    rarityColor: "#FFC857"
                    animationStyle: "blackbull-noir"
                    animatedEffects: smoothMotionPopup.opened && settingsController.state.animationsEnabled
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: "BLACK BULL × XOMACITO"
                        color: "#FFC857"
                        font.pixelSize: 11
                        font.weight: Font.Bold
                        font.letterSpacing: 1.7
                    }
                    Text {
                        objectName: "smoothMotionPromotionTitle"
                        Layout.fillWidth: true
                        text: "Smooth Motion acelera tu After Effects"
                        color: "white"
                        font.pixelSize: window.denseWindow ? 22 : 28
                        font.weight: Font.Black
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        text: "ALIANZA ESPECIAL · BLACK BULL EDITION!!!"
                        color: "#52C8FF"
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 190
                radius: 17
                color: "#030813"
                border.width: 1
                border.color: "#274B92"
                clip: true
                Image {
                    anchors.fill: parent
                    anchors.margins: 2
                    source: "../../../assets/release/smooth-motion.png"
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: true
                }
                AnimatedImage {
                    objectName: "smoothMotionBuilderCatLeft"
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 3
                    height: Math.min(parent.height * 0.72, 240)
                    width: height * 0.872
                    source: "../../../assets/release/smooth-motion-cat-left.webp"
                    fillMode: Image.PreserveAspectFit
                    playing: smoothMotionPopup.opened && settingsController.state.animationsEnabled
                    cache: true
                    z: 3
                }
                AnimatedImage {
                    objectName: "smoothMotionBuilderCatRight"
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 3
                    height: Math.min(parent.height * 0.72, 240)
                    width: height * 0.881
                    source: "../../../assets/release/smooth-motion-cat-right.webp"
                    fillMode: Image.PreserveAspectFit
                    playing: smoothMotionPopup.opened && settingsController.state.animationsEnabled
                    cache: true
                    z: 3
                }
            }

            Text {
                Layout.fillWidth: true
                text: "15 paneles en una sola suite para After Effects: curvas, texto, composición, FX, color, guías y exportación. Live Sync y herramientas en español para editar sin romper tu flujo."
                color: "#C7D6EC"
                font.pixelSize: window.denseWindow ? 10 : 11
                lineHeight: 1.15
                wrapMode: Text.WordWrap
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: window.denseWindow ? 48 : 54
                radius: 14
                color: "#1C1507"
                border.width: 1
                border.color: "#FFC857"
                Text {
                    anchors.centerIn: parent
                    width: parent.width - 28
                    text: "✦ Visita Smooth Motion y BLACK BULL 6★ se desbloqueará automáticamente en tu colección."
                    color: "#FFF0B5"
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    font.pixelSize: window.denseWindow ? 10 : 12
                    font.weight: Font.Bold
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                XButton {
                    objectName: "smoothMotionLaterButton"
                    text: "Quizás luego"
                    kind: "secondary"
                    onClicked: smoothMotionPopup.close()
                }
                XButton {
                    objectName: "smoothMotionVisitButton"
                    text: "Visitar web"
                    onClicked: {
                        appController.claimSmoothMotionBlackBull()
                        appController.openUrl("https://getsmoothmotion.com/")
                        smoothMotionPopup.close()
                    }
                }
            }
        }
    }

    Popup {
        id: socialOnboardingPopup
        objectName: "socialOnboardingPopup"
        anchors.centerIn: parent
        width: Math.min(580, window.width - 40)
        height: Math.min(
            socialOnboardingPopup.flow === "create" ? 520
            : socialOnboardingPopup.flow === "login" ? 450
            : socialOnboardingPopup.flow.indexOf("recover") === 0 ? 405 : 490,
            window.height - 36
        )
        modal: true; focus: true; padding: 0
        clip: true
        closePolicy: Popup.CloseOnEscape
        property string flow: "create"
        readonly property bool createMode: flow === "create"
        onClosed: {
            if (socialOnboardingPopup.flow.indexOf("recover") === 0)
                socialController.cancelPasswordReset()
            if (!socialController.state.authenticated)
                socialController.dismissOnboarding()
        }
        background: Rectangle {
            radius: 24
            color: theme.colors.surfaceRaised
            border.width: 1
            border.color: theme.colors.primary
            Rectangle {
                anchors.fill: parent
                anchors.margins: 6
                radius: 19
                color: "transparent"
                border.width: 1
                border.color: theme.colors.border
            }
        }
        contentItem: ColumnLayout {
            id: socialOnboardingContent
            objectName: "socialOnboardingContent"
            anchors.fill: parent
            anchors.margins: window.denseWindow ? 20 : 26
            spacing: window.denseWindow ? 10 : 12

            Text {
                text: socialOnboardingPopup.flow.indexOf("recover") === 0
                      ? "RECUPERAR CUENTA" : "COMUNIDAD XOMACITO"
                color: theme.colors.primary
                font.pixelSize: 10
                font.weight: Font.Bold
                font.letterSpacing: 1.2
            }
            Text {
                objectName: "socialOnboardingTitle"
                Layout.fillWidth: true
                text: socialOnboardingPopup.flow === "create" ? "15 tiradas para empezar"
                      : socialOnboardingPopup.flow === "login" ? "Volver a tu cuenta"
                      : socialOnboardingPopup.flow === "recover-request" ? "Recupera tu contraseña"
                      : "Revisa tu correo"
                color: theme.colors.text
                font.pixelSize: window.denseWindow ? 21 : 23
                font.weight: Font.DemiBold
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: socialOnboardingPopup.flow === "create"
                      ? "Crea tu nombre público, protege tu progreso y entra a La Liga."
                      : socialOnboardingPopup.flow === "login"
                        ? "Continúa tu colección y tu posición en el scoreboard."
                        : socialOnboardingPopup.flow === "recover-request"
                          ? "Usa el correo conectado a tu cuenta."
                          : "Abre el enlace de Supabase mientras Xomacito permanece abierto."
                color: theme.colors.textMuted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }

            Rectangle {
                objectName: "socialOnboardingBenefitCard"
                Layout.fillWidth: true
                Layout.preferredHeight: window.denseWindow ? 50 : 54
                radius: 12
                color: theme.colors.surfaceSoft
                border.width: 1
                border.color: socialOnboardingPopup.flow === "create"
                              ? theme.colors.primary : theme.colors.border
                Text {
                    objectName: "socialOnboardingPrivacy"
                    anchors.fill: parent
                    anchors.margins: 11
                    text: socialOnboardingPopup.flow === "create"
                          ? "REGALO DE BIENVENIDA  ·  Conecta un correo real y recibe hasta 15 tiradas, una sola vez por cuenta."
                          : socialOnboardingPopup.flow.indexOf("recover") === 0
                            ? "Te enviaremos un enlace seguro. Al abrirlo podrás crear tu nueva contraseña en el navegador."
                            : "Tu contraseña se valida con Supabase Auth y no se guarda en este equipo."
                    color: theme.colors.textMuted
                    font.pixelSize: 10
                    font.weight: Font.Medium
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                }
            }

            XTextField {
                id: socialUsername
                objectName: "socialUsernameField"
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 46 : 0
                visible: socialOnboardingPopup.flow === "create"
                placeholderText: "ID pública (ej. strike2911)"
                enabled: !socialController.state.busy
            }
            XTextField {
                id: socialEmail
                objectName: "socialEmailField"
                Layout.fillWidth: true
                Layout.preferredHeight: 46
                placeholderText: socialOnboardingPopup.flow === "login"
                                 ? "Correo (o tu ID anterior)" : "Tu correo"
                enabled: !socialController.state.busy
                         && socialOnboardingPopup.flow !== "recover-wait"
            }
            XTextField {
                id: socialPassword
                objectName: "socialPasswordField"
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 46 : 0
                visible: socialOnboardingPopup.flow === "create"
                         || socialOnboardingPopup.flow === "login"
                placeholderText: "Contraseña (mínimo 8 caracteres)"
                echoMode: TextInput.Password
                enabled: !socialController.state.busy
            }
            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? implicitHeight : 0
                visible: socialController.state.error.length > 0
                text: socialController.state.error
                color: theme.colors.error
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            XButton {
                Layout.alignment: Qt.AlignRight
                Layout.preferredHeight: visible ? implicitHeight : 0
                visible: socialOnboardingPopup.flow === "login"
                text: "Olvidé mi contraseña"
                kind: "ghost"
                enabled: !socialController.state.busy
                onClicked: socialOnboardingPopup.flow = "recover-request"
            }
            Item { Layout.preferredHeight: 2 }
            RowLayout {
                objectName: "socialOnboardingActions"
                Layout.fillWidth: true
                spacing: 8
                XButton {
                    Layout.fillWidth: true
                    text: socialOnboardingPopup.flow === "create" ? "Ya tengo cuenta"
                          : socialOnboardingPopup.flow === "login" ? "Crear cuenta"
                          : "Volver"
                    kind: "ghost"
                    enabled: !socialController.state.busy
                    onClicked: {
                        if (socialOnboardingPopup.flow === "create")
                            socialOnboardingPopup.flow = "login"
                        else if (socialOnboardingPopup.flow === "login")
                            socialOnboardingPopup.flow = "create"
                        else {
                            socialController.cancelPasswordReset()
                            socialOnboardingPopup.flow = "login"
                        }
                    }
                }
                XButton {
                    Layout.fillWidth: true
                    text: "Ahora no"
                    kind: "secondary"
                    enabled: !socialController.state.busy
                    onClicked: {
                        if (socialOnboardingPopup.flow.indexOf("recover") === 0)
                            socialController.cancelPasswordReset()
                        socialController.dismissOnboarding()
                        socialOnboardingPopup.close()
                    }
                }
                XButton {
                    Layout.fillWidth: true
                    text: socialController.state.busy ? "Procesando…"
                          : socialOnboardingPopup.flow === "create" ? "Crear y recibir 15"
                          : socialOnboardingPopup.flow === "login" ? "Entrar"
                          : socialOnboardingPopup.flow === "recover-request" ? "Enviar enlace"
                          : "Reenviar enlace"
                    enabled: !socialController.state.busy
                             && socialEmail.text.length >= 3
                             && (socialOnboardingPopup.flow.indexOf("recover") === 0
                                  || (socialOnboardingPopup.flow === "login" && socialPassword.text.length >= 8)
                                  || (socialOnboardingPopup.flow === "create"
                                      && socialUsername.text.length >= 3 && socialPassword.text.length >= 8))
                    onClicked: {
                        if (socialOnboardingPopup.flow === "create")
                            socialController.signUp(socialUsername.text, socialEmail.text, socialPassword.text)
                        else if (socialOnboardingPopup.flow === "login")
                            socialController.signIn(socialEmail.text, socialPassword.text)
                        else if (socialOnboardingPopup.flow.indexOf("recover") === 0)
                            socialController.requestPasswordReset(socialEmail.text)
                    }
                }
            }
        }
        Connections {
            target: socialController
            function onStateChanged() {
                if (socialController.state.authenticated && socialOnboardingPopup.opened) {
                    socialPassword.text = ""
                    socialOnboardingPopup.close()
                } else if (socialController.state.recoveryLinkSent) {
                    socialOnboardingPopup.flow = "recover-wait"
                    socialEmail.text = socialController.state.recoveryEmail
                    socialPassword.text = ""
                } else if (socialController.state.verificationPending) {
                    socialOnboardingPopup.flow = "login"
                    socialEmail.text = socialController.state.email
                    socialPassword.text = ""
                }
            }
        }
    }

    Popup {
        id: recoveryEmailPopup
        objectName: "recoveryEmailRequiredPopup"
        anchors.centerIn: parent
        width: Math.min(570, window.width - 40)
        height: Math.min(455, window.height - 36)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.NoAutoClose
        onOpened: {
            window.pendingRecoveryEmailRequirement = false
            recoveryAccountEmail.text = socialController.state.recoveryEmail || ""
        }
        onClosed: window.tryOpenSocialOnboarding()

        Overlay.modal: Rectangle { color: "#D9000710" }
        background: Rectangle {
            radius: 24
            color: theme.colors.surfaceRaised
            border.width: 2
            border.color: theme.colors.primary
            Rectangle {
                anchors.fill: parent
                anchors.margins: 7
                radius: 17
                color: "transparent"
                border.width: 1
                border.color: theme.colors.border
            }
        }

        contentItem: ColumnLayout {
            id: recoveryEmailContent
            objectName: "recoveryEmailRequiredContent"
            anchors.fill: parent
            anchors.margins: 26
            spacing: 12

            Text {
                text: "ACTUALIZACIÓN DE CUENTA OBLIGATORIA"
                color: theme.colors.primary
                font.pixelSize: 10
                font.weight: Font.Bold
                font.letterSpacing: 1.2
            }
            Text {
                objectName: "recoveryEmailRequiredTitle"
                Layout.fillWidth: true
                text: "Agrega un correo de recuperación"
                color: theme.colors.text
                font.pixelSize: 24
                font.weight: Font.DemiBold
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: "Tu ID antigua no tenía un correo real. Agrégalo para recuperar tu contraseña y conservar el acceso a tu progreso."
                color: theme.colors.textMuted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 70
                radius: 14
                color: theme.colors.surfaceSoft
                border.width: 1
                border.color: theme.colors.accent
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 13
                    spacing: 12
                    Rectangle {
                        width: 42; height: 42; radius: 21
                        color: theme.colors.accent
                        Text { anchors.centerIn: parent; text: "15"; color: "#071018"; font.pixelSize: 13; font.weight: Font.Bold }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 1
                        Text { text: "15 TIRADAS GATUNAS"; color: theme.colors.text; font.pixelSize: 12; font.weight: Font.Bold }
                        Text { text: "Se entregan cuando Supabase confirma tu correo real."; color: theme.colors.textMuted; font.pixelSize: 10 }
                    }
                }
            }

            XTextField {
                id: recoveryAccountEmail
                objectName: "recoveryAccountEmailField"
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                placeholderText: "Correo personal al que tengas acceso"
                enabled: !socialController.state.emailBusy
                         && !socialController.state.recoveryEmailUpdatePending
            }
            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? implicitHeight : 0
                visible: socialController.state.recoveryEmailUpdatePending
                text: "Revisa " + (socialController.state.recoveryEmail || "tu correo")
                      + ", confirma el cambio y vuelve aquí."
                color: theme.colors.accent
                font.pixelSize: 11
                font.weight: Font.DemiBold
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? implicitHeight : 0
                visible: socialController.state.emailError.length > 0
                text: socialController.state.emailError
                color: theme.colors.error
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true
                spacing: 9
                XButton {
                    text: "Cerrar sesión"
                    kind: "ghost"
                    enabled: !socialController.state.emailBusy
                    onClicked: socialController.signOut()
                }
                Item { Layout.fillWidth: true }
                XButton {
                    visible: socialController.state.recoveryEmailUpdatePending
                    text: socialController.state.emailBusy ? "Comprobando…" : "Comprobar correo"
                    enabled: !socialController.state.emailBusy
                    onClicked: socialController.checkRecoveryEmail()
                }
                XButton {
                    objectName: "recoveryEmailSaveButton"
                    visible: !socialController.state.recoveryEmailUpdatePending
                    text: socialController.state.emailBusy ? "Guardando…" : "Guardar y recibir 15"
                    enabled: !socialController.state.emailBusy && recoveryAccountEmail.text.length >= 5
                    onClicked: socialController.updateRecoveryEmail(recoveryAccountEmail.text)
                }
            }
        }

        Connections {
            target: socialController
            function onStateChanged() {
                if ((!socialController.state.authenticated
                        || !socialController.state.needsRecoveryEmail)
                        && recoveryEmailPopup.opened) {
                    recoveryEmailPopup.close()
                } else if (socialController.state.recoveryEmailUpdatePending
                           && socialController.state.recoveryEmail.length > 0) {
                    recoveryAccountEmail.text = socialController.state.recoveryEmail
                }
            }
        }
    }

    TutorialOverlay {
        id: tutorialOverlay
        steps: window.tutorialSteps
        onPageRequested: function(page) { appController.setPage(page) }
        onFinished: {
            appController.completeGuidedTour()
            window.tryOpenRecoveryEmailRequirement()
            window.tryOpenSocialOnboarding()
        }
        onSkipped: {
            appController.completeGuidedTour()
            window.tryOpenRecoveryEmailRequirement()
            window.tryOpenSocialOnboarding()
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
        function onZaneBirthdayRequested(info) { window.requestZaneBirthday(info) }
        function onCollectionCompletedRequested() { platinumDelay.restart() }
        function onSmoothMotionPromotionRequested() {
            window.pendingSmoothMotionPromo = true
            if (!noticePopup.opened && !platinumPopup.opened && !updatePopup.opened)
                smoothMotionDelay.restart()
        }
        function onGuidedTourRequested() { window.requestGuidedTutorial() }
        function onShowWindowRequested() {
            window.show()
            window.raise()
            window.requestActivate()
        }
    }
    Connections {
        target: socialController
        function onOnboardingRequested() { window.requestSocialOnboarding() }
        function onRecoveryEmailRequired() { window.requestRecoveryEmailRequirement() }
    }
    Connections {
        target: dialogBroker
        function onRequested(requestId, kind, title, message, options, defaultValue) { window.dialogRequestId = requestId; window.dialogOptions = options; dialogPopup.dialogKind = kind; dialogPopup.dialogTitle = title; dialogPopup.dialogMessage = message; dialogPopup.defaultValue = defaultValue; dialogInput.text = defaultValue; dialogPopup.open() }
    }
}
