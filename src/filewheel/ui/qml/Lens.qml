import QtQuick
import QtQuick.Shapes

// Static tessellation; its parent animates only opacity and scenegraph rotation.
Item {
    id: lens
    width: 0
    height: 0
    transformOrigin: Item.TopLeft
    property bool dark: false
    property bool lowEffects: false
    property real halfArc: 18
    readonly property real radians: halfArc * Math.PI / 180
    readonly property real sine: Math.sin(radians)
    readonly property real cosine: Math.cos(radians)

    Shape {
        y: lens.lowEffects ? 0 : 1
        visible: !lens.lowEffects
        ShapePath {
            fillColor: "#16302318"
            strokeColor: "#14201910"
            strokeWidth: 1
            startX: -106 * lens.sine; startY: -106 * lens.cosine
            PathArc { x: 106 * lens.sine; y: -106 * lens.cosine; radiusX: 106; radiusY: 106; direction: PathArc.Clockwise }
            PathArc { x: 46 * lens.sine; y: -46 * lens.cosine; radiusX: 30; radiusY: 30; direction: PathArc.Clockwise }
            PathArc { x: -46 * lens.sine; y: -46 * lens.cosine; radiusX: 46; radiusY: 46; direction: PathArc.Counterclockwise }
            PathArc { x: -106 * lens.sine; y: -106 * lens.cosine; radiusX: 30; radiusY: 30; direction: PathArc.Clockwise }
        }
    }

    Shape {
        ShapePath {
            strokeWidth: 1
            strokeColor: lens.dark ? "#B6B0C59B" : "#DBFFFFFF"
            fillGradient: LinearGradient {
                x1: 0; y1: -108; x2: 0; y2: -44
                GradientStop { position: 0; color: lens.lowEffects ? (lens.dark ? "#304A38" : "#E3E5CF") : (lens.dark ? "#F44C624A" : "#F8FFFFED") }
                GradientStop { position: 0.36; color: lens.lowEffects ? (lens.dark ? "#304A38" : "#E3E5CF") : (lens.dark ? "#F2354E3B" : "#F3E6E9D5") }
                GradientStop { position: 1; color: lens.lowEffects ? (lens.dark ? "#304A38" : "#E3E5CF") : (lens.dark ? "#F02B4231" : "#E9CDD4B8") }
            }
            startX: -106 * lens.sine; startY: -106 * lens.cosine
            PathArc { x: 106 * lens.sine; y: -106 * lens.cosine; radiusX: 106; radiusY: 106; direction: PathArc.Clockwise }
            PathArc { x: 46 * lens.sine; y: -46 * lens.cosine; radiusX: 30; radiusY: 30; direction: PathArc.Clockwise }
            PathArc { x: -46 * lens.sine; y: -46 * lens.cosine; radiusX: 46; radiusY: 46; direction: PathArc.Counterclockwise }
            PathArc { x: -106 * lens.sine; y: -106 * lens.cosine; radiusX: 30; radiusY: 30; direction: PathArc.Clockwise }
        }
        ShapePath {
            fillColor: "transparent"
            strokeColor: lens.lowEffects ? "transparent" : (lens.dark ? "#678B9A76" : "#899BA481")
            strokeWidth: 1.2
            capStyle: ShapePath.RoundCap
            startX: 46 * lens.sine; startY: -46 * lens.cosine
            PathArc { x: -46 * lens.sine; y: -46 * lens.cosine; radiusX: 46; radiusY: 46; direction: PathArc.Counterclockwise }
        }
    }
}
