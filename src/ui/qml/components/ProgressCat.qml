import QtQuick

Item {
    id: root
    property string variant: settingsController.state.progressCat || "classic"
    property bool animated: false
    property int frame: 0
    readonly property bool animate: animated && visible && settingsController.state.animationsEnabled
    readonly property string assetPrefix: variant === "siamese" ? "cat-siamese-" : variant === "orange" ? "cat-orange-" : "cat-run-"
    implicitWidth: 58
    implicitHeight: 39
    Timer { interval: 140; repeat: true; running: root.animate; onTriggered: root.frame = 1 - root.frame }
    Image {
        anchors.fill: parent
        source: "../../../../assets/progress/" + root.assetPrefix + "1.png"
        sourceClipRect: root.variant === "siamese" ? Qt.rect(200, 340, 1000, 670) : Qt.rect(410, 430, 830, 550)
        fillMode: Image.PreserveAspectFit
        smooth: false
        visible: !root.animate || root.frame === 0
    }
    Image {
        anchors.fill: parent
        source: "../../../../assets/progress/" + root.assetPrefix + "2.png"
        sourceClipRect: Qt.rect(200, 340, 1000, 670)
        fillMode: Image.PreserveAspectFit
        smooth: false
        visible: root.animate && root.frame === 1
    }
}
