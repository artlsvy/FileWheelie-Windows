"""Execute the production compositor script in Qt's JS engine with signal mocks."""

import json

import pytest

from filewheel.platforms.linux.kwin_placement import placement_script

MOCK = r"""
function signal(){return {slots:[],connect:function(f){this.slots.push(f);},emit:function(){
 var args=arguments;this.slots.slice().forEach(function(f){f.apply(null,args);});}};}
var a={geometry:{x:0,y:0,width:1920,height:1080},area:{x:0,y:0,width:1920,height:1040}};
var b={geometry:{x:-1600,y:-200,width:1600,height:1000},area:{x:-1600,y:-200,width:1560,height:960}};
var wins=[];
var workspace={screens:[a,b],activeScreen:a,currentDesktop:{},cursorPos:{x:300,y:300},activeWindow:null,
 windowAdded:signal(),windowRemoved:signal(),screensChanged:signal(),virtualScreenGeometryChanged:signal(),currentDesktopChanged:signal(),
 windowList:function(){return wins.slice();},
 screenAt:function(p){for(var i=0;i<this.screens.length;i++){
  var s=this.screens[i],g=s.geometry;if(p.x>=g.x&&p.x<g.x+g.width&&p.y>=g.y&&p.y<g.y+g.height)return s;
 }return null;},clientArea:function(kind,target){return target.area;}};
var KWin={MaximizeArea:1};
function makeWindow(pid,title,geometry,output,dock){
 var w={pid:pid,caption:title,_frame:geometry,output:output||a,dock:!!dock,keepAbove:false,writes:0,
 frameGeometryChanged:signal(),captionChanged:signal(),outputChanged:signal(),hiddenChanged:signal()};
 Object.defineProperty(w,'frameGeometry',{get:function(){return this._frame;},set:function(g){
  if(++this.writes>30)throw Error('geometry feedback loop');
  var old=this._frame;this._frame=g;this.frameGeometryChanged.emit(old);
 }});wins.push(w);workspace.windowAdded.emit(w);return w;
}
function resize(w,width,height){w._frame={x:w._frame.x,y:w._frame.y,width:width,height:height};w.frameGeometryChanged.emit();}
function rect(w){return w.frameGeometry;}
function result(value){return JSON.stringify(value);}
"""

_qt_app = None


def run(script):
    global _qt_app
    from PySide6.QtQml import QJSEngine
    from PySide6.QtWidgets import QApplication

    _qt_app = QApplication.instance() or QApplication([])
    engine = QJSEngine()
    value = engine.evaluate(MOCK + placement_script(777) + script)
    assert not value.isError(), value.toString()
    return json.loads(value.toString())


def test_resize_expanded_and_repeated_compact_stays_above_panel():
    result = run("""
var wheel=makeWindow(777,'Filewheel — test.png',{x:0,y:0,width:240,height:240});
var pill=makeWindow(777,'Filewheel progress',{x:0,y:0,width:272,height:72});
var compact=rect(pill);
resize(pill,272,190);var expanded=rect(pill);
resize(pill,272,72);var compactAgain=rect(pill);
result({compact:compact,expanded:expanded,again:compactAgain,focused:workspace.activeWindow===wheel,writes:pill.writes});
""")
    assert result["compact"] == result["again"]
    assert result["expanded"]["y"] + 190 == 1040 - 16
    assert result["compact"]["y"] + 72 == 1040 - 16
    assert result["focused"] and result["writes"] == 3


@pytest.mark.parametrize(
    "area",
    [
        [0, 0, 1858.0645, 1107],
        [-1920, -180, 1920, 1000],
        [40, 0, 1880, 1080],
        [0, 55, 1920, 1025],
        [0, 0, 1860, 1080],
    ],
)
def test_fractional_coordinates_negative_origins_and_panel_edges(area):
    x, y, width, height = area
    result = run(f"""
a.geometry={{x:{x},y:{y},width:{width},height:{height}}};a.area=a.geometry;
workspace.cursorPos={{x:{x + 200},y:{y + 200}}};
makeWindow(777,'Filewheel — test.png',{{x:0,y:0,width:240,height:240}});
var pill=makeWindow(777,'Filewheel progress',{{x:0,y:0,width:272.2580645,height:72.2580645}});
resize(pill,272.2580645,190.3225806);result(rect(pill));
""")
    assert result["x"] >= x + 16 and result["y"] >= y + 16
    assert result["x"] + result["width"] == pytest.approx(x + width - 16)
    assert result["y"] + result["height"] == pytest.approx(y + height - 16)


def test_progress_retains_invocation_monitor_when_cursor_moves():
    result = run("""
workspace.cursorPos={x:-800,y:100};
var wheel=makeWindow(777,'Filewheel — on-left.png',{x:10,y:10,width:240,height:240},a);
workspace.cursorPos={x:1500,y:700};
var pill=makeWindow(777,'Filewheel progress',{x:500,y:500,width:272,height:72},a);
resize(pill,272,190);result(rect(pill));
""")
    assert -1600 <= result["x"] < 0
    assert result["y"] + 190 == 760 - 16


def test_removed_monitor_falls_back_inside_remaining_work_area():
    result = run("""
workspace.cursorPos={x:-800,y:100};
makeWindow(777,'Filewheel — left.png',{x:10,y:10,width:240,height:240},b);
var pill=makeWindow(777,'Filewheel progress',{x:-900,y:500,width:272,height:190},b);
workspace.screens=[a];workspace.activeScreen=a;workspace.screensChanged.emit();result(rect(pill));
""")
    assert result["x"] == 1920 - 272 - 16
    assert result["y"] == 1040 - 190 - 16


def test_work_area_change_reflows_without_moving_foreign_windows():
    result = run("""
makeWindow(777,'Filewheel — test.png',{x:0,y:0,width:240,height:240});
var pill=makeWindow(777,'Filewheel progress',{x:0,y:0,width:272,height:190});
var foreign=makeWindow(123,'Filewheel progress',{x:20,y:20,width:500,height:500});
var dock=makeWindow(123,'Panel',{x:0,y:1040,width:1920,height:40},a,true);
a.area={x:0,y:0,width:1920,height:980};dock.frameGeometryChanged.emit();
result({pill:rect(pill),foreign:rect(foreign),dock:rect(dock),foreignWrites:foreign.writes,dockWrites:dock.writes});
""")
    assert result["pill"]["y"] + 190 == 980 - 16
    assert result["foreignWrites"] == result["dockWrites"] == 0


def test_reused_surface_title_and_new_invocation_on_other_output():
    result = run("""
var wheel=makeWindow(777,'',{x:0,y:0,width:240,height:240});
wheel.caption='Filewheel — first.png';wheel.captionChanged.emit();
var pill=makeWindow(777,'Filewheel progress',{x:0,y:0,width:272,height:72});
workspace.cursorPos={x:-800,y:100};wheel.caption='Filewheel — second.png';wheel.captionChanged.emit();
pill.hiddenChanged.emit();result(rect(pill));
""")
    assert result["x"] < 0
    assert result["y"] + 72 == 760 - 16


def test_tiny_work_area_anchors_at_origin_without_resize_loop():
    result = run("""
a.area={x:0,y:0,width:200,height:150};
var pill=makeWindow(777,'Filewheel progress',{x:50,y:50,width:272,height:190});
result({frame:rect(pill),writes:pill.writes});
""")
    assert result["frame"]["x"] == result["frame"]["y"] == 0
    assert result["writes"] == 1


def test_initial_zero_size_is_placed_when_native_size_arrives():
    result = run("""
workspace.cursorPos={x:-800,y:100};
var wheel=makeWindow(777,'Filewheel — delayed.png',{x:0,y:0,width:0,height:0},a);
resize(wheel,240,240);result({frame:rect(wheel),focused:workspace.activeWindow===wheel});
""")
    assert result["frame"]["x"] < 0
    assert result["focused"]
