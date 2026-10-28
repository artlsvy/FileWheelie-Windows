import QtQuick

// Separate retained surface: no resizing a native Popup while it owns input.
Item {
    id: root
    width: 272
    height: progress.surfaceExpanded ? 190 : 72
    property real entrance: 1
    opacity: entrance
    scale: 0.85 + entrance * 0.15
    transformOrigin: Item.Center
    readonly property var session: progress
    readonly property bool expanded: progress.surfaceExpanded
    readonly property var palette: progress.colors
    readonly property color foreground: palette.text
    readonly property color brass: palette.accent
    readonly property color surface: palette.surface
    readonly property color outline: palette.outline
    readonly property color reflection: palette.reflection
    readonly property color hover: palette.hover
    function glass(color, alpha) {
        return Qt.rgba(color.r, color.g, color.b, progress.lowEffects ? 1 : alpha)
    }
    Rectangle {
        x: 4; y: 4; width: parent.width - 8; height: parent.height - 8
        radius: root.expanded ? 24 : 31
        color: root.glass(root.surface, 237 / 255)
        border.width: 1
        border.color: root.glass(root.outline, progress.dark ? 128 / 255 : 166 / 255)
        Rectangle {
            x: 22; y: 1; width: parent.width - 44; height: 1
            color: root.glass(root.reflection, progress.dark ? 102 / 255 : 192 / 255)
        }
    }
    Text {
        x: 20; y: 16; width: 210; height: 22
        color: root.foreground
        font.family: "Segoe UI"; font.pixelSize: 14; font.weight: Font.Medium
        text: progress.statusTitle
        textFormat: Text.PlainText
        elide: Text.ElideRight
    }
    Text {
        x: 221; y: 17; width: 25; height: 20
        text: progress.stage === "converting" ? (progress.progressKnown ? Math.round(progress.progress * 100) + "%" : "···") : (progress.presentation === "succeeded" ? "✓" : "!")
        color: root.brass
        font.pixelSize: 13
        horizontalAlignment: Text.AlignRight
    }
    Rectangle {
        x: 20; y: 48; width: 230; height: 3; radius: 1.5
        color: root.glass(root.outline, 96 / 255)
        Rectangle {
            width: progress.stage === "converting" ? (progress.progressKnown ? parent.width * progress.progress : 64) : parent.width
            height: parent.height; radius: 1.5
            color: root.brass
            opacity: progress.stage === "converting" && !progress.progressKnown ? 0.65 : 1
            SequentialAnimation on opacity {
                running: progress.stage === "converting" && !progress.progressKnown && !progress.reducedMotion && !progress.lowEffects
                loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 700 }
                NumberAnimation { to: 0.85; duration: 700 }
            }
        }
    }
    MouseArea {
        x: 4; y: 4; width: parent.width - 8; height: 58
        onClicked: root.session.expandProgress()
    }
    Text {
        visible: root.expanded
        x: 20; y: 65; width: 232; height: 42
        color: root.foreground
        text: progress.filename
        textFormat: Text.PlainText
        font.family: "Segoe UI"; font.pixelSize: 12
        wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideMiddle
    }
    Text {
        visible: root.expanded
        x: 20; y: 111; width: 232; height: 28
        color: root.foreground
        text: progress.stage === "converting" ? "Local conversion continues in the background" : (progress.presentation === "failed" ? "Open details for the cause and local log" : (progress.presentation === "cancelled" ? "Temporary files cleaned up" : "Output saved safely"))
        textFormat: Text.PlainText
        font.pixelSize: 11
        wrapMode: Text.Wrap; maximumLineCount: 2
    }
    Row {
        visible: root.expanded
        x: 16; y: 146; spacing: 8
        Repeater {
            model: progress.stage === "converting" ? ["Cancel", "Compact"] : (progress.presentation === "succeeded" ? ["Reveal", "Dismiss"] : ["Details", "Dismiss"])
            delegate: Rectangle {
                required property string modelData
                width: 112; height: 28; radius: 14
                color: root.hover
                border.color: root.glass(root.outline, progress.dark ? 112 / 255 : 160 / 255)
                Text { anchors.centerIn: parent; text: modelData; font.pixelSize: 12; color: root.foreground }
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.session.progressAction(modelData)
                }
            }
        }
    }
    // Escape is meaningful only after the user explicitly focuses details.
    Keys.onEscapePressed: root.session.keyAction(Qt.Key_Escape)
}
