"""Event-driven compositor placement in KWin logical coordinates.

KWin owns global Wayland positions. Qt's work area can include panels, and an
unparented Tool cannot repair its global position with QWindow.setPosition().
"""


def placement_script(pid):
    return r"""
var anchorOutput=null;
var owned=[];
var docks=[];
function containsOutput(output) {
 return output && workspace.screens.indexOf(output)!==-1;
}
function progressWindow(w) {return w.caption==='Filewheel progress';}
function wheelWindow(w) {return w.caption.indexOf('Filewheel — ')===0;}
function place(state, initial) {
 var w=state.window;
 if(state.placing || w.pid!==APP_PID || (!progressWindow(w) && !wheelWindow(w)))return;
 initial=initial||!state.placed;
 var output;
 if(progressWindow(w)) {
  output=containsOutput(anchorOutput)?anchorOutput:w.output;
 } else {
  output=initial?(workspace.screenAt(workspace.cursorPos)||w.output):w.output;
  if(initial)anchorOutput=output;
 }
 if(!containsOutput(output))output=workspace.activeScreen;
 if(!output)return;
 // MaximizeArea excludes panels; use a live output, not a stale area snapshot.
 var area=workspace.clientArea(KWin.MaximizeArea,output,workspace.currentDesktop);
 var g=w.frameGeometry;
 if(area.width<=0 || area.height<=0 || g.width<=0 || g.height<=0)return;
 var x=g.x,y=g.y,margin=progressWindow(w)?16:0;
 if(progressWindow(w)) {
  x=area.x+area.width-g.width-margin;
  y=area.y+area.height-g.height-margin;
 } else if(initial) {
  x=workspace.cursorPos.x-g.width/2;y=workspace.cursorPos.y-g.height/2;
 }
 // Tiny work areas cannot contain the fixed surface; anchor at the origin.
 x=area.width<g.width+margin*2?area.x:Math.max(area.x+margin,Math.min(x,area.x+area.width-g.width-margin));
 y=area.height<g.height+margin*2?area.y:Math.max(area.y+margin,Math.min(y,area.y+area.height-g.height-margin));
 state.placing=true;state.placed=true;
 try {
  if(Math.abs(g.x-x)>0.1 || Math.abs(g.y-y)>0.1)
   w.frameGeometry={x:x,y:y,width:g.width,height:g.height};
  w.keepAbove=true;
  if(initial && wheelWindow(w))workspace.activeWindow=w;
 } finally {state.placing=false;}
}
function reflow() {
 if(!containsOutput(anchorOutput))anchorOutput=null;
 owned.forEach(function(state){place(state,false);});
}
function watch(w) {
 if(w.pid!==APP_PID) {
  // Observe reserved-area changes only; never move or focus another app.
  if(w.dock && docks.indexOf(w)===-1) {
   docks.push(w);w.frameGeometryChanged.connect(reflow);w.hiddenChanged.connect(reflow);
  }
  return;
 }
 if(owned.some(function(state){return state.window===w;}))return;
 var state={window:w,placing:false,placed:false};owned.push(state);
 // A compact 72px pill can later become a 190px detail view. Re-anchor on
 // every committed size, including reuse, native recreation and late resizes.
 w.frameGeometryChanged.connect(function(){place(state,false);});
 w.captionChanged.connect(function(){place(state,true);});
 w.outputChanged.connect(function(){place(state,false);});
 w.hiddenChanged.connect(function(){place(state,false);});
 place(state,true);
}
workspace.windowAdded.connect(watch);
workspace.windowRemoved.connect(function(w){
 owned=owned.filter(function(state){return state.window!==w;});
 docks=docks.filter(function(dock){return dock!==w;});
 reflow();
});
workspace.screensChanged.connect(reflow);
workspace.virtualScreenGeometryChanged.connect(reflow);
workspace.currentDesktopChanged.connect(reflow);
workspace.windowList().forEach(watch);
""".replace("APP_PID", str(int(pid)))
