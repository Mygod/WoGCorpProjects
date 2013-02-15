#Provides a visual representation of a LevelWorld using a QGraphicView

# Notes of caution:
# QRectF right edge is x + width, but QRect right edge is x + width -1


from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import math
import louie
import metaworld
import metaworldui
import qthelper
import metawog
from datetime import datetime

ROUND_DIGITS = 2 #Rounds Sizes, Positions, Radii and Angles to 2 Decimal Places
Z_TOOL_ITEMS = 1000000 # makes sure always on top
Z_LEVEL_ITEMS = 10000.0
Z_PHYSIC_ITEMS = 9000.0

TOOL_SELECT = 'select'
TOOL_PAN = 'pan'
TOOL_MOVE = 'move'

# x coordinate of the unit vector of length = 1
UNIT_VECTOR_COORDINATE = math.sqrt(0.5)

KEY_ELEMENT = 0
KEY_TOOL = 1
#@DaB
#Added to allow storage of pre-computed item area to item.data
KEY_AREA = 2
KEY_TYPE = 3
KEY_EXTRA = 4

ELEMENT_STATE_NONE = 0
ELEMENT_STATE_LOCKED = 1
ELEMENT_STATE_INVISIBLE = 2

# Rectangle corner/middle position identifiers
# Each position is made of a tuple (weight0, weight1, weight2, weight3) were
# each weight correspond respectively to the weight of corner
# top-left, top-right, bottom-right and bottom-left respectively.
# The sum of the weight must always be equal to 1.0
POS_TOP_LEFT = (1,0, 0,0)
POS_TOP_CENTER = (0.5,0.5, 0,0)
POS_TOP_RIGHT = (0,1, 0,0)
POS_CENTER_LEFT = (0.5,0, 0,0.5)
POS_CENTER = (0.25,0.25, 0.25,0.25)
POS_CENTER_RIGHT = (0,0.5, 0.5,0)
POS_BOTTOM_LEFT = (0,0, 0,1)
POS_BOTTOM_CENTER = (0,0, 0.5,0.5)
POS_BOTTOM_RIGHT = (0,0, 1,0)
#@DaB
#Positions for Rotate Handles
POS_MID_RIGHT = (0.15,0.35,0.35,0.15)
POS_MID_LEFT = (0.35,0.15,0.15,0.35)

def poly_weighted_pos(rect, weights):
    """Given a rectangle, computes the specified position. 
       @param pos tuple (xmin_weigth,xmax_weigth,ymin_weight,ymax_weight)
    """
    assert sum(weights) == 1.0
    weighted_pos = [rect[index] * weight 
                    for index,weight in enumerate(weights)]
    pos = weighted_pos[0]
    for weigthed in weighted_pos[1:]:
        pos += weigthed
    return pos

traced_level = 0

TRACED_ACTIVE = False

def traced(f):
    """A decorator that print the method name when it is entered and exited."""
    if not TRACED_ACTIVE:
        return f
    if hasattr(f,'im_class'):
        name = '%s.%s' % (f.im_class.__name__,f.__name__)
    else:
        name = '%s' % (f.__name__)
    def traced_call( *args, **kwargs ):
        global traced_level
        print '%sEnter %s' % (traced_level*'  ', name)
        traced_level += 1
        result = f(*args, **kwargs)
        traced_level -= 1
        print '%sExit %s' % (traced_level*'  ', name)
        return result
    return traced_call

def toQPointF(pos):
    x,y = pos
    return QtCore.QPointF(x,y)

def vector2d_length(x, y):
    """Computes the magnitude of vector (x,y)."""
    return math.sqrt(x*x + y*y)

def vector2d_angle(u, v):
    """Computes the angle required to rotate 'u' around the Z axis counter-clockwise
       to be in the direction as 'v'.
       @param u tuple (x,y) representing vector U
       @param v tuple (x,y) representing vector V
       @exception ValueError is raise if either u or v is the null vector.
       @returns Angle between vector 'u' and 'v' in degrees, in range ]-180,180]
    """
    # We have: cos_uv = U.V / (|U|*|V|), where U.V is the scalar product of U and V, 
    # and |U| the magnitude of U.
    # and we have: sin_uv = |U*V| / (|U|*|V|), where U*V is the cross product of U and V
    # U.V = Ux * Vx + Uy * Vy
    # U*V = (0,0,Ux * Vy - Uy * Vx)
    # |U*V| = Ux * Vy - Uy * Vx
    length_uv = vector2d_length(*u) * vector2d_length(*v)
    if length_uv == 0.0:
        raise ValueError( "Can not computed angle between a null vector and another vector." )
    cos_uv = (u[0] * v[0] + u[1] * v[1]) / length_uv
    sign_sin_uv = u[0] * v[1] - u[1] * v[0]
    angle = math.acos( cos_uv )
    if sign_sin_uv < 0:
        angle = -angle
    return math.degrees( angle )  

# Actions:
# left click: do whatever the current tool is selected to do.
#             for move tool, determine move/resize based on click location
# middle click or left+right click: start panning
# right click: context menu selection

def _interpolateValue(element,attribute, default,time, toskip=None, isangle=False):
    # find previous and next keyframe in which attribute is specified
    pvalue = None
    pinter = 'none'
    ptime = None
    nvalue = None
    ntime = None

    # get the value and the time
    toskip = toskip or set()
    for keyframe in element:
      if keyframe not in toskip:
        frametime = keyframe.get_native('time',0)
        #print element.get('image'),attribute,frametime,value
        if frametime <= time:
            npvalue = keyframe.get_native(attribute,None)
            if npvalue is not None:
                pvalue = npvalue
                ptime = frametime
                pinter = keyframe.get('interpolation','none')
        if frametime >=time:
            nvalue=keyframe.get_native(attribute,None)
            ntime = frametime
            if nvalue is not None:
                break

    if pvalue is None and nvalue is None:
        return default
    if pinter=='none':
        if pvalue is None:
            return default
        else:
            return pvalue
    if nvalue is None:
        return pvalue
    if pvalue is None:
        return nvalue
    if ntime <= ptime:
        return pvalue

    if isangle:
        #if pvalue>180:
        #    pvalue = pvalue - 360
        #elif pvalue <-180:
        #    pvalue = pvalue + 360
        #if nvalue>180:
        #    nvalue = nvalue - 360
        #elif nvalue <-180:
        #    nvalue = nvalue + 360

        if (pvalue - nvalue)>180:
            nvalue = nvalue+360
        if (pvalue - nvalue)<-180:
            nvalue = nvalue-360

    return pvalue+((nvalue-pvalue)*(time-ptime)/(ntime-ptime))

def _interpolateValues(element,attribute, default, time, toskip=None):
    # find previous and next keyframe in which attribute is specified
    pvalue = None
    ptime = None
    nvalue = None
    ntime = None
    pinter = 'none'
    # get the value and the time
    #        print element.get('image'),attribute,frametime,value
    toskip = toskip or set()
    for keyframe in element:
      if keyframe not in toskip:
        frametime = keyframe.get_native('time',0)
        if frametime <= time:
            npvalue = keyframe.get_native(attribute,None)
            if npvalue is not None:
                pvalue = npvalue
                ptime = frametime
                pinter = keyframe.get('interpolation','none')
        if frametime >=time:
            nvalue=keyframe.get_native(attribute,None)
            ntime = frametime
            if nvalue is not None:
                break

   # print element.get('image'),attribute,"  prev:", pvalue,ptime, "   next:",nvalue,ntime,"   time:",self.time

    if pvalue is None and nvalue is None:
        return default
    if pinter=='none':
        if pvalue is None:
            return default
        else:
            return pvalue
    if nvalue is None:
        return pvalue
    if pvalue is None:
        return nvalue
    if ntime <= ptime:
        return pvalue

    return [pvalue[i]+((nvalue[i]-pvalue[i])*(time-ptime)/(ntime-ptime))
              for i in range(len(pvalue)) ]


def getActorTime(element,time, toskip = None):
    actorlength = 0
    kf = None
    toskip = toskip or set()
    for keyframe in element:
      if keyframe not in toskip:
        frametime = keyframe.get_native('time',0)
        if frametime > actorlength:
            actorlength = frametime
        if abs(frametime - time)<0.01:
            kf = keyframe

    if not element.get_native('loop',False):
        return time,kf

    if actorlength < (time-0.01) and actorlength > 0:
        actortime = time - (actorlength * int(time/actorlength))
        for keyframe in element:
          if keyframe not in toskip:
            frametime = keyframe.get_native('time',0)
            if abs(frametime - actortime)<0.01:
                kf = keyframe
        return actortime,kf
    else:
        return time,kf

class BasicTool(object):
    def __init__(self, view):
        self._view = view
        self._last_event = None
        self._press_event = None
        self.activated = False
        self.in_use = False
        self.override_tool = None
        self._downat = QtCore.QPoint(0,0) #@DaB Added to store original Mouse_Press Location
        self._moveto = QtCore.QPoint(0,0)

    def on_mouse_press_event(self, event):
        """Handles tool overriding with mouse button and dispatch press event.
           Middle click or left+right mouse button override the current tool
           with the PanTool.
        """
        self._downat = event.pos() #@DaB Store Press Location
        if ( (event.buttons() == Qt.MidButton) or 
             (event.buttons() == (Qt.LeftButton|Qt.RightButton)) ):
            if self.override_tool is None:
                self.stop_using_tool()
                self.override_tool = PanTool(self._view)
                self.override_tool._handle_press_event(event)
        elif self.override_tool is None: #@DaB Removed LeftButton Filter
            self._handle_press_event(event)
    
    def _handle_press_event(self, event):
        """Handle press event for the tool."""
        if not self.in_use:
            self.start_using_tool()
        self._press_event = qthelper.clone_mouse_event(event)
        self._last_event = self._press_event 
        self.activated = True
    
    def on_mouse_release_event(self, event):
        if self.override_tool is not None:
            self.override_tool.on_mouse_release_event(event)
            self.override_tool.stop_using_tool()
            self.override_tool = None
        self.start_using_tool()
        self.activated = False
        self._handle_release_event(event)
        self._last_event = qthelper.clone_mouse_event(event)
    
    def _handle_release_event(self, event):
        pass
    
    def on_mouse_move_event(self, event):
        self._moveto = event.pos()
        if self.override_tool is not None:
            self.override_tool.on_mouse_move_event(event)
        self.start_using_tool()
        self._handle_move_event(event)
        self._last_event = qthelper.clone_mouse_event(event)
        

    def _handle_move_event(self, event):
        pass


    def start_using_tool(self):
        if not self.in_use:
            self.in_use = True
            self._on_start_using_tool()

    def stop_using_tool(self):
        if self.in_use:
            self._on_stop_using_tool()
            self._last_event = None
            self.in_use = False

    def _on_start_using_tool(self):
        pass
    
    def _on_stop_using_tool(self):
        pass

    def downat(self):
        return _downat()
    def moveto(self):
        return _moveto()

#@DaB - Used for StrandMode
class SelectTool(BasicTool):
    def __init__(self,view):
        BasicTool.__init__( self, view )
        self._press_element = None
        self._release_element = None

    def _on_start_using_tool(self):
        self._view.graphicsView.viewport().setCursor( Qt.ArrowCursor )
        self._p1 = QtCore.QPointF(0,0)

    def _handle_press_event(self, event):
        BasicTool._handle_press_event( self, event )
        self._press_element = None
        self._release_element = None
        clicked_items = self._view.graphicsView.items( event.pos() )
        if len(clicked_items) > 0:
            selected_index = -1
            for index, item in enumerate(clicked_items):
                if item.data(KEY_TYPE).toString()=='BallInstance':
                    if selected_index==-1:
                        minarea = item.data(KEY_AREA).toFloat()[0]
                        selected_index=index
                    else:
                        itemarea = item.data(KEY_AREA).toFloat()[0]
                        if itemarea<minarea:
                            minarea=itemarea
                            selected_index=index
                
            if selected_index != -1:
                data = clicked_items[selected_index].data( KEY_ELEMENT )
                if data.isValid():
                    self._press_element = data.toPyObject()
                    if self._press_element.get('id')=='' or self._press_element.get('type') in metawog.BALLS_NO_STRANDS:
                        self._press_element = None
                    else:
                        #@DaB: Changed to ensure strands come from the center of Rectangle Goos too!
                        self._p1 = poly_weighted_pos(clicked_items[selected_index].mapToScene( clicked_items[selected_index].boundingRect() ),POS_CENTER)
                        #self._p1 = clicked_items[selected_index].pos()
                        p2 = self._view.graphicsView.mapToScene( event.pos() )
                        self._view._show_band(self._p1,p2)
                        self._view.select_item_element( clicked_items[selected_index] )

    def _handle_move_event(self,event):
        BasicTool._handle_move_event(self, event)
        if self._press_element is not None:
            p2 = self._view.graphicsView.mapToScene( event.pos() )
            self._view._show_band(self._p1,p2)

    def _handle_release_event(self, event):
        BasicTool._handle_release_event( self, event )
        self._view._remove_band()
        clicked_items = self._view.items( event.pos() )
        if len(clicked_items) > 0:
            selected_index = -1
            for index, item in enumerate(clicked_items):
              if item.data(KEY_TYPE).toString()=='BallInstance':
                if selected_index==-1:
                    minarea = item.data(KEY_AREA).toFloat()[0]
                    selected_index=index
                else:
                    itemarea = item.data(KEY_AREA).toFloat()[0]
                    if itemarea<minarea:
                        minarea=itemarea
                        selected_index=index

            if selected_index != -1:
                data = clicked_items[selected_index].data( KEY_ELEMENT )
                if data.isValid():
                    self._release_element = data.toPyObject()
                self._act_on_press_release(self._press_element,self._release_element)
        self._press_element = None
        self._release_element = None

    def _act_on_press_release(self, p_element, r_element):
        if p_element is None or r_element is None:
            return
        #Only Strands at the mo
        if (p_element.tag == 'BallInstance') and (r_element.tag=='BallInstance'):
             gb1 = p_element.get('id')
             gb2 = r_element.get('id')

             if (gb1 == '') or (gb2 ==''):
                QtGui.QMessageBox.warning(self._view, self._view.tr("Empty GooBall Id!"),
                                          self._view.tr('GooBalls must have an id to connect a strand') )
                return

             if (gb1 == gb2):
                return

             for child_element in self._view.world.level_root:
                if child_element.tag=='Strand':
                    egb = child_element.get('gb1')
                    if egb==gb1 or egb==gb2:
                        egb = child_element.get('gb2')
                        if egb==gb1 or egb==gb2:
                            QtGui.QMessageBox.warning(self._view, self._view.tr("Duplicate Strand!"),
                                                      self._view.tr('You can\'t have 2 strands between the same balls') )
                            return

             gt1 = p_element.get('type')
             gt2 = r_element.get('type')
             if gt2 in metawog.BALLS_NO_STRANDS:
                 QtGui.QMessageBox.warning(self._view, self._view.tr("Invalid Strand!"),
                                           self._view.tr('You can\'t connect a strand to a ' + gt2) )
                 return

             if (gt1 in metawog.BALLS_MUST_BE_GB1) and (gt2 in metawog.BALLS_MUST_BE_GB1):
                 QtGui.QMessageBox.warning(self._view, self._view.tr("Invalid Strand!"),
                                           self._view.tr('You can\'t connect a ' + gt1 + ' to a ' + gt2) )
                 return
             elif (gt1 in metawog.BALLS_SHOULD_BE_GB2) or (gt2 in metawog.BALLS_MUST_BE_GB1):
                 # swap 'em
                 tb = gb1
                 gb1 = gb2
                 gb2 = tb
             self._addStrand(gb1,gb2)

    def _addStrand(self, gb1, gb2):
            lr = self._view.world.level_root
            attrib = {'gb1':gb1,'gb2':gb2}
            new_strand = lr.make_child( lr.meta.find_immediate_child_by_tag('Strand'), attrib )
            new_strand.world.set_selection( new_strand )            

class PanTool(BasicTool):
    def _on_start_using_tool(self):
        self._view.graphicsView.viewport().setCursor( Qt.OpenHandCursor )

    def _handle_press_event(self, event):
        BasicTool._handle_press_event(self, event)
        self._view.graphicsView.viewport().setCursor( Qt.ClosedHandCursor )
        return True
#@DaB
#Rewritten to allow Zoom in "Pan" Mode
#Click-Release in same location (<5px delta)
# Left = Zoom-in  Right=Zoom-out    
    def _handle_release_event(self, event):
        delta = event.pos() - self._downat
        if vector2d_length(delta.x(),delta.y())<5:
           factor=0
           if (self._press_event.buttons() == Qt.LeftButton):
               # zoomin
               factor = 1.5
           elif (self._press_event.buttons() == Qt.RightButton):
               #zoomout
               factor = 0.6666
           if factor!=0:
                self._view.zoomView( factor, event.pos().x(), event.pos().y() )

        self._view.graphicsView.viewport().setCursor( Qt.OpenHandCursor )
        return True

#@DaB
#Modified to only Pan at delta >5px
    def _handle_move_event(self, event):
        BasicTool._handle_move_event(self, event)
        if self._last_event and self.activated:
            delta = event.pos() - self._downat
            if vector2d_length(delta.x(),delta.y())>5:
                view = self._view.graphicsView
                h_bar = view.horizontalScrollBar()
                v_bar = view.verticalScrollBar()
                delta = event.pos() - self._last_event.pos()
                x_value = h_bar.value()
                if view.isRightToLeft():
                    x_value += delta.x()
                else:
                    x_value -= delta.x()
                h_bar.setValue( x_value )
                v_bar.setValue( v_bar.value() - delta.y() )
        return True


class MoveOrResizeTool(BasicTool):
    """
Need to get current selected item to:
- apply transformation to
- detect tool to activate on click (translate, rotate, resize)
    """
    def __init__(self, view):
        BasicTool.__init__( self, view )
        self._active_tool = None


    def _get_tool_for_event_location(self,event):
        item_at_pos = self._view.graphicsView.itemAt( event.pos() )
        if item_at_pos is not None:
            data = item_at_pos.data( KEY_TOOL )
            activated_tool = None
            if data.isValid():
                activated_tool = data.toPyObject()
                return activated_tool
		#@DaB - Allow Move only if the press was ON the item
        return None

    def _showContextMenu(self,event):
        if len(self._view.world.selected_elements)>0:
            for selected_element in self._view.world.selected_elements:
                top_item = selected_element.tag
                break
        else:
            selected_element = None
            top_item = None

        menu = QtGui.QMenu( self._view )
        if top_item:
           menu.addAction( qthelper.action( menu, enabled=False,  text = top_item  ) )
           menu.addSeparator()

        menu.addAction( self._view.common_actions['cut'] )
        menu.addAction( self._view.common_actions['copy'] )
        menu.addAction(  self._view.common_actions['pastehere'] )
        menu.addSeparator()
        menu.addAction( self._view.common_actions['delete'] )

        is_selected = (selected_element is not None)
        self._view.common_actions['cut'].setEnabled(is_selected)
        self._view.common_actions['copy'].setEnabled(is_selected)
        self._view.common_actions['delete'].setEnabled(is_selected)

        # sort out paste to
        menu.exec_( self._view.graphicsView.mapToGlobal(event.pos() ))

    def _handle_press_event(self, event):
        BasicTool._handle_press_event(self, event)
        # Commit previous tool if any
        if self._active_tool:
            self._active_tool.cancel()
            self._active_tool = None
        if event.buttons() != Qt.LeftButton:
            return
        # Find if any tool handle was clicked by user
        activated_tool = self._get_tool_for_event_location( event )
        if activated_tool is None: #@DaB - Missed all the handles
            # compare previous and newly selected element
            if self._new_select_tool(event): #@DaB - Try a Selec
               activated_tool = self._view.get_current_inner_tool()


        if activated_tool is not None:
            self._active_tool = activated_tool 
            scene_pos = self._view.graphicsView.mapToScene( event.pos() )
            self._active_tool.activated( scene_pos.x(), scene_pos.y(),event.modifiers() )
                
    def _new_select_tool(self, event):
        clicked_items = self._view.graphicsView.items( event.pos() )
        if len(clicked_items) > 0:
            selected_index = -1
            for index, item in enumerate(clicked_items):
                area = item.data(KEY_AREA).toFloat()[0]
                if area>0:
                  if selected_index==-1:
                    minarea = item.data(KEY_AREA).toFloat()[0]
                    selected_index=index
                  else:
                    itemarea = item.data(KEY_AREA).toFloat()[0]
                    if itemarea<minarea:
                        minarea=itemarea
                        selected_index=index
            if selected_index >= 0:
                # something was clicked
                oldsel = self._view.world.selected_elements
                data = clicked_items[selected_index].data( KEY_ELEMENT )
                if data.isValid():
                    clicked_element = data.toPyObject()
                else:
                    clicked_element = None
                if clicked_element is not None:
                    if (event.modifiers() & Qt.ControlModifier)==Qt.ControlModifier:
                        self._view.modify_selection( clicked_items[selected_index] )
                    else:
                        if clicked_element in oldsel:
                            return True
                        self._view.select_item_element( clicked_items[selected_index] )
                return False


        self._view.clear_selection()
        return False
        
    def _handle_release_event(self, event):
        if event.button()==Qt.RightButton:
            self._new_select_tool(event) #@DaB - Try a Selec
            self._showContextMenu(event)
            return

        if self._active_tool is not None:
            scene_pos = self._view.graphicsView.mapToScene( event.pos() )
            self._active_tool.commit( scene_pos.x(), scene_pos.y(),event.modifiers() )
            self._active_tool = None
            self._view.graphicsView.viewport().setCursor( Qt.ArrowCursor )
        else:
            self._handle_move_event(event)

    def _handle_move_event(self, event):
        BasicTool._handle_move_event(self, event)
        # If a tool delegate has been activated, then forward all events
        if self._active_tool is not None:
            scene_pos = self._view.graphicsView.mapToScene( event.pos() )
            self._active_tool.on_mouse_move( scene_pos.x(), scene_pos.y() , event.modifiers())
        else:
            # Otherwise try to find if one would be activated and change mouse cursor
            tool = self._get_tool_for_event_location( event )
            if tool is None: # If None, then go back to selection
                self._view.graphicsView.viewport().setCursor( Qt.ArrowCursor )
            else:
                tool.set_activable_mouse_cursor()

# ###################################################################
# ###################################################################
# Tool Delegates
# ###################################################################
# ###################################################################

class ToolDelegate(object):
    """A tool delegate operate on a single attribute of the object. 
       It provides the following features:
       - set mouse icon corresponding to the tool when mouse is hovering over 
         the tool activation location
       - set mouse icon to activated icon when the user press the left mouse button
       - modify the item to match user action when the mouse is moved
       - cancel or commit change to the underlying element attribute.
    """
    def __init__(self, view, element, item, attribute_meta, state_handler,
                 position_is_center = False, activable_cursor = None, 
                 activated_cursor = None):
        self.view = view
        self.element = element
        self.item = item
        self.attribute_meta = attribute_meta
        self.state_handler = state_handler
        self.activable_cursor = activable_cursor
        self.activated_cursor = activated_cursor or activable_cursor
        self.position_is_center = position_is_center
        self._reset()
        
    def _reset(self): 
        self.activation_pos = None
        self.activation_value = None
        self.activation_item_state = None
        
    def set_activable_mouse_cursor(self):
        if self.activable_cursor is not None:
            self.view.viewport().setCursor( self.activable_cursor )
    
    def set_activated_mouse_cursor(self):
        if self.activated_cursor is not None:
            self.view.viewport().setCursor( self.activated_cursor )

    def activated(self, scene_x, scene_y, modifiers):
     #   print 'Activated:', self
        self.set_activated_mouse_cursor()
        item_pos = self.item.mapFromScene( scene_x, scene_y )
#        print 'Activated:', self, item_pos.x(), item_pos.y()
        self.activation_pos = item_pos
        self.last_pos = self.activation_pos
        self.activation_value = self._get_activation_value()
        self.activation_item_state = self.state_handler.get_item_state(self.item)
        self.on_mouse_move( scene_x, scene_y, modifiers, is_activation = True )

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        if self.attribute_meta.type ==metaworld.XY_TYPE:
            time = self.element.get_native('time')
            return _interpolateValues(self.element.parent,self.attribute_meta.name,(0,0),time)
        elif self.attribute_meta.type ==metaworld.SCALE_TYPE:
            time = self.element.get_native('time')
            return _interpolateValues(self.element.parent,self.attribute_meta.name,(1,1),time)
        elif self.attribute_meta.type in [metaworld.ANGLE_DEGREES_TYPE,metaworld.REAL_TYPE]:
            time = self.element.get_native('time')
            return _interpolateValue(self.element.parent,self.attribute_meta.name,0,time,isangle=True)
        return self.attribute_meta.get_native( self.element )
        
    def cancel(self):
#        print 'Cancelled:', self
        if self.activation_item_state is not None:
            self.restore_activation_state()
        self._reset()
    
    def restore_activation_state(self):
        assert self.activation_item_state is not None
        self.state_handler.restore_item_state( self.item, self.activation_item_state )
    
    def commit(self, scene_x, scene_y, modifiers):
        attribute_value = self.on_mouse_move( scene_x, scene_y , modifiers)
#        print 'Committed:', self, attribute_value
        if attribute_value is not None:
            attributes_to_update = self._list_attributes_to_update( attribute_value )
            for attribute_meta, value in attributes_to_update:
                # Delay until next event loop: destroying the scene while in event
                # handler makes the application crash
                self.view.parent().delayed_element_property_update( self.element,
                                                           attribute_meta,
                                                           value )
        self._reset()
        
    def _list_attributes_to_update(self, attribute_value):
        """Returns a list of tuple(attribute_meta, attribute_value).
           Called on commit to update the element attributes.
        """
        return [ (self.attribute_meta, attribute_value) ]
    
    def on_mouse_move(self, scene_x, scene_y, modifiers, is_activation = False):
        item_pos = self.item.mapFromScene( scene_x, scene_y )
        if is_activation:
            self._on_activation( item_pos )
        result = self._on_mouse_move( item_pos , modifiers)
        self.last_pos = item_pos
        return result

    def _on_activation(self, item_pos):
        pass
    
    def _on_mouse_move(self, item_pos,modifiers):
        raise NotImplemented()
        
    def get_item_bound(self):
        if isinstance(self.item, QtGui.QGraphicsPixmapItem):
            width, height = self.item.pixmap().width(), self.item.pixmap().height()
            return QtCore.QRectF( 0, 0, width, height )
		#@DaB
		#boundingRect includes LineWidth so center was wrong by linewidth/2
        elif isinstance(self.item, QtGui.QGraphicsRectItem):
            return self.item.rect()  #Use .rect instead
        return self.item.boundingRect()
        
    def get_item_center_offset(self):
        """Returns the offset of the center in the item coordinates.
           Some item such as pixmap have their position in the top-left corner.
        """
       #@DaB
       #position_is_center is set for Rects and PixMaps (but position is NOT center)
       # 2 Lines - Temporarily Commented out until I can decide if I can unset the flag
       # Without Harming Anything Else

       # if self.position_is_center:
       #     return QtCore.QPointF()
        bounding_rect = self.get_item_bound()
        return bounding_rect.center() - bounding_rect.topLeft()
        
    def get_item_center_offset_in_parent(self):
        """Returns the offset of the center in the parent coordinates.
           Some item such as pixmap have their position in the top-left corner.
        """
        #if self.position_is_center:
        #    return QtCore.QPointF()
        bounding_rect = self.item.mapToParent( self.get_item_bound() )
        center = poly_weighted_pos( bounding_rect, POS_CENTER )
        offset = center - self.item.pos()
#        print 'Pos: %.f,%.f Center: %.f,%.f, Offset: %.f,%.f' % (
#            self.item.pos().x(), self.item.pos().y(),
#            center.x(), center.y(), 
#            offset.x(), offset.y() )
        return offset

    def get_item_center_pos(self):
        return self.item.pos() + self.get_item_center_offset_in_parent()

class MoveToolDelegate(ToolDelegate):
    """This tool allow the user to move the element in its parent (scene or compositegeom).
    """
    def __init__(self, view, element, item, state_handler, position_is_center, attribute_meta, pos_delegate=None):
        ToolDelegate.__init__( self, view, element, item, state_handler, 
                               position_is_center, attribute_meta,
                               activable_cursor = Qt.SizeAllCursor )
        self.rect_position = None
        self.pos_delegate = pos_delegate

    def set_rect_position(self,rect_position):
        assert self.rect_position is None
        self.rect_position = rect_position

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        av = ToolDelegate._get_activation_value(self)
        if av is None and self.pos_delegate is not None:
            av = self.pos_delegate.get_native( self.element )
        return av


    def _on_mouse_move(self, item_pos,modifiers):
        if self.activation_pos is None:
            return None
        # Compute delta between current position and activation click in parent coordinate
        # then impact position with the delta (position is always in parent coordinate).
        parent_pos = self.item.mapToParent(item_pos)
        self.restore_activation_state()
        activation_parent_pos = self.item.mapToParent( self.activation_pos )
        delta_pos = parent_pos - activation_parent_pos
#       
#        print 'Delta: %.2f, %.2f, New pos: %.2f, %.2f' % (delta_pos.x(), delta_pos.y(),
#                                                          pdelta.x(), pdelta.y())
        if (modifiers & Qt.ControlModifier)==Qt.ControlModifier:
            if abs(delta_pos.x())>abs(delta_pos.y()):
                delta_pos = QtCore.QPointF(delta_pos.x(),0)
            else:
                delta_pos = QtCore.QPointF(0,delta_pos.y())
                
        new_pos = self.item.pos() + delta_pos

        self.item.setPos( new_pos )
        self.view.parent()._update_tools_handle()
        if self.activation_value is None: # Default value to (0,0)
            return delta_pos.x(), -delta_pos.y()
        #@DaB - Round position atrributes
	element_pos_x = round((self.activation_value[0] + delta_pos.x()),ROUND_DIGITS)
        element_pos_y = round((self.activation_value[1] + delta_pos.y()),ROUND_DIGITS)
        return element_pos_x, element_pos_y 

    def _moveVertex(self,new_pos, velement):
          pchild = velement.previous_element()
          prefx, prefy = pchild.get_native( 'pos', (0.0,0.0) )
          ppchild = pchild.previous_element()
          ddx = 1
          ddy = 1
          if ppchild!=velement.parent:
              # limit to a single dimension
              pprefx,pprefy = ppchild.get_native('pos',(0.0,0.0))
              if abs(prefx-pprefx) >abs(prefy-pprefy):
                ddx = 0
              else:
                ddy = 0

          dx = abs(new_pos.x()- prefx)*ddx
          dy = abs(new_pos.y()+ prefy)*ddy
          if dx >= dy:
              new_pos = QtCore.QPointF(new_pos.x(),-prefy)
          else:
              new_pos = QtCore.QPointF(prefx,new_pos.y())

          #Offset center of Item because of Line Width
          new_item_pos = new_pos + QtCore.QPointF(-5,-5)

          self.item.setPos( new_item_pos )
          self.view._update_tools_handle()

          if self.activation_value is None: # Default value to (0,0)
               return new_pos.x(), -new_pos.y()
        #@DaB - Round position atrributes
          element_pos_x = round(new_pos.x(),ROUND_DIGITS)
          element_pos_y = -round(new_pos.y(),ROUND_DIGITS)
          return element_pos_x, element_pos_y

class MultiMoveToolDelegate(ToolDelegate):
    """This tool allow the user to move the element in its parent (scene or compositegeom).
    """
    def __init__(self, view, items, position_is_center):
        self.rect_position = None
        self.view = view
        self.items = set()
        self.element = {}
        self.attribute_meta = {}
        self.state_handler = {}
        for item in items:
         if item is not None:
          if item.data(KEY_ELEMENT).isValid():
            element = item.data(KEY_ELEMENT).toPyObject()
            attrib = []
            for attribute_meta in element.meta.attributes:
              if attribute_meta.type == metaworld.XY_TYPE:
                 if attribute_meta.position:
                   attrib.append(attribute_meta)
                 elif attribute_meta.name=='imagepos':
                   attrib.append(attribute_meta)

            if len(attrib)>0:
                if item not in self.items:
                    self.items.add(item)
                    self.attribute_meta[item] = []
                    self.attribute_meta[item].extend(attrib)
                    self.element[item] = element
                    self.state_handler[item]=self._get_state_manager(item)

        for item in list( self.items ):
            if self.element[item].parent in self.element.values():
                # this items parent was also selected...
                # remove this item
                self.items.remove(item)
        
        self.activable_cursor = Qt.SizeAllCursor
        self.activated_cursor = Qt.SizeAllCursor
        self.position_is_center = position_is_center
        self._reset()

    def _get_state_manager(self,item):
        """Returns the state manager used to save and restore the state of the item."""
        if isinstance( item, QtGui.QGraphicsEllipseItem ):
                return EllipseStateManager()
        elif isinstance( item, QtGui.QGraphicsPixmapItem ):
                return PixmapStateManager()
        elif isinstance( item, QtGui.QGraphicsRectItem):
                return RectStateManager()
        elif isinstance( item, QtGui.QGraphicsLineItem):
                return LineStateManager()
        elif isinstance( item, QtGui.QGraphicsTextItem):
                return TextStateManager()
        elif isinstance( item, QtGui.QGraphicsItemGroup):
                return GroupStateManager()
        return None

    def _reset(self):
        self.activation_pos = {}
        self.activation_value = {}
        self.activation_item_state = {}

    def set_activable_mouse_cursor(self):
        if self.activable_cursor is not None:
            self.view.graphicsView.viewport().setCursor( self.activable_cursor )

    def set_activated_mouse_cursor(self):
        if self.activated_cursor is not None:
            self.view.graphicsView.viewport().setCursor( self.activated_cursor )

    def activated(self, scene_x, scene_y, modifiers):
        self.set_activated_mouse_cursor()
        for item in self.items:
            self.activation_pos[item] = item.mapFromScene( scene_x, scene_y )
            self.activation_item_state[item] = self.state_handler[item].get_item_state(item)
        self.on_mouse_move( scene_x, scene_y, modifiers, is_activation = True )

    def cancel(self):
#        print 'Cancelled:', self
        for item in self.items:
            if self.activation_item_state[item] is not None:
                self.restore_activation_state(item)
        self._reset()

    def restore_activation_state(self,item):
        assert self.activation_item_state[item] is not None
        self.state_handler[item].restore_item_state( item, self.activation_item_state[item] )

    def commit(self, scene_x, scene_y, modifiers):
        for item in self.items:
          attribute_value = self._on_mouse_move( item, scene_x, scene_y , modifiers)
          if attribute_value is not None:

             for attribute in self.attribute_meta[item]:
                activation_value = attribute.get_native( self.element[item], None )
                if activation_value:
                    newvalue = (round(activation_value[0]+attribute_value[0],ROUND_DIGITS),
                                round(activation_value[1]+attribute_value[1],ROUND_DIGITS))

                    self.view.delayed_element_property_update( self.element[item],
                                                        attribute,
                                                        newvalue )
        self._reset()


    def on_mouse_move(self, scene_x, scene_y, modifiers, is_activation = False):
        for item in self.items:
           result = self._on_mouse_move( item, scene_x, scene_y , modifiers)
        return

    def _on_mouse_move(self, item, scene_x,scene_y,modifiers):
        # Compute delta between current position and activation click in parent coordinate
        # then impact position with the delta (position is always in parent coordinate).
        parent_pos = item.mapToParent(item.mapFromScene(scene_x,scene_y))
        self.restore_activation_state(item)
        delta_pos = parent_pos - item.mapToParent( self.activation_pos[item] )
        if (modifiers & Qt.ControlModifier)==Qt.ControlModifier:
            if abs(delta_pos.x())>abs(delta_pos.y()):
                delta_pos = QtCore.QPointF(delta_pos.x(),0)
            else:
                delta_pos = QtCore.QPointF(0,delta_pos.y())
        item.setPos( item.pos() + delta_pos )
        return delta_pos.x(), -delta_pos.y()

class LineToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, state_handler, position_is_center,
                 attribute_meta):
        ToolDelegate.__init__( self, view, element, item, state_handler,
                               position_is_center, attribute_meta,
                               activable_cursor = Qt.SizeBDiagCursor )

    def set_rect_position(self,position):
        pass

    def _on_mouse_move(self, item_pos,modifiers):
        #item will be combined item
        dl = item_pos-self.activation_pos
        dx = self.activation_value[0] + dl.x()*0.02
        dy = self.activation_value[1] - dl.y()*0.02
        oline = self.item.childItems()[1].line()
        self.item.childItems()[1].setLine(oline.x1(),oline.y1(), item_pos.x(),item_pos.y() )

        try:
            angle = vector2d_angle( (self.activation_value[0], self.activation_value[1]),
                                    (dx, dy) )
        except ValueError:
            return None # Current mouse position is the Null vector @todo makes this last value

        transform = QtGui.QTransform()
        transform.translate( oline.x1(), oline.y1() )
        transform.rotate( -angle )
        transform.translate(-oline.x1(), -oline.y1() )
        self.item.childItems()[0].setTransform( transform )

        # return stuff

        self.view._update_tools_handle()
        l = vector2d_length(dx,dy)
        if l==0:
            dx = 1
            dy = 0
        else:
            dx = dx / l
            dy = dy / l
    
        return round(dx,ROUND_DIGITS+3),round(dy,ROUND_DIGITS+3)


class RotateToolDelegate(ToolDelegate):
    """This tool allow the user to rotate the element around its center.
    """
    def __init__(self, view, element, item, state_handler, position_is_center, 
                 attribute_angle, attribute_scale):
        ToolDelegate.__init__( self, view, element, item, state_handler, 
                               position_is_center, attribute_angle,
                               activable_cursor = Qt.ArrowCursor )
        self.attribute_scale = attribute_scale

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        try:
            time = self.element.get_native('time')
            scale_attrib = _interpolateValues(self.element.parent,self.attribute_scale.name,(1,1),time)
        except:
          scale_attrib = None
        return ( ToolDelegate._get_activation_value(self) , scale_attrib )

    def _on_mouse_move(self, item_pos,modifiers):
        # Map current, activation position in parent coordinate
        # Compute angle vectors based on the item center in parent coordinate
        # The angle between both vectors give the angle of rotation to apply
        parent_pos = self.item.mapToParent( item_pos )
        self.restore_activation_state()
        center_pos = self.get_item_center_pos()
        activation_vector = self.item.mapToParent( self.activation_pos ) - center_pos
        new_vector = parent_pos - center_pos 
        if activation_vector.isNull():
            activation_vector = QtCore.QPointF( 1.0, 0 ) # arbitrary move it
        try:
            angle = vector2d_angle( (activation_vector.x(), activation_vector.y()),
                                    (new_vector.x(), new_vector.y()) )
        except ValueError:
            return None # Current mouse position is the Null vector @todo makes this last value
#        print '  Activation: %.2f, %.2f Current: %.2f, %.2f Parent: %.f, %.f Center: %.f, %.f' % (
#            activation_vector.x(), activation_vector.y(), 
#            new_vector.x(), new_vector.y(),
#            parent_pos.x(), parent_pos.y(),
#            center_pos.x(), center_pos.y() )
        # Rotates around the item center
        center_offset = self.get_item_center_offset()
        if self.activation_value[1] is not None: #item has scale attribute
            center_offset = QtCore.QPointF( center_offset.x() * self.activation_value[1][0], center_offset.y() * self.activation_value[1][1])

        # for this to work right....
        # the next bit of code
        # has to EXACTLY match the code / transform sequence that generated the rect / pixmap in the first place
        # took me a while to figure out that it didn't!... does now!
        transform = QtGui.QTransform()
        transform.translate( center_offset.x(), center_offset.y() )
        transform.rotate( -((self.activation_value[0] or 0.0) -angle) )
        transform.translate( -center_offset.x(), -center_offset.y() )
        if self.activation_value[1] is not None:
            transform.scale(self.activation_value[1][0],self.activation_value[1][1])
        self.item.setTransform( transform )

        finalx = center_pos.x() - center_offset.x()
        finaly = center_pos.y() - center_offset.y()
        self.item.setPos( finalx, finaly )
        
        self.view.parent()._update_tools_handle()
        return round((self.activation_value[0] or 0.0) -angle,ROUND_DIGITS)

class MoveAndScaleToolDelegate(ToolDelegate):
    """This tool allow the user to move the corner of a pixmap.
       It will automatically center position and scale factor accordingly.
    """
    def __init__(self, view, element, item, state_handler, position_is_center, 
                 attribute_center, attribute_scale, center_delegate=None):
        ToolDelegate.__init__( self, view, element, item, state_handler, 
                               position_is_center, attribute_center,
                               activable_cursor = Qt.SizeBDiagCursor )
        self.attribute_scale = attribute_scale
        self.center_delegate = center_delegate
        self.rect_position = None 
        
    def set_rect_position(self,rect_position):
        assert self.rect_position is None
        self.rect_position = rect_position 

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        av = ToolDelegate._get_activation_value(self)
        if av is None and self.center_delegate is not None:
            av = self.center_delegate.get_native( self.element )

        time = self.element.get_native('time')
        scale_attrib = _interpolateValues(self.element.parent,self.attribute_scale.name,(1,1),time)

        return ( av, scale_attrib )
        
    def _list_attributes_to_update(self, attribute_value):
        """Returns a list of tuple(attribute_meta, attribute_value).
           Called on commit to update the element attributes.
        """
        return [(self.attribute_meta, attribute_value[0]),
                (self.attribute_scale, attribute_value[1])]
        
    def _on_mouse_move(self, item_pos,modifiers):
        if self.activation_pos is None:
            return None
        if self.activation_value is None:
            return [(0,0),(scale_x, scale_y)]

        activation_pos, activation_scale = self.activation_value
        if activation_scale is None:
            activation_scale = (1,1)

        # item pos is in coordinate system at scale 1 (= to image size)
        # First, map the position to parent coordinate. Restore original item
        # state and map the position back to item coordinate.
        # Then in item coordinate, compare new size to original size
        # => this give us the scale factor
        # From the new item bound, compute the center and map it to parent coordinate.
        # Then determine if the item position needs to be modified (
        # center is center position, or dragging top or left corners).
        parent_item_pos = self.item.mapToParent( item_pos )
        self.restore_activation_state()
        item_pos = self.item.mapFromParent( parent_item_pos )
        
        # Computes new item bounds
        bound_rect = self.get_item_bound()
        if not bound_rect.isValid(): # has 0 width or height ?
            return None
        xminmax = [bound_rect.x(), bound_rect.right()]  
        yminmax = [bound_rect.y(), bound_rect.bottom()]

        oldcenter = self.item.mapToParent(QtCore.QPointF((bound_rect.left()+bound_rect.right())*0.5,(bound_rect.top()+bound_rect.bottom())*0.5))
        # x/y minmax impacted indexes by position
        old_width, old_height = xminmax[1] - xminmax[0], yminmax[1] - yminmax[0]

        impacts_by_position = { # tuple(xindex,yindex)
            POS_TOP_LEFT: (0,0,2,2),
            POS_TOP_CENTER: (None,0,1,2),
            POS_TOP_RIGHT: (1,0,0,2),
            POS_CENTER_LEFT: (0,None,2,1),
            POS_CENTER: (None,None,1,1),
            POS_CENTER_RIGHT: (1,None,0,1),
            POS_BOTTOM_LEFT: (0,1,2,0),
            POS_BOTTOM_CENTER: (None,1,1,0),
            POS_BOTTOM_RIGHT: (1,1,0,0),
            }
        impact = impacts_by_position[self.rect_position]
        assert impact is not None
        if impact[0] is not None:
            xminmax[ impact[0] ] = item_pos.x()
        if impact[1] is not None:
            yminmax[ impact[1] ] = item_pos.y()
        new_width, new_height = xminmax[1] - xminmax[0], yminmax[1] - yminmax[0]
        if new_width <= 0.0 or new_height <= 0.0:
            return None
        # Computes scale factor
        scale_x = new_width / bound_rect.width()
        scale_y = new_height / bound_rect.height()
        if (modifiers & Qt.AltModifier)==Qt.AltModifier:
            if scale_x<scale_y:
               # use scale_x
               scale_y = scale_x
               if impact[1]==0: #moving top
                    yminmax[0] = yminmax[1]-old_height*scale_y
               else: # moving bottom
                    yminmax[1] = yminmax[0]+old_height*scale_y
            else:
               # use scale_y
               scale_x = scale_y
               if impact[0]==0: #moving top
                    xminmax[0] = xminmax[1]-old_width*scale_x
               else: # moving bottom
                    xminmax[1] = xminmax[0]+old_width*scale_x

        elif (modifiers & Qt.ControlModifier)==Qt.ControlModifier:
            real_scalex = activation_scale[0]*scale_x
            real_scaley = activation_scale[1]*scale_y

            if real_scalex<real_scaley:
               # use scale_x
               scale_y = real_scalex/activation_scale[1]
               if impact[1]==0: #moving top
                    yminmax[0] = yminmax[1]-old_height*scale_y
               else: # moving bottom
                    yminmax[1] = yminmax[0]+old_height*scale_y
            else:
               # use scale_y
               scale_x = real_scaley/activation_scale[0]
               if impact[0]==0: #moving top
                    xminmax[0] = xminmax[1]-old_width*scale_x
               else: # moving bottom
                    xminmax[1] = xminmax[0]+old_width*scale_x

        newcenter = self.item.mapToParent(QtCore.QPointF((xminmax[0]+xminmax[1])*0.5,(yminmax[0]+yminmax[1])*0.5))
        deltacenter = newcenter-oldcenter


        newpos = self.item.pos()
        newposx = newpos.x() + impact[2] * deltacenter.x()
        newposy = newpos.y() + impact[3] * deltacenter.y()
        self.item.setPos(QtCore.QPointF(newposx,newposy))
        self.item.scale( scale_x, scale_y )
        self.view.parent()._update_tools_handle()

        #@DaB - Round position and scale atrributes
        if activation_pos is None:
            activation_pos = (0,0)
        if activation_scale is None:
            activation_scale = (1,1)
        new_scale_x = round(activation_scale[0] * scale_x,ROUND_DIGITS+1)
        new_scale_y = round(activation_scale[1] * scale_y,ROUND_DIGITS+1)
        new_pos_x = round((activation_pos[0] + deltacenter.x()),ROUND_DIGITS)
        new_pos_y = round((activation_pos[1] + deltacenter.y()),ROUND_DIGITS)
        return [(new_pos_x,new_pos_y), (new_scale_x, new_scale_y)]
        
class DXDYToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, state_handler, position_is_center,
                 attribute_meta):
        ToolDelegate.__init__( self, view, element, item, state_handler,
                               position_is_center, attribute_meta,
                               activable_cursor = Qt.SizeBDiagCursor )

    def set_rect_position(self,position):
        pass

    def _on_mouse_move(self, item_pos,modifiers):
        dl = item_pos-self.activation_pos
        dx = self.activation_value[0] + dl.x()*0.05
        dy = self.activation_value[1] - dl.y()*0.05
        oline = self.item.line()
        self.item.setLine(oline.x1(),oline.y1(), item_pos.x(),item_pos.y() )
        self.view._update_tools_handle()
        return round(dx,ROUND_DIGITS),round(dy,ROUND_DIGITS)

class ResizeToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, state_handler, position_is_center, attribute_center, attribute_size):
        ToolDelegate.__init__( self, view, element, item, state_handler,
                               position_is_center, attribute_center,
                               activable_cursor = Qt.SizeBDiagCursor )
        self.attribute_size = attribute_size
        self.rect_position = None

    def set_rect_position(self,rect_position):
        assert self.rect_position is None
        self.rect_position = rect_position

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        return ( ToolDelegate._get_activation_value(self),
                 self.attribute_size.get_native( self.element ) )

    def _list_attributes_to_update(self, attribute_value):
        """Returns a list of tuple(attribute_meta, attribute_value).
           Called on commit to update the element attributes.
        """
        return [(self.attribute_meta, attribute_value[0]),
                (self.attribute_size, attribute_value[1])]

    def _on_mouse_move(self, item_pos,modifiers):
        if self.activation_pos is None:
            return None
        # item pos is in coordinate system at scale 1 (= to image size)
        # First, map the position to parent coordinate. Restore original item
        # state and map the position back to item coordinate.
        # Then in item coordinate, compare new size to original size
        # => this give us the scale factor
        # From the new item bound, compute the center and map it to parent coordinate.
        # Then determine if the item position needs to be modified (
        # center is center position, or dragging top or left corners).
        parent_item_pos = self.item.mapToParent( item_pos )
        self.restore_activation_state()
        item_pos = self.item.mapFromParent( parent_item_pos )

        # Computes new item bounds
        bound_rect = self.get_item_bound()
        if not bound_rect.isValid(): # has 0 width or height ?
            return None
        xminmax = [bound_rect.x(), bound_rect.right()]
        yminmax = [bound_rect.y(), bound_rect.bottom()]
        oldcenter = self.item.mapToParent(QtCore.QPointF((bound_rect.left()+bound_rect.right())*0.5,(bound_rect.top()+bound_rect.bottom())*0.5))
        # x/y minmax impacted indexes by position
        impacts_by_position = { # tuple(xindex,yindex)
            POS_TOP_LEFT: (0,0,2,2),
            POS_TOP_CENTER: (None,0,1,2),
            POS_TOP_RIGHT: (1,0,0,2),
            POS_CENTER_LEFT: (0,None,2,1),
            POS_CENTER: (None,None,1,1),
            POS_CENTER_RIGHT: (1,None,0,1),
            POS_BOTTOM_LEFT: (0,1,2,0),
            POS_BOTTOM_CENTER: (None,1,1,0),
            POS_BOTTOM_RIGHT: (1,1,0,0),
            }
        impact = impacts_by_position[self.rect_position]
        assert impact is not None

        if impact[0] is not None:
            xminmax[ impact[0] ] = item_pos.x()
        if impact[1] is not None:
            yminmax[ impact[1] ] = item_pos.y()

        new_width = xminmax[1] - xminmax[0]
        new_height = yminmax[1] - yminmax[0]
        if new_width <= 0.0 or new_height <= 0.0:
            return None

        scale_x = new_width / bound_rect.width()
        scale_y = new_height / bound_rect.height()


        newcenter = self.item.mapToParent(QtCore.QPointF((xminmax[0]+xminmax[1])*0.5,(yminmax[0]+yminmax[1])*0.5))
        deltacenter = newcenter-oldcenter

        # Computes scale factor

        self.item.scale( scale_x, scale_y )
        #self.item.rect().setWidth(new_width)
        #self.item.rect().setHeight(new_height)

        newpos = self.item.pos()
        newposx = newpos.x() + impact[2] * deltacenter.x()
        newposy = newpos.y() + impact[3] * deltacenter.y()
        self.item.setPos(QtCore.QPointF(newposx,newposy))
        self.view._update_tools_handle()

        if self.activation_value is None:
            return [(0,0),(scale_x, scale_y)]
        activation_pos, activation_size = self.activation_value
        if activation_pos is None:
            activation_pos = (0,0)
        if activation_size is None:
            activation_size = (5,5)
        new_size_x = round(activation_size[0] * scale_x,ROUND_DIGITS)
        new_size_y = round(activation_size[1] * scale_y,ROUND_DIGITS)
        new_pos_x = round(activation_pos[0] + deltacenter.x(),ROUND_DIGITS)
        new_pos_y = round(activation_pos[1] - deltacenter.y(),ROUND_DIGITS)
        return [(new_pos_x,new_pos_y), (new_size_x, new_size_y)]

class RadiusToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, state_handler, position_is_center, 
                 attribute_meta):
        ToolDelegate.__init__( self, view, element, item, state_handler, 
                               position_is_center, attribute_meta,
                               activable_cursor = Qt.SizeBDiagCursor )
        
    def set_rect_position(self,position):
        pass
        
    def _on_mouse_move(self, item_pos,modifiers):
        # Circle are always zero centered, hence we can just get the current distance
        # from the origin to get the current length.
        # The difference between the current length and the activation length is
        # used to impact the radius as it was at the time of the activation
        r_pos = vector2d_length( item_pos.x(), item_pos.y() )
        r_activation = vector2d_length( self.activation_pos.x(),
                                        self.activation_pos.y() )
        r = round(abs(self.activation_value + r_pos - r_activation),ROUND_DIGITS)
        self.item.setRect( -r, -r, r*2, r*2 )
        self.view._update_tools_handle()
        return r


# ###################################################################
# ###################################################################
# Tools Factories
# ###################################################################
# ###################################################################
# Tool selector needs to handle:
# Move: inside
# Resize: 
# - on rectangle: 4 corners, rely on shift modifier to force horizontal/vertical only
# - on circle: 4 middle crossing the axis
# Rotate: 
# - on rectangle: 4 middle handles
# - on circle: 4 handles spread over at 45 degrees
# Using scene item has handle implies:
# -> Creates/destroy item on selection change, hide them during operation
# -> associates them with selected item
# -> compute handle position in item coordinate and map to scene
# -> handle should show no direction (avoid rotation transformation issue)
#
class ToolsFactory(object):
    """Responsible for creating and positioning the "handle" items used to
       activate tools (rotate, resize...) when clicked.
    """  
    
    def get_pixel_length(self, view):
        """Returns the length of a pixel in scene unit."""
        origin_pos = view.mapToScene( QtCore.QPoint() )
        f = 10000
        unit_pos = view.mapToScene( QtCore.QPoint( UNIT_VECTOR_COORDINATE*f,
                                                   UNIT_VECTOR_COORDINATE*f ) )
        unit_vector = (unit_pos - origin_pos) / f
        unit_length = vector2d_length( unit_vector.x(), unit_vector.y() )
        return unit_length

    
    def create_tools(self, item, element, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        self._make_tools( item, element, view, self._get_state_manager() )
        resize_tool_pos, rotate_tool_pos = self._get_tools_positions()
        bouding_poly = item.mapToScene( item.boundingRect() )
#        for index in range(0,4):
#            pos = bouding_poly[index]
#            print 'Bounding poly [%d] = %.2f, %.2f' % (index, pos.x(), pos.y())
        items = []
        pixel_length = self.get_pixel_length( view )
        for tool_index, positions in enumerate( (resize_tool_pos, rotate_tool_pos) ):
            for pos_index, position in enumerate( positions ):
                pos = poly_weighted_pos( bouding_poly, position )
#                print 'Tool %d, index %d %s: %.2f,%.2f' % (tool_index, pos_index, position,
#                                                           pos.x(), pos.y() ) 
                size = QtCore.QPointF( 3*pixel_length, 3*pixel_length )
                bound = QtCore.QRectF( pos - size, pos + size )
                if tool_index == 0 and self.resize_tools is not None:
                    tool_item = view.scene().addRect( bound )
                    tool = self.resize_tools[pos_index]
                    tool.set_rect_position( position )
                elif tool_index == 1 and self.rotate_tools is not None:
                    tool_item = view.scene().addEllipse( bound )
                    tool = self.rotate_tools[pos_index]
                else:
                    tool_item = None
                if tool_item is not None:
                    tool_item.setZValue( Z_TOOL_ITEMS )
                    tool_item.setData( KEY_TOOL, QtCore.QVariant( tool ) )
                    tool_item.setData(KEY_TYPE,QtCore.QVariant('TOOL'))
                    items.append( tool_item )
        return self.move_tool, items

    def _make_tools(self, item, element, view, state_manager):
        attribute_radius = None
        attribute_center = None
        attribute_size = None
        attribute_scale = None
        attribute_angle = None
        attribute_dxdy = None
        for attribute_meta in element.meta.attributes:
            if attribute_meta.type == metaworld.RADIUS_TYPE:
                attribute_radius = attribute_meta
            elif attribute_meta.type == metaworld.XY_TYPE:
                attribute_center = attribute_center or attribute_meta
            elif attribute_meta.type == metaworld.SIZE_TYPE:
                attribute_size = attribute_size or attribute_meta
            elif attribute_meta.type == metaworld.SCALE_TYPE:
                attribute_scale = attribute_scale or attribute_meta
            elif attribute_meta.type == metaworld.DXDY_TYPE:
                attribute_dxdy = attribute_dxdy or attribute_meta
            elif attribute_meta.type in (metaworld.ANGLE_DEGREES_TYPE, 
                                         metaworld.ANGLE_RADIANS_TYPE):
                attribute_angle = attribute_angle or attribute_meta
        position_is_center = not self._center_is_top_left()
        def make_delegate( type, attribute, *args ):
            if attribute is not None:
                return type( view, element, item, attribute, state_manager, 
                             position_is_center, *args )
            return None
        self.move_tool = make_delegate( MoveToolDelegate, attribute_center )
        self.resize_tools = None
        if attribute_radius is not None:
            self.resize_tools = [ make_delegate( RadiusToolDelegate, 
                                                 attribute_radius )
                                  for i in range(0,4) ]
# @todo Restore this once resizing is implemented
        elif attribute_size is not None:
            self.resize_tools =  [ make_delegate( ResizeToolDelegate, attribute_center,
                                                 attribute_size )   for i in range(0,4) ]
        elif attribute_scale is not None:
            self.resize_tools = [ make_delegate( MoveAndScaleToolDelegate, attribute_center,
                                                 attribute_scale ) 
                                  for i in range(0,4) ]
        elif attribute_dxdy is not None:
            self.resize_tools = [ make_delegate( DXDYToolDelegate, attribute_dxdy )
                                   for i in range(0,4) ]

        if attribute_angle is not None:
            self.rotate_tools = [ make_delegate(RotateToolDelegate, attribute_angle, attribute_scale)
                                  for i in range(0,4) ]
        else:
            self.rotate_tools = None 

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        raise NotImplemented()

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        raise NotImplemented()

    def _center_is_top_left(self):
        """Indicates if the item position represents the center or the top-left corner of
           the bounding box.
        """
        return False

class CircleToolsFactory(ToolsFactory):

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        resize_tool_pos = ( POS_TOP_CENTER, POS_BOTTOM_CENTER,
                            POS_CENTER_LEFT, POS_CENTER_RIGHT ) 
#        rotate_tool_pos = ( POS_TOP_LEFT, POS_TOP_RIGHT,
#                            POS_BOTTOM_RIGHT, POS_BOTTOM_LEFT )
        return  resize_tool_pos, ()

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return EllipseStateManager()

class PixmapToolsFactory(ToolsFactory):
    """Pixmap may be either circle with image, rectangle with image, SceneLayer or
       part of a compositgeom.
    """

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        rotate_tool_pos = ( POS_CENTER_LEFT, POS_CENTER_RIGHT )
        resize_tool_pos = ( POS_TOP_LEFT,POS_BOTTOM_RIGHT )
        return  resize_tool_pos, rotate_tool_pos 

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return PixmapStateManager()

    def _center_is_top_left(self):
        return True

class BallToolsFactory(ToolsFactory):
    """Pixmap may be either circle with image, rectangle with image, SceneLayer or
       part of a compositgeom.
    """
    def create_tools(self, item, element, view ):
        self.ball_type = element.get('type')
        return ToolsFactory.create_tools(self,item,element,view)

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        if self.ball_type is None or self.ball_type=='':
            rotate_tool_pos=()
        else:
            try:
                ball_shape = metawog.BALLS_SHAPES[self.ball_type]
                if ball_shape[0]=='circle':
                    rotate_tool_pos=()
                else:
                    rotate_tool_pos = ( POS_CENTER_LEFT, POS_CENTER_RIGHT )
            except KeyError:
                rotate_tool_pos=()

        return (), rotate_tool_pos

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return PixmapStateManager()

    def _center_is_top_left(self):
        return True

class MultiMoveToolsFactory(ToolsFactory):

    def create_tools(self, items, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        self.move_tool = MultiMoveToolDelegate(view,items,False)
        return self.move_tool, []


class RectangleToolsFactory(ToolsFactory):

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        rotate_tool_pos = ( POS_CENTER_LEFT, POS_CENTER_RIGHT )
        resize_tool_pos = ( POS_TOP_LEFT,POS_BOTTOM_RIGHT )
        return  resize_tool_pos, rotate_tool_pos

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return RectStateManager()

class LineToolsFactory(ToolsFactory):

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        rotate_tool_pos = ( POS_CENTER_LEFT, POS_CENTER_RIGHT )
        resize_tool_pos = ( )
        return  resize_tool_pos, rotate_tool_pos

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return LineStateManager()

class TextToolsFactory(ToolsFactory):     

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        rotate_tool_pos = ( POS_MID_RIGHT, POS_MID_RIGHT )
        return  (), rotate_tool_pos

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return TextStateManager()

#@DaB Different framwork for Group Items... because...
# Different SubItems require different tools
# Tool Positions need to based on subitem bounding rect, not combined item

# returns the 1 default movetool and list of other tools
class GroupToolsFactory(ToolsFactory):

    def _build_tool(self,view,pos,position,size,type,tool, fillcolor=QtGui.QColor(0,0,0)):
        bound = QtCore.QRectF( pos - size, pos + size )
        if type == 'rect':
            tool_item = view.scene().addRect( bound )
            tool.set_rect_position( position )
        elif type == 'rectfill':
            pen = QtGui.QPen(QtGui.QColor(255,255,255))
            xbrush = QtGui.QBrush( fillcolor,Qt.SolidPattern )
            tool_item = view.scene().addRect( bound ,pen, xbrush)
            tool.set_rect_position( position )
        elif type=='circle':
            tool_item = view.scene().addEllipse( bound )
        elif type=='circlefill':
            pen = QtGui.QPen(QtGui.QColor(255,255,255))
            xbrush = QtGui.QBrush( fillcolor,Qt.SolidPattern )
            tool_item = view.scene().addEllipse( bound,pen,xbrush )
        else:
            tool_item = None
        if tool_item is not None:
            tool_item.setZValue( Z_TOOL_ITEMS )
            tool_item.setData( KEY_TOOL, QtCore.QVariant( tool ) )
            tool_item.setData(KEY_TYPE,QtCore.QVariant('TOOL'))
        return tool_item

class RectangleGroupToolFactory(GroupToolsFactory):

    def create_tools(self, item, element, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        items = []
        pixel_length = self.get_pixel_length( view )
        size = QtCore.QPointF( 4*pixel_length, 4*pixel_length )

        bounding_poly= []
        for subitem in item.childItems():
            bounding_poly.append(subitem.mapToScene( subitem.boundingRect() ))

        self.move_tool = MoveToolDelegate(view,element,item.childItems()[1],
                                            element.meta.attribute_by_name('center'),
                                            RectStateManager(),False)
        self.resize_tools = []
        newtool = ResizeToolDelegate(view,element, item.childItems()[1],
                                                 element.meta.attribute_by_name('center'),
                                                 RectStateManager(),
                                                 False,
                                                 element.meta.attribute_by_name('size'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[1],POS_TOP_LEFT)
        items.append(self._build_tool(view,pos,POS_TOP_LEFT,size,'rect',newtool))

        newtool = ResizeToolDelegate(view,element, item.childItems()[1],
                                                 element.meta.attribute_by_name('center'),
                                                 RectStateManager(),
                                                 False,
                                                 element.meta.attribute_by_name('size'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[1],POS_BOTTOM_RIGHT)
        items.append(self._build_tool(view,pos,POS_BOTTOM_RIGHT,size,'rect',newtool))

        newtool = MoveAndScaleToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagepos'),
                                                 PixmapStateManager(),
                                                 True,
                                                 element.meta.attribute_by_name('imagescale')
                                                 ,element.meta.attribute_by_name('center'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_TOP_LEFT)
        items.append(self._build_tool(view,pos,POS_TOP_LEFT,size,'rectfill',newtool))

        newtool = MoveAndScaleToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagepos'),
                                                 PixmapStateManager(),
                                                 True,
                                                 element.meta.attribute_by_name('imagescale')
                                                 ,element.meta.attribute_by_name('center'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_BOTTOM_RIGHT)
        items.append(self._build_tool(view,pos,POS_BOTTOM_RIGHT,size,'rectfill',newtool))

        newtool = MoveToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagepos'),
                                                 PixmapStateManager(),
                                                 True,
                                                 element.meta.attribute_by_name('center'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_CENTER)
        items.append(self._build_tool(view,pos,POS_CENTER,size,'rectfill',newtool))

        newtool = RotateToolDelegate(view,element, item.childItems()[1],
                                                 element.meta.attribute_by_name('rotation'),
                                                 RectStateManager(),
                                                 True,None)
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[1],POS_CENTER_RIGHT)
        items.append(self._build_tool(view,pos,POS_CENTER_RIGHT,size,'circle',newtool))

        newtool = RotateToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagerot'),
                                                 PixmapStateManager(),
                                                 True,element.meta.attribute_by_name('imagescale'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_CENTER_LEFT)
        items.append(self._build_tool(view,pos,POS_CENTER_LEFT,size,'circlefill',newtool))

        return self.move_tool, items

class LineGroupToolFactory(GroupToolsFactory):

    def create_tools(self, item, element, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        items = []
        pixel_length = self.get_pixel_length( view )
        size = QtCore.QPointF( 4*pixel_length, 4*pixel_length )

        bounding_poly= []
        for subitem in item.childItems():
            bounding_poly.append(subitem.mapToScene( subitem.boundingRect() ))

        self.move_tool = MoveToolDelegate(view,element,item.childItems()[0],
                                            element.meta.attribute_by_name('anchor'),
                                            LineStateManager(),False)
        self.resize_tools = []
        newtool = LineToolDelegate(view,element, item,
                                                 element.meta.attribute_by_name('normal'),
                                                 GroupStateManager(),
                                                 False)
        self.resize_tools.append(newtool)
        pos = item.childItems()[1].mapToScene( item.childItems()[1].line().p2() )
        items.append(self._build_tool(view,pos,POS_BOTTOM_RIGHT,size,'circle',newtool))

        return self.move_tool, items


class CircleGroupToolFactory(GroupToolsFactory):
    def create_tools(self, item, element, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        items = []
        pixel_length = self.get_pixel_length( view )
        size = QtCore.QPointF( 4*pixel_length, 4*pixel_length )

        bounding_poly= []
        for subitem in item.childItems():
            bounding_poly.append(subitem.mapToScene( subitem.boundingRect() ))

        self.move_tool = MoveToolDelegate(view,element,item.childItems()[1],
                                            element.meta.attribute_by_name('center'),
                                            EllipseStateManager(),False)
        self.resize_tools = [RadiusToolDelegate(view,element, item.childItems()[1],
                                                 element.meta.attribute_by_name('radius'),
                                                 EllipseStateManager(),
                                                 False)  for i in range(0,4)]

        for index, position in enumerate( (POS_TOP_CENTER,POS_CENTER_LEFT,POS_CENTER_RIGHT,POS_BOTTOM_CENTER)):
          pos = poly_weighted_pos(bounding_poly[1],position)
          items.append(self._build_tool(view,pos,position,size,'rect',self.resize_tools[index]))

        newtool = MoveAndScaleToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagepos'),
                                                 PixmapStateManager(),
                                                 True,
                                                 element.meta.attribute_by_name('imagescale'),
                                                 element.meta.attribute_by_name('center'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_TOP_LEFT)
        items.append(self._build_tool(view,pos,POS_TOP_LEFT,size,'rectfill',newtool))

        newtool = MoveAndScaleToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagepos'),
                                                 PixmapStateManager(),
                                                 True,
                                                 element.meta.attribute_by_name('imagescale'),
                                                 element.meta.attribute_by_name('center'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_BOTTOM_RIGHT)
        items.append(self._build_tool(view,pos,POS_BOTTOM_RIGHT,size,'rectfill',newtool))

        newtool = MoveToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagepos'),
                                                 PixmapStateManager(),
                                                 True,
                                                 element.meta.attribute_by_name('center'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_CENTER)
        items.append(self._build_tool(view,pos,POS_CENTER,size,'rectfill',newtool))

        newtool = RotateToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('imagerot'),
                                                 PixmapStateManager(),
                                                 True,element.meta.attribute_by_name('imagescale'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_CENTER_LEFT)
        items.append(self._build_tool(view,pos,POS_CENTER_LEFT,size,'circlefill',newtool))

        return self.move_tool, items

class LinearFFGroupToolFactory(GroupToolsFactory):
    def create_tools(self, item, element, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        items = []
        pixel_length = self.get_pixel_length( view )
        size = QtCore.QPointF( 4*pixel_length, 4*pixel_length )

        bounding_poly= []
        for subitem in item.childItems():
            bounding_poly.append(subitem.mapToScene( subitem.boundingRect() ))

        self.move_tool = MoveToolDelegate(view,element,item.childItems()[0],
                                            element.meta.attribute_by_name('center'),
                                            RectStateManager(),False)
        self.resize_tools = []
        newtool = ResizeToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('center'),
                                                 RectStateManager(),
                                                 False,
                                                 element.meta.attribute_by_name('size'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_TOP_LEFT)
        items.append(self._build_tool(view,pos,POS_TOP_LEFT,size,'rect',newtool))

        newtool = ResizeToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('center'),
                                                 RectStateManager(),
                                                 False,
                                                 element.meta.attribute_by_name('size'))
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(bounding_poly[0],POS_BOTTOM_RIGHT)
        items.append(self._build_tool(view,pos,POS_BOTTOM_RIGHT,size,'rect',newtool))

        newtool = DXDYToolDelegate(view,element, item.childItems()[1],
                                                 element.meta.attribute_by_name('force'),
                                                 LineStateManager(),
                                                 False)
        self.resize_tools.append(newtool)
        pos = item.childItems()[1].mapToScene( item.childItems()[1].line().p2() )
        items.append(self._build_tool(view,pos,POS_BOTTOM_RIGHT,size,'rect',newtool))


        return self.move_tool, items

class RadialFFGroupToolFactory(GroupToolsFactory):
    def create_tools(self, item, element, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        items = []
        pixel_length = self.get_pixel_length( view )
        size = QtCore.QPointF( 4*pixel_length, 4*pixel_length )

        bounding_poly= []
        for subitem in item.childItems():
            bounding_poly.append(subitem.mapToScene( subitem.boundingRect() ))

        self.move_tool = MoveToolDelegate(view,element,item.childItems()[0],
                                            element.meta.attribute_by_name('center'),
                                            EllipseStateManager(),False)
        self.resize_tools = [RadiusToolDelegate(view,element, item.childItems()[0],
                                                 element.meta.attribute_by_name('radius'),
                                                 EllipseStateManager(),
                                                 False)  for i in range(0,4)]

        for index, position in enumerate( (POS_TOP_CENTER,POS_CENTER_LEFT,POS_CENTER_RIGHT,POS_BOTTOM_CENTER)):
          pos = poly_weighted_pos(bounding_poly[0],position)
          items.append(self._build_tool(view,pos,position,size,'rect',self.resize_tools[index]))

        return self.move_tool, items

class CompGeomGroupToolFactory(GroupToolsFactory):

    def create_tools(self, item, element, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        items = []
        pixel_length = self.get_pixel_length( view )
        size = QtCore.QPointF( 4*pixel_length, 4*pixel_length )

        children_bounding_poly= None
        children_item = None
        pixmap_bounding_poly = None
        pixmap_item = None
        for subitem in item.childItems():
             if isinstance( subitem, QtGui.QGraphicsItemGroup):
                children_item = subitem
                children_bounding_poly = subitem.mapToScene( subitem.childrenBoundingRect() )
             elif isinstance( subitem, QtGui.QGraphicsPixmapItem):
                pixmap_item = subitem
                pixmap_bounding_poly= subitem.mapToScene( subitem.boundingRect() )

        self.move_tool = MoveToolDelegate(view,element,children_item,
                                            element.meta.attribute_by_name('center'),
                                            GroupStateManager(),False)
        self.resize_tools = []
        newtool = MoveToolDelegate(view,element, children_item,
                                                 element.meta.attribute_by_name('center'),
                                                 GroupStateManager(),
                                                 True)
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(children_item.mapToScene(QtCore.QRectF(-1,-1,2,2)),POS_CENTER)
        items.append(self._build_tool(view,pos,POS_CENTER,size,'rect',newtool))

        newtool = RotateToolDelegate(view,element, children_item,
                                                 element.meta.attribute_by_name('rotation'),
                                                 GroupStateManager(),
                                                 True,None)
        self.resize_tools.append(newtool)
        pos = poly_weighted_pos(children_bounding_poly,POS_CENTER_RIGHT)
        items.append(self._build_tool(view,pos,POS_CENTER_RIGHT,QtCore.QPointF( 6*pixel_length, 6*pixel_length ),'circlefill',newtool,QtGui.QColor(0,255,0)))

        if pixmap_item:
            newtool = MoveAndScaleToolDelegate(view,element, pixmap_item,
                                                 element.meta.attribute_by_name('imagepos'),
                                                 PixmapStateManager(),
                                                 True,
                                                 element.meta.attribute_by_name('imagescale')
                                                 ,element.meta.attribute_by_name('center'))
            self.resize_tools.append(newtool)
            pos = poly_weighted_pos(pixmap_bounding_poly,POS_TOP_LEFT)
            items.append(self._build_tool(view,pos,POS_TOP_LEFT,size,'rectfill',newtool))

            newtool = MoveAndScaleToolDelegate(view,element, pixmap_item,
                                                     element.meta.attribute_by_name('imagepos'),
                                                     PixmapStateManager(),
                                                     True,
                                                     element.meta.attribute_by_name('imagescale')
                                                     ,element.meta.attribute_by_name('center'))
            self.resize_tools.append(newtool)
            pos = poly_weighted_pos(pixmap_bounding_poly,POS_BOTTOM_RIGHT)
            items.append(self._build_tool(view,pos,POS_BOTTOM_RIGHT,size,'rectfill',newtool))

            newtool = MoveToolDelegate(view,element, pixmap_item,
                                                     element.meta.attribute_by_name('imagepos'),
                                                     PixmapStateManager(),
                                                     True,
                                                     element.meta.attribute_by_name('center'))
            self.resize_tools.append(newtool)
            pos = poly_weighted_pos(pixmap_bounding_poly,POS_CENTER)
            items.append(self._build_tool(view,pos,POS_CENTER,size,'rectfill',newtool))


            newtool = RotateToolDelegate(view,element, pixmap_item,
                                                     element.meta.attribute_by_name('imagerot'),
                                                     PixmapStateManager(),
                                                     True,element.meta.attribute_by_name('imagescale'))
            self.resize_tools.append(newtool)
            pos = poly_weighted_pos(pixmap_bounding_poly,POS_CENTER_LEFT)
            items.append(self._build_tool(view,pos,POS_CENTER_LEFT,size,'circlefill',newtool))

        return self.move_tool, items

GroupToolsFactorys = {'rectangle':RectangleGroupToolFactory,
                      'circle':CircleGroupToolFactory,
                      'compositegeom':CompGeomGroupToolFactory,
                      'linearforcefield':LinearFFGroupToolFactory,
                      'radialforcefield':RadialFFGroupToolFactory,
                      'line':LineGroupToolFactory}

# ###################################################################
# ###################################################################
# State Managers
# ###################################################################
# ###################################################################

class StateManager(object):
    def get_item_state(self, item):
        """Returns an object representing the current item state."""
        return (item.pos(), item.transform(), self._get_item_state(item))
    
    def _get_item_state(self, item): #IGNORE:W0613
        """Returns an object represent the state specific to the item type."""
        return None
    
    def restore_item_state(self, item, state):
        """Restore the item in the state capture by get_item_state."""
        pos, transform, specific_state = state
        item.setPos( pos )
        item.setTransform( transform ) 
        self._set_item_state( item, specific_state )
        
    def _set_item_state(self, item, state):
        """Restore the item specific state capture by _get_item_state()."""
        pass

PixmapStateManager = StateManager
TextStateManager = StateManager
GroupStateManager = StateManager

class RectStateManager(StateManager):
    def _get_item_state(self, item):
        return item.rect()
    
    def _restore_item_state(self, item, state):
        item.setRect( state )

class LineStateManager(StateManager):
    def _get_item_state(self, item):
        return item.line()

    def _restore_item_state(self, item, state):
        item.setLine( state )

class EllipseStateManager(StateManager):
    def _get_item_state(self, item):
        return (item.rect(), item.startAngle(), item.spanAngle())
    
    def _restore_item_state(self, item, state):
        rect, start_angle, span_angle = state
        item.setRect( rect )
        item.setStartAngle( start_angle )
        item.setSpanAngle( span_angle )

class MyQGraphicsView(QtGui.QGraphicsView):


    def wheelEvent(self,event):
        self.parent().wheelEvent(event)
        event.accept()
    def mousePressEvent(self, event):
        self.parent().mousePressEvent(event)
        event.accept()
    def mouseDoubleClickEvent(self, event):
        self.parent().mouseDoubleClickEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.parent().mouseReleaseEvent(event)
        event.accept()

    def mouseMoveEvent( self, event):
        self.parent().mouseMoveEvent(event)
        event.accept()



class GraphicView(QtGui.QWidget):
    """A graphics view that display scene and level elements.
       Signals:
       QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)')
         => when the mouse mouse in the map. parameters: x,y in scene coordinate.
    """
    def __init__( self, window,world, tools_actions, common_actions ):
        QtGui.QWidget.__init__( self )
        self.window = window
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.slider = QtGui.QSlider(self)
        self.slider.setSizePolicy(sizePolicy)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.slider.setTickInterval(1)
        self.slider.setTracking(True)
        self.slider.setObjectName("slider")
        self.horizontalLayout.addWidget(self.slider)

        self.timelabel = QtGui.QLabel(self)
        self.timelabel.setObjectName("timelabel")
        self.timelabel.setMinimumSize(80,40)

        font = QtGui.QFont()
        font.setPointSize(10)
        font.setWeight(75)
        font.setBold(True)
        self.timelabel.setFont(font)
        self.timelabel.setAlignment(QtCore.Qt.AlignCenter)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.timelabel.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.timelabel)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.graphicsView = MyQGraphicsView(self)
        self.graphicsView.setObjectName("graphicsView")
#        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
#        self.graphicsView.setSizePolicy(sizePolicy)
        self.verticalLayout.addWidget(self.graphicsView)

        self.connect( self.slider, QtCore.SIGNAL('valueChanged(int)'),self._on_slider_change)
#        self.connect( self.graphicsView, QtCore.SIGNAL('wheelEvent(PyQt_PyObject)'),self.wheelEvent)

        self.__world = world

        self.common_actions = common_actions
        self.setAttribute( Qt.WA_DeleteOnClose )
        self.__scene = QtGui.QGraphicsScene()
        self.__balls_by_id = {}
        self.__ball_shapes = {}
        self.__strands = []
        self.__lines = []
        self.__scene_elements = set()
        self.__level_elements = set()
        self.__tools_by_actions = {}
        self.__tools_group = None
        self._delayed_property_updates = []
        self._delayed_timer_id = None
        self._band_item = None
        self._BGColour = QtGui.QColor(192,192,192)
        self._slider_timer_id = None

        for name, action in tools_actions.iteritems():
            self.__tools_by_actions[action] = name
            self.__tools_group = self.__tools_group or action.actionGroup()
        self._tools_by_name = {
            TOOL_SELECT: SelectTool(self),
            TOOL_PAN: PanTool(self),
            TOOL_MOVE: MoveOrResizeTool(self)
            }
        self._elements_to_skip = None
        self._active_tool = None
        self._tools_handle_items = []
        self._current_inner_tool = None
        self._items_by_element = {}
        self._actor_by_item = {}
        self._selection_tool_degates_cache = (None,[])
        self.graphicsView.setScene( self.__scene )
        self.__scene.setSceneRect(-500,-500,2095,1600)

        # Notes: we disable interactive mode. It is very easily to make the application
        # crash when interactive mode is allowed an mouse events are "sometimes" 
        # accepted by the overridden view. Instead, we handle selection and panning
        # ourselves.
        self.graphicsView.setInteractive( False )
        self._type_states = {}
        self._type_states['camera']=ELEMENT_STATE_INVISIBLE
        self._type_states['poi']=ELEMENT_STATE_INVISIBLE
        
#@DaB
        self.graphicsView.scale( 0.75, 0.75 )
        self.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.graphicsView.centerOn (1095/2, 600/2)

        self.graphicsView.setMouseTracking(True)
        self.graphicsView.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform )
        self._last_press_at = QtCore.QPointF(0,0)
        self._last_release_at = QtCore.QPointF(0,0)
        self._time = 0
        self.starttime = 0
        self.playing = False
        self.movielength = 0
        self.changingslider = False
        self._fps = self.autoFPS()

        self.setWindowTitle( self.tr( self.__world.key + '   ( '+`self.fps` + " fps )"))

        self.refreshFromModel()

        # Subscribes to level element change to refresh the view
        for tree in self.__world.trees:
            tree.connect_to_element_events( self.__on_element_added,
                                            self.__on_element_updated,
                                            self.__on_element_about_to_be_removed )
        louie.connect( self._on_active_world_change, metaworldui.ActiveWorldChanged, 
                       self.__world.universe )
        louie.connect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                       self.__world )
        

    @property
    def world(self):
        return self.__world

    @property
    def scene(self):
        return self.__scene

    @property
    def time(self):
        return self._time


    def is_selected_item(self, item):
        data = item.data( KEY_ELEMENT )
        if data.isValid():
            return data.toPyObject() in self.__world.selected_elements
        return False

    def get_enabled_view_tools(self):
        return set( [TOOL_PAN, TOOL_SELECT, TOOL_MOVE] )

    def get_current_inner_tool(self):
        """Returns the tool delegate to use when the user click inside a shape.
           This is usually the MoveToolDelegate.
        """
        return self._current_inner_tool
    
    @property
    def fps(self):
        return float(self._fps)

    def setBGColour(self,colour):
        self._BGColour = colour
        self.refreshFromModel()
    def autoFPS(self):
        # tries to automatically determine the frame rate from the keyframe times
        # unless it gets a "good" match will default to 20
        frame_times = []
        nframes = 0
        for keyframe in self.__world.movie_root.findall('.//keyframe'):
            frametime = keyframe.get_native('time')
            if frametime > 0:
                nframes+=1
                if frametime not in frame_times:
                    frame_times.append(frametime)
        frame_times.sort()
        nframetimes = len(frame_times)
        residuals = []
        for qfps in range(10,40):
            residual = 0
            for frametime in frame_times:
                rawresidual = (frametime * float(qfps)) - int((frametime * float(qfps))+0.5)
                residual+= abs(rawresidual)/nframetimes
            residuals.append(residual)
        
        tfps = 0
        minres = 10000
        for i,residual in enumerate(residuals):
            if residual < minres:
                tfps = i+10
                minres = residual
                if residual == 0:
                    break

        if tfps == 0 or minres > 0.01:
            #no lock
            return float(20)
        return tfps

    def _update_tools_handle(self):
        """Updates tools' handle on current select item. 
           Must be called whenever the scale factory change or selection change.
        """
        # Removes any existing handle
        # Notes: we need to be very careful there, removing item that have been removed
        # by other means such as clear() cause the application to crash.
        for tool_item in self._tools_handle_items:
            self.__scene.removeItem( tool_item )
        self._tools_handle_items = []
        self._current_inner_tool = None 
        # get selected elements, corresponding item and generate new handles
        elements = self.__world.selected_elements
        if len(elements) > 1: # @todo handle multiple selection
            return
        if len(elements)!=1:
            return
        if self._get_active_tool() != self._tools_by_name[TOOL_MOVE]:
            return # No handle for select or pan tool
        element = iter(elements).next()
        item = self._items_by_element.get( element )

        # selected element and item do not match
        if item is None:
            # element could be keyframe or actor
            actor_element = None
            # if element is keyframe..
              # is there in item with a keyframe of the same parent
            if element.tag=='keyframe':
                actor_element = element.parent
            elif element.tag=='actor':
                actor_element = element
            if actor_element is None:
               return
            select_item = None
            select_element = None
            for itemelement,item in self._items_by_element.items():
                if itemelement.tag =='keyframe':
                    if itemelement.parent==actor_element:
                        select_item = item
                        select_element = itemelement
                        break
            if select_item is None:
                return

            item = select_item
            element = select_element

            
        factory_type = None
        if isinstance( item, QtGui.QGraphicsEllipseItem ):
            factory_type = CircleToolsFactory
        elif isinstance( item, QtGui.QGraphicsPixmapItem ):
            if element.tag=='BallInstance':
                factory_type = BallToolsFactory
            else:
                factory_type = PixmapToolsFactory
        elif isinstance( item, QtGui.QGraphicsRectItem):
            factory_type = RectangleToolsFactory
        elif isinstance( item, QtGui.QGraphicsLineItem):
            factory_type = LineToolsFactory
        elif isinstance( item, QtGui.QGraphicsTextItem):
            factory_type = TextToolsFactory
        elif isinstance( item, QtGui.QGraphicsItemGroup)  and self.is_selected_item(item):
            factory_type = GroupToolsFactorys[element.tag]

        if factory_type is not None:
            self._current_inner_tool, self._tools_handle_items = factory_type().create_tools(item, element, self.graphicsView)

        if self._tools_handle_items:
          for tool_item in self._tools_handle_items:
            # Prevent the item from being selected
            tool_item.setAcceptedMouseButtons( Qt.NoButton ) 

    def delayed_element_property_update(self, element, attribute_meta, new_value):
        self._delayed_property_updates.append( (element, attribute_meta, new_value) )
        if self._delayed_timer_id is None:
            self._delayed_timer_id = self.startTimer(0)
        
    def timerEvent(self, event):
        if event.timerId() == self._delayed_timer_id:
            self.killTimer( self._delayed_timer_id )
            self._delayed_timer_id = None
            pending, self._delayed_property_updates = self._delayed_property_updates, []
            for element, attribute_meta, new_value in pending:
                attribute_meta.set_native( element, new_value )
            event.accept()
        elif event.timerId() == self._slider_timer_id:
            self.killTimer( self._slider_timer_id )
            self.updateFromModel()
            self._slider_timer_id = None
        else:
            QtGui.QGraphicsView.timerEvent(self, event)
        
#        if self._selection_tool_degates_cache[0] == element:
#            return self._selection_tool_degates_cache[1][:]
#        # Only handle plain rectangle, pixmap and circle at the current time
#        tool_factories = None
#        if isinstance( item, QtGui.QGraphicsRectItem, QtGui.QGraphicsPixmapItem ):
#            return RectangleToolSelector( self, element, item )
##            tool_factories = {
##                metaworld.XY_TYPE: RectangleMoveToolDelegate,
##                metaworld.SIZE_TYPE: RectangleResizeToolDelegate
##                }
#        elif isinstance( item, QtGui.QGraphicsEllipseItem ):
#            return 
##            tool_factories = {
##                metaworld.XY_TYPE: CircleMoveToolDelegate,
##                metaworld.RADIUS_TYPE: CircleRadiusToolDelegate
##                }
#        elif isinstance( item, QtGui.QGraphicsPixmapItem ):
#            tool_factories = {
#                metaworld.XY_TYPE: PixmapMoveToolDelegate,
#                metaworld.SCALE_TYPE: PixmapScaleToolDelegate
#                }
#        available_tools = []
#        for attribute in element.attributes:
#            factory = tool_factories.get(attribute.type)
#            if factory:
#                if factory == MoveOrRadiusToolDelegate:
#                    if available_tools and isinstance( available_tools[-1], 
#                                                       MoveToolDelegate):
#                        del available_tools[-1] # tool replace simple moving tool
#                        
#                tool = factory( self, element, item, attribute )
#                available_tools.append( tool )
#        self._selection_tool_degates_cache = (element, available_tools[:])
#        return available_tools

    def tool_activated( self, tool_name ):
        """Activates the corresponding tool in the view and commit any pending change.
        """
        if self._active_tool:
            self._active_tool.stop_using_tool()
        self._get_active_tool().start_using_tool()
        self._update_tools_handle()
#        if tool_name == TOOL_SELECT:
#            self.setDragMode( QtGui.QGraphicsView.NoDrag )
#        elif tool_name == TOOL_PAN:
#            self.setDragMode( QtGui.QGraphicsView.ScrollHandDrag )

    def _on_slider_change(self,t):
        if not self.changingslider:
            self.changingslider=True
            self._time = float(t)/self.fps
            if self._slider_timer_id is None:
                self._slider_timer_id = self.startTimer(0)
            self.changingslider=False
        
    def _setFrame(self,f):
        self._time = float(f)/self.fps
        self.updateFromModel()

    def _setTime(self,t):
        self._time = float(t)
        self.changingslider=True
        self.slider.setValue(int(t*self.fps)+0.5)
        self.changingslider=False
        self.updateFromModel()

    def selectOnSubWindowActivation( self ):
        """Called when the user switched MDI window."""
        if self.window.playing:
            self.window.stop()
        self.__world.game_model.selectMovie( self.__world.key )

    def clear_selection(self):
        self.__world.set_selection( [] )

    def select_item_element(self, item):
        """Selects the element corresponding to the specified item.
           Called when the user click on an item with the selection tool.
        """
        data = item.data( KEY_ELEMENT )
        if data.isValid():
            element = data.toPyObject()
            self.__world.set_selection( element )
        else:
            print "data is not valid for ",item

    def modify_selection(self, item):
        """Selects the element corresponding to the specified item.
           Called when the user click on an item with the selection tool.
        """
        data = item.data( KEY_ELEMENT )
        if data.isValid():
            element = data.toPyObject()
            return self.__world.modify_selection( element )
        else:
            print "data is not valid for ",item
        return False

    def _get_active_tool(self):
        name = self.__tools_by_actions.get( self.__tools_group.checkedAction() )
        tool = self._tools_by_name.get(name)
        if tool is None:
            tool =  self._tools_by_name[TOOL_SELECT]
        self._active_tool = tool
        return tool

    def mousePressEvent(self, event):
        self._last_press_at = self.graphicsView.mapToScene(event.pos())
        self._get_active_tool().on_mouse_press_event( event )
        event.accept()
	#@DaB - Ensure if Click then Press to move is quick enough to be consider a Double-click
	# that it still works.
    def mouseDoubleClickEvent(self, event):
        self._last_press_at = self.graphicsView.mapToScene(event.pos())
        self._get_active_tool().on_mouse_press_event( event )
        event.accept()

    def mouseReleaseEvent(self, event):
        self._last_release_at = self.graphicsView.mapToScene(event.pos())
        self._get_active_tool().on_mouse_release_event( event )
        event.accept()

    def mouseMoveEvent( self, event):
        self._last_pos = self.graphicsView.mapToScene( event.pos() )
        self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), self._last_pos.x(), self._last_pos.y() )
        self._get_active_tool().on_mouse_move_event( event )
        

    def closeEvent(self,event):
        # could check for unsaved change and ask here
        if not self.__world.isReadOnly and self.__world.is_dirty:
            # ask unsaved changes
            ret =  QtGui.QMessageBox.warning(self, "Save Changes to " + self.__world.name,
                            'There are unsaved changes to ' + self.__world.name,
                            QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel )
            if ret==QtGui.QMessageBox.Cancel:
                event.ignore()
                return
            if ret==QtGui.QMessageBox.Save:
                self.__world.saveModifiedElements()

        self.__world.parent_world.remove_world(self.__world)
        del self.__world.game_model.models_by_name[self.__world.name]
        if self._delayed_timer_id is not None:
            self.killTimer( self._delayed_timer_id )#
        if len(self.parent().mdiArea().subWindowList())==1:
            louie.send( metaworldui.ActiveWorldChanged, None, None )

        
        
        QtGui.QWidget.closeEvent(self,event)
        event.accept()

    def wheelEvent(self, event):
        """Handle zoom when wheel is rotated."""
#@DaB
#Added to update displayed position on Zoom
        pos = self.graphicsView.mapToScene( event.pos() )
        self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), pos.x(), pos.y() )
        event.accept()
        delta = event.delta()
        if delta != 0:
            small_delta = delta / 500.0
            factor = abs(small_delta)
            if small_delta < 0:
                factor = 1/(1+factor)
            else:
                factor = 1 + small_delta
#@DaB
#New function zoomView replaces scaleView
			#self.scaleView( factor ) 
            self.zoomView( factor, event.pos().x(), event.pos().y() )
            self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), pos.x(), pos.y() )

#@DaB
#New Zoom function which give a more "natural" zooming
#In the center of the window 0.2 -> 0.8 
#Keeps the part of the scene at the mouse pointer still (in the same place after zoom)
#At the edges (0->0.2  0.8>1) it scrolls the scene by an increasing amount
#to bring "off-screen" items inwards

    def zoomView(self, scaleFactor, orX, orY):
        factor = self.graphicsView.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()

        if factor < 0.07 or factor > 100:
            return
        self.graphicsView.scale(scaleFactor, scaleFactor)
        
        dx = (orX - self.graphicsView.width()*0.5)
        if scaleFactor > 1:
            llimit = self.graphicsView.width()*0.30
            if dx > llimit :
                dx = dx*4 - llimit*3
            elif dx<-llimit:
                dx = dx*4 + llimit*3

        dy = (self.graphicsView.height()*0.5 - orY)
        if scaleFactor > 1:
            llimit = self.graphicsView.height()*0.30
            if dy > llimit :
                dy = dy*4 - llimit*3
            elif dy<-llimit:
                dy = dy*4 + llimit*3

        h_bar = self.graphicsView.horizontalScrollBar()
        v_bar = self.graphicsView.verticalScrollBar()
        x_value = h_bar.value()
        if self.graphicsView.isRightToLeft():
            x_value -= dx * (scaleFactor-1)
        else:
            x_value += dx * (scaleFactor-1)
        h_bar.setValue( x_value )
        v_bar.setValue( v_bar.value() - dy * (scaleFactor-1) )
        self._update_tools_handle()

    def _on_selection_change(self, selection, #IGNORE:W0613
                             selected_elements, deselected_elements,
                             **kwargs): 
        """Ensures that the selected element is seleted in the graphic view.
           Called whenever an element is selected in the tree view or the graphic view.
        """
        # Notes: we do not change selection if the item belong to an item group.
        # All selection events send to an item belonging to a group are forwarded
        # to the item group, which caused infinite recursion (unselect child,
        # then unselect parent, selection parent...)
        
        # if the selection has changed...
        if len(selected_elements)>0:
            element = iter(selected_elements).next()
            if element.tag == 'keyframe':
                time = element.get_native('time',0)
                self._setTime(time)
                return

        # get selected actors
        selected_actors = [element.parent for element in selection if element.tag=='keyframe']
        selected_actors.extend([element for element in selection if element.tag=='actor'])

        for item in self.__scene.items():
          data = item.data( KEY_ELEMENT )
          if data.isValid():
             #itemtype = item.data( KEY_TYPE ).toString()
             #if itemtype!='TOOL':
             #   print "Data not valid in _on_selection_change",itemtype,item
          #else:
            element = item.data(KEY_ELEMENT).toPyObject()
            if element in selection or self._actor_by_item[item] in selected_actors:
##                print 'Selecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                if not item.isSelected() and item.group() is None:
                    item.setSelected( True )
            elif item.isSelected() and item.group() is None:
                item.setSelected( False )


        self._update_tools_handle()
 

    def getModel( self ):
        return self.__world

    def __on_element_added(self, element, index_in_parent): #IGNORE:W0613
        self.refreshFromModel()

    def __on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        self.refreshFromModel()

    def __on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0613
        self.refreshFromModel( set([element]) )

    def _on_active_world_change(self, active_world):
        """Called when a new world becomes active (may be another one).
        """
        if active_world == self.__world:
            self.refreshFromModel()
        
    def refreshFromModel( self, elements_to_skip = None ):

        self._elements_to_skip = elements_to_skip or set()
        scene = self.__scene
        scene.setBackgroundBrush(QtGui.QBrush (self._BGColour, Qt.SolidPattern))
        scene.clear()
#        scene.setSceneRect(-200,-200,1495,1000)

        self._tools_handle_items = []
        self._current_inner_tool = None
        self._items_by_element = {}
        self._actor_by_item = {}

        for actor in self.__world.movie_root.findall('actor'):
            if actor not in self._elements_to_skip:
                item = self.drawActor(scene,actor)
                if item:
                    self._items_by_element[item.data(KEY_ELEMENT).toPyObject()]=item
                    self._actor_by_item[item]=actor
        
        length = 0
        for keyframe in self.__world.movie_root.findall('.//keyframe'):
            if keyframe not in self._elements_to_skip:
                if keyframe.get_native('time',0)>length:
                    length=keyframe.get_native('time',0)

        self.movielength = length
        self.slider.setMaximum(self.movielength*self.fps)

        self._sceneBuilder(scene)

        # Select currently selected item if any
        self._on_selection_change( self.__world.selected_elements, set(), set() )
        self.timelabel.setText("%3.2f : %3.1f" % (self.time,self.movielength) )


    def updateFromModel(self):
        self._items_by_element = {}
        actor_keys = self._actor_by_item.keys()
        for item in self.__scene.items():
            itemtype = item.data( KEY_TYPE ).toString()
            if itemtype!='TOOL':
                if item in actor_keys:
                    self.updateActor( self._actor_by_item[item],item)
                    self._items_by_element[item.data(KEY_ELEMENT).toPyObject()]=item

        #for actor in self.__world.movie_root.findall('actor'):
        #    self.updateActor( actor)
        self._on_selection_change( self.__world.selected_elements, set(), set() )
        self.timelabel.setText("%3.2f : %3.1f" % (self.time,self.movielength) )

    def get_element_state(self,elementtype):
        try:
            estate = self._type_states[elementtype]
        except KeyError:
            estate = ELEMENT_STATE_NONE
        return estate
    
    def set_element_state(self,elementtype,estate):
        self._type_states[elementtype]=estate

    def updateActor( self, actor,item ):
        if len(actor)==1:
            return
        updaters = {
            'image': self._sceneSceneLayerUpdate,
            'text': self._sceneLabelUpdate,
            }
        updater = updaters.get( actor.get('type') )
        if updater:
            updater(  actor, item)


    def drawActor( self, scene, actor ):
        if not actor.get_native('visible',True):
            return None

        builders = {
            'image': self._sceneSceneLayerBuilder,
            'text': self._sceneLabelBuilder,
            }
        builder = builders.get( actor.get('type') )
        item = None
        if builder:
            item = builder( scene, actor )
            if item:
               item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, True )
               #self._items_by_element[item.data(KEY_ELEMENT).toPyObject()] = item

#        element_set.add( element )
        return item

    @staticmethod
    def _elementV2Pos( element, attribute, default_value = (0.0,0.0) ): # y=0 is bottom => Negate y
        x, y = element.get_native( attribute, default_value )
        return x, -y

    @staticmethod
    def _elementImageWithPosScaleRot( element ):
        image = element.get('image')
        if image is None:
            return None,None,None,None
        if element.get('imagepos') is not None:
            imagepos = GraphicView._elementV2Pos( element, 'imagepos' )
        else:
            imagepos=None
        imagescale = element.get_native( 'imagescale', (1.0,1.0) )
        imagerot = element.get_native( 'imagerot',0.0 )
        return image, imagepos, imagescale, imagerot

    @staticmethod
    def _setLevelItemZ( item ):
        item.setZValue( Z_LEVEL_ITEMS )

    @staticmethod
    def _setLevelItemXYZ( item, x, y ):
        item.setZValue( Z_LEVEL_ITEMS )
        item.setPos( x, y )

    @staticmethod
    def _setSceneItemXYZ( item, x, y ):
        item.setZValue( Z_PHYSIC_ITEMS )
        item.setPos( x, y )

    def getImagePixmap( self, image_id ):
        """Returns the image pixmap for the specified image id."""
        if image_id is not None:
            return self.__world.getImagePixmap( image_id )
        return None

    def _getKeyFrame(self,element):
        pframe = None
        for keyframe in element.findall('keyframe'):
            frametime = keyframe.get_native('time',0)
            #print element.get('image'),attribute,frametime,value
            if frametime <= self.time:
                pframe = keyframe
            if frametime >=self.time:
                break
        return pframe

    def _getPreviousKeyFrame(self,element,time):
        # find previous and next keyframe in which attribute is specified
        pframe = None
        # get the value and the time
        for keyframe in element:
            frametime = keyframe.get_native('time',0)
            if frametime <= time:
                pframe = keyframe
            if frametime >=time:
                break
        return pframe

    def _sceneSceneLayerUpdate(self,element,item):
        time,kf = getActorTime(element,self.time,self._elements_to_skip)
        scalex,scaley = _interpolateValues(element,'scale',(0,0),time,self._elements_to_skip)
        alpha= float(_interpolateValue(element,'alpha',0,time,self._elements_to_skip))/255.0
        if alpha ==0 or scalex==0 or scaley==0:
                #if item.isVisible():
                #    print item," now invisible"
                item.setVisible(False)
                return
        x,y = _interpolateValues(element,'position',(0,0),time,self._elements_to_skip)
        rotation = _interpolateValue(element,'angle',0,time,self._elements_to_skip,isangle=True)
        depth = element.get_native( 'depth', 0.0 )
        item.setVisible(True)
        r,g,b = _interpolateValues(element,'color',(255,255,255),time,self._elements_to_skip)
        if isinstance(item,QtGui.QGraphicsPixmapItem):
            cr,cg,cb = item.data(KEY_EXTRA).toPyObject()
        else:
            cr,cg,cb = 255,255,255
            
        image = element.get('image','')
        pixmap = None
        if r!=cr or g!=cg or b!=cb :
            #print "color update frame : ",r,g,b
            if image!='':
                pixmap = self.getImagePixmap( image )
            if pixmap is not None:
                color_pixmap = QtGui.QPixmap(pixmap.width(),pixmap.height())
                color_pixmap.fill(QtGui.QColor(r,g,b))
 #               pixmap_alpha = pixmap.alphaChannel()
                new_pixmap = pixmap.copy(0,0,pixmap.width(),pixmap.height())
                painter = QtGui.QPainter( new_pixmap )
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_Multiply)
                painter.drawPixmap( 0,0, color_pixmap )
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
                painter.drawPixmap( 0,0, pixmap )
                painter.end()
#                new_pixmap.setAlphaChannel(pixmap_alpha)
                item.setPixmap(new_pixmap)
                item.setData(KEY_EXTRA ,QtCore.QVariant( (r,g,b) ) )

        if isinstance(item,QtGui.QGraphicsPixmapItem):
            self._applyPixmapTransform( item, item.pixmap(), x, y, rotation, scalex, scaley, depth )
        else:
            self._applyTransform( item, 50, 50, x, y, rotation, 1.0, 1.0, depth )

        item.setOpacity(alpha)
        if kf is None:
            item.setData( KEY_ELEMENT, QtCore.QVariant( element  ) )
        else:
            item.setData( KEY_ELEMENT, QtCore.QVariant( kf ) )

    def _sceneSceneLayerBuilder( self, scene, element ):
        time,kf = getActorTime(element,self.time,self._elements_to_skip)
        x,y = _interpolateValues(element,'position',(0,0),time,self._elements_to_skip)
        rotation = _interpolateValue(element,'angle',0,time,self._elements_to_skip,isangle=True)
        scalex,scaley = _interpolateValues(element,'scale',(0,0),time,self._elements_to_skip)
        alpha= _interpolateValue(element,'alpha',0,time,self._elements_to_skip)
        alpha=float(alpha)/255.0
        depth = element.get_native( 'depth', 0.0 ) 

        image = element.get('image')
        if image!='':
            pixmap = self.getImagePixmap( image )
        else:
            pixmap = None
        if pixmap is not None:
            r,g,b = _interpolateValues(element,'color',(255,255,255),time,self._elements_to_skip)
            if r!=255 or g!=255 or b!=255:
                color_pixmap = QtGui.QPixmap(pixmap.width(),pixmap.height())
                color_pixmap.fill(QtGui.QColor(r,g,b))
                #pixmap_alpha = pixmap.alphaChannel()
                new_pixmap = pixmap.copy(0,0,pixmap.width(),pixmap.height())
                painter = QtGui.QPainter( new_pixmap )
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_Multiply)
                painter.drawPixmap( 0,0, color_pixmap )
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
                painter.drawPixmap( 0,0, pixmap )
                painter.end()
                #new_pixmap.setAlphaChannel(pixmap_alpha)
                item = scene.addPixmap( new_pixmap )
            else:
                item = scene.addPixmap( pixmap )
            item.setData(KEY_EXTRA ,QtCore.QVariant( (r,g,b) ) )
            item.setData(KEY_AREA , QtCore.QVariant( pixmap.height()*pixmap.width()*scalex*scaley ))
            item.setTransformationMode(Qt.SmoothTransformation)
            self._applyPixmapTransform( item, pixmap, x, y, rotation, scalex, scaley, depth )
            item.setOpacity(alpha)
        else:
            pen = QtGui.QPen( QtGui.QColor( 255, 0, 0 ) )
            pen.setWidth( 4 )
            item = scene.addRect( 0, 0, 100, 100, pen )
            item.setData(KEY_AREA , QtCore.QVariant( 10000 ))
            self._applyTransform( item, 50, 50, x, y, rotation, 1.0, 1.0, depth )

        item.setData(KEY_TYPE , QtCore.QVariant( element.get('type') ) )
        if kf is None:
            item.setData( KEY_ELEMENT, QtCore.QVariant( element  ) )
        else:
            item.setData( KEY_ELEMENT, QtCore.QVariant( kf ) )

        return item

    @staticmethod
    def _applyPixmapTransform( item, pixmap, x, y, rotation, scalex, scaley, depth ):
        GraphicView._applyTransform( item, pixmap.width()/2.0, pixmap.height()/2.0,
                                          x, y, rotation, scalex, scaley, depth )

    @staticmethod
    def _applyTransform( item, xcenter, ycenter, x, y, rotation, scalex, scaley, depth ):
        """Rotate, scale and translate the item. xcenter, ycenter indicates the center of rotation.
        """
        # Notes: x, y coordinate are based on the center of the image, but Qt are based on top-left.
        # Hence, we adjust the x, y coordinate by half width/height.
        # But rotation is done around the center of the image, that is half width/height
        transform = QtGui.QTransform()
        xcenter, ycenter = xcenter * scalex, ycenter * scaley
        transform.translate( xcenter, ycenter )
        transform.rotate( -rotation )
        transform.translate( -xcenter, -ycenter )
        transform.scale(scalex,scaley)
        item.setTransform( transform )
        x -= xcenter
        y -= ycenter
        item.setPos( x, y )
        item.setZValue( depth )

    def _sceneLabelUpdate(self,element,item):
        time,kf = getActorTime(element,self.time,self._elements_to_skip)
        scalex,scaley = _interpolateValues(element,'scale',(0,0),time,self._elements_to_skip)
        alpha= float(_interpolateValue(element,'alpha',0,time,self._elements_to_skip))/255.0
        if alpha ==0 or scalex==0 or scaley==0:
                #if item.isVisible():
                #    print item," now invisible"
                item.setVisible(False)
                return
        item.setVisible(True)
        x,y = _interpolateValues(element,'position',(0,0),time,self._elements_to_skip)
        rotation = _interpolateValue(element,'angle',0,time,self._elements_to_skip, isangle=True)
        depth = element.get_native('depth',0)
        alignment = element.get('align',"left")
        item.setOpacity(alpha)


        offsety = item.boundingRect().height()/2
        if alignment=="left":
            offsetx = 0
        elif alignment=="right":
            offsetx = item.boundingRect().width()
        else:
            offsetx = item.boundingRect().width()/2
        self._applyTransform( item,offsetx, offsety, x, y, rotation, scalex, scaley, depth )


        if kf is None:
            item.setData( KEY_ELEMENT, QtCore.QVariant( element  ) )
        else:
            item.setData( KEY_ELEMENT, QtCore.QVariant( kf ) )

    def _sceneLabelBuilder( self, scene, element ):
        time,kf = getActorTime(element,self.time,self._elements_to_skip)
        x,y = _interpolateValues(element,'position',(0,0),time,self._elements_to_skip)
        rotation = _interpolateValue(element,'angle',0,time,self._elements_to_skip,isangle=True)
        scalex,scaley = _interpolateValues(element,'scale',(0,0),time,self._elements_to_skip)
        alpha= _interpolateValue(element,'alpha',0,time,self._elements_to_skip)
        alpha=float(alpha)/255.0
        depth = element.get_native('depth',0)
        alignment = element.get('align',"left")
        font = QtGui.QFont()
        font.setPointSize( 16.0 )
        font.setBold( True )
        font.setStyleStrategy(QtGui.QFont.PreferAntialias | QtGui.QFont.PreferQuality)

        text = element.get('text')
        if text is None:
            text='!Set_Text!'
        item = scene.addText( text, font )
        item.setData(KEY_AREA , QtCore.QVariant( item.boundingRect().width() * item.boundingRect().height() ))
        item.setData(KEY_TYPE , QtCore.QVariant( element.get('type') ) )
        item.setDefaultTextColor( QtGui.QColor( 64, 255, 0 ) )
        item.setOpacity(alpha)
        offsety = item.boundingRect().height()/2
        if alignment=="left":
            offsetx = 0
        elif alignment=="right":
            offsetx = item.boundingRect().width()
        else:
            offsetx = item.boundingRect().width()/2

        self._applyTransform( item,offsetx, offsety, x, y, rotation, scalex, scaley, depth )
        if kf is None:
            item.setData( KEY_ELEMENT, QtCore.QVariant( element  ) )
        else:
            item.setData( KEY_ELEMENT, QtCore.QVariant( kf ) )
        return item

    def _sceneBuilder( self, scene ):
        minx,maxx = 0,1095
        miny,maxy = 0,600
        x, y = (minx+maxx)*0.5,(miny+maxy)*0.5
        rotation = 0
        width, height = abs(maxx-minx),abs(maxy-miny)
        pen = QtGui.QPen( QtGui.QColor( 0, 0, 0 ) )
        pen.setWidth( 2 )
        pen.setStyle( Qt.DotLine)
        item = scene.addRect( 0, 0, width, height, pen )
        item.setData(KEY_AREA , QtCore.QVariant( 10*width*height +1))
        item.setData(KEY_TYPE , QtCore.QVariant( 'scene' ) )
        self._applyTransform( item, width/2.0, height/2.0, x, y, rotation, 1.0, 1.0, Z_TOOL_ITEMS )

        minx,maxx = 0,800
        width, height = abs(maxx-minx),abs(maxy-miny)
        pen = QtGui.QPen( QtGui.QColor( 0, 0, 0 ) )
        pen.setWidth( 1 )
        pen.setStyle( Qt.DotLine)
        item = scene.addRect( 0, 0, width, height, pen )
        item.setData(KEY_AREA , QtCore.QVariant( 10*width*height +1))
        item.setData(KEY_TYPE , QtCore.QVariant( 'scene' ) )
        self._applyTransform( item, width/2.0, height/2.0, x, y, rotation, 1.0, 1.0, Z_TOOL_ITEMS )
        return item
