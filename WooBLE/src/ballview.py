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

ROUND_DIGITS = 2 #Rounds Sizes, Positions, Radii and Angles to 2 Decimal Places
Z_TOOL_ITEMS = 1000000 # makes sure always on top
Z_LEVEL_ITEMS = 10000.0
Z_PHYSIC_ITEMS = 9000.0

TOOL_SELECT = 'select'
TOOL_PAN = 'pan'
TOOL_MOVE = 'move'


BALL_STATE_DRAW_ORDER=[
    ['standing','walking','climbing','falling','dragging'],
    ['attached','detaching','sleeping','pipe','tank'],
    ['stuck','stuck_attached','stuck_detaching']]

# x coordinate of the unit vector of length = 1
UNIT_VECTOR_COORDINATE = math.sqrt(0.5)

KEY_ELEMENT = 0
KEY_TOOL = 1
#@DaB
#Added to allow storage of pre-computed item area to item.data
KEY_AREA = 2
KEY_TYPE = 3
KEY_EXTRA = 4
KEY_ATTRIB = 5
KEY_TOOLFACTORY = 6
KEY_STATE = 7

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

class PanTool(BasicTool):
    def _on_start_using_tool(self):
        self._view.viewport().setCursor( Qt.OpenHandCursor )

    def _handle_press_event(self, event):
        BasicTool._handle_press_event(self, event)
        self._view.viewport().setCursor( Qt.ClosedHandCursor )
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

        self._view.viewport().setCursor( Qt.OpenHandCursor )
        return True

#@DaB
#Modified to only Pan at delta >5px
    def _handle_move_event(self, event):
        BasicTool._handle_move_event(self, event)
        if self._last_event and self.activated:
            delta = event.pos() - self._downat
            if vector2d_length(delta.x(),delta.y())>5:
                view = self._view
                h_bar = self._view.horizontalScrollBar()
                v_bar = self._view.verticalScrollBar()
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
        item_at_pos = self._view.itemAt( event.pos() )
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
        menu.addAction(  self._view.common_actions['paste'] )
        menu.addSeparator()
        menu.addAction( self._view.common_actions['delete'] )

        is_selected = (selected_element is not None)
        self._view.common_actions['cut'].setEnabled(is_selected)
        self._view.common_actions['copy'].setEnabled(is_selected)
        self._view.common_actions['delete'].setEnabled(is_selected)

        # sort out paste to
        menu.exec_( self._view.mapToGlobal(event.pos() ))

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
            oldsel = self._view.scene().selectedItems()
            sel_item = self._new_select_tool(event)
            if sel_item: #@DaB - Try a Selec
                if sel_item in oldsel:
                    activated_tool = self._view.get_current_inner_tool()
                else:
                    self._view.scene().clearSelection()
                    sel_item.setSelected(True)
                    self._view._update_tools_handle()

        if activated_tool is not None:
            self._active_tool = activated_tool 
            scene_pos = self._view.mapToScene( event.pos() )
            self._active_tool.activated( scene_pos.x(), scene_pos.y(),event.modifiers() )
                
    def _new_select_tool(self, event):
        clicked_items = self._view.items( event.pos() )
        if len(clicked_items) > 0:
            selected_index = -1
            for index, item in enumerate(clicked_items):
              if item.data(KEY_AREA).isValid():
                area = item.data(KEY_AREA).toFloat()[0]
                if area>0:
                  if selected_index==-1:
                    minarea = area
                    selected_index=index
                  else:
                    itemarea = area
                    if itemarea<minarea:
                        minarea=itemarea
                        selected_index=index
            if selected_index >= 0:
                self._view.select_item_element( clicked_items[selected_index] )
                return clicked_items[selected_index]
        self._view.clear_selection()
        return None
        
    def _handle_release_event(self, event):
        if event.button()==Qt.RightButton:
            self._new_select_tool(event) #@DaB - Try a Selec
            self._showContextMenu(event)
            return

        if self._active_tool is not None:
            scene_pos = self._view.mapToScene( event.pos() )
            self._active_tool.commit( scene_pos.x(), scene_pos.y(),event.modifiers() )
            self._active_tool = None
            self._view.viewport().setCursor( Qt.ArrowCursor )
        else:
            self._handle_move_event(event)

    def _handle_move_event(self, event):
        BasicTool._handle_move_event(self, event)
        # If a tool delegate has been activated, then forward all events
        if self._active_tool is not None:
            scene_pos = self._view.mapToScene( event.pos() )
            self._active_tool.on_mouse_move( scene_pos.x(), scene_pos.y() , event.modifiers())
        else:
            # Otherwise try to find if one would be activated and change mouse cursor
            tool = self._get_tool_for_event_location( event )
            if tool is None: # If None, then go back to selection
                self._view.viewport().setCursor( Qt.ArrowCursor )
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
        self.set_activated_mouse_cursor()
        item_pos = self.item.mapFromScene( scene_x, scene_y )
        self.activation_pos = item_pos
        self.last_pos = self.activation_pos
        self.activation_value = self._get_activation_value()
        self.activation_item_state = self.state_handler.get_item_state(self.item)
        self.on_mouse_move( scene_x, scene_y, modifiers, is_activation = True )

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
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
                self.view.delayed_element_property_update( self.element, 
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

class PartMoveToolDelegate(ToolDelegate):
    """This tool allow the user to move the element in its parent (scene or compositegeom).
    """
    def __init__(self, view, element, item,  attributes_in, state_handler, position_is_center, pos_delegate=None):
        ToolDelegate.__init__( self, view, element, item,attributes_in[0], state_handler,
                               position_is_center, 
                               activable_cursor = Qt.SizeAllCursor )
        self.attributes = attributes_in
        self.rect_position = None
        self.pos_delegate = pos_delegate

    def set_rect_position(self,rect_position):
        assert self.rect_position is None
        self.rect_position = rect_position

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        return  [ attribute.get_native(self.element) for attribute in self.attributes ]

    def _list_attributes_to_update(self, attribute_value):
        """Returns a list of tuple(attribute_meta, attribute_value).
           Called on commit to update the element attributes.
        """
        return [(self.attributes[0], attribute_value[0]),
                (self.attributes[1], attribute_value[1])]

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
        self.view._update_tools_handle()
        if self.activation_value is None: # Default value to (0,0)
            return ([delta_pos.x(),delta_pos.x()], [-delta_pos.y(),-delta_pos.y()])
        #@DaB - Round position atrributes
        activation_x, activation_y = self.activation_value

        if activation_x is None:
            output_x = round(delta_pos.x(),1)
        elif len(activation_x)==1:
            output_x = round(activation_x[0]+delta_pos.x(),1)
        else:
            output_x = (round(activation_x[0]+delta_pos.x(),1),round(activation_x[1]+delta_pos.x(),1))

        if activation_y is None:
            output_y = -round(delta_pos.y(),1)
        elif len(activation_y)==1:
            output_y = round(activation_y[0]-delta_pos.y(),1)
        else:
            output_y = (round(activation_y[0]-delta_pos.y(),1),round(activation_y[1]-delta_pos.y(),1))
        return output_x,output_y

class PartScaleToolDelegate(ToolDelegate):
    """This tool allow the user to move the corner of a pixmap.
       It will automatically center position and scale factor accordingly.
    """
    def __init__(self, view, element, item, attributes_in,state_handler, position_is_center):

        ToolDelegate.__init__( self, view, element, item,attributes_in[0], state_handler,
                               position_is_center,
                               activable_cursor = Qt.SizeBDiagCursor )
        self.attributes = attributes_in
        self.attribute_scale = attributes_in[2]
        self.rect_position = None

    def set_rect_position(self,rect_position):
        assert self.rect_position is None
        self.rect_position = rect_position

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        return  [ attribute.get_native(self.element) for attribute in self.attributes ]

    def _list_attributes_to_update(self, attribute_value):
        """Returns a list of tuple(attribute_meta, attribute_value).
           Called on commit to update the element attributes.
        """
        return [(self.attribute_scale, attribute_value)]

    def _on_mouse_move(self, item_pos,modifiers):

        # item pos is in coordinate system at scale 1 (= to image size)
        # First, map the position to parent coordinate. Restore original item
        # state and map the position back to item coordinate.
        # Then in item coordinate, compare new size to original size
        # => this give us the scale factor
        # From the new item bound, compute the center and map it to parent coordinate.
        # Then determine if the item position needs to be modified (
        # center is center position, or dragging top or left corners).
        cursor_in_scene = self.item.mapToParent( item_pos )
        self.restore_activation_state()
        # Computes new item bounds
        bound_rect = self.get_item_bound()
        if not bound_rect.isValid(): # has 0 width or height ?
            return None

        center_in_scene = self.item.mapToParent(QtCore.QPointF((bound_rect.left()+bound_rect.right())*0.5,(bound_rect.top()+bound_rect.bottom())*0.5))
        # x/y minmax impacted indexes by position
        distance_cursor_to_center= vector2d_length(center_in_scene.x()-cursor_in_scene.x(),
                                                       center_in_scene.y()-cursor_in_scene.y())
        ref_length = vector2d_length(bound_rect.width(),bound_rect.height())*0.5        
        scale = distance_cursor_to_center/ref_length

        newposx = center_in_scene.x()-(bound_rect.width()*0.5*scale)
        newposy = center_in_scene.y()-(bound_rect.height()*0.5*scale)
        self.item.setPos(QtCore.QPointF(newposx,newposy))
        activation_x,activation_y, activation_scale = self.activation_value
        rescale = scale / activation_scale
        self.item.scale( rescale,rescale )
        self.view._update_tools_handle()
        return round(scale,3)

class PartResizeToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, attributes_in,state_handler, position_is_center):

        ToolDelegate.__init__( self, view, element, item,attributes_in[0], state_handler,
                               position_is_center,
                               activable_cursor = Qt.SizeBDiagCursor )
        self.attributes = attributes_in
        self.rect_position = None

    def set_rect_position(self,rect_position):
        assert self.rect_position is None
        self.rect_position = rect_position

    def _get_activation_value(self): #@todo do we really need this ? We never modify the element until commit!
        """Returns the activation value of the element."""
        return  [ attribute.get_native(self.element) for attribute in self.attributes ]

    def _list_attributes_to_update(self, attribute_value):
        """Returns a list of tuple(attribute_meta, attribute_value).
           Called on commit to update the element attributes.
        """
        return [(self.attributes[0], attribute_value[0]),
                (self.attributes[1], attribute_value[1])]

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
        xminmaxinit = []
        xminmaxinit.extend(xminmax)

        yminmax = [bound_rect.y(), bound_rect.bottom()]
        yminmaxinit = []
        yminmaxinit.extend(yminmax)

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

        if new_width < 0.0:
            return

        if new_height < 0.0:
            return
 
        scale_x = new_width / bound_rect.width()
        scale_y = new_height / bound_rect.height()

        newcenter = self.item.mapToParent(QtCore.QPointF((xminmax[0]+xminmax[1])*0.5,(yminmax[0]+yminmax[1])*0.5))
        deltacenter = newcenter-oldcenter

        # Computes scale factor
        self.item.scale( scale_x, scale_y )

        newpos = self.item.pos()
        newposx = newpos.x() + impact[2] * deltacenter.x()
        newposy = newpos.y() + impact[3] * deltacenter.y()
        self.item.setPos(QtCore.QPointF(newposx,newposy))
        self.view._update_tools_handle()

        if self.activation_value is None:
            return [0,0]

        activation_x, activation_y = self.activation_value

        if activation_x is None:
            activation_x = (0,0)
        elif len(activation_x)==1:
            activation_x = (activation_x,activation_x)
        if activation_y is None:
            activation_y = (0,0)
        elif len(activation_y)==1:
            activation_y = (activation_y,activation_y)
        
        dminx =  xminmax[0]-xminmaxinit[0]
        dmaxx =  xminmax[1]-xminmaxinit[1]
        dminy =  yminmax[0]-yminmaxinit[0]
        dmaxy =  yminmax[1]-yminmaxinit[1]

        return [(round(activation_x[0]+dminx,1),round(activation_x[1]+dmaxx,1)),
                    (round(activation_y[0]-dmaxy,1),round(activation_y[1]-dminy,1))]


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

    
    def create_tools(self, item, element, attrib, state, view ):
        """Creates graphic scene item representing the tool handle.
           Returns: tuple(move_tool, list of items)
        """
        self._make_tools( item, element, attrib, state, view, self._get_state_manager() )

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


class PartRectToolFactory(ToolsFactory):
    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        rotate_tool_pos = ( )
        resize_tool_pos = ( POS_TOP_LEFT,POS_BOTTOM_RIGHT )
        return  resize_tool_pos, rotate_tool_pos

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return RectStateManager()

    def _make_tools(self, item, element, attrib, state, view, state_manager):

        #expect 2 attrib in list
        position_is_center = not self._center_is_top_left()
        self.move_tool = PartMoveToolDelegate( view, element, item, attrib, state_manager,
                             position_is_center )

        self.resize_tools = [ PartResizeToolDelegate( view, element, item, attrib, state_manager,
                             position_is_center) for i in range(0,2)]

class PartPixmapToolFactory(ToolsFactory):
    """Pixmap may be either circle with image, rectangle with image, SceneLayer or
       part of a compositgeom.
    """

    def _get_tools_positions(self):
        """Returns the of positions for the resize tools and the rotate tools."""
        rotate_tool_pos = ( )
        resize_tool_pos = ( POS_TOP_LEFT,POS_BOTTOM_RIGHT )
        return  resize_tool_pos, rotate_tool_pos

    def _get_state_manager(self):
        """Returns the state manager used to save and restore the state of the item."""
        return PixmapStateManager()

    def _make_tools(self, item, element, attrib, state, view, state_manager):

        #expect 2 attrib in list
        position_is_center = not self._center_is_top_left()
        self.move_tool = PartMoveToolDelegate( view, element, item, (attrib[0],attrib[1]), state_manager,
                             position_is_center )

        self.resize_tools = [ PartScaleToolDelegate( view, element, item, attrib, state_manager,
                             position_is_center) for i in range(0,2)]


    def _center_is_top_left(self):
        return True


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

class RectStateManager(StateManager):
    def _get_item_state(self, item):
        return item.rect()
    
    def _restore_item_state(self, item, state):
        item.setRect( state )

class BallGraphicView(QtGui.QGraphicsView):
    """A graphics view that display scene and level elements.
       Signals:
       QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)')
         => when the mouse mouse in the map. parameters: x,y in scene coordinate.
    """
    def __init__( self, world, tools_actions, common_actions ):
        QtGui.QGraphicsView.__init__( self )
        self.__world = world
        self.common_actions = common_actions
        self.setWindowTitle( self.tr( self.__world.key))
        self.setAttribute( Qt.WA_DeleteOnClose )
        self.__scene = QtGui.QGraphicsScene()
        self.__tools_by_actions = {}
        self.__tools_group = None
        self._delayed_property_updates = []
        self._delayed_timer_id = None
        self._band_item = None
        self._BGColour = QtGui.QColor(192,192,192)

        for name, action in tools_actions.iteritems():
            self.__tools_by_actions[action] = name
            self.__tools_group = self.__tools_group or action.actionGroup()
        self._tools_by_name = {
#            TOOL_SELECT: SelectTool(self),
            TOOL_PAN: PanTool(self),
            TOOL_MOVE: MoveOrResizeTool(self)
            }
        self._elements_to_hide = set()
        self._elements_to_skip = []
        self._active_tool = None
        self._tools_handle_items = []
        self._current_inner_tool = None
        self._items_by_element = {}
        self._selection_tool_degates_cache = (None,[])
        self.setScene( self.__scene )
        # Notes: we disable interactive mode. It is very easily to make the application
        # crash when interactive mode is allowed an mouse events are "sometimes" 
        # accepted by the overridden view. Instead, we handle selection and panning
        # ourselves.
        self.setInteractive( False )

        #self.refreshFromModel()

        self.scale( 1.0, 1.0 )
#@DaB
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setMouseTracking(True)
        self.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform )
        self._last_press_at = QtCore.QPointF(0,0)
        self._last_release_at = QtCore.QPointF(0,0)
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

#    @property
#    def scene(self):
#        return self.__scene

    def toggle(self,elementtype):
        self._elements_to_hide=self._elements_to_hide.symmetric_difference(set(elementtype))

    def setBGColour(self,colour):
        self._BGColour = colour
        self.refreshFromModel()

    def is_selected_item(self, item):
        data = item.data( KEY_ELEMENT )
        if data.isValid():
            return data.toPyObject() in self.__world.selected_elements
        return False

    def get_enabled_view_tools(self):
        return set( [TOOL_PAN, TOOL_MOVE] )

    def get_current_inner_tool(self):
        """Returns the tool delegate to use when the user click inside a shape.
           This is usually the MoveToolDelegate.
        """
        return self._current_inner_tool

    def _update_tools_handle(self):
        """Updates tools' handle on current select item. 
           Must be called whenever the scale factory change or selection change.
        """
        # Removes any existing handle
        # Notes: we need to be very careful there, removing item that have been removed
        # by other means such as clear() cause the application to crash.
        items = self.__scene.items()
        for tool_item in self._tools_handle_items:
          if tool_item in items:
            self.__scene.removeItem( tool_item )
        self._tools_handle_items = []
        self._current_inner_tool = None 

        selected_items = self.__scene.selectedItems()
        if selected_items is None:
            return
        if len(selected_items) != 1: # @todo handle multiple selection
            return

#        print "active_tool", self._get_active_tool(), "TOOL_MOVE",self._tools_by_name[TOOL_MOVE]
        if self._get_active_tool() != self._tools_by_name[TOOL_MOVE]:
            return # No handle for select or pan tool
        item = selected_items[0]
#        print "item is ",item
        if item is None:
            return

        # unwrap
        all_valid = True
        for data_key in [KEY_TYPE,KEY_STATE,KEY_ELEMENT,KEY_ATTRIB,KEY_TOOLFACTORY]:
            if not item.data(data_key).isValid():
                #print "data key invalid ",data_key," in ", item
                all_valid  = False
        if not all_valid:
            return
        type = item.data(KEY_TYPE).toString()
        element = item.data(KEY_ELEMENT).toPyObject()
        attrib = item.data(KEY_ATTRIB).toPyObject()
        toolfactory = item.data(KEY_TOOLFACTORY).toPyObject()
        state = item.data(KEY_STATE).toString()
#        print "Item data ",type,state,element,attrib,toolfactory
        
        if toolfactory is not None:
            self._current_inner_tool, self._tools_handle_items = toolfactory().create_tools(item, element, attrib, state, self)

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
        else:
            QtGui.QGraphicsView.timerEvent(self, event)
        
    def tool_activated( self, tool_name ):
        """Activates the corresponding tool in the view and commit any pending change.
        """
        if self._active_tool:
            self._active_tool.stop_using_tool()
        self._get_active_tool().start_using_tool()
        self._update_tools_handle()

    def selectLevelOnSubWindowActivation( self ):
        """Called when the user switched MDI window."""
        self.__world.game_model.selectBall( self.__world.key )

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

    def _get_active_tool(self):
        name = self.__tools_by_actions.get( self.__tools_group.checkedAction() )
        tool = self._tools_by_name.get(name)
        if tool is None:
            tool =  self._tools_by_name[TOOL_SELECT]
        self._active_tool = tool
        return tool

    def mousePressEvent(self, event):
        self._last_press_at = self.mapToScene(event.pos())
        self._get_active_tool().on_mouse_press_event( event )
        event.accept()
	#@DaB - Ensure if Click then Press to move is quick enough to be consider a Double-click
	# that it still works.
    def mouseDoubleClickEvent(self, event):
        self._last_press_at = self.mapToScene(event.pos())
        self._get_active_tool().on_mouse_press_event( event )
        event.accept()

    def mouseReleaseEvent(self, event):
        self._last_release_at = self.mapToScene(event.pos())
        self._get_active_tool().on_mouse_release_event( event )
        event.accept()

    def mouseMoveEvent( self, event):
        self._last_pos = self.mapToScene( event.pos() )
        self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), self._last_pos.x(), self._last_pos.y() )
        self._get_active_tool().on_mouse_move_event( event )
        

    def closeEvent(self,event):
        # could check for unsaved change and ask here
        if self.__world.is_dirty:
          if not self.__world.isReadOnly:
            # ask unsaved changes
            ret =  QtGui.QMessageBox.warning(self, "Save Changes to " + self.__world.name,
                            'There are unsaved changes to ' + self.__world.name,
                            QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel )
            if ret==QtGui.QMessageBox.Cancel:
                event.ignore()
                return
            if ret==QtGui.QMessageBox.Save:
                self.__world.saveModifiedElements()

        game_model= self.__world.game_model
        name= self.__world.name
        self.__world.parent_world.remove_world(self.__world)
        del self.__world.game_model.models_by_name[self.__world.key]
        self.__world.setView(None)
        game_model.getModel(name,False)

        if self._delayed_timer_id is not None:
            self.killTimer( self._delayed_timer_id )#
        if len(self.parent().mdiArea().subWindowList())==1:
            louie.send( metaworldui.ActiveWorldChanged, None, None )

        
        
        QtGui.QGraphicsView.closeEvent(self,event)
        event.accept()

    def wheelEvent(self, event):
        """Handle zoom when wheel is rotated."""
#@DaB
#Added to update displayed position on Zoom
        pos = self.mapToScene( event.pos() )
        self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), pos.x(), pos.y() )

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

        factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()
        if factor < 0.3 or factor > 100:
            return            
        self.scale(scaleFactor, scaleFactor)
        
        dx = (orX - self.width()*0.5)
        if scaleFactor > 1:
            llimit = self.width()*0.30
            if dx > llimit :
                dx = dx*4 - llimit*3
            elif dx<-llimit:
                dx = dx*4 + llimit*3

        dy = (self.height()*0.5 - orY)
        if scaleFactor > 1:
            llimit = self.height()*0.30
            if dy > llimit :
                dy = dy*4 - llimit*3
            elif dy<-llimit:
                dy = dy*4 + llimit*3

        h_bar = self.horizontalScrollBar()
        v_bar = self.verticalScrollBar()
        x_value = h_bar.value()
        if self.isRightToLeft():
            x_value -= dx * (scaleFactor-1)
        else:
            x_value += dx * (scaleFactor-1)
        h_bar.setValue( x_value )
        v_bar.setValue( v_bar.value() - dy * (scaleFactor-1) )
        self._update_tools_handle()


    def scaleView(self, scaleFactor):
        """Scales the view by a given factor."""
        factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()

        if factor < 0.07 or factor > 100:
            return

        self.scale(scaleFactor, scaleFactor)
        self._update_tools_handle()

    def _on_selection_change(self, selection, #IGNORE:W0613
                             selected_elements, deselected_elements,
                             **kwargs): 
        """Ensures that the selected element is seleted in the graphic view.
           Called whenever an element is selected in the tree view or the graphic view.
        """

        #Thought... completely ignore this....
        #If they select an element in the tree there is very little point
        #in trying to highlight it in the GUI... on a Ball at least.

        # that would simplfy things when it comes to selections.
        # since we can go with just a single item "ever"

        #Just need to ensure that a particular item can reselected after a refresh...
        # if it still exists
        # Item will be identifiable by element and attributes
        # list comparison, or we add an additional data tag contain attribute names
        # appended or joined in some way.. for exact comparision

        return

        # Notes: we do not change selection if the item belong to an item group.
        # All selection events send to an item belonging to a group are forwarded
        # to the item group, which caused infinite recursion (unselect child,
        # then unselect parent, selection parent...)
        for item in self.__scene.items():
          data = item.data( KEY_ELEMENT )
          if not data.isValid():
             itemtype = item.data( KEY_TYPE ).toString()
             #if itemtype!='TOOL':
             #   print "Data not valid in _on_selection_change",itemtype,item
          else:
            element = item.data(KEY_ELEMENT).toPyObject()
            if item.data(KEY_ATTRIB).isValid():
                attribs = item.data(KEY_ATTRIB).toPyObject()
                print "attribs=",attribs
                
            if element in selection:
                print 'Selecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                if not item.isSelected() and item.group() is None:
                    item.setSelected( True )
            elif item.isSelected() and item.group() is None:
                print 'Unselecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
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
        self.__scene.setBackgroundBrush(QtGui.QBrush (self._BGColour, Qt.SolidPattern))
        self.__scene.clear()
        if elements_to_skip:
            self._elements_to_skip = elements_to_skip
        ball = self.__world.ball_root
        # process state scales
        maxstatescale=0
        statescales={}
        statescaleraw = ball.get('statescales','')
        if statescaleraw!='':
            statescale2 = statescaleraw.split(',')
            expectstate=True
            for thing in statescale2:
                if expectstate:
                    newstate=thing.strip()
                else:
                    try:
                        thisscale = float(thing)
                    except ValueError:
                        print "Invalid Statescale",newstate,thing
                        thisscale = 1
                    if len(statescales)==0:
                        maxstatescale = thisscale
                    elif thisscale>maxstatescale:
                        maxstatescale = thisscale
                    statescales[newstate]=thisscale

                expectstate= not expectstate

        shape = ball.get('shape','rectangle,100,100').split(',')
        if shape[0]=='circle':
            xdiff=float(shape[1])+100
            ydiff=float(shape[1])+100
            lpos = float(shape[1])/2 +25
        else:
            xdiff=float(shape[1])+100
            ydiff=float(shape[2])+100
            lpos = float(shape[2])/2+25

        y = 0
        for row in BALL_STATE_DRAW_ORDER:
            x = 0
            for state in row:
                if state in statescales.keys():
                    statescale=statescales[state]
                else:
                    statescale=1.0
                self._drawBall(self.__scene, ball,state,x,y,lpos,statescale)
                x+=xdiff
            y+=ydiff
        x=0

        if 'strand' not in self._elements_to_hide:
            maxt=(xdiff-100)
            strand = ball.find('strand')
            if strand is not None and strand not in self._elements_to_skip:
                self._drawStrand(self.__scene, strand,x,y,lpos,xdiff,ydiff,maxthickness=maxt)
                if ball.get_native('burntime',0.0)>0:
                    self._labelState(self.__scene,'burnt',x+2*xdiff,y-lpos)
                    self._drawAStrand(self.__scene,strand,'burntimage',x+2*xdiff,y,1.0,maxt)

            strand = ball.find('detachstrand')
            if strand is not None and strand not in self._elements_to_skip:
              if ball.get_native('detachable',True) | (ball.get_native('draggable',True) & (ball.get('fling','')!='')):
                 self._labelState(self.__scene,'detach',x+3*xdiff,y-lpos)
                 self._drawDStrand(self.__scene, strand,'image',x+3*xdiff,y,1.0)

        self._elements_to_skip = []
        #self._on_selection_change( self.__world.selected_elements, set(), set() )

    def get_element_state(self,elementtype):
        try:
            estate = self._type_states[elementtype]
        except KeyError:
            estate = ELEMENT_STATE_NONE
        return estate
    
    def set_element_state(self,elementtype,estate):
        self._type_states[elementtype]=estate

    def _labelState(self,scene,state,offset_x,offset_y):
        font = QtGui.QFont()
        font.setPointSize( 12.0 )
        item = scene.addText( state, font )
        bgc = self._BGColour.getRgb()
        brightness=0
        for i in range(0,3):
            brightness+=bgc[i]
        if brightness>200:
            item.setDefaultTextColor( QtGui.QColor( 0, 0, 0 ) )
        else:
            item.setDefaultTextColor( QtGui.QColor( 255, 255, 255 ) )
        offsety = item.boundingRect().height()/2
        offsetx = item.boundingRect().width()/2

        self._applyTransform( item,offsetx, offsety, offset_x, offset_y, 0, 1,1, Z_TOOL_ITEMS )

    def _ballStateValid(self,ball,state):
        #checks the given state against properties of the ball...
        #decides if this is a valid state the ball can exist in
        if state in ["pipe","tank"]:
            return ball.get_native('suckable',True)
        elif state in ["dragging","marker"]:
            return ball.get_native('draggable',True)
        elif state=="climbing":
            return ball.get_native('climber',True)
        elif state=="detaching":
            return ball.get_native('detachable',True) and ball.get_native('strands',0)>=1
        elif state=="attached":
            return ball.get_native('strands',0)>=1
        elif state in ["stuck_detaching","stuck_attached","stuck"]:
            return ball.get_native('sticky',False) or ball.get_native('stickyattached',False) or ball.get_native('stickyunattached',False)
        return True

    def _drawStrand(self,scene,strand,offset_x,offset_y,label_offset,xdiff,ydiff, maxthickness=25):

        self._labelState(scene,'strand',offset_x,offset_y-label_offset)
        self._drawAStrand(scene,strand,'image',offset_x,offset_y,1.0,maxthickness)

        offset_x+=xdiff
        self._labelState(scene,'inactive',offset_x,offset_y-label_offset)
        self._drawAStrand(scene,strand,'inactiveimage',offset_x,offset_y,0.5,maxthickness)


    def _drawAStrand(self,scene,element,prop,offset_x,offset_y,alpha,maxthickness):
        image = element.get(prop,'')
        if image!='':
            pixmap = self.getImagePixmap( image )
        else:
            pixmap = None
        if pixmap is not None:
            item = scene.addPixmap( pixmap )
            item.setTransformationMode(Qt.SmoothTransformation)
            thickness=element.get_native('thickness',maxthickness)
            if thickness>maxthickness:
                thickness=maxthickness
            maxlen = element.get_native('maxlen2',140)
            minlen = element.get_native('minlen',100)
            scalex = float(thickness)/float(pixmap.width())
            scaley = float(maxlen+minlen)/float(2*pixmap.height())
            self._applyPixmapTransform( item, pixmap, offset_x, offset_y, 45, scalex, scaley, 0 )
            item.setOpacity(alpha)
            item.setData(KEY_AREA , QtCore.QVariant(pixmap.height()*pixmap.width()*scalex*scaley ))
            item.setData(KEY_TYPE , QtCore.QVariant( element.tag ) )
            item.setData(KEY_ELEMENT , QtCore.QVariant( element ) )

    def _drawDStrand(self,scene,element,prop,offset_x,offset_y,alpha):
        image = element.get(prop,'')
        if image!='':
            pixmap = self.getImagePixmap( image )
        else:
            pixmap = None
        if pixmap is not None:
            item = scene.addPixmap( pixmap )
            item.setTransformationMode(Qt.SmoothTransformation)
            thickness=20
            maxlen = element.get_native('maxlen',60)
            minlen = 100
            scalex = float(thickness)/float(pixmap.width())
            scaley = float(maxlen+minlen)/float(2*pixmap.height())
            self._applyPixmapTransform( item, pixmap, offset_x, offset_y, 45, scalex, scaley, 0 )
            item.setOpacity(alpha)
            item.setData(KEY_AREA , QtCore.QVariant(pixmap.height()*pixmap.width()*scalex*scaley ))
            item.setData(KEY_TYPE , QtCore.QVariant( element.tag ) )
            item.setData(KEY_ELEMENT , QtCore.QVariant( element ) )

    def _drawBallOutline(self,scene,ball,x,y,scale):

        ballshape = ball.get('shape','rectangle,100,100').split(',')
        ballshape[0]=ballshape[0].strip()
        pen = QtGui.QPen(QtGui.QColor(0,0,255))
        pen.setWidth(0.5)

        if ballshape[0]=='circle':
            r = float(ballshape[1])
            item = scene.addEllipse( -r/2, -r/2, r, r ,pen)
            item.setZValue(100)
            item.setZValue( Z_LEVEL_ITEMS )
            item.setPos( x, y )
        else:
            width = float(ballshape[1])
            height = float(ballshape[2])
            item = scene.addRect( 0, 0, width, height ,pen)
            self._applyTransform( item, width*0.5, height*0.5, x, y, 0, 1.0, 1.0, 100 )
            item.setData(KEY_AREA , QtCore.QVariant( width*height +1))        
        item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, False )
        return item

    def _drawBall(self,scene,ball,state,offset_x,offset_y,label_offset, scale):
        
        self._labelState(scene,state,offset_x,offset_y-label_offset)

        #determine if ball can exist in this state...
        if not self._ballStateValid(ball,state):
            self._labelState(scene,"N/A",offset_x,offset_y)
        else:
          if 'geom' not in self._elements_to_hide:
               self._drawBallOutline(scene,ball,offset_x,offset_y,scale)

          for part in ball.findall('part'):
            drawit=False
            partstate = part.get('state','')
            if partstate=='':
                #always draw
                drawit=True
            elif state in partstate.split(','):
                drawit=True

        #    print part.get('name'),' drawit=',drawit
            if drawit and part not in self._elements_to_skip:
                self._drawPart(scene,part,state,offset_x,offset_y,scale)

            if 'marker' not in self._elements_to_hide:
                marker = ball.find('marker')
                if marker is not None and marker not in self._elements_to_skip:
                    if state=="dragging":
                        self._drawThing(scene,marker,'drag',offset_x,offset_y,scale,Z_PHYSIC_ITEMS,1.0)
                    elif state=="detaching":
                        self._drawThing(scene,marker,'detach',offset_x,offset_y,scale,Z_PHYSIC_ITEMS,1.0)

            if 'shadow' not in self._elements_to_hide:
                shadow = ball.find('shadow')
                if shadow is not None and shadow not in self._elements_to_skip:
                    if state=="standing" or state=="walking":
                        self._drawThing(scene,shadow,'image',offset_x,offset_y,scale,-1,0.10)

    def _drawThing(self,scene,element,prop,offset_x,offset_y,scale,depth,alpha,rotation=0):
        image = element.get(prop,'')
        if image!='':
            pixmap = self.getImagePixmap( image )
        else:
            pixmap = None
        if pixmap is not None:
            item = scene.addPixmap( pixmap )
            item.setTransformationMode(Qt.SmoothTransformation)
            self._applyPixmapTransform( item, pixmap, offset_x, offset_y, rotation, scale, scale, depth )
            item.setOpacity(alpha)
            item.setData(KEY_AREA , QtCore.QVariant(pixmap.height()*pixmap.width()*scale*scale ))
            item.setData(KEY_TYPE , QtCore.QVariant( element.tag ) )
            item.setData(KEY_ELEMENT , QtCore.QVariant( element ) )
            item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, True )

    def _drawPart(self,scene,part,state,offset_x,offset_y,scale):
        xraw = part.get('x').split(',')
        if len(xraw)==1:
            x = float(xraw[0])
        else:
            x = (float(xraw[0])+float(xraw[1]))*0.5

        yraw = part.get('y').split(',')
        if len(yraw)==1:
            y = -float(yraw[0])
        else:
            y = -(float(yraw[0])+float(yraw[1]))*0.5
            
        depth = part.get_native( 'layer', 0.0 )
        image = part.get('image','').split(',')[0]
        if image!='':
            pixmap = self.getImagePixmap( image )
        else:
            pixmap = None
        rotation = 0 # element.get_native( 'rotation', 0.0 )
        scaleimage = part.get_native( 'scale', 1.0 )
        alpha = 1.0 #part.get_native('alpha',1.0)
        #print part.get('name'),image,scale,depth,x,y
        if pixmap is not None:
            item = scene.addPixmap( pixmap )
            item.setTransformationMode(Qt.SmoothTransformation)
            self._applyPixmapTransform( item, pixmap, offset_x + x, offset_y + y, rotation, scaleimage*scale, scaleimage*scale, depth )
            item.setOpacity(alpha)
            item.setData(KEY_AREA , QtCore.QVariant(pixmap.height()*pixmap.width()*scaleimage*scale*scaleimage*scale ))
            item.setData(KEY_TYPE , QtCore.QVariant( part.tag ) )
            item.setData(KEY_ELEMENT , QtCore.QVariant( part ) )
            item.setData(KEY_ATTRIB , QtCore.QVariant( [part.attribute_meta('x'),part.attribute_meta('y'),part.attribute_meta('scale')] ) )
            item.setData(KEY_TOOLFACTORY , QtCore.QVariant( PartPixmapToolFactory ) )
            item.setData(KEY_STATE , QtCore.QVariant( state ) )
        else:
            pen = QtGui.QPen( QtGui.QColor( 255, 0, 0 ) )
            pen.setWidth( 4 )
            item = scene.addRect( 0, 0, 100, 100, pen )
            self._applyTransform( item, 50, 50, offset_x+x, offset_y+y, rotation, 1.0, 1.0, Z_PHYSIC_ITEMS )
            item.setData(KEY_AREA , QtCore.QVariant( 100*100 ))

        item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, True )

        if 'geom' not in self._elements_to_hide:
            if len(xraw)>1 or len(yraw)>1:
            #draw part range rectangle
               pen = QtGui.QPen(QtGui.QColor(64,255,64))
               pen.setWidth(0.5)
               width = 0
               if len(xraw)>1:
                   width = (float(xraw[1])-float(xraw[0]))
               height = 0
               if len(yraw)>1:
                   height = (float(yraw[1])-float(yraw[0]))
               item = scene.addRect( 0, 0, width, height ,pen)
               self._applyTransform( item, width*0.5, height*0.5, offset_x + x, offset_y + y, 0, 1.0, 1.0, Z_PHYSIC_ITEMS )
               item.setData(KEY_AREA , QtCore.QVariant( width*height +1))
               item.setData(KEY_ELEMENT , QtCore.QVariant( part ) )
               item.setData(KEY_TYPE , QtCore.QVariant( part.tag ) )
               item.setData(KEY_ATTRIB , QtCore.QVariant( [part.attribute_meta('x'),part.attribute_meta('y')] ) )
               item.setData(KEY_TOOLFACTORY , QtCore.QVariant( PartRectToolFactory ) )
               item.setData(KEY_STATE , QtCore.QVariant( state ) )
               item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, True )

            xraw = part.get('xrange','').split(',')
            if len(xraw)==1:
                if xraw[0]=='':
                    xrange=0
                else:
                    xrange = float(xraw[0])
            else:
                xrange = (float(xraw[0])+float(xraw[1]))*0.5

            yraw = part.get('yrange','').split(',')
            if len(yraw)==1:
                if yraw[0]=='':
                    yrange=0
                else:
                    yrange = float(yraw[0])
            else:
                yrange = -(float(yraw[0])+float(yraw[1]))*0.5

            if len(xraw)>1 or len(yraw)>1:
                #draw part range rectangle
               pen = QtGui.QPen(QtGui.QColor(255,192,64))
               pen.setWidth(0.5)
               width = 0
               if len(xraw)>1:
                   width = (float(xraw[1])-float(xraw[0]))
               height = 0
               if len(yraw)>1:
                   height = (float(yraw[1])-float(yraw[0]))
               item = scene.addRect( 0, 0, width, height ,pen)
               self._applyTransform( item, width*0.5, height*0.5, offset_x + xrange, offset_y + yrange, 0, 1.0, 1.0, Z_PHYSIC_ITEMS )
               item.setData(KEY_AREA , QtCore.QVariant( width*height +1))
               item.setData(KEY_ELEMENT , QtCore.QVariant( part ) )
               item.setData(KEY_TYPE , QtCore.QVariant( part.tag ) )
               item.setData(KEY_ATTRIB , QtCore.QVariant( [part.attribute_meta('xrange'),part.attribute_meta('yrange')] ) )
               item.setData(KEY_TOOLFACTORY , QtCore.QVariant( PartRectToolFactory ) )
               item.setData(KEY_STATE , QtCore.QVariant( state ) )
               item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, True )

        if part.get('eye')=='true':
           pupilraw = part.get('pupil','')
           if pupilraw!='':
               pupil =pupilraw.split(',')[0]
               if pupil!='':
                    pixmap = self.getImagePixmap( pupil )
               else:
                    pixmap = None
               if pixmap is not None:
                    item = scene.addPixmap( pixmap )
                    item.setTransformationMode(Qt.SmoothTransformation)
                    self._applyPixmapTransform( item, pixmap, offset_x + x, offset_y + y, rotation, scaleimage*scale, scaleimage*scale, depth+0.1 )
                    item.setOpacity(alpha)

        return item

    def getImagePixmap( self, image_id ):
        """Returns the image pixmap for the specified image id."""
        if image_id is not None:
            return self.__world.getImagePixmap( image_id )
        return None

    def _getBallPixmap(self,balltype):
       try:
          image = metawog.BALLS_IMAGES[balltype]
       except KeyError:
          image = [None,0]
       pixmap = None
       if image[0] is not None:
          pixmap = self.__world.game_model.pixmap_cache.get_pixmap( image[0] )
          return [pixmap,image[1]]
       return [None,0]

    @staticmethod
    def _applyPixmapTransform( item, pixmap, x, y, rotation, scalex, scaley, depth ):
        BallGraphicView._applyTransform( item, pixmap.width()/2.0, pixmap.height()/2.0,
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
