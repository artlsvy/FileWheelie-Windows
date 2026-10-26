import QtQuick
import QtQuick.Shapes

// A tube around one circular centerline. Both concentric arcs and all four
// quarter-circle cap arcs are fixed for a menu count; only this Item rotates.
Item {
    id: lens
    objectName: "hoverLens"
    width: 0
    height: 0
    transformOrigin: Item.TopLeft
    property bool dark: false
    property bool lowEffects: false
    property real sectorAngle: 120
    readonly property real centerRadius: 76
    // Keep rounded ends inside narrow sectors too. 2..6 options retain the
    // same thickness; crowded menus reduce it only when the menu changes.
    readonly property real capRadius: Math.min(28, centerRadius * Math.sin(Math.max(4, Math.min(90, sectorAngle - 12)) * Math.PI / 360))
    readonly property real capDegrees: Math.asin(capRadius / centerRadius) * 180 / Math.PI
    readonly property real halfArc: Math.max(1, Math.min(18, (sectorAngle - 8) / 2 - capDegrees))
    readonly property real outerRadius: centerRadius + capRadius
    readonly property real innerRadius: centerRadius - capRadius
    readonly property real radians: halfArc * Math.PI / 180
    readonly property real sine: Math.sin(radians)
    readonly property real cosine: Math.cos(radians)
    readonly property real capTipX: centerRadius * sine + capRadius * cosine
    readonly property real capTipY: -centerRadius * cosine + capRadius * sine

    Shape {
        width: 0; height: 0
        transformOrigin: Item.TopLeft
        ShapePath {
            // Exactly one outline; the former second inner-edge stroke and
            // displaced shadow path caused unnecessary ghost contours.
            strokeWidth: 0.8
            strokeColor: lens.dark ? "#80B0C59B" : "#B0FFFFFF"
            fillGradient: LinearGradient {
                x1: 0; y1: -lens.outerRadius; x2: 0; y2: -lens.innerRadius
                GradientStop { position: 0; color: lens.lowEffects ? (lens.dark ? "#304A38" : "#E3E5CF") : (lens.dark ? "#F44C624A" : "#F8FFFFED") }
                GradientStop { position: 0.36; color: lens.lowEffects ? (lens.dark ? "#304A38" : "#E3E5CF") : (lens.dark ? "#F2354E3B" : "#F3E6E9D5") }
                GradientStop { position: 1; color: lens.lowEffects ? (lens.dark ? "#304A38" : "#E3E5CF") : (lens.dark ? "#F02B4231" : "#E9CDD4B8") }
            }
            startX: -lens.outerRadius * lens.sine
            startY: -lens.outerRadius * lens.cosine
            PathArc {
                x: lens.outerRadius * lens.sine; y: -lens.outerRadius * lens.cosine
                radiusX: lens.outerRadius; radiusY: lens.outerRadius
                direction: PathArc.Clockwise
            }
            // Split each semicircle at its tangent tip. A diametric PathArc
            // can choose different centers after floating-point normalization.
            PathArc {
                x: lens.capTipX; y: lens.capTipY
                radiusX: lens.capRadius; radiusY: lens.capRadius
                direction: PathArc.Clockwise
            }
            PathArc {
                x: lens.innerRadius * lens.sine; y: -lens.innerRadius * lens.cosine
                radiusX: lens.capRadius; radiusY: lens.capRadius
                direction: PathArc.Clockwise
            }
            PathArc {
                x: -lens.innerRadius * lens.sine; y: -lens.innerRadius * lens.cosine
                radiusX: lens.innerRadius; radiusY: lens.innerRadius
                direction: PathArc.Counterclockwise
            }
            PathArc {
                x: -lens.capTipX; y: lens.capTipY
                radiusX: lens.capRadius; radiusY: lens.capRadius
                direction: PathArc.Clockwise
            }
            PathArc {
                x: -lens.outerRadius * lens.sine; y: -lens.outerRadius * lens.cosine
                radiusX: lens.capRadius; radiusY: lens.capRadius
                direction: PathArc.Clockwise
            }
        }
    }
}
