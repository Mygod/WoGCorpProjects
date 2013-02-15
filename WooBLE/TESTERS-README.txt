WooBLE v0.1 Beta

If you've used WooGLE then the interface should very familiar, 
although there are a few differences and improvements.
* Tabbed Interface - Each ball has it's own tab.
* Property Categories - Attributes are grouped by function

The main GUI area is quite "passive" at the moment.
- You can Zoom and Pan
- You can click a "thing" and it will highlight the element in the tree
- But no click and drag / resize / rotate

What is does show... States, Parts and Strands etc
Each valid state the ball can be in will be displayed
The solid part of the ball (from shape) is shown in blue
Each Part can have a position, or a range
  If it only has position the graphic will be drawn there
  If it has a range...
     then the graphic will be drawn at the centre of the range
     and a green rectangle will be drawn showing the range
  If it also has x/yrange values this is drawn in Orange
Only strands that will be used are shown
  If a ball is not flammable, the burnt strand will not be shown.
  If a ball is not detachable, the detachstrand will not be shown.
Markers only show on dragging and detaching stated
Shadows only show on walking and standing states
No Particle effects are shown

Property Validation and Error checking
Each XML property is validated against the model
- If it will not accept the value you enter, check the status bar for info
There are some "cross-property" checks (on Save), but not many

What we'd like you to report...
Model Issues 
- Attributes that can be set to invalid values or cause game crashes
- Attributes that cannot be set to valid values
- There are known problems with some Original balls (see below**)

Program Issues
- Error Messages and other such problems
- Please try to discover how to repeat the problem before posting

Game Crashes
- Please try to discover what you have set (or not set) to cause this.

Suggestions / Thoughts
What changes would make it easier or better for everyone?

Finally...  don't take it too seriously,
and try to make some fun new balls while you're at it. 

Thanks :o)
DaB

** Problems with ORIGINAL Balls
Several of the original balls show real problems... 

BeautyProductEye
Bit
DrainedISH           -  Invalid Part references in sinanim 
Pixel
PixelProduct

Beauty - Invalid xrange entry in both eyes (trailing comma)
Fish - Timebug Wing Resource issue (known see Fish Ball Fix addin)
Water - Duplicate sound events for almost all events

And "loads" have unused resources warnings...
mostly relating to DRAGMARKER_P2