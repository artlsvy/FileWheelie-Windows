import QtQuick
import QtQuick.Shapes

// A scenegraph-only material study. The Python session owns all hit testing,
// conversion work, selection state and accessibility preferences.
Item {
    id: root
    width: 240
    height: 240
    focus: true

    readonly property bool selection: wheel.stage === "categories" || wheel.stage === "formats"
    readonly property int count: wheel.labels.length
    readonly property int activeIndex: wheel.hovered >= 0 ? wheel.hovered : wheel.keyboardIndex
    readonly property color foreground: wheel.dark ? "#F3ECDD" : "#20392F"
    readonly property color accent: wheel.dark ? "#D6BF83" : "#65532A"
    readonly property color material: wheel.dark
        ? (wheel.lowEffects ? "#182C24" : "#F5182C24")
        : (wheel.lowEffects ? "#F4F0E5" : "#F5F4F0E5")
    readonly property color selectedMaterial: wheel.dark ? "#304A38" : "#E3E5CF"
    readonly property real sectorAngle: count > 0 ? 360 / count : 360
    readonly property real halfRadians: sectorAngle * Math.PI / 360
    readonly property real radians: sectorAngle * Math.PI / 180
    readonly property real progressAngle: Math.max(0, Math.min(1, wheel.progress)) * Math.PI * 2

    Keys.onPressed: function(event) {
        wheel.keyAction(event.key)
        event.accepted = true
    }

    Rectangle {
        x: 10; y: 10; width: 220; height: 220; radius: 110
        color: root.material
        border.width: 1
        border.color: wheel.dark ? "#A196B69A" : "#B38B9478"
    }

    // Only this fixed path rotates on hover. No per-frame path generation,
    // bitmap painting, desktop capture or shader dependencies are involved.
    Shape {
        x: 120; y: 120
        width: 0; height: 0
        visible: root.selection && root.count > 0 && root.activeIndex >= 0
        rotation: root.activeIndex * root.sectorAngle
        transformOrigin: Item.TopLeft
        ShapePath {
            strokeWidth: 0
            strokeColor: "transparent"
            fillColor: root.selectedMaterial
            startX: 0; startY: -108
            PathArc {
                x: 108 * Math.sin(root.halfRadians)
                y: -108 * Math.cos(root.halfRadians)
                radiusX: 108; radiusY: 108
                direction: PathArc.Clockwise
            }
            PathArc {
                x: 108 * Math.sin(root.radians)
                y: -108 * Math.cos(root.radians)
                radiusX: 108; radiusY: 108
                direction: PathArc.Clockwise
            }
            PathLine {
                x: 42 * Math.sin(root.radians)
                y: -42 * Math.cos(root.radians)
            }
            PathArc {
                x: 42 * Math.sin(root.halfRadians)
                y: -42 * Math.cos(root.halfRadians)
                radiusX: 42; radiusY: 42
                direction: PathArc.Counterclockwise
            }
            PathArc {
                x: 0; y: -42
                radiusX: 42; radiusY: 42
                direction: PathArc.Counterclockwise
            }
            PathLine { x: 0; y: -108 }
        }
    }

    // A continuous, restrained specular edge belongs to the whole surface.
    Shape {
        visible: !wheel.lowEffects
        ShapePath {
            fillColor: "transparent"
            strokeColor: wheel.dark ? "#719EB29B" : "#D9FFFFFF"
            strokeWidth: 1.4
            capStyle: ShapePath.RoundCap
            startX: 24; startY: 75
            PathArc { x: 163; y: 22; radiusX: 106; radiusY: 106; direction: PathArc.Clockwise }
        }
        ShapePath {
            fillColor: "transparent"
            strokeColor: wheel.dark ? "#686A865F" : "#647D805F"
            strokeWidth: 1
            capStyle: ShapePath.RoundCap
            startX: 217; startY: 160
            PathArc { x: 151; y: 224; radiusX: 106; radiusY: 106; direction: PathArc.Clockwise }
        }
    }

    Repeater {
        model: root.selection ? wheel.labels : []
        delegate: Text {
            required property int index
            required property string modelData
            readonly property real angle: (index + 0.5) * root.sectorAngle * Math.PI / 180
            x: 120 + 76 * Math.sin(angle) - width / 2
            y: 120 - 76 * Math.cos(angle) - height / 2
            width: root.count <= 4 ? 76 : 60
            height: 40
            text: modelData
            color: root.foreground
            font.family: "Segoe UI"
            font.pixelSize: 14
            font.weight: root.activeIndex === index ? Font.DemiBold : Font.Medium
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
    }

    Shape {
        visible: !root.selection && wheel.stage !== "closed"
        ShapePath {
            fillColor: "transparent"
            strokeColor: root.accent
            strokeWidth: 3
            capStyle: ShapePath.RoundCap
            startX: 120; startY: 17
            PathArc {
                x: 120 + 103 * Math.sin(root.progressAngle / 2)
                y: 120 - 103 * Math.cos(root.progressAngle / 2)
                radiusX: 103; radiusY: 103
                direction: PathArc.Clockwise
            }
            PathArc {
                x: 120 + 103 * Math.sin(root.progressAngle)
                y: 120 - 103 * Math.cos(root.progressAngle)
                radiusX: 103; radiusY: 103
                direction: PathArc.Clockwise
            }
        }
    }

    Text {
        visible: root.selection && root.count === 0
        x: 40; y: 42; width: 160; height: 32
        text: "No formats"
        color: root.foreground
        font.pixelSize: 14
        horizontalAlignment: Text.AlignHCenter
    }

    Text {
        visible: !root.selection
        x: 48; y: 46; width: 144; height: 40
        text: wheel.statusTitle
        color: root.foreground
        font.family: "Segoe UI"
        font.pixelSize: 16
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.Wrap
        maximumLineCount: 2
        elide: Text.ElideRight
    }

    Text {
        visible: wheel.stage === "converting"
        x: 65; y: 164; width: 110; height: 30
        text: Math.round(Math.max(0, Math.min(1, wheel.progress)) * 100) + "%"
        color: root.foreground
        font.family: "Segoe UI"
        font.pixelSize: 16
        horizontalAlignment: Text.AlignHCenter
    }

    Rectangle {
        x: 81; y: 81; width: 78; height: 78; radius: 39
        color: wheel.dark ? "#182C24" : "#F4F0E5"
        border.width: 1
        border.color: wheel.dark ? "#677E68" : "#A3AA91"
        Text {
            anchors.fill: parent
            anchors.margins: 6
            text: wheel.centerLabel
            color: root.foreground
            font.family: "Segoe UI"
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.Wrap
            maximumLineCount: 2
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onPositionChanged: function(mouse) { wheel.hoverAt(mouse.x, mouse.y) }
        onExited: wheel.clearHover()
        onPressed: function(mouse) { wheel.activateAt(mouse.x, mouse.y) }
    }
}
