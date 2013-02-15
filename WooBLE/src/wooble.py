# The Ball editor GUI.

# The following workflow is expected:
# 1) User load a ball
# 2) main windows display
#    right-side-top-dock display:
#   - Ball tree
#   - Ball resources tree (a list in fact)
# 3) user select an element in one of the tree, related properties are displayed in
#    right-side-down-dock property list
# 4) user edit properties in property list
#
# Later on, provides property edition via scene layout display
# Add toolbar to create new element
#
# In memory, we keep track of two things:
# - updated ball

from __future__ import with_statement  # Makes "With" work in Python 2.5
import xml.etree.ElementTree
import sys
import os
import os.path
import glob
import subprocess
import louie
import wogfile
import metaworld
import metawog
import metaworldui
import metatreeui
import metaelementui
import ballview
import math
import random
from shutil import copy2
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import qthelper
import editleveldialog
import editballdialog
import newleveldialog_ui
import wooble_rc #IGNORE:W0611
import shutil
import zipfile
import errors
import hashlib
from datetime import datetime
LOG_TO_FILE = False
APP_NAME_UPPER = 'WOOBLE'
APP_NAME_LOWER = 'wooble'
APP_NAME_PROPER = 'WooBLE'
STR_DIR_STUB='balls'
CURRENT_VERSION = "v0.14 Final"
CREATED_BY = '<!-- Created by ' + APP_NAME_PROPER + ' ' + CURRENT_VERSION + ' -->\n'
ISSUE_LEVEL_NONE = 0
ISSUE_LEVEL_ADVICE = 1
ISSUE_LEVEL_WARNING = 2
ISSUE_LEVEL_CRITICAL =4

PLATFORM_WIN=0
PLATFORM_LINUX=1
PLATFORM_MAC=2
MAXRECENTFILES=4
random.seed()

PLATFORM_STRING = ['win','linux','mac']
if sys.platform=='win32' or sys.platform=='cygwin':
    ON_PLATFORM = PLATFORM_WIN
elif sys.platform=='darwin':
    ON_PLATFORM = PLATFORM_MAC
else:
    ON_PLATFORM = PLATFORM_LINUX
metaworld.ON_PLATFORM = ON_PLATFORM

def app_path():
    if hasattr(sys, 'frozen'):
        return os.path.dirname(sys.executable)
    #elif __file__:
    #   return os.path.dirname(__file__)
    else:
        return os.path.dirname(sys._getframe(1).f_code.co_filename)

def _getRealFilename(path):
    # Only required on Windows
    # will return the filename in the AcTuaL CaSe it is stored on the drive
    # ensure "clean" split
    path_bits = path.replace('\\','/').replace('//','/').split('/')
    real_path_bits=[]
    currentpath=path_bits.pop(0)+"\\"
    for path_bit in path_bits:
        insensitive_match=''
        sensitive_match=''
        for entry in os.listdir(currentpath):
            if entry == path_bit:
                # case senstive match - we can bail
                sensitive_match=entry
                break
            elif entry.lower()== path_bit.lower():
                # case insenstive match
                insensitive_match=entry
                break
        else:
            print "File not Found!", path
            return ''
        if sensitive_match!='':
           currentpath = os.path.join(currentpath,entry)
        elif insensitive_match!='':
            currentpath = os.path.join(currentpath,insensitive_match)
    return currentpath

def _newResName(self,filename,pattern,name,reference_world,reference_family):
        ALLOWED_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
        pathbits = os.path.split( filename )
        resource_id = pattern % (name.upper(),''.join( c for c in pathbits[1].upper() if c in ALLOWED_CHARS ))
        if not self.is_valid_reference( reference_world,reference_family, resource_id ):
            return resource_id
        serial_number = 2
        while True:
            id_value = '%s%d' % (resource_id,serial_number)
            if not self.is_valid_reference( reference_world,reference_family, id_value ):
                return id_value
            serial_number += 1

#@DaB New actions for Add item toolbar
def _appendChildTag( parent_element, new_element_meta , mandatory_attributes, keepid=False ):
                    """Adds the specified child tag to the specified element and update the tree view."""
                    assert parent_element is not None
                    # build the list of attributes with their initial values.
                    for attribute_meta in new_element_meta.attributes:
                        if attribute_meta.mandatory:
                          if attribute_meta.type == metaworld.IDENTIFIER_TYPE:
                              try:
                                given_id = mandatory_attributes[attribute_meta.name]
                              except KeyError:
                                given_id = None
                              if given_id is None or not keepid:
                                  init_value = parent_element.world.generate_unique_identifier(
                                                      attribute_meta )
                                  mandatory_attributes[attribute_meta.name] = init_value
                          else:
                            init_value = attribute_meta.init
                            if init_value is not None:
                              if attribute_meta.name not in mandatory_attributes:
                                mandatory_attributes[attribute_meta.name] = init_value

                        if (attribute_meta.default is not None and not attribute_meta.mandatory):
                            if attribute_meta.name not in mandatory_attributes:
                                init_value = attribute_meta.default
                                mandatory_attributes[attribute_meta.name] = init_value
                    # Notes: when the element is added, the ElementAdded signal will cause the
                    # corresponding item to be inserted into the tree.
                    child_element = parent_element.make_child( new_element_meta,
                                                               mandatory_attributes )
                    # Select new item in tree view
                    if not keepid:
                        child_element.world.set_selection( child_element )
                    return child_element
class BGColourFactory(object):
            def __init__( self, window, colour):
                self.window = window
                self.colour = colour
            def __call__( self ):
                subwindow = self.window.mdiArea.activeSubWindow()
                if subwindow:
                    subwindow.widget().setBGColour(self.colour)


class AddItemFactory(object):
                def __init__( self, window, parent,itemtag,attrib):
                    self.window = window
                    self.itemtag = itemtag
                    self.attrib = attrib
                    self.parent = parent

                def __call__( self ):
                    assert self.parent is not None
                    model = self.window.getCurrentModel()
                    if model:
                        window = self.window.mdiArea.activeSubWindow()
                        if window:
                            if self.parent=='ball':
                               root = model.ball_root
                            elif self.parent=='resource':
                                root = model.resource_root
                            elif self.parent=='addin':
                                root = model.addin_root
                            else:
                                print "Unknown Parent in AddItemFactory", self.parent
                            rootmbt = root.meta.find_immediate_child_by_tag(self.itemtag)
                            if rootmbt is not None:
                                _appendChildTag(root,rootmbt,self.attrib)

def tr( context, message ):
    return QtCore.QCoreApplication.translate( context, message )

def find_element_in_tree( root_element, element ):
    """Searchs the specified element in the root_element children and returns all its parent, and its index in its immediate parent.
       Returns None if the element is not found, otherwise returns a tuple ([parent_elements], child_index)
       root_element, element: must provides the interface xml.etree.ElementTree.
    """
    for index, child_element in enumerate(root_element):
        if child_element is element:
            return ([root_element], index)
        found = find_element_in_tree( child_element, element )
        if found is not None:
            found_parents, found_index = found
            found_parents.insert( 0, root_element )
            return found_parents, found_index
    return None

def flattened_element_children( element ):
    """Returns a list of all the element children, including its grand-children..."""
    children = []
    for child_element in element:
        children.append( child_element )
        children.extend( flattened_element_children( child_element ) )
    return children

class GameModelException(Exception):
    pass

class PixmapCache(object):
    """A global pixmap cache the cache the pixmap associated to each element.
       Maintains the cache up to date by listening for element events.
    """
    def __init__(self, wog_dir, universe):
        self._wog_dir = wog_dir
        self._pixmaps_by_path = {}
        self._filedate_by_path = {}
        self.__event_synthetizer = metaworld.ElementEventsSynthetizer(universe,
            None,
            self._on_element_updated, 
            self._on_element_about_to_be_removed )
        
    def get_pixmap(self, image_element):
        """Returns a pixmap corresponding to the image_element.
           The pixmap is loaded if not present in the cache.
           None is returned on failure to load the pixmap.
        """
        assert image_element.tag == 'Image'
        image_path = image_element.get('path','')
        pixmap = self._pixmaps_by_path.get( image_path )
        if pixmap:
            return pixmap
        path = os.path.join( self._wog_dir, image_path + '.png' )
        if not os.path.isfile(path):
            print 'Warning: invalid image path for "%(id)s": "%(path)s"' % \
                image_element.attributes
        else:
            return self._addToCache(path,image_element.attributes)
        return None

    def _addToCache(self,path, image_attrib):
            pixmap = QtGui.QPixmap()
            image_path = image_attrib['path']
            if pixmap.load( path ):
                #print "plain loaded:",path
                self._pixmaps_by_path[image_path] = pixmap
                self._filedate_by_path[image_path] = os.path.getmtime(path)
                return pixmap
            else:
                data = file( path, 'rb' ).read()
                if pixmap.loadFromData( data ):
                    #print "loadFromData:",path
                    self._pixmaps_by_path[image_path] = pixmap
                    self._filedate_by_path[image_path] = os.path.getmtime(path)
                    return pixmap
                else:
                   if image_path in self._pixmaps_by_path.keys():
                       del self._pixmaps_by_path[image_path]
                       del self._filedate_by_path[image_path]
                   print 'Warning: failed to load image "%(id)s": "%(path)s"' % \
                        image_attrib
            return None

    def refresh(self):
        # check each file in the cache...
        # if it's out of date then reload
        for image_path,filedate in self._filedate_by_path.items():
            path = os.path.normpath(os.path.join( self._wog_dir, image_path + '.png' ))
            if not os.path.isfile(path):
                if image_path in self._pixmaps_by_path.keys():
                    del self._pixmaps_by_path[image_path]
                    del self._filedate_by_path[image_path]
                print 'Warning: File is missing %s' % path
            elif os.path.getmtime(path)>filedate:
                # refresh
                self._addToCache(path,{'id':path,'path':image_path})


    def _on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0
        if element.tag == 'Image':
          if element.get('path','') in self._pixmaps_by_element:
            del self._pixmaps_by_element[element.get('path','')]

    def _on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        if element.tag == 'Image':
          if old_value in self._pixmaps_by_element:
            del self._pixmaps_by_element[old_value]
    

class GameModel(QtCore.QObject):
    def __init__( self, wog_path,window):
        """Loads FX, material, text and global resources.
           Loads Balls
           Loads Levels

           The following signals are provided:
           QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)')
        """
        QtCore.QObject.__init__( self )
        self._window = window
        self._wog_path = wog_path

        if ON_PLATFORM==PLATFORM_MAC:
            # on Mac
            # wogdir is Contents\Resources\game\
            self._wog_dir = os.path.join(self._wog_path,u'Contents',u'Resources',u'game')
        else:
            self._wog_dir = os.path.split( wog_path )[0]
        
        metaworld.WOG_PATH = self._wog_dir
        self._properties_dir = os.path.join( self._wog_dir, u'properties' )
        self._res_dir = os.path.join( self._wog_dir, u'res' )

        #self._generateFilesXML()
    
        # On MAC
        # enumerate all files in res folder
        # convert all .png.binltl to .png
        if ON_PLATFORM==PLATFORM_MAC:
            window.statusBar().showMessage(self.tr("Checking graphics files..."))
            skipped,processed,found=0,0,0
            lresdir = len(self._res_dir)
            toconvert=[]
            for (path, dirs, files) in os.walk(self._res_dir):
             for name in files:
              if name.endswith('.png.binltl'):
                found+=1
                output_path=os.path.join(path, name[:-11]) + '.png'
                if not os.path.isfile( output_path ):
                    toconvert.append([os.path.join(path, name),output_path,os.path.join(path, name)[lresdir:]])
                    processed+=1
                else:
                    skipped+=1
            #print "png.binltl found",found,'processed',processed,'skipped',skipped
            if processed>0:
                progress=QtGui.QProgressDialog("", QtCore.QString(), 0, processed, window);
                progress.setWindowTitle(window.tr("Converting PNG.BINLTL files to PNG..."));
                progress.setWindowModality(Qt.WindowModal);
                progress.setMinimumWidth(300)
                progress.forceShow()
                for filepair in toconvert:
                    if progress.wasCanceled():
                        break
                    progress.setValue(progress.value()+1);
                    progress.setLabelText(filepair[2])
                    width,height=wogfile.pngbinltl2png(filepair[0],filepair[1])
                progress.setValue(progress.value()+1);
                
        window.statusBar().showMessage(self.tr("Game Model : Initializing"))
        self._universe = metaworld.Universe()
        self.global_world = self._universe.make_world( metawog.WORLD_GLOBAL, 'game' )
        window.statusBar().showMessage(self.tr("Game Model : Loading Properties XMLs"))

        self._loadTree( self.global_world, metawog.TREE_GLOBAL_FX,
                                             self._properties_dir, 'fx.xml.bin' )

        self._loadTree( self.global_world, metawog.TREE_GLOBAL_MATERIALS,
                                               self._properties_dir, 'materials.xml.bin' )


        self._loadUnPackedTree( self.global_world, metawog.TREE_GLOBAL_FILES,
                                               app_path(), 'files.%s.xml' % PLATFORM_STRING[ON_PLATFORM] ,'')
        self._processOriginalFiles()
    
	self._loadTree( self.global_world, metawog.TREE_GLOBAL_RESOURCE,
                                               self._properties_dir, 'resources.xml.bin' )
        
        self._readonly_resources = set()    # resources in resources.xml that have expanded defaults idprefix & path
        self._texts_tree = self._loadTree( self.global_world, metawog.TREE_GLOBAL_TEXT,
                                           self._properties_dir, 'text.xml.bin' )

        self._levels = self._loadDirList( os.path.join( self._res_dir, 'levels' ),
                                          filename_filter = '%s.scene.bin' )
        self.models_by_name = {}
        self.__is_dirty = False
        self._initializeGlobalReferences()

        try:
            window.statusBar().showMessage(self.tr("Game Model : Loading Goo Ball Info"))
            self._loadBalls()
        except GameModelException,e:
            QtGui.QMessageBox.warning(window,"Errors found Loading Balls", unicode(e))

        self.modified_worlds_to_check = set()
        louie.connect( self._onElementAdded, metaworld.ElementAdded )
        louie.connect( self._onElementAboutToBeRemoved, metaworld.ElementAboutToBeRemoved )
        louie.connect( self._onElementUpdated, metaworld.AttributeUpdated )
        self.pixmap_cache = PixmapCache( self._wog_dir, self._universe )
        window.statusBar().showMessage(self.tr("Game Model : Complete"))

    @property
    def _effects_tree( self ):
        return self.global_world.find_tree( metawog.TREE_GLOBAL_FX )

    @property
    def _materials_tree( self ):
        return self.global_world.find_tree( metawog.TREE_GLOBAL_MATERIALS )

    @property
    def _resources_tree( self ):
        return self.global_world.find_tree( metawog.TREE_GLOBAL_RESOURCE )

    @property
    def _files_tree( self ):
        return self.global_world.find_tree( metawog.TREE_GLOBAL_FILES )

    @property
    def is_dirty(self):
        worlds = self.modified_worlds_to_check
        self.modified_worlds_to_check = set()
        for world in worlds:
            if world:
                self.__is_dirty = self.__is_dirty or world.is_dirty
        return self.__is_dirty

    def getResourcePath( self, game_dir_relative_path ):
        return os.path.join( self._wog_dir, game_dir_relative_path )

    def _loadTree( self, world, meta_tree, directory, file_name ):
        path = os.path.join( directory, file_name )
        if not os.path.isfile( path ):
            raise GameModelException( tr( 'LoadData',
                'File "%1" does not exist. You likely provided an incorrect World of Goo directory.' ).arg( path ) )
        xml_data = wogfile.decrypt_file_data( path )
        try:
            new_tree =  world.make_tree_from_xml( meta_tree, xml_data )
        except IOError,e:
            raise GameModelException(unicode(e)+u' in file '+file_name )
        new_tree.setFilename(path)
        return new_tree

    def _loadUnPackedTree( self, world, meta_tree, directory, file_name, template ):
        input_path = os.path.join( directory, file_name )
        if not os.path.isfile( input_path ):
            xml_data = template
        else:
            xml_data = file( input_path, 'rb' ).read()
        try:
            new_tree =  world.make_tree_from_xml( meta_tree, xml_data )
        except IOError,e:
            raise GameModelException(unicode(e)+u' in file '+file_name )
        new_tree.setFilename(input_path)
        return new_tree

    def _loadUnPackedXML( self, directory, file_name, template ):
        input_path = os.path.join( directory, file_name )
        if not os.path.isfile( input_path ):
            return template
        else:
            return file( input_path, 'rb' ).read()

    def _savePackedXML( self, directory, file_name, xml_data ):
        if not os.path.isdir( directory ):
            os.makedirs( directory )
        path = os.path.join( directory, file_name )
        xml_data = xml_data.replace('><','>\n<')
        wogfile.encrypt_file_data( path, xml_data )

    def _saveUnPackedData(self,directory,file_name,tree):
        if not os.path.isdir( directory ):
            os.makedirs( directory )
        output_path = os.path.join( directory, file_name )
        xml_data = tree.to_xml()
        xml_data = CREATED_BY + xml_data.replace('><','>\n<')
        file( output_path, 'wb' ).write( xml_data )
        tree.setFilename(output_path)

    def _savePackedData( self, directory, file_name, tree ):
        if not os.path.isdir( directory ):
            os.makedirs( directory )
        path = os.path.join( directory, file_name )
        xml_data = tree.to_xml()
        xml_data = xml_data.replace('><','>\n<')
        wogfile.encrypt_file_data( path, xml_data )
        tree.setFilename(path)

    def _loadDirList( self, directory, filename_filter ):
        if not os.path.isdir( directory ):
            raise GameModelException( tr('LoadLevelList',
                'Directory "%1" does not exist. You likely provided an incorrect World of Goo directory.' ).arg( directory ) )
        def is_valid_dir( entry ):
            """Accepts the directory only if it contains a specified file."""
            dir_path = os.path.join( directory, entry )
            if os.path.isdir( dir_path ):
                try:
                    filter_file_path = filename_filter % entry
                except TypeError:
                    filter_file_path = filename_filter
                if os.path.isfile( os.path.join( dir_path, filter_file_path ) ):
                    return True
            return False
        dirs = [ entry for entry in os.listdir( directory ) if is_valid_dir( entry ) ]
        dirs.sort(key=unicode.lower)
        return dirs

    def _loadBalls( self ):
        """Loads all ball models and initialize related identifiers/references."""
        ball_names = self._loadDirList( os.path.join( self._res_dir, 'balls' ),
                                        filename_filter = 'balls.xml.bin' )
        dir = os.path.join( self._res_dir, STR_DIR_STUB )
        self.ball_name_map = {}
        metaworld.BALL_NAMES = []
        firstpart=True
        for name in ball_names:
            #WoG Editor was having trouble when the Ball Folder name
            #wasn't a 100% case-sensitive match to <ball name="..."> in the balls.xml
            #but WOG was fine with it, even on Linux.

            #read in the ball_tree (balls.xml) first...
            #get name attribute out of it, and use that to create the Ball World
            try:
                xml_data = wogfile.decrypt_file_data( os.path.join(dir, name, 'balls.xml.bin') )
                ball_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_MAIN, xml_data )
            except IOError,e:
                raise GameModelException(unicode(e)+u' in '+name+u'/balls.xml.bin')
            
            real_name = ball_tree.root.get('name')
            if real_name not in metaworld.BALL_NAMES:
                self.ball_name_map[real_name]=name
                metaworld.BALL_NAMES.append(real_name)
                try:
                    xml_data = wogfile.decrypt_file_data( os.path.join(dir, name, 'resources.xml.bin') )
                    resource_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_RESOURCE, xml_data )
                except IOError,e:
                    raise GameModelException(unicode(e)+u' in '+real_name+u'/resources.xml.bin')
                resource = resource_tree.root.find("Resources")
                if resource:
                    # check id
                    res_id=resource.get('id','')
                    if res_id<>"ball_"+real_name:
                        ret= QtGui.QMessageBox.warning(self._window,"Error found loading Balls",
                                            'An error was found loading <b>'+real_name+'</b><br> <br>The Resources id <b>'+res_id+'</b> does not match ball name <b>'+real_name+'</b><br> <br>'+
                                            'Would you like WooBLE to correct this now?',
                                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                        if ret==QtGui.QMessageBox.Yes:
                            resource.set('id','ball_'+real_name)
                            self._savePackedData( os.path.join(dir, name), 'resources.xml.bin',
                                                 resource_tree )
                            
                    self.getModel(real_name,False)

            else:
                 QtGui.QMessageBox.warning(self._window,"Errors found Loading Balls",
                                            'Duplicate ball name <b>'+real_name+'</b> found in folder <b>' + self.ball_name_map[real_name] + '</b>  and  <b>' + name + '</b><br>'+
                                            'Only the first one can be loaded!')
        metaworld.BALL_NAMES.sort(cmp=lambda x,y: cmp(x.lower(), y.lower()))

    def _processSetDefaults(self,resource_tree):
        #Unwraps the SetDefaults "processing instruction"
        #updates all paths and ids to full
        resource_element = resource_tree.root.find('Resources')
        idprefix = ''
        pathprefix=''
        for element in resource_element:
            if element.tag =='SetDefaults':
                idprefix = element.get('idprefix','')
                pathprefix = element.get('path','./').strip().replace("\\","/")
                if not pathprefix.endswith('/'):
                      pathprefix += '/'
                pathprefix = pathprefix.replace("./","")

                element.set('idprefix',"")
                element.set('path',"./")
            else:
                element.set('path',pathprefix+element.get('path','').replace('\\','/'))
                element.set('id',idprefix+element.get('id',''))

    def _initializeGlobalReferences( self ):
        """Initialize global effects, materials, resources and texts references."""
        self._expandResourceDefaultsIdPrefixAndPath()

    def _expandResourceDefaultsIdPrefixAndPath( self ):
        """Expands the default idprefix and path that are used as short-cut in the XML file."""
        # Notes: there is an invalid global resource:
        # IMAGE_GLOBAL_ISLAND_6_ICON res/images/islandicon_6
        resource_manifest = self._resources_tree.root
        default_idprefix = ''
        default_path = ''
        for resources in resource_manifest:
            for element in resources:
                if element.tag == 'SetDefaults':
                    default_path = element.get('path','').strip()
                    if not default_path.endswith('/'):
                       default_path += '/'
                    default_path = default_path.replace("./","")
                    default_idprefix = element.get('idprefix','')
                elif element.tag in ('Image', 'Sound', 'font'):
                    new_id = default_idprefix + element.get('id','')
                    new_path = default_path + element.get('path','')
##                    if element.tag == 'Sound':
##                        full_path = os.path.join( self._wog_dir, new_path + '.ogg' )
##                    else:
##                        full_path = os.path.join( self._wog_dir, new_path + '.png' )
##                    if not os.path.isfile( full_path ):
##                        print 'Invalid resource:', element.get('id'), element.get('path'), new_id, full_path
                    element.set( 'id', new_id )
                    element.set( 'path', new_path )
                self._readonly_resources.add( element )


    @property
    def level_names( self ):
        return self._levels

    def getModel( self, name, builddepends=True ):
        if name not in self.models_by_name:
            try:
                ballfolder = self.ball_name_map[name]
            except KeyError,e:
                raise GameModelException(name + u' not found!')

            dir = os.path.join( self._res_dir, STR_DIR_STUB, ballfolder )

            world = self.global_world.make_world( metawog.WORLD_BALL, 
                                                        name, 
                                                        BallWorld, 
                                                        self )
            #@DaB Prepare addin template
            addin_template = metawog.BALL_ADDIN_TEMPLATE.replace("BallName",name)
            self._loadUnPackedTree (world, metawog.TREE_BALL_ADDIN,
                            dir, name + '.addin.xml', addin_template)

            self._loadTree( world, metawog.TREE_BALL_MAIN,
                            dir, 'balls.xml.bin' )
            self._loadTree( world, metawog.TREE_BALL_RESOURCE,
                            dir, 'resources.xml.bin' )

            self._processSetDefaults(world.find_tree(metawog.TREE_BALL_RESOURCE))

 #           #clean up resource paths for Linux
 #           for resource in world.resource_root.findall('.//Image'):
 #               res_path = resource.get('path')
 #               clean_res_path = res_path.replace('\\','/')
 #               if res_path != clean_res_path:
 #                   print "Normalizing Path:",res_path,"->",clean_res_path
 #                   resource.set( 'path', clean_res_path )
 #           for resource in world.resource_root.findall('.//Sound'):
 #               res_path = resource.get('path')
 #               clean_res_path = res_path.replace('\\','/')
 #               if res_path != clean_res_path:
 #                   print "Normalizing Path:",res_path,"->",clean_res_path
 #                   resource.set( 'path', clean_res_path )

            if builddepends:
                world._buildDependancyTree()

            if world.isReadOnly:
               world.clean_dirty_tracker()
            world._cleanballtree()
            world.clear_undo_queue()
            self.models_by_name[name] = world
        else:
            #print "world already loaded"
            if self.models_by_name[name].find_tree(metawog.TREE_BALL_DEPENDANCY) is None:
                #print "no dependancy tree found..."
                self.models_by_name[name]._buildDependancyTree()
        return self.models_by_name[name]

    def selectBall( self, name ):
        """Activate the specified ball
           Returns the activated World.
        """
        model = self.getModel(name)
        assert model is not None
        louie.send( metaworldui.ActiveWorldChanged, self._universe, model )
        return model

    def _onElementAdded(self, element, index_in_parent): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )

    def _onElementUpdated(self, element, attribute_name, new_value, old_value): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )
        
    def _onElementAboutToBeRemoved(self, element, index_in_parent): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )

    def hasModifiedReadOnly( self ):
        """Checks if the user has modified read-only """
        for model in self.models_by_name.itervalues():
            if model.is_dirty and model.isReadOnly:
                return True
        return False

    def playLevel( self, ball_name, level_name, nballs=10, visual_debug=False):
    
        #On Mac
        if ON_PLATFORM==PLATFORM_MAC:
            #  Add this WooBLE as Chapter 1 Button
            #print "ON MAC - Save and Play"
            self.prepareTestChamber(ball_name,nballs,visual_debug)
            if self.addLevelButton("WooBLE"):
                #Then run the program file itself with no command-line parameters
                pid = subprocess.Popen( os.path.join(self._wog_path,u'Contents',u'MacOS',u'World of Goo'), cwd = self._wog_dir ).pid
        else:
            if level_name=="WooBLE":
                self.prepareTestChamber(ball_name,nballs,visual_debug)
            pid = subprocess.Popen( [self._wog_path, level_name], cwd = self._wog_dir ).pid

            # Don't wait for process end...
            # @Todo ? Monitor process so that only one can be launched ???

    def prepareTestChamber(self, name,nballs, visual_debug=False):
        output_folder= os.path.join(self._res_dir,'levels','WooBLE')

        # load level scene.xml (app.path/TestChamber/WooBLE.scene.xml) and just output "straight"
        self._savePackedXML(output_folder,'WooBLE.scene.bin',self._loadUnPackedXML(os.path.join(app_path(),'TestChamber'),'WooBLE.scene.xml',''))
        # load level resource  (app.path/TestChamber/WooBLE.resrc.xml) and just output "straight"
        self._savePackedXML(output_folder,'WooBLE.resrc.bin',self._loadUnPackedXML(os.path.join(app_path(),'TestChamber'),'WooBLE.resrc.xml',''))
        # load level level... (app.path/TestChamber/WooBLE.level.xml)
        level_xml = self._loadUnPackedXML(os.path.join(app_path(),'TestChamber'),'WooBLE.level.xml','')

        #set visual_debug
        if visual_debug:
            level_xml=level_xml.replace('visualdebug="false"','visualdebug="true"')
        
        #add the BallInstances to the xml...
        ball_template='<BallInstance angle="0" id="%(id)s" type="%(balltype)s" x="%(x)s" y="%(y)s" />'
        balls = []
        xn = int(math.sqrt(nballs))+1
        xd = 1000/(xn-1)
        y = 500-xd
        for i in range(0,nballs):
            if (i % xn) == 0:
                x = -500+random.random()
                y+= xd
            else:
                x+=xd
            balls.append(ball_template % {'id':'testgoo'+`i`,'balltype':name,'x':`x+(random.random()-0.5)*xd*0.5`,'y':`y`})
            
        #then save
        self._savePackedXML(output_folder,'WooBLE.level.bin',str(level_xml.replace('<targetheight y="10000" />','\n'.join(balls))))

        local_text_ids = ['WOOBLE_TEST_NAME','WOOBLE_TEST_TEXT']
        text_xml=self._loadUnPackedXML(os.path.join(app_path(),'TestChamber'),'WooBLE.text.xml','')
        text_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_TEXT, text_xml )
        # load level text as tree.. then process as normal.. add to Global Text Tree
        for text_element in text_tree.root.findall('string'):
            local_text_ids.append(text_element.get('id'))

        for text_element in self._texts_tree.root.findall('string'):
            if text_element.get('id') in local_text_ids:
                text_element.parent.remove(text_element)
        root = self._texts_tree.root
        rootmbt = root.meta.find_immediate_child_by_tag('string')
        for text_element in text_tree.root.findall('string'):
            local_attrib = text_element.attrib.copy()
            _appendChildTag(root,rootmbt,local_attrib,keepid=True)

        #ADD WOOGLE_TEST_ENTRIES
        if ON_PLATFORM==PLATFORM_MAC:
            local_attrib={'id':'WOOBLE_TEST_NAME','text':"WooBLE : Test Chamber|"+name}
            _appendChildTag(root,rootmbt,local_attrib,keepid=True)
            local_attrib={'id':'WOOGLE_TEST_TEXT','text':'(testing 1 2 3)'}
            _appendChildTag(root,rootmbt,local_attrib,keepid=True)
        # Save it
        self._savePackedData(self._properties_dir, 'text.xml.bin', self._texts_tree )

    def addLevelButton(self,level_name):
        #print "addLevelButton"
            # To prevent "problems" we need to remove
            # a) Old / Last WOOGLE Test level entries
            # and
            # b) Entries for the Level to be tested, if it's been added by GooTool already.
            # then add our new entries
        button_x,button_y = -660,580
        label_x,label_y = button_x+30,button_y
        scenelayer_x,scenelayer_y=button_x,button_y+20
        #load res/islands/island1.xml.bin
        path = os.path.join( self._res_dir,u'islands',u'island1.xml.bin' )
        if not os.path.isfile( path ):
            print "File not found:",path
            return false
        else:
        #    print "Doing",path
            xml_data = wogfile.decrypt_file_data( path )
            tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_ISLAND, xml_data )
            root = tree.root
            rootmbt = root.meta.find_immediate_child_by_tag('level')
            # seek WooGLE_Test element

            for level in root.findall('level'):
                if level.get('name')==APP_NAME_UPPER+'_TEST_NAME':
                    # remove if found
                    level.parent.remove(level)
                #elif level.get('id')==level_name:
                #    level.parent.remove(level)

            #add new WooGLE_Test element
            attrib={'id':level_name,'name':APP_NAME_UPPER+"_TEST_NAME",'text':APP_NAME_UPPER+"_TEST_TEXT"}
            _appendChildTag(root,rootmbt,attrib,keepid=True)
            
            #save file
            xml_data = tree.to_xml()
            xml_data = xml_data.replace('><','>\n<')
            wogfile.encrypt_file_data( path, xml_data )
         #   print "Done",path

        #load res/levels/island1/island1.scene.bin
        path = os.path.join( self._res_dir,u'levels',u'island1',u'island1.scene.bin' )
        if not os.path.isfile( path ):
            print "File not found:",path
            return false
        else:
          #  print "Doing",path
            xml_data = wogfile.decrypt_file_data( path )
            tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_SCENE, xml_data )
            root = tree.root
            # seek WooGLE_Test Label element
          #  print "seeking label"
            for label in root.findall('label'):
                x,y = label.get_native('position')
                if abs(x-label_x)<1:
                 if abs(y-label_y)<1:
          #          print "Removing old label",label.get('id')
                    label.parent.remove(label)


            attrib={'id':'txt_'+level_name, 'text':APP_NAME_UPPER+"_TEST_NAME",
            'depth':"0.1", 'position':`label_x`+","+`label_y`,
            'align':"left", 'rotation':"6.337", 'scale':"0.7",
            'overlay':"false",'screenspace':"false", 'font':"FONT_INGAME36"}
            rootmbt = root.meta.find_immediate_child_by_tag('label')
            _appendChildTag(root,rootmbt,attrib,keepid=True)

           # print "seek scenelayer"
            for scenelayer in root.findall('SceneLayer'):
                x,y = scenelayer.get_native('center')
                if abs(x-scenelayer_x)<1:
                 if abs(y-scenelayer_y)<1:
           #         print "removing old scenelayer",scenelayer.get('id')
                    scenelayer.parent.remove(scenelayer)
            
           # print "create scenelayer",'ocd_'+level_name
            attrib={ 'id':'ocd_'+level_name, 'name':"OCD_flag1",
                    'depth':"-0.1", 'center':`scenelayer_x`+","+`scenelayer_y`,
                    'scale':"0.7,0.7", 'rotation':"17.59",
                    'alpha':"1",'colorize':"255,255,255",
                    'image':"IMAGE_SCENE_ISLAND1_OCD_FLAG1",
                    'anim':"ocdFlagWave",'animspeed':"1"}
            rootmbt = root.meta.find_immediate_child_by_tag('SceneLayer')
            _appendChildTag(root,rootmbt,attrib,keepid=True)

            # seek WooGLE_Test Button element
           # print "seeking button"
            for buttongroup in root.findall('buttongroup'):
                if buttongroup.get('id')=='levelMarkerGroup':
                    buttongroupelement=buttongroup
                for button in buttongroup.findall('button'):
                    x,y = button.get_native('center')
                    if abs(x-button_x)<1:
                     if abs(y-button_y)<1:
            #            print "removing button",button.get('id')
                        button.parent.remove(button)

           # print "create button","lb_"+level_name
            rootmbt = buttongroupelement.meta.find_immediate_child_by_tag('button')
            attrib={'id':"lb_"+level_name,'onclick':"pl_"+level_name,
                    'depth': "0", 'center':`button_x`+","+`button_y`,
                    'scale':"1.008,0.848",'rotation':"-0.5",
                    'alpha':"1", 'colorize':"255,255,255",
                    'up':"IMAGE_SCENE_ISLAND1_LEVELMARKERA_UP",
                    'over':"IMAGE_SCENE_ISLAND1_LEVELMARKERA_OVER"}
            _appendChildTag(buttongroupelement,rootmbt,attrib,keepid=True)

            #save file
            xml_data = tree.to_xml()
            xml_data = xml_data.replace('><','>\n<')
            wogfile.encrypt_file_data( path, xml_data )
           # print "Done",path
        return True

    def newBall( self, name ):
        """Creates a new blank level with the specified name.
           May fails with an IOError or OSError."""
        return self._addNewBall( name,
            self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_MAIN,
                                                          metawog.BALL_BALL_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_RESOURCE,
                                                          metawog.BALL_RESOURCE_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_ADDIN,
                                                          metawog.BALL_ADDIN_TEMPLATE.replace("BallName",name)),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_DEPENDANCY,
                                                          metawog.BALL_DEPENDANCY_TEMPLATE ) )

    def cloneBall( self, cloned_name, new_name ):
        #Clone an existing ball and its resources.
           model = self.getModel( cloned_name )
           dir = os.path.join( self._res_dir, STR_DIR_STUB, new_name )
           if not os.path.isdir( dir ):
                os.mkdir( dir )

            #New Clone Method
            #get xml from existing
            #make unattached trees from it
           new_ball_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_MAIN, 
                                                                        model.ball_root.tree.to_xml() )

           new_res_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_RESOURCE, 
                                                                        model.resource_root.tree.to_xml() )

           new_addin_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_ADDIN, 
                                                                        model.addin_root.tree.to_xml() )
            #change stuff

           for resource_element in new_res_tree.root.findall( './/Resources' ):
                resource_element.set( 'id', 'ball_%s' % new_name )

           for resource_element in new_res_tree.root.findall( './/Image' ):
                self.transferResource(resource_element,cloned_name,new_name)

           for resource_element in new_res_tree.root.findall( './/Sound' ):
                self.transferResource(resource_element,cloned_name,new_name)

           id_element = new_addin_tree.root.find('.//id')
           id_element.set('value', "")

           new_ball_tree.root.set('name',new_name)
           self._res_swap(new_ball_tree.root,'_'+cloned_name.upper()+'_','_'+new_name.upper()+'_')

            #save out new trees

           self._saveUnPackedData( dir, new_name + '.addin.xml', new_addin_tree )
           self._savePackedData( dir, 'balls.xml.bin', new_ball_tree )
           self._savePackedData( dir, 'resources.xml.bin', new_res_tree )

           self.ball_name_map[new_name]=new_name
           metaworld.BALL_NAMES.append(new_name)
           metaworld.BALL_NAMES.sort(key=str.lower)
           self.__is_dirty = True

    def transferResource(self,resource_element,old_name,new_name):
        resid = resource_element.get('id')
        resource_element.set('id',resid.replace('_'+old_name.upper()+'_','_'+new_name.upper()+'_',1))
        # deal with paths and transfers
        res_path = resource_element.get('path','')
        if res_path=='':
            return
        fileext = {'Image':'png','Sound':'ogg'}[resource_element.tag]
        if self._isOriginalFile(res_path,fileext):
            #res path remains unchanged
            return 
        #@DaB - Ensure if the file is copied that it's new extension is always lower case
        file = os.path.join(self._wog_dir,res_path+"."+fileext)
        fname = os.path.splitext(os.path.split( file )[1])[0] + "." + fileext
        if fileext=='png':
            newfile = os.path.join(self._wog_dir,'res',STR_DIR_STUB,new_name,fname.replace(' ',''))
        else:
            newfile = os.path.join(self._wog_dir,'res','sounds',fname.replace(' ',''))
        if os.path.normpath(file)!=os.path.normpath(newfile):
            basefile = os.path.splitext(newfile)
            serial = 2
            while os.path.isfile(newfile):
                newfile = "%s%d%s" % (basefile[0],serial,basefile[1])
                serial+=1
            copy2(file, newfile)
        resource_element.set('path',os.path.splitext(newfile)[0][len(self._wog_dir)+1:])


    def _res_swap(self,element,find,replace):
           for attribute in element.meta.attributes:
                if attribute.type==metaworld.REFERENCE_TYPE:
                    if attribute.reference_family in ['image','sound']:
                        value = element.get(attribute.name,None)
                        if value is not None:
                            rv = ','.join([v.replace(find,replace,1) for v in value.split(',')])
                            element.set(attribute.name,rv)
           for child in element.getchildren():
                self._res_swap(child,find,replace)

    def creategoomod( self, name ,goomod_filename, include_deps = False):
           model = self.getModel( name )
           dir = os.path.join( self._res_dir, STR_DIR_STUB, name )
           goomod_dir = os.path.join(dir,"goomod")
           stub = os.path.join('res',STR_DIR_STUB,name)
           compile_dir = os.path.join(goomod_dir,'compile', stub)
           if not os.path.isdir( compile_dir ):
                os.makedirs( compile_dir)
           files_to_goomod=[os.path.join(goomod_dir,'addin.xml')]
           self._saveUnPackedData( goomod_dir, 'addin.xml', model.addin_root.tree )

           files_to_goomod.append(os.path.join(compile_dir, 'balls.xml.xml'))
           self._saveUnPackedData( compile_dir, 'balls.xml.xml', model.ball_root.tree )
           files_to_goomod.append(os.path.join(compile_dir, 'resources.xml.xml'))
           self._saveUnPackedData( compile_dir, 'resources.xml.xml', model.resource_root.tree )

           #That's the ball xml taken care of... now lets see if there are any resources to copy
           # The dependancy tree is our friend here.
           # it already contains elements for every (non-original) image and sound
           # as well as entries for balls, particles and materials.
           # it's kinda why I did it.

           # if they've said include_all_dep then we include "everything" in the dep_tree
           # if not, we only do Root Level images and sounds (immediate child of root)
           global_resources = {}
           files_to_copy = set()
           self._add_dep_to_goomod(model.dependancy_root,files_to_copy,files_to_goomod,global_resources,compile_dir,goomod_dir,full_dep=include_deps)

           if len(files_to_copy)>0:
               override_dir = os.path.join(goomod_dir,'override')
               if not os.path.isdir( override_dir ):
                    os.makedirs( override_dir)
               for file in files_to_copy:
                   file_bits = os.path.split(file)
                   dest_dir = os.path.join(override_dir,file_bits[0])
                   if not os.path.isdir( dest_dir ):
                      os.makedirs( dest_dir)
                   src_file = os.path.join(self._wog_dir,file)
                   dest_filename = os.path.splitext(file)
                   dest_file = os.path.join(override_dir,dest_filename[0]+dest_filename[1].lower())
                   copy2(src_file,dest_file)
                   files_to_goomod.append(dest_file)
                   #print "Copied",src_file," to ",dest_file

           #Now create the zip file.
           len_gf = len(goomod_dir)+1
           zout = zipfile.ZipFile(goomod_filename, "w")
           for file in files_to_goomod:
                file_in_zip = file[len_gf:].replace("\\","/")
                #print "goomoding...",file,"as",file_in_zip
                zout.write(file,file_in_zip)
           zout.close()

    def _add_dep_to_goomod(self,element,files_to_copy,files_to_goomod,global_resources,compile_dir,goomod_dir,full_dep=False):
        # first an any 'image' or 'sound' children at this level

        for child in element.getchildren():
            if child.tag == "image":
                files_to_copy.add(child.get('path')+".png")
                if element.tag in ['effect']:
                    #print "effect image found ",child,child.get('id'),child.get('path')
                    global_resources[child.get('id')]=child.get('path')
            elif child.tag=="sound":
                files_to_copy.add(child.get('path')+".ogg")

        if full_dep:
        # findall balls and call with full_dep false
            ball_path = os.path.join(goomod_dir,'compile','res','balls')
            for ball in element.findall('.//ball'):
                # locate ball world
                ball_world = self.global_world.find_world(metawog.WORLD_BALL,ball.get('name'))
                ball_dir = os.path.join(ball_path, ball.get('name'))
                # ENSURE PATH EXISTS
                if not os.path.isdir( ball_dir ):
                   os.makedirs( ball_dir )

                filename =os.path.join(ball_dir,'balls.xml.xml')
                files_to_goomod.append(filename)
                xml_data = wogfile.decrypt_file_data( ball_world.find_tree(metawog.TREE_BALL_MAIN).filename )
                file( filename, 'wb' ).write( xml_data )
                #self._saveUnPackedData( ball_dir, 'balls.xml.xml', ball_tree)

                filename =os.path.join(ball_dir,'resources.xml.xml')
                files_to_goomod.append(filename)
                xml_data = wogfile.decrypt_file_data( ball_world.find_tree(metawog.TREE_BALL_RESOURCE).filename )
                file( filename, 'wb' ).write( xml_data )
#                self._saveUnPackedData( ball_dir, 'resources.xml.xml', ball_tree)

                self._add_dep_to_goomod(ball,files_to_copy,files_to_goomod,global_resources,compile_dir,goomod_dir,full_dep = False)

        # findall particles (store xml) and call with fulldep=false
            particle_xml = ''
            for effect in element.findall('.//effect'):
               res_element = self.global_world.resolve_reference( metawog.WORLD_GLOBAL, 'effect', effect.get('name') )
               particle_xml+=res_element.to_xml()+"\n"
               self._add_dep_to_goomod(effect,files_to_copy,files_to_goomod,global_resources,compile_dir,goomod_dir,full_dep = False)

        # findall materials (store xml)
            material_xml=''
            for material in element.findall('.//material'):
               res_element = self.global_world.resolve_reference( metawog.WORLD_GLOBAL, 'material', material.get('id') )
               material_xml+=res_element.to_xml()+"\n"

            # output xsl for particles, and add for goomod
            merge_path = os.path.join(goomod_dir,'merge','properties')
            if particle_xml!='':
               # print "particle_xml=",particle_xml
                params = {}
                params['path']='/effects'
                params['xml_data'] = particle_xml
                files_to_goomod.append(os.path.join(merge_path,'fx.xml.xsl'))
                self._output_xsl(metawog.XSL_ADD_TEMPLATE,params,merge_path,'fx.xml.xsl')

            # output xsl for materials, and add for goomod
            if material_xml!='':
               # print "material_xml=",material_xml
                params = {}
                params['path']='/materials'
                params['xml_data'] = material_xml
                files_to_goomod.append(os.path.join(merge_path,'materials.xml.xsl'))
                self._output_xsl(metawog.XSL_ADD_TEMPLATE,params,merge_path,'materials.xml.xsl')

            # custom resources required for particles effect need to go in 
            # the global  resources.xml  so require a merge xsl
            if len(global_resources)>0:
               resource_xml= '<SetDefaults path="./" idprefix=""/>\n'
               for id,path in global_resources.items():
                    resource_xml+='<Image id="%(id)s" path="%(path)s" />\n' % {'id':id,'path':path}
               params = {}
               params['path']="/ResourceManifest/Resources[@id='common']"
               params['xml_data'] = resource_xml
               files_to_goomod.append(os.path.join(merge_path,'resources.xml.xsl'))
               self._output_xsl(metawog.XSL_ADD_TEMPLATE,params,merge_path,'resources.xml.xsl')

            # done?
            
    def _output_xsl(self,template,params,directory,filename):
        if not os.path.isdir( directory  ):
            os.makedirs( directory )
        output_path = os.path.join( directory, filename )
        xsl = template % params
        output_data = CREATED_BY + xsl.replace('><','>\n<')
        file( output_path, 'wb' ).write( output_data )

    def _generateFilesXML(self):
        # make top element
        root = xml.etree.ElementTree._ElementInterface('root',{})
        self._addFoldertoFilesXML(root,self._wog_dir,'res')
        res_element = root.find('folder')
        xml_data = xml.etree.ElementTree.tostring(res_element,'utf-8')
        file ( 'files.test.xml','wb').write(xml_data)

    def _addFoldertoFilesXML(self,element,path,dirname):
        newfolder = xml.etree.ElementTree._ElementInterface('folder',{'name':dirname})
        newpath = os.path.join(path,dirname)
        for entry in os.listdir(newpath):
            testpath = os.path.join(newpath,entry)
            if os.path.isdir(testpath):
                self._addFoldertoFilesXML(newfolder,newpath,entry)
            elif os.path.isfile(testpath):
                ext = os.path.splitext(entry)[1][1:]
                if ext in ["png","ogg","binltl","binltl64"]:
                    fileattrib = {'name':os.path.splitext(entry)[0]}
                    fileattrib['type']=ext
                    input_data = file(testpath,'rb').read()
                    fileattrib['size']=str(len(input_data))
                    fileattrib['hash']=hashlib.sha1(input_data).hexdigest()
                    newfile = xml.etree.ElementTree._ElementInterface('file',fileattrib)
                    newfolder.append(newfile)
                    print testpath,",",fileattrib['hash'],",",fileattrib['size']
            else:
                print "Err...",testpath," not a dir or file"
        if len(newfolder)>0:
            element.append(newfolder)

    def _processOriginalFiles(self):
        # expands the files.xml.xml into a number of sets() based in extension
        # bit more memory usage.. but HUGELY faster to determine if a filename is original or not.
        metaworld.ORIGINAL_FILES = {}
        metaworld.ORIGINAL_SIZES = {}
        metaworld.ORIGINAL_HASH = {}
        self._addOriginalFiles(self._files_tree.root)
        
    def _addOriginalFiles(self,element,path=''):
        if element.tag=='folder':
            if path=='':
                path = element.get('name')
            else:
                path = os.path.join(path,element.get('name'))
            for child in element.getchildren():
                self._addOriginalFiles(child,path)
        elif element.tag=='file':
             filename = element.get('name')
             ext=element.get('type')
             if ext not in metaworld.ORIGINAL_FILES.keys():
                 metaworld.ORIGINAL_FILES[ext]=set([os.path.join(path,filename).replace('\\','/')])
                 metaworld.ORIGINAL_SIZES[ext]=set([element.get_native('size')])
                 metaworld.ORIGINAL_HASH[ext]={element.get('hash'):os.path.join(path,filename).replace('\\','/')}
             else:
                 metaworld.ORIGINAL_FILES[ext].add(os.path.join(path,filename).replace('\\','/'))
                 metaworld.ORIGINAL_SIZES[ext].add(element.get_native('size'))
                 metaworld.ORIGINAL_HASH[ext][element.get('hash')]=os.path.join(path,filename).replace('\\','/')

             #if ext=='png':
             #print os.path.join(path,filename+"."+ext),element.get('hash',''),element.get('size','')
        else:
            print "Unknown tag in files.xml"

    def _isOriginalFile(self, filename,extension):
        return filename.replace('\\','/') in metaworld.ORIGINAL_FILES[extension]
        
        
    def _addNewBall( self, name, ball_tree, resource_tree, addin_tree=None, dependancy_tree=None ):
        """Adds a new level using the specified level, scene and resource tree.
           The level directory is created, but the level xml files will not be saved immediately.
        """
        dir_path = os.path.join( self._res_dir, STR_DIR_STUB, name )
        if not os.path.isdir( dir_path ):
             os.mkdir( dir_path )

                
        # Fix the hard-coded level name in resource tree: <Resources id="scene_NewTemplate" >
        for resource_element in resource_tree.root.findall( './/Resources' ):
            resource_element.set( 'id', 'ball_%s' % name )

        #also set the ball name
        ball_tree.root.set('name',name)

        # Creates and register the new level
        world = self.global_world.make_world( metawog.WORLD_BALL, name,
                                                    BallWorld, self)
        treestoadd = [ball_tree,resource_tree]
        if addin_tree is not None:
            treestoadd.append(addin_tree)
        if dependancy_tree is not None:
            treestoadd.append(dependancy_tree)

        world.add_tree( treestoadd )

        self.models_by_name[name] = world
        self.ball_name_map[name]=name
        metaworld.BALL_NAMES.append(name)
        metaworld.BALL_NAMES.sort(key=str.lower)

class ThingWorld(metaworld.World,
                 metaworldui.SelectedElementsTracker,
                 metaworldui.ElementIssueTracker,
                 metaworldui.UndoWorldTracker):
    def __init__( self, universe, world_meta, name, game_model, is_dirty = False ):
        metaworld.World.__init__( self, universe, world_meta, name )
        metaworldui.SelectedElementsTracker.__init__( self, self )
        metaworldui.ElementIssueTracker.__init__( self,self )
        metaworldui.UndoWorldTracker.__init__(self,self,100)
        self.game_model = game_model

    @property
    def name( self ):
        return self.key

class BallWorld(ThingWorld):
    def __init__( self, universe, world_meta, name, game_model, is_dirty = False ):
        ThingWorld.__init__(self, universe, world_meta, name, game_model, is_dirty = is_dirty )
        self.__dirty_tracker = metaworldui.DirtyWorldTracker( self, is_dirty )
        self._importError = [None,None]
        self._ballissues = ''
        self._resrcissues = ''
        self._globalissues = ''
        self._ball_issue_level = ISSUE_LEVEL_NONE
        self._resrc_issue_level = ISSUE_LEVEL_NONE
        self._global_issue_level = ISSUE_LEVEL_NONE
        self._dependancyissues = ''
        self._dependancy_issue_level = ISSUE_LEVEL_NONE
        self._recursion = []
        self._view = None
        
        if name in metaworld.BALL_NAMES:
            self.ball_folder = game_model.ball_name_map[name]
        else:
            self.ball_folder = name

    @property
    def ball_root( self ):
        return self.find_tree( metawog.TREE_BALL_MAIN ).root

    @property
    def resource_root( self ):
        return self.find_tree( metawog.TREE_BALL_RESOURCE ).root

    @property
    def addin_root( self ):
        return self.find_tree( metawog.TREE_BALL_ADDIN ).root

    @property
    def dependancy_root( self ):
        return self.find_tree( metawog.TREE_BALL_DEPENDANCY ).root

    @property
    def is_dirty( self ):
        return self.__dirty_tracker.is_dirty

    @property
    def isReadOnly( self ):
        return self.name in metawog.BALLS_ORIGINAL

    @property
    def view( self ):
        return self._view

    def setView (self, newview):
        self._view = newview

   #@DaB - Issue checking used when saving the level, or making a goomod
    def hasIssues (self):
		#Checks all 3 element trees for outstanding issues
		# Returns True if there are any.
        self._buildDependancyTree()
        tIssue = ISSUE_LEVEL_NONE
        if self.element_issue_level(self.ball_root):
            tIssue |= ISSUE_LEVEL_CRITICAL
        if self.element_issue_level(self.resource_root):
            tIssue |= ISSUE_LEVEL_CRITICAL
        if self.element_issue_level(self.dependancy_root):
            tIssue |= ISSUE_LEVEL_CRITICAL

        #If we have a tree Issue.. don't perform the extra checks
        #because that can cause rt errors (because of the tree issues)
        #and then we don't see a popup.
        if tIssue==ISSUE_LEVEL_CRITICAL:
            #ensure old issues don't get redisplayed if we do "bail" here
            self._ballissues = ''
            self._resrcissues = ''
            self._globalissues = ''
            return tIssue
        if self.hasball_issue():
            tIssue |= self._ball_issue_level
        if self.hasresrc_issue():
            tIssue |= self._resrc_issue_level
        if self.hasglobal_issue():
            tIssue |= self._global_issue_level
        if self.hasdependancy_issue():
            tIssue |= (self._dependancy_issue_level & 6)

        return tIssue

    def getIssues (self):
		#Get a 'report' of outstanding Issues
		#Used for Popup Message
        txtIssue = ''
        if self.element_issue_level(self.ball_root):
            txtIssue = txtIssue + '<p>Ball Tree:<br>' + self.element_issue_report(self.ball_root) + '</p>'
        if self.ball_issue_report!='':
            txtIssue+= '<p>Ball Checks:<br>' + self.ball_issue_report + '</p>'
        if self.element_issue_level(self.resource_root):
            txtIssue = txtIssue + '<p>Resource Tree:<br>' + self.element_issue_report(self.resource_root) + '</p>'
        if self.resrc_issue_report!='':
            txtIssue+= '<p>Resource Checks:<br>' + self.resrc_issue_report + '</p>'
        if self.global_issue_report!='':
            txtIssue+= '<p>Global Checks:<br>' + self.global_issue_report + '</p>'
#        if self.element_issue_level(self.text_root):
#            txtIssue = txtIssue + '<p>Text Tree:<br>' + self.element_issue_report(self.text_root) + '</p>'
        if self.dependancy_issue_report!='':
            txtIssue+= '<p>Dependancy Checks:<br>' + self.dependancy_issue_report + '</p>'

        return txtIssue



 #@DaB Additional Checking Level,Scene,Resource (at tree level)
    def hasglobal_issue(self):
        # check for issues across trees
        #if there's a levelexit it must be within the scene bounds
        self._globalissues = ''
        self._global_issue_level = ISSUE_LEVEL_NONE

        return self._global_issue_level!=ISSUE_LEVEL_NONE

    def addBallError(self,error_num,subst):
        error = errors.ERROR_INFO[error_num]
        self._ball_issue_level,self._ballissues = self.addError(self._ball_issue_level,self._ballissues,error,error_num,subst)

    def addResourceError(self,error_num,subst):
        error = errors.ERROR_INFO[error_num]
        self._resrc_issue_level,self._resrcissues = self.addError(self._resrc_issue_level,self._resrcissues,error,error_num,subst)

    def addGlobalError(self,error_num,subst):
        error = errors.ERROR_INFO[error_num]
        self._global_issue_level,self._globalissues = self.addError(self._global_issue_level,self._globalissues,error,error_num,subst)

    def addDependancyError(self,error_num,subst):
        error = errors.ERROR_INFO[error_num]
        self._dependancy_issue_level,self._dependancyissues = self.addError(self._dependancy_issue_level,self._dependancyissues,error,error_num,subst)


    def addError(self,err_level,err_message,error,error_num,err_subst):
        err_level|=error[0]
        err_message+=errors.ERROR_FRONT[error[0]]
        if err_subst is not None:
            err_message+=error[1] % err_subst
        else:
            err_message+=error[1]
        err_message+=errors.ERROR_MORE_INFO % error_num
        err_message+="<br>"
        return err_level,err_message

    def hasball_issue(self):
        # rules for "DUMBASS" proofing (would normally use a much ruder word)

        root = self.ball_root
        self._ballissues=''
        self._ball_issue_level = ISSUE_LEVEL_NONE
              #     self._levelissues+='Advice: '+c_aspect+' poi traveltime will cause a delay starting the level.\n'
              #     self._level_issue_level |= ISSUE_LEVEL_ADVICE

        #BALL_ROOT
        #detachable=true but no detachstrand "weirdness"
        if root.get_native('detachable',False):
            element = root.find('detachstrand')
            if element is None:
                self.addBallError(501,None)

        #static and draggable
        if root.get_native('static',False) and root.get_native('draggable',True):
            self.addBallError(516,None)

        #contains but no poppoarticles or popsound crash
        if root.get('contains','')!='':
            if root.get('popparticles','')=='':
                self.addBallError(502,None)
            if root.get('popsound','')=='':
                self.addBallError(503,None)
            if root.get_native('static',False):
                self.addBallError(518,None)
            if root.get_native('strands',0)>0:
                self.addBallError(519,None)
            if (root.get_native('sticky',False)) or (root.get_native('stickyattached',False)) or (root.get_native('stickyunattached',False)):
                self.addBallError(520,None)

        if (root.get_native('autoattach',False)) and (root.get_native('strands',0)>0):
            strand = root.find('strand')
            if strand is None:
                self.addBallError(521,None)
        #low towermass glitch
        if abs(root.get_native('towermass',10))<1:
            self.addBallError(504,None)

        #stacking and circle crash
        if root.get_native('stacking',False):
           shape = root.get('shape','circle').split(',')[0]
           if shape.lower()=='circle':
               self.addBallError(505,None)

        if root.get_native('dragmass',100)<10:
               self.addBallError(506,None)

        #Attenuation 2 arg
        for att_name in ['attenuationselect','attenuationdeselect','attenuationdrag','attenuationdrop']:
            att_value = root.get_native(att_name,[0,1,1])
            if len(att_value)==2:
                if att_value[0]>0.0:
                   self.addBallError(507,att_name)

        #PARTS
        body_part = False
        for part in root.findall('part'):
            #eye=true but no pupil image
            if part.get('name')=='body':
                body_part = True
            if part.get_native('eye',False):
                if part.get('pupil','')=='':
                   self.addBallError(508,part.get('name'))
        
        if not body_part:
           self.addBallError(509,None)
           
        #strands
        strand = root.find('strand')
        if strand is not None:
            maxlen2 = strand.get_native('maxlen2',0)
            if maxlen2==0:
               self.addBallError(510,None)
            maxlen1 =  strand.get_native('maxlen1',0)
            minlen = strand.get_native('minlen',0)
            if ((maxlen1 > 0) & (minlen > maxlen1)) | ( minlen > maxlen2) :
               self.addBallError(511,None)
            if strand.get_native('burnspeed',0)>0:
               if strand.get('fireparticles','')=='':
                   self.addBallError(512,None)
               if root.get_native('burntime',0)>0:
                 if strand.get_native('ignitedelay',0) > (root.get_native('burntime',0)-1):
                   self.addBallError(513,None)
            if strand.get('type','')=='rigid':
               if strand.get_native('mass',0)==0:
                   self.addBallError(517,None)
        #Throw Sound Advice
        soundevents = []
        for sound in root.findall('sound'):
            if sound.get('event') in ['bounce','land','deathfall','exit','throw']:
                soundevents.append(sound.get('event'))

        if 'throw' in soundevents:
           if soundevents[-1]!='throw':
                self.addBallError(514,soundevents[-1])
        elif len(soundevents)>0:
            self.addBallError(515,soundevents[-1])

        return self._ball_issue_level!=ISSUE_LEVEL_NONE

    def _get_all_resource_ids(self,root,tag):
        resource_ids = set()
        for resource in root.findall('.//'+tag):
            resource_ids.add(resource.get('id'))
        return resource_ids

    def _get_unused_resources(self):
        used = self._get_used_resources()
        resources={}
        resources['image'] = self._get_all_resource_ids(self.resource_root,"Image")
        resources['sound'] = self._get_all_resource_ids(self.resource_root,"Sound")
        unused = {'image':set(),'sound':set()}
        for restype in unused.keys():
            unused[restype] = resources[restype]-used[restype]
        return unused

    def _remove_unused_resources(self,unused):
        self.suspend_undo()
        for family,unusedset in unused.items():
          for unusedid in unusedset:
            element = self.resolve_reference(metawog.WORLD_BALL, family, unusedid)
            if element is not None:
                element.parent.remove(element)
        self.activate_undo()

    def _get_used_resources(self):
        used = {'image':set(),'sound':set()}
        oftype = ['image','sound']
        #go through scene and level root
        #store the resource id of any that do
        for element in self.ball_root:
            for attribute_meta in element.meta.attributes:
                if attribute_meta.type == metaworld.REFERENCE_TYPE:
                    if attribute_meta.reference_family in oftype:
                        if element.get(attribute_meta.name):
                            if attribute_meta.is_list:
                                for res in element.get(attribute_meta.name).split(','):
                                    used[attribute_meta.reference_family].add(res)
                            else:
                                used[attribute_meta.reference_family].add(element.get(attribute_meta.name))

        element = self.ball_root
        for attribute_meta in element.meta.attributes:
            if attribute_meta.type == metaworld.REFERENCE_TYPE:
                if attribute_meta.reference_family in oftype:
                    if element.get(attribute_meta.name):
                        if attribute_meta.is_list:
                            for res in element.get(attribute_meta.name).split(','):
                                used[attribute_meta.reference_family].add(res)
                        else:
                            used[attribute_meta.reference_family].add(element.get(attribute_meta.name))
        #print "Used Resources :",used
        return used

    def hasresrc_issue(self):
        root = self.resource_root
        self._resrcissues = ''
        self._resrc_issue_level = ISSUE_LEVEL_NONE
        # confirm every file referenced exists
        used_resources = self._get_used_resources()
        image_resources = set()
        for resource in root.findall('.//Image'):
            image_resources.add(resource.get('id'))
#            full_filename = os.path.join(self.game_model._wog_dir,resource.get('path')+".png")
#            if ON_PLATFORM == PLATFORM_WIN:
#                #confirm extension on drive is lower case
#                real_filename= _getRealFilename(full_filename)
#                real_ext = os.path.splitext(real_filename)[1]
#                if real_ext != ".png":
#                  self.addResourceError(201,resource.get('path')+real_ext)

        unused_images = image_resources.difference(used_resources['image'])
        if len(unused_images)!=0:
            for unused in unused_images:
               self.addResourceError(202,unused)

        sound_resources = set()
        for resource in root.findall('.//Sound'):
            sound_resources.add(resource.get('id'))
#            full_filename = os.path.join(self.game_model._wog_dir,resource.get('path')+".ogg")
#            if ON_PLATFORM == PLATFORM_WIN:
#                #confirm extension on drive is lower case
#                real_filename=_getRealFilename(full_filename)
#                real_ext = os.path.splitext(real_filename)[1]
#                if real_ext != ".ogg":
#                    self.addResourceError(203,resource.get('path')+real_ext)

        unused_sounds = sound_resources.difference(used_resources['sound'])
        if len(unused_sounds)!=0:
            for unused in unused_sounds:
               self.addResourceError(204,unused)

        return self._resrc_issue_level != ISSUE_LEVEL_NONE


    @property
    def ball_issue_report(self):
        return self._ballissues
    @property
    def resrc_issue_report(self):
        return self._resrcissues
    @property
    def global_issue_report(self):
        return self._globalissues

    #@DaB Additional Issue checking when trying to produce a goomod
    def hasAddinIssues (self):
        if self.element_issue_level(self.addin_root):
            return True
        return False

    def getAddinIssues (self):
        txtIssue = ''
        if self.element_issue_level(self.addin_root):
            txtIssue = txtIssue + 'Addin : ' + self.element_issue_report(self.addin_root) + '<br>'
        return txtIssue

    def _buildDependancyTree(self):
        self.suspend_undo()

        dependancy_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_DEPENDANCY, metawog.BALL_DEPENDANCY_TEMPLATE )

        current={'imagedep':set(),'sounddep':set(),'effectdep':set(),'materialdep':set(),'balldep':set()}
        ball_trace=''
        self._recursion = []
        self._addDependancies(self.ball_root,dependancy_tree.root,current,ball_trace)

        self.game_model.global_world.refreshFromFiles()
          
        for element in self.resource_root.findall('.//Image'):
            child_attrib = {'found':"true"}
            for attribute in element.meta.attributes:
               child_attrib[attribute.name]=element.get(attribute.name)
            if child_attrib['path'] not in current['imagedep']:
                child_element = metaworld.Element( metawog.BALL_DEP_IMAGE, child_attrib)
                dependancy_tree.root._children.append( child_element )
                child_element._parent = dependancy_tree.root
                current['imagedep'].add(child_attrib['path'])

        for element in self.resource_root.findall('.//Sound'):
            child_attrib = {'found':"true"}
            for attribute in element.meta.attributes:
               child_attrib[attribute.name]=element.get(attribute.name)
            if child_attrib['path'] not in current['sounddep']:
                child_element = metaworld.Element( metawog.BALL_DEP_SOUND, child_attrib)
                dependancy_tree.root._children.append( child_element )
                child_element._parent = dependancy_tree.root
                current['sounddep'].add(child_attrib['path'])

        self._removeOriginalDependancies(dependancy_tree.root)

        old_tree = self.find_tree(metawog.TREE_BALL_DEPENDANCY)
        if old_tree is None:
            self.add_tree( [dependancy_tree] )
        else:
            old_tree.set_root(dependancy_tree.root)

        self.activate_undo()
        self.__dirty_tracker.clean_tree(metawog.TREE_BALL_DEPENDANCY)

        return dependancy_tree

    def _isNumber(self,input):
        try:
            f = float(input)
            return True
        except ValueError:
            return False

    def _removeOriginalDependancies(self,element):
        children = []
        children.extend(element.getchildren())
        for child in children:
            self._removeOriginalDependancies(child)

        remove = False
        if (element.tag=='image') or (element.tag=='sound'):
          extensions={'image':'png','sound':'ogg'}
          if self.game_model._isOriginalFile(element.get('path'),extensions[element.tag]):
             remove = True
          if not remove:
             if element.get('id','')=='':
                # path but no id, swap em
                element.set('found','* resource id not found *')
             elif element.get_native('found',False):
                fullfilename = os.path.normpath(os.path.join(self.game_model._wog_dir,element.get('path')+'.'+extensions[element.tag]))
                if not os.path.exists(fullfilename):
                     element.set('found','* file not found *')
             #print "remove",element.tag, element.get('path')
        elif element.tag=='material':
            if element.get('id') in metawog.MATERIALS_ORIGINAL:
                 remove = True
            if not remove:
              if not element.get_native('found',False):
                  element.set('found','* custom material not found *')
             #    print "remove",element.tag, element.get('id')
        elif element.tag=='effect':
            if (element.get('name') in metawog.PARTICLEEFFECTS_ORIGINAL) or (element.get('name') in metawog.AMBIENTEFFECTS_ORIGINAL):
                 remove = True
            if not remove:
              if not element.get_native('found',False):
                  element.set('found','* particle effect not found *')
        elif element.tag=='ball':
            if element.get('name') in metawog.BALLS_ORIGINAL:
                 remove = True
            if not remove:
              if not element.get_native('found',False):
                  element.set('found','* ball not found *')
#                 print "remove",element.tag, element.get('name')
        elif element.tag=='dependancy':
                remove=False
        else:
            print "Unknown Dependancy Tag", element.tag

        if remove and len(element.getchildren())==0 and element.get_native('found',False):
#            print "Actually Removing",element.tag
             index = element.parent._children.index( element )
             del element.parent._children[index]
             element._parent = None
             del element

    def _addDependancies(self,element,dep_element,current, ball_trace):
        #run through the attributes of the element
        # add nodes at this level for any direct deps
        if element.tag=='ball':
            if element.get('name') in ball_trace.split(','):
                self._recursion.append(ball_trace+element.get('name'))
                return
            else:
                ball_trace+=element.get('name')+","
            #only bother refreshing custom balls
            if element.get('name') not in metawog.BALLS_ORIGINAL:
                world = element.world
                element.world.refreshFromFiles()
                element = world.find_tree(metawog.TREE_BALL_MAIN).root

        for attribute_meta in element.meta.attributes:
             if attribute_meta.type == metaworld.REFERENCE_TYPE:
                if attribute_meta.reference_family in ['image','sound','effect','material','ball']:
                    attribute_value = attribute_meta.get(element)
                    ref_world = attribute_meta.reference_world
                    ref_family = attribute_meta.reference_family
                    is_list = attribute_meta.is_list
                else:
                    attribute_value = None
             elif attribute_meta.name=='contains':
                attribute_value = attribute_meta.get(element)
                ref_world = metawog.WORLD_BALL
                ref_family = 'ball'
                is_list = True
             else:
                attribute_value=None
                
             if attribute_value is not None:
                  if is_list:
                      references=attribute_value.split(',')
                  else:
                      references=[attribute_value]
                  for reference in references:
                   if reference.strip()!='' and not self._isNumber(reference.strip()):
                    res_element = None
                    try:
                        res_element = self.resolve_reference( ref_world, ref_family, reference )
                    except ValueError:
                        print "try-except ValueError"
                    if res_element is None:
                        ball_element = element
                        for i in range(4):
                          if ball_element.tag=="ball":
                             world = ball_element.world
                             if world is not None:
                                res_element = world.resolve_reference( ref_world, ref_family, reference )
                             break
                          elif ball_element.parent is None:
                              print "ball_element no parent",ball_element.tag,i
                              break
                          ball_element = ball_element.parent
                    
                    new_dep_meta = dep_element.meta.find_immediate_child_by_tag(ref_family)
                    child_attrib = {}
                    id_attribute = None
                    if res_element is None:
                        #print "Empty res_element",element.tag, attribute_meta.name, attribute_meta.reference_world,attribute_meta.reference_family, reference
                        for dep_attribute in new_dep_meta.attributes:
                            if dep_attribute.type == metaworld.IDENTIFIER_TYPE:
                                child_attrib[dep_attribute.name]=reference
                                id_attribute = dep_attribute
                    else:
                        child_attrib['found']="true"
                        for dep_attribute in new_dep_meta.attributes:
                            if dep_attribute.name!='found':
                             child_attrib[dep_attribute.name]=res_element.get(dep_attribute.name)
                             if dep_attribute.type == metaworld.IDENTIFIER_TYPE:
                                id_attribute = dep_attribute

                    if id_attribute is None or res_element is None:
                        if reference not in current[id_attribute.reference_family]:
                            child_element = metaworld.Element( new_dep_meta, child_attrib)
                            dep_element._children.append( child_element )
                            child_element._parent = dep_element
                            current[id_attribute.reference_family].add(reference)
                    elif res_element.get(id_attribute.name) not in current[id_attribute.reference_family]:
                        child_element = metaworld.Element( new_dep_meta, child_attrib)
                        dep_element._children.append( child_element )
                        child_element._parent = dep_element
                        current[id_attribute.reference_family].add(res_element.get(id_attribute.name))
                        self._addDependancies(res_element,child_element,current,ball_trace)


        #now run through child elements
        for child_element in element.getchildren():
            self._addDependancies(child_element,dep_element,current,ball_trace)

    def hasDependancies(self):
        return len(self.dependancy_root.getchildren())>0

    def hasdependancy_issue(self):
        # things to check
        self._dependancyissues = ''
        self._dependancy_issue_level = ISSUE_LEVEL_NONE

        if len(self._recursion)>0:
            for recurse in self._recursion:
                self.addDependancyError(301,recurse.replace(',',' --> '))
    
        # Custom Balls
        ball_dep = {}
        for ball in self.dependancy_root.findall(".//ball"):
            ball_dep[ball.get('name')]=ball.get_native('found',False)

        if len(ball_dep)!=0:
            self.addDependancyError(302,','.join(ball_dep.keys()))
            for ball,found in ball_dep.items():
                if not found:
                    self.addDependancyError(303,ball)

        # Custom Materials
        material_dep = {}
        for material in self.dependancy_root.findall(".//material"):
            material_dep[material.get('id')]=material.get_native('found',False)

        if len(material_dep)!=0:
            self.addDependancyError(304,','.join(material_dep.keys()))
            for material,found in material_dep.items():
                if not found:
                    self.addDependancyError(305,material)

        # Custom Particles
        particles_dep = {}
        for effect in self.dependancy_root.findall(".//effect"):
            particles_dep[effect.get('name')]=effect.get_native('found',False)

        if len(particles_dep)!=0:
            self.addDependancyError(306,','.join(particles_dep.keys()))
            for effect,found in particles_dep.items():
                if not found:
                    self.addDependancyError(307,effect)
 
        return self._dependancy_issue_level != ISSUE_LEVEL_NONE

    @property
    def dependancy_issue_report(self):
        return self._dependancyissues

    def _cleanballtree(self):
        self.suspend_undo()
        # ? determine already sorted... and skip

        selected = self.selected_elements
        elements = []
        #get sortable list [element, sort order]
        sortorder={'marker':1,'shadow':2,'particles':3,'strand':4,'detachstrand':5,'splat':6,
                    'part':10,
                    'sinvariance':100,'sound':101}

       #Use OFF-LINE tree to do the actual sorting
        old_tree = self.find_tree(metawog.TREE_BALL_MAIN)
        #new_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_BALL_MAIN,
        #                    old_tree.to_xml() )

        for element in old_tree.root.getchildren():
            sort_order = sortorder[element.tag]
            if element.tag=='part':
                sort_order+= element.get_native('layer',0)
            elements.append((element,sort_order))

        #sort it
        sorted_elements=sorted(elements, key=lambda part: part[1])
        element_index_map = {}
        for i in range(0,len(sorted_elements)):
            element_index_map[elements[i][0]]=i
        sortedone = False
        for i in range(0,len(sorted_elements)):
            if sorted_elements[i][0]!=elements[i][0]:
                # sorted_element[i] is not at the right index
#                print "element",i,sorted_elements[i][0].tag, " incorrect.. correct at", element_index_map[sorted_elements[i][0]]
                elements.insert(i,elements.pop(element_index_map[sorted_elements[i][0]]))
                old_tree.root.remove(sorted_elements[i][0])
                old_tree.root.insert(i,sorted_elements[i][0])
                sortedone = True
#            else:
#               print "element",i,sorted_elements[i][0].tag, "correct"
        if sortedone:
            self.set_selection(selected)
        #old_tree.set_root(new_tree.root)


        self.activate_undo()

    def _cleanresourcetree(self):
        #removes any unused resources from the resource and text resource trees
        self.suspend_undo()
        root = self.resource_root

        #ensure cAsE sensitive path is stored in resource file
        #Only required on windows...
        #If path was not CaSe SenSitivE match on Linux / Mac would be File not found earlier
        if ON_PLATFORM==PLATFORM_WIN:
          for resource in root.findall('.//Image'):
            full_filename = os.path.normpath(os.path.join(self.game_model._wog_dir,resource.get('path')+".png"))
            if os.path.exists(full_filename):
                #confirm extension on drive is lower case
                len_wogdir = len(os.path.normpath(self.game_model._wog_dir))+1
                real_filename = os.path.normpath(_getRealFilename(full_filename))
                real_file = os.path.splitext(real_filename)[0][len_wogdir:]
                full_file = os.path.splitext(full_filename)[0][len_wogdir:]
                if real_file != full_file:
                    print "Correcting Path",resource.get('id'),full_file,"-->",real_file
                    resource.attribute_meta('path').set(resource, real_file)

          for resource in root.findall('.//Sound'):
            full_filename = os.path.normpath(os.path.join(self.game_model._wog_dir,resource.get('path')+".ogg"))
            if os.path.exists(full_filename):
                #confirm extension on drive is lower case
                len_wogdir = len(os.path.normpath(self.game_model._wog_dir))
                real_filename = os.path.normpath(_getRealFilename(full_filename))
                real_file = os.path.splitext(real_filename)[0][len_wogdir:]
                full_file = os.path.splitext(full_filename)[0][len_wogdir:]
                if real_file != full_file:
                    print "Correcting Path",resource.get('id'),full_file,"-->",real_file
                    resource.attribute_meta('path').set(resource, real_file)

        self.activate_undo()

    def checkClonedFiles(self):
        clonedfiles = {}
        ext_tag = {'Image':'png','Sound':'ogg'}
        #for res_element in self.resource_root.getchildren():
        for element in self.resource_root.findall('.//*'): #res_element.getchildren():
          if element.tag in ['Image','Sound']:  #don't try SetDefaults
             path = element.get('path','')
             if path !='':
                full_filename = os.path.join(self.game_model._wog_dir,path+"."+ext_tag[element.tag])
#                print "Checking : ",full_filename
                if os.path.isfile(full_filename):
                   if not self.game_model._isOriginalFile(path,ext_tag[element.tag]):
                      size = os.path.getsize(full_filename)
#                      print "Is Not Original Name   size=",size
                      if size in metaworld.ORIGINAL_SIZES[ext_tag[element.tag]]:
                          # check hash
                          hash = hashlib.sha1(file(full_filename,'rb').read()).hexdigest()
#                          print "Is Not Original Name : Size Found : hash=",hash
                          try:
                              originalfile = metaworld.ORIGINAL_HASH[ext_tag[element.tag]][hash]
                              clonedfiles[path]=originalfile
#                              print "Is Clone : ", path," = ", originalfile
                          except KeyError:
                              originalfile=''
#                              print "Is not Clone",path

        if len(clonedfiles)>0:
            return clonedfiles
        else:
            return None

    def fixClonedFiles(self,clonedfiles):
        for element in self.resource_root.findall('.//*'):
          if element.tag in ['Image','Sound']:  #don't try SetDefaults
             path = element.get('path','')
             if path !='':
                 try:
                     originalfile = clonedfiles[path]
                 except:
                     originalfile = ''
                 if originalfile !='':
                     element.set('path',originalfile)


    def saveModifiedElements( self ):
        """Save the modified ball, resource tree."""
        if not self.isReadOnly:  # Discards change made on read-only level
            name = self.name
            dir = os.path.join( self.game_model._res_dir, STR_DIR_STUB, self.ball_folder )
            if not os.path.isdir( dir ):
                os.mkdir( dir )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_BALL_ADDIN):
                self.game_model._saveUnPackedData( dir, name + '.addin.xml',
                                                 self.addin_root.tree )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_BALL_MAIN):
                if not self.element_issue_level(self.ball_root):
                  # only clean trees with no issues
                  self._cleanballtree()

                self.game_model._savePackedData( dir, 'balls.xml.bin',
                                                 self.ball_root.tree )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_BALL_RESOURCE):
                if not self.element_issue_level(self.resource_root):
                  # only clean trees with no issues
                  self._cleanresourcetree()
                self.game_model._savePackedData( dir, 'resources.xml.bin',
                                                 self.resource_root.tree )

            # ON Mac
            # Convert all "custom" png to .png.binltl
            # Only works with REAL PNG
            if ON_PLATFORM==PLATFORM_MAC:
                for image in self.resource_root.findall('.//Image'):
                  if not self.game_model._isOriginalFile(image.get('path'),'png'):
                    in_path=os.path.join(self.game_model._wog_dir,image.get('path'))
                    out_path=in_path+'.png.binltl'
                    in_path+='.png'
                    wogfile.png2pngbinltl(in_path,out_path)

            self.__dirty_tracker.clean()

    def clean_dirty_tracker(self):
        self.__dirty_tracker.clean()

    def getImagePixmap( self, image_id ):
        image_element = self.resolve_reference( metawog.WORLD_BALL, 'image', image_id )
        pixmap = None
        if image_element is not None:
            pixmap = self.game_model.pixmap_cache.get_pixmap( image_element )
        else:
            print 'Warning: invalid image reference:|',image_id,'|'
        return pixmap


    def updateResources( self ):
        """Ensures all image/sound resource present in the level directory
           are in the resource tree.
           Adds new resource to the resource tree if required.
        """
        self._importError=[None,None]
        dir = os.path.join( os.path.normpath( self.game_model._wog_dir ), 'res', STR_DIR_STUB, self.name )
        existing_paths = []
        for extension in ('png','ogg'):
            existing_paths.extend(glob.glob( os.path.join( dir, '*.' + extension ) ))
            
        for file in list(existing_paths):
            res_path = file[len(os.path.normpath(self.game_model._wog_dir))+1:]
            if ' ' in res_path:
                self.addImportError("Resource filenames cannot contain spaces : " + res_path)
                existing_paths.remove(file)
        return self.addResources(existing_paths)

	#@DaB New Functionality - Import resources direct from files
    def importError(self):
        return self._importError

    def addImportError(self,error_desc):
        if self._importError[0] is None:
           self._importError[0] = 'Errors encoutered during import'
           self._importError[1] = error_desc
        else:
           self._importError[1]+= "\n"+ error_desc
           
    def importResources( self, importedfiles):
        """Import Resources direct from files into the Resource Tree
           If files are located outside the Wog/res folder it copies them
           png -> res/balls/{name}
           ogg -> res/sounds
        """
        self._importError = [None,None]
        level_path = os.path.join( os.path.normpath(self.game_model._res_dir), STR_DIR_STUB, self.name )
        if not os.path.isdir( level_path ):
            os.mkdir( level_path )
        localfiles = [self.transferResource(file) for file in importedfiles]
        return self.addResources(localfiles)

    def transferResource(self,file):
        fileext = os.path.splitext(file)[1][1:4].lower()
        res_path = file[len(os.path.normpath(self.game_model._wog_dir))+1:]
        if self.game_model._isOriginalFile(os.path.splitext(res_path)[0],fileext):
            return file
        #@DaB - Ensure if the file is copied that it's new extension is always lower case
        fname = os.path.splitext(os.path.split( file )[1])[0] + "." + fileext
        if fileext=='png':
            newfile = os.path.join(self.game_model._wog_dir,'res',STR_DIR_STUB,self.name,fname.replace(' ',''))
        else:
            newfile = os.path.join(self.game_model._wog_dir,'res','sounds',fname.replace(' ',''))
        if os.path.normpath(file)!=os.path.normpath(newfile):
            basefile = os.path.splitext(newfile)
            serial = 2
            while os.path.isfile(newfile):
                newfile = "%s%d%s" % (basefile[0],serial,basefile[1])
                serial+=1
            copy2(file, newfile)
        return newfile


    def addResources(self,filenames):
        game_dir = self.game_model._wog_dir
        resource_element = self.resource_root.find( './/Resources' )
        added_elements = []
        resmap = {'png':('Image','IMAGE_BALL_%s_%s','image'),'ogg':('Sound','SOUND_BALL_%s_%s','sound')}
        known_paths = {'Image':set(),'Sound':set()}
        for ext in resmap:
          for element in self.resource_root.findall( './/' + resmap[ext][0] ):
            path = os.path.normpath( os.path.splitext( element.get('path','').lower() )[0] )
            # known path are related to wog top dir in unix format & lower case without the file extension
            known_paths[resmap[ext][0]].add( path )
        for file in filenames:
          if file!='':
            file = file[len(game_dir)+1:] # makes path relative to wog top dir            print file
            filei = os.path.splitext(file)
            path = os.path.normpath( filei[0] ).lower()
            ext = filei[1][1:4]
            if path not in known_paths[resmap[ext][0]]:
                resource_id = _newResName(self,filei[0],resmap[ext][1],self.name,self._world_meta,resmap[ext][2])
                resource_path = filei[0].replace("\\","/")
                meta_element = metawog.TREE_BALL_RESOURCE.find_element_meta_by_tag( resmap[ext][0] )
                new_resource = metaworld.Element( meta_element, {'id':resource_id,
                                                                 'path':resource_path} )
                resource_element.append( new_resource )
                added_elements.append( new_resource )
        return added_elements

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowIcon( QtGui.QIcon(":/images/icon.png" ))
        self.setAttribute( Qt.WA_DeleteOnClose )
        self.actionTimer = None
        self.statusTimer = None
        self._wog_path = None # Path to worl of goo executable
        self._last_level_name=''
        self.createMDIArea()
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.createDockWindows()
        self.setWindowTitle(self.tr("World of Goo Ball Editor"))        
        self._readSettings()

        self._game_model = None
        if self._wog_path:
	   #Check that the stored path is still valid
            if not os.path.exists(self._wog_path):
                self.changeWOGDir()
            else:
                self._reloadGameModel()
        else:
            # if wog_path is missing, prompt for it.
            self.changeWOGDir()

    def changeWOGDir(self):
        wog_path =  QtGui.QFileDialog.getOpenFileName( self,
             self.tr( 'Select WorldOfGoo program in the folder you want to edit' ),
             r'',
             self.tr( 'World Of Goo (World*Goo*)' ) )
        if wog_path.isEmpty(): # user canceled action
            #wog_path="D:\World of Goo.app"
            return
        self._wog_path = os.path.normpath(unicode(wog_path))
        #print "_wog_path=",self._wog_path
        
        self._reloadGameModel()

    def _reloadGameModel( self ):
        try:
            self._game_model = GameModel( self._wog_path,self)
        except GameModelException, e:
            QtGui.QMessageBox.warning(self, self.tr("Loading World of Goo levels ("+APP_NAME_PROPER+" "+CURRENT_VERSION+")"),
                                      unicode(e))
    def _updateRecentFiles(self):
        if self.recentFiles is None:
            numRecentFiles =0
        else:
            numRecentFiles = min(len(self.recentFiles),MAXRECENTFILES)
        for i in range(0,numRecentFiles):
            self.recentfile_actions[i].setText(self.recentFiles[i])
            self.recentfile_actions[i].setVisible(True)
        for i in range(numRecentFiles,MAXRECENTFILES):
            self.recentfile_actions[i].setVisible(False)
        self.separatorRecent.setVisible(numRecentFiles > 0);

    def _setRecentFile(self,filename):
        self.recentFiles.removeAll(filename)
        self.recentFiles.prepend(filename)
        if len(self.recentFiles) > MAXRECENTFILES:
           self.recentFiles = self.recentFiles[:MAXRECENTFILES]
        self._updateRecentFiles()

    def on_recentfile_action(self):
        action = self.sender()
        name = unicode(action.text())
        if self.open_ball_view_by_name( name ):
            self._setRecentFile( name )
        
    def editBall( self ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = editballdialog.Ui_EditBallDialog()
            ui.setupUi( dialog , set(metaworld.BALL_NAMES), set(metawog.BALLS_ORIGINAL ))
            if dialog.exec_() and ui.ballList.currentItem():
                settings = QtCore.QSettings()
                settings.beginGroup( "MainWindow" )
                settings.setValue( "ball_filter", ui.comboBox.currentIndex())
                settings.endGroup( )
                name = unicode( ui.ballList.currentItem().text() )
                if self.open_ball_view_by_name( name ):
                    self._setRecentFile( name )
                
    def open_ball_view_by_name( self, name ):
        try:
            world = self._game_model.selectBall( name )
        except GameModelException, e:
            QtGui.QMessageBox.warning(self, self.tr("Failed to load ball!"),
                      unicode(e))
        else:
            sub_window = self._findWorldMDIView( world )
            if sub_window:
                self.mdiArea.setActiveSubWindow( sub_window )
            else:
                self._addGraphicView( world )
            return True
        return False

    def _addGraphicView( self, world ):
        """Adds a new MDI LevelGraphicView window for the specified ball."""
        ball_view = ballview.BallGraphicView( world, self.view_actions, self.common_actions )
        sub_window = self.mdiArea.addSubWindow( ball_view )
        self.connect( ball_view, QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'),
                      self._updateMouseScenePosInStatusBar )
        self.connect( sub_window, QtCore.SIGNAL('aboutToActivate()'),
                      ball_view.selectLevelOnSubWindowActivation )
        world.set_selection(world.ball_root)
        world.setView(ball_view)
        ball_view.show()

    def _updateMouseScenePosInStatusBar( self, x, y ):
        """Called whenever the mouse move in the LevelView."""
		# Round displayed coordinate to 2dp (0.01)
        x = round(x,2)
        y = -round(y,2) # Reverse transformation done when mapping to scene (in Qt 0 = top, in WOG 0 = bottom)
        self._mousePositionLabel.setText( self.tr('x: %1 y: %2').arg(x).arg(y) )

    def _findWorldMDIView( self, world ):
        """Search for an existing MDI window showing this ball.
           Return the BallGraphicView widget, or None if not found."""
        for window in self.mdiArea.subWindowList():
            sub_window = window.widget()
            if sub_window.world == world:
                return window
        return None
        
    def get_active_view(self):
        """Returns the view of the active MDI window. 
           Returns None if no view is active.
        """
        window = self.mdiArea.activeSubWindow()
        if window:
            return window.widget()
        return None
        
    def getCurrentModel( self ):
        """Returns the level model of the active MDI window."""
        window = self.mdiArea.activeSubWindow()
        if window:
            return window.widget().getModel()
        return None

        #@DaB - New save routines to save ONLY the current Level

    def saveCurrent(self):
       if self._game_model:
            model = self.getCurrentModel()
            if model is not None:
                if model.isReadOnly:
                    if model.is_dirty:
                        QtGui.QMessageBox.warning(self, self.tr("Can not save World Of Goo standard balls!"),
                              self.tr('You can not save changes made to balls that come with World Of Goo.\n'
                                      'Instead, clone the ball using the "Clone selected ball" tool.\n'
                                      'Do so now, or your change will be lost once you quit the editor' ) )
                        return False
                    return True
                else:
                    #Check for issues
                    try:
                        model.saveModifiedElements()
                        self.statusBar().showMessage(self.tr("Saved " + model.name), 2000)
                        return True
                    except (IOError,OSError), e:
                        QtGui.QMessageBox.warning(self, self.tr("Failed saving levels"), unicode(e))

       return False

    def saveIT(self):
       if self.saveCurrent():
         QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)
         model = self.getCurrentModel()
         issue_level = model.hasIssues()
         QtGui.QApplication.restoreOverrideCursor()
         if issue_level>=ISSUE_LEVEL_WARNING:
            txtIssue = self.tr("""<p>There are unresolved issues with this ball that may cause problems.<br>
                                    You should fix these before you try to play or make goomod.</p>""")
            txtIssue = txtIssue + self.tr(model.getIssues())
            txtIssue = txtIssue + self.tr( '<br>The ball has been saved!')
            QtGui.QMessageBox.warning(self, self.tr("This ball has issues!"),
                  txtIssue )
    
    def saveAndPlayLevel(self):
        #select level to play
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = editleveldialog.Ui_EditLevelDialog()
            ui.setupUi( dialog, set(self._game_model.level_names), set(metawog.LEVELS_ORIGINAL ))

            if self._last_level_name != '':
                if self._last_level_name in self._game_model.level_names:
                    items = ui.levelList.findItems(self._last_level_name,Qt.MatchExactly)
                    if items:
                        ui.levelList.setCurrentItem(items[0])

            if dialog.exec_() and ui.levelList.currentItem():
                settings = QtCore.QSettings()
                settings.beginGroup( "MainWindow" )
                settings.setValue( "level_filter", ui.comboBox.currentIndex())
                settings.endGroup( )
                level_name = unicode( ui.levelList.currentItem().text() )
                self._last_level_name = level_name
                self._saveAndPlay(level_name)


    def saveAndPlayTC1(self):
        self._saveAndPlay(APP_NAME_PROPER,nballs=1,visual_debug=self.playTCVisualDebug.isChecked())

    def saveAndPlayTC10(self):
        self._saveAndPlay(APP_NAME_PROPER,nballs=10,visual_debug=self.playTCVisualDebug.isChecked())

    def saveAndPlayTC100(self):
        self._saveAndPlay(APP_NAME_PROPER,nballs=100,visual_debug=self.playTCVisualDebug.isChecked())

    def _saveAndPlay(self,level_name,nballs=100, visual_debug=False):
	#@DaB only save current level, and don't "play" if it has "Issues"
        if self.saveCurrent(): #returns false if there are issues
            model = self.getCurrentModel()
            if model:
                QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)
                issue_level = model.hasIssues()
                QtGui.QApplication.restoreOverrideCursor()

                if issue_level>=ISSUE_LEVEL_CRITICAL:
                    txtIssue = self.tr("""<p>There are CRITICAL issues with this ball that will cause World of Goo to crash.<br>
                                       You must fix these before you try to play.</p>""")
                    txtIssue = txtIssue + self.tr(model.getIssues())
                    txtIssue = txtIssue + self.tr( '<br>The ball has been saved!')
                    QtGui.QMessageBox.warning(self, self.tr("This ball has CRITICAL issues!"),
                          txtIssue )
                elif issue_level>ISSUE_LEVEL_NONE:
                    txtIssue = self.tr("""<p>There are Advice/Warnings for this ball that may cause problems.<br>
                               			You should fix these before you try to play with it.</p>""")
                    txtIssue = txtIssue + self.tr(model.getIssues())
                    txtIssue = txtIssue + self.tr( '<br>Click OK to Play anyway, or click Cancel to go back.')
                    ret = QtGui.QMessageBox.warning(self, self.tr("This ball has warnings!"),
                        txtIssue,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret==QtGui.QMessageBox.Ok:
                        self._game_model.playLevel( model.name, level_name, nballs , visual_debug)
                else:
                    self._game_model.playLevel( model.name, level_name, nballs, visual_debug )
            elif level_name==APP_NAME_PROPER:
                self.statusBar().showMessage(self.tr("You must select a ball to play with"), 2000)

    def makegoomod(self):
      if self.saveCurrent(): #returns false if it failed
        if self._game_model:
            model = self.getCurrentModel()
            if model is not None:
                self.statusBar().showMessage(self.tr("Checking for Issues : " + model.name), 2000)
                QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)
                issue_level = model.hasIssues()
                QtGui.QApplication.restoreOverrideCursor()

                if issue_level==ISSUE_LEVEL_ADVICE:
                    txtIssue = self.tr("""<p>There are Advice issues for this ball.<br>
                               You should probably fix these before you upload the goomod</p>""")
                    txtIssue = txtIssue + self.tr(model.getIssues())
                    txtIssue = txtIssue + self.tr( '<br>Click OK to make the goomod anyway, or click Cancel to go back.')
                    ret = QtGui.QMessageBox.warning(self, self.tr("This ball has advice!"),
                        txtIssue,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret==QtGui.QMessageBox.Cancel:
                        return False
                elif issue_level>=ISSUE_LEVEL_WARNING:
                        txtIssue = self.tr("""<p>There are unresolved issues with this ball.<br>
                                           You must fix these before you can produce a .goomod</p>""")
                        txtIssue = txtIssue + self.tr(model.getIssues())
                        QtGui.QMessageBox.warning(self, self.tr("This ball has issues!"), txtIssue )
                        return False

                if model.hasAddinIssues():
                        txtIssue = self.tr("""<p>There are unresolved issues with the Addin info.<br>
                                           You must fix these before you can produce a .goomod</p>""")
                        txtIssue = txtIssue + self.tr(model.getAddinIssues())
                        QtGui.QMessageBox.warning(self, self.tr("This ball has Addin issues!"), txtIssue )
                        return False

                include_all_dep = False
                if model.hasDependancies():
                    # level has some dependancies (might just be custom gfx or Sounds
                    if model.hasdependancy_issue():
                        # has more deps than just GFX or Sound (Balls or Materials or Particles)
                        if model._dependancy_issue_level>ISSUE_LEVEL_ADVICE:
                            #Theres a problem and we can't build the goomod
                            txtIssue = self.tr("""<p>You must fix these before you can produce a .goomod</p>""")
                            txtIssue+= model.dependancy_issue_report
                            QtGui.QMessageBox.warning(self, self.tr("This ball has dependancy issues!"), txtIssue )
                            return False
                        else:
                            #There's no "problem" we need just to ask if they want to localize all
                            txtIssue = self.tr("""<p>This ball depends on several custom resources.</p>""")
                            txtIssue+= model.dependancy_issue_report
                            txtIssue+= self.tr('<br>Would you like to include ALL these resources in the goomod?')
                            ret = QtGui.QMessageBox.warning(self, self.tr("This ball has dependancies!"),
                                txtIssue,QtGui.QMessageBox.Yes|QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel )
                            if ret==QtGui.QMessageBox.Cancel:
                                return False
                            elif ret==QtGui.QMessageBox.Yes:
                                include_all_dep = True

                #maybe actually think about doing it!
                #ask here instead?
                dir = os.path.normpath(os.path.join( os.path.split( self._wog_path )[0],'res', STR_DIR_STUB, model.name ))
                goomod_dir = os.path.join(dir,u'goomod')
                if not os.path.isdir( goomod_dir ):
                    os.mkdir( goomod_dir )
                id_element = model.addin_root.find('id')

                if self._goomod_path=='':
                    goomod_filename = os.path.join(goomod_dir,id_element.text) + ".goomod"
                else:
                    goomod_filename = os.path.join(self._goomod_path,id_element.text) + ".goomod"

                filename = QtGui.QFileDialog.getSaveFileName(self, self.tr("Save goomod File"),
                        goomod_filename,
                        self.tr("goomod (*.goomod)"));
                if filename!='':
                    self.statusBar().showMessage(self.tr("Creating goomod : " + model.name), 2000)

                    filename = os.path.normpath(str(filename))
                    if filename[:len(dir)] == dir:
                        self._goomod_path = u''
                    else:
                        self._goomod_path = os.path.split(filename)[0]
                    self._game_model.creategoomod(model.name,filename,include_deps = include_all_dep)
                    self.statusBar().showMessage(self.tr("goomod Created: " + filename), 2000)

      return False
        
    def newBall( self ):
        """Creates a new blank ball."""
        new_name = self._pickNewBallName( is_cloning = False )
        if new_name:
            try:
                self._game_model.newBall( new_name )
                world = self._game_model.selectBall( new_name )
                self._addGraphicView( world )
            except (IOError,OSError), e:
                QtGui.QMessageBox.warning(self, self.tr("Failed to create the new ball!"),
                                          unicode(e))

    def _pickNewBallName( self, is_cloning = False ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = newleveldialog_ui.Ui_NewLevelDialog()
            ui.setupUi( dialog )
            reg_ex = QtCore.QRegExp( '[A-Za-z][0-9A-Za-z_][0-9A-Za-z_]+' )
            validator = QtGui.QRegExpValidator( reg_ex, dialog )
            ui.levelName.setValidator( validator )
            if is_cloning:
                dialog.setWindowTitle(tr("NewLevelDialog", "Clone this Ball"))
     
            if dialog.exec_():
                new_name = str(ui.levelName.text())
                if new_name.lower() not in [name.lower() for name in metaworld.BALL_NAMES]:
                    return new_name
                QtGui.QMessageBox.warning(self, self.tr("Cannot create ball!"),
                    self.tr("There is already a ball named '%1'").arg(new_name))
        return None

    def cloneBall( self ):
        """Clone the selected ball."""
        current_model = self.getCurrentModel()
        if current_model:
            new_name = self._pickNewBallName( is_cloning = True )
            if new_name:
                try:
                    self._game_model.cloneBall( current_model.name, new_name )
                    world = self._game_model.selectBall( new_name )
                    self._addGraphicView( world )
                    self._setRecentFile( new_name )
                except (IOError,OSError), e:
                    QtGui.QMessageBox.warning(self, self.tr("Failed to create the new cloned ball!"),unicode(e))

                                              

    def updateResources( self ):
        """Adds any resource in the ball folder into the resource tree ."""
        model = self.getCurrentModel()
        if model:
            added_resource_elements = model.updateResources()
            if added_resource_elements:
                model.set_selection( added_resource_elements )
            model.game_model.pixmap_cache.refresh()
            model._view.refreshFromModel()
            ie = model.importError()
            if ie[0] is not None:
                QtGui.QMessageBox.warning(self, self.tr(ie[0]), self.tr(ie[1] ) )

    def cleanResources(self):
        model = self.getCurrentModel()
        noproblems = True
        if model:
            unused = model._get_unused_resources()
            unusedlist = ''
            for family,unusedset in unused.items():
                for id in unusedset:
                    unusedlist+=id+'\n'
            if unusedlist!='':
                unusedlist="The following resources are unused\n"+unusedlist+"\nAre you sure you want to remove them?"
                ret = QtGui.QMessageBox.warning(self, self.tr("Remove unused resources"),
                        unusedlist,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                if ret==QtGui.QMessageBox.Ok:
                    model._remove_unused_resources(unused)
                noproblems = False
            
            clonedfiles = model.checkClonedFiles()
            if clonedfiles is not None:
                    txtIssue = self.tr("""<p>This ball uses renamed / moved copies of original World of Goo files.<br>
                                        WooBLE will not include the following files in a goomod.</p>
                                        <p>%s</p>
                                        <p>If you want WooBLE to automatically fix this, click OK<br>Otherwise click Cancel</p>"""
                                        % self.tr("<br>".join(clonedfiles.keys())) )
                    ret = QtGui.QMessageBox.warning(self, self.tr("Clean Resources"),
                        txtIssue,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret==QtGui.QMessageBox.Ok:
                        model.fixClonedFiles(clonedfiles)
                    noproblems = False

            if noproblems:
                 QtGui.QMessageBox.warning(self, self.tr("Clean Resources"),
                        self.tr("No problems were found!\n") )

    def importResources( self ):
        """Adds the required resource in the level based on existing file."""
        model = self.getCurrentModel()
        if model:
            #game_dir = os.path.normpath( os.path.split( self._wog_path )[0] )
            #res_dir =  os.path.join( game_dir, 'res' )
            dir = os.path.join( self._game_model._res_dir, STR_DIR_STUB )
            files =  QtGui.QFileDialog.getOpenFileNames( self,
                        self.tr( 'Select the Images or Sounds to import...' ),
                        dir,
                        self.tr( 'Resources (*.png *.ogg)' ) )

            if files.isEmpty(): # user canceled action
                return
            safefiles = []
            for file in files:
                safefiles.append( os.path.normpath(str(file)))

            added_resource_elements = model.importResources(safefiles)
            if added_resource_elements:
                model.set_selection( added_resource_elements )
                model.game_model.pixmap_cache.refresh()
                model._view.refreshFromModel()

            ie = model.importError()
            if ie[0] is not None:
               QtGui.QMessageBox.warning(self, self.tr(ie[0]), self.tr(ie[1] ) )

    def about(self):
        QtGui.QMessageBox.about(self, self.tr("About World of Goo Ball Editor " + CURRENT_VERSION),
            self.tr("""<p>World of Goo Ball Editor <b>(WooBLE)</b> helps you create new Goo Balls<p>
            <p>Download Page:<br>
            <a href="http://goofans.com/download/utility/world-of-goo-ball-editor">http://goofans.com/download/utility/world-of-goo-ball-editor</a></p>
            <p>FAQ and Tutorial : TBA<br>
            <a href="http://goofans.com/developers/game-file-formats/balls-xml">Reference Guide</a></p>
            <p>Copyright 2010-, DaftasBrush</p>
            <p>&nbsp;<br>Based (very loosely now) on the WoGEdit Sourceforge project: (v0.5)
            <a href="http://www.sourceforge.net/projects/wogedit">http://www.sourceforge.net/projects/wogedit</a><br>
            Copyright 2008-2009, NitroZark &lt;nitrozark at users.sourceforget.net&gt;</p>"""))

    def on_cut_action(self):
        elements = self.on_copy_action( is_cut_action=True )
        if elements:
            for element in elements:
                if element.meta.read_only:
                    #Messagebox
                    QtGui.QMessageBox.warning(self, self.tr("Cannot Cut read only element!"),
                              self.tr('This element is read only.\n'
                                      'It cannot be cut' ) )                    
                    return
            self.on_delete_action( is_cut_action=True )
            self.statusBar().showMessage( 
                self.tr('Element "%s" cut to clipboard' % 
                        elements[0].tag), 1000 )

    def on_copy_action(self, is_cut_action = False):
        world = self.getCurrentModel()
        if world:
            elements = list(world.selected_elements)
            if len(elements) == 1:
                on_clipboard = elements[0].tag
                self.common_actions['paste'].setText("Paste ("+on_clipboard+")")
                xml_data = elements[0].to_xml_with_meta()
                clipboard = QtGui.QApplication.clipboard()
                clipboard.setText( xml_data )
                if not is_cut_action:
                    self.statusBar().showMessage( 
                        self.tr('Element "%s" copied to clipboard' % 
                                elements[0].tag), 1000 )
                return elements
    def _getPositionAttribute(self,element):
        for attribute_meta in element.meta.attributes:
            if attribute_meta.type == metaworld.XY_TYPE:
                if attribute_meta.position:
                    return attribute_meta
        return None
    
    def _getImageposAttribute(self,element):
        image= element.get('image',None)
        if image is None:
            return None
        for attribute_meta in element.meta.attributes:
            if attribute_meta.type == metaworld.XY_TYPE:
                if attribute_meta.name=="imagepos":
                    return attribute_meta
        return None

    def on_paste_action(self):
        clipboard = QtGui.QApplication.clipboard()
        xml_data = unicode(clipboard.text())
        world = self.getCurrentModel()
        if world is None or not xml_data:
            return
        elements = list(world.selected_elements)
        if len(elements) == 0: # Allow pasting to root when no selection
            elements = [tree.root for tree in world.trees]
        # Try to paste in one of the selected elements. Stop when succeed
        for element in elements:
            while element is not None:
                child_elements = element.make_detached_child_from_xml( xml_data )
                if child_elements:
                    for child_element in child_elements:
                        element.safe_identifier_insert( len(element), child_element )
                    element.world.set_selection( child_elements[0] )
                    break
                element = element.parent

    def on_undo_action(self):
        world = self.getCurrentModel()
        if world is None:
            return
        world.undo()

    def on_redo_action(self):
        world = self.getCurrentModel()
        if world is None:
            return
        world.redo()


    def on_delete_action(self, is_cut_action = False):
        world = self.getCurrentModel()
        if world is None:
            return
        deleted_elements = []
        for element in  list(world.selected_elements):
            if element.meta.read_only:
                #messagebox
                QtGui.QMessageBox.warning(self, self.tr("Cannot delete read only element!"),
                              self.tr('This element is read only.\n'
                                      'It cannot be deleted' ) )

                return 0
            elif not element.is_root():
                deleted_elements.append( element.previous_element() )
                element.parent.remove( element )
                
        if is_cut_action:
            return len(deleted_elements)
        if deleted_elements:
            self.statusBar().showMessage( 
                self.tr('Deleted %d element(s)' % len(deleted_elements)), 1000 )
            world.set_selection( deleted_elements[0] )


    def _on_view_tool_actived( self, tool_name ):
        active_view = self.get_active_view()
        if active_view is not None:
            active_view.tool_activated( tool_name )

    def on_select_tool_action(self):
        self._on_view_tool_actived( ballview.TOOL_SELECT )

    def on_pan_tool_action(self):
        self._on_view_tool_actived( ballview.TOOL_PAN )

    def on_move_tool_action(self):
        self._on_view_tool_actived( ballview.TOOL_MOVE )

    def onRefreshAction( self ):
        """Called multiple time per second. Used to refresh enabled flags of actions."""
        has_wog_dir = self._game_model is not None
        #@DaB - Now that save and "save and play" only act on the
		# current level it's better if that toolbars buttons
 		# change state based on the current level, rather than all levels
	currentModel = self.getCurrentModel()
        is_selected = currentModel is not None
        can_select = is_selected and self.view_actions[ballview.TOOL_MOVE].isChecked()

        if is_selected:
            can_save = has_wog_dir and currentModel.is_dirty
            element_is_selected = can_select and len(currentModel.selected_elements)>0
            can_import = is_selected and not currentModel.isReadOnly
            can_undo = currentModel.can_undo
            can_redo = currentModel.can_redo
            if currentModel.is_dirty:
                if currentModel.isReadOnly:
                    self.mdiArea.activeSubWindow().setWindowIcon(  QtGui.QIcon ( ':/images/nosave.png' ) )
                else:
                    self.mdiArea.activeSubWindow().setWindowIcon(  QtGui.QIcon ( ':/images/dirty.png' ) )
            else:
                self.mdiArea.activeSubWindow().setWindowIcon(  QtGui.QIcon ( ':/images/clean.png' ) )
        else:
            can_save = False
            element_is_selected = False
            can_import = False
            can_undo = False
            can_redo = False

        self.newBallAction.setEnabled( has_wog_dir )
        self.editBallAction.setEnabled( has_wog_dir )
        self.cloneBallAction.setEnabled( is_selected )
        self.saveAction.setEnabled( can_save and True or False )
        self.playTC1Action.setEnabled( is_selected )
        self.playTC10Action.setEnabled( is_selected )
        self.playTC100Action.setEnabled( is_selected )
        self.playTCVisualDebug.setEnabled( is_selected )
        self.playLevelAction.setEnabled( is_selected )
        self.goomodAction.setEnabled (can_import)

        #Edit Menu / ToolBar

        self.common_actions['cut'].setEnabled (element_is_selected)
        self.common_actions['copy'].setEnabled (element_is_selected)
        self.common_actions['paste'].setEnabled (is_selected)
        self.common_actions['delete'].setEnabled (element_is_selected)
        self.undoAction.setEnabled (can_undo)
        self.redoAction.setEnabled (can_redo)

        #Resources
        self.importResourcesAction.setEnabled (can_import  )
        self.cleanResourcesAction.setEnabled (can_import  )
        self.updateLevelResourcesAction.setEnabled( can_import )

        self.addItemToolBar.setEnabled( can_select )

        #self.showhideToolBar.setEnabled( is_selected )
        for action in self.showhide_actions.values():
            action.setEnabled( is_selected )

        for action in self.bgcolour_actions.values():
            action.setEnabled( is_selected )

        active_view = self.get_active_view()
        enabled_view_tools = set()
        if active_view:
            enabled_view_tools = active_view.get_enabled_view_tools()
        for name, action in self.view_actions.iteritems():
            is_enabled = name in enabled_view_tools
            action.setEnabled( is_enabled )
        if self.view_action_group.checkedAction() is None:
            self.view_actions[ballview.TOOL_MOVE].setChecked( True )
        
    def _on_refresh_element_status(self):
        # broadcast the event to all ElementIssueTracker
        louie.send_minimal( metaworldui.RefreshElementIssues )

    def createMDIArea( self ):
        self.mdiArea = QtGui.QMdiArea()
        self.mdiArea.setViewMode(QtGui.QMdiArea.TabbedView)
        for thing in self.mdiArea.findChildren(QtGui.QTabBar):
            thing.setTabsClosable(True)
            self.connect ( thing, QtCore.SIGNAL("tabCloseRequested(int)"), self.on_closeTab )
        self.setCentralWidget(self.mdiArea)

    def on_closeTab(self,index):
        sub = self.mdiArea.subWindowList()[index]
        sub.close()

    def createActions(self):
        self.changeWOGDirAction = qthelper.action( self, handler = self.changeWOGDir,
            icon = ":/images/open.png",
            text = "&Change World of Goo directory...",
            shortcut = QtGui.QKeySequence.Open,
            status_tip = "Change World Of Goo top-directory" )

        self.editBallAction = qthelper.action( self, handler = self.editBall,
            icon = ":/images/icon-wog-level.png",
            text = "&Edit existing Goo Ball...",
            shortcut = "Ctrl+L",
            status_tip = "Select a Goo Ball to edit" )

        self.newBallAction = qthelper.action(self, handler = self.newBall,
            icon = ":/images/icon-wog-new-level2.png",
            text = "&New Goo Ball...",
            shortcut = QtGui.QKeySequence.New,
            status_tip = "Creates a new Goo Ball" )

        self.cloneBallAction = qthelper.action( self, handler = self.cloneBall,
            icon = ":/images/icon-wog-clone-level.png",
            text = "&Clone selected Goo Ball...",
            shortcut = "Ctrl+D",
            status_tip = "Clone the selected Goo Ball" )
        
        self.saveAction = qthelper.action( self, handler = self.saveIT,
            icon = ":/images/save.png",
            text = "&Save...",
            shortcut = QtGui.QKeySequence.Save,
            status_tip = "Saves the Goo Ball" )
        
        self.playTC1Action = qthelper.action( self, handler = self.saveAndPlayTC1,
            icon = ":/images/play1.png",
            text = "&Save and play with 1 Ball...",
            status_tip = "Save and play Test Chamber level" )

        self.playTC10Action = qthelper.action( self, handler = self.saveAndPlayTC10,
            icon = ":/images/play10.png",
            text = "&Save and play with 10 Balls...",
            shortcut = "Ctrl+P",
            status_tip = "Save and play Test Chamber level" )

        self.playTC100Action = qthelper.action( self, handler = self.saveAndPlayTC100,
            icon = ":/images/play100.png",
            text = "&Save and play with 100 Balls...",
            status_tip = "Save and play Test Chamber level" )

        self.playTCVisualDebug = qthelper.action( self, 
            icon = ":/images/vdgoo.png",
            text = "&Play Test Chamber in Visual Debug mode",
            checkable=True,
            status_tip = "Visual Debug Mode" )


        self.playLevelAction = qthelper.action( self, handler = self.saveAndPlayLevel,
            icon = ":/images/play.png",
            text = "&Save and play a level...",
            status_tip = "Save and play a level" )

        self.goomodAction = qthelper.action( self, handler = self.makegoomod,
            icon = ":/images/goomod.png",
            text = "&Make .goomod",
            shortcut = "Ctrl+G",
            status_tip = "Make a .goomod file for this Goo Ball" )


        self.updateLevelResourcesAction = qthelper.action( self,
            handler = self.updateResources,
            icon = ":/images/update-level-resources.png",
            text = "&Update resources...",
            shortcut = "Ctrl+U",
            status_tip = "Adds automatically all .png & .ogg files in the ball directory to the resources" )

        self.cleanResourcesAction = qthelper.action( self,
            handler = self.cleanResources,
            icon = ":/images/cleanres.png",
            text = "&Clean Resources",
            status_tip = "Removes any unused resource from the ball." )

        self.importResourcesAction = qthelper.action( self,
            handler = self.importResources,
            icon = ":/images/importres.png",
            text = "&Import resources...",
            shortcut = "Ctrl+I",
            status_tip = "Adds images and sounds to the resources" )

        self.quitAct = qthelper.action( self, handler = self.close,
            text = "&Quit",
            shortcut = "Ctrl+Q",
            status_tip = "Quit the application" )
        
        self.aboutAct = qthelper.action( self, handler = self.about,
            icon = ":/images/icon.png",
            text = "&About",
            status_tip = "Show the application's About box" )

        self.recentfile_actions = [qthelper.action( self, handler = self.on_recentfile_action, visible=False)
                                    for i in range(0,MAXRECENTFILES)]

        self.common_actions = {
            'cut': qthelper.action( self, handler = self.on_cut_action,
                    icon = ":/images/cut.png",
                    text = "Cu&t", 
                    shortcut = QtGui.QKeySequence.Cut ),
            'copy': qthelper.action( self, handler = self.on_copy_action,
                    icon = ":/images/copy.png",
                    text = "&Copy", 
                    shortcut = QtGui.QKeySequence.Copy ),
            'paste': qthelper.action( self, handler = self.on_paste_action,
                    icon = ":/images/paste.png",
                    text = "&Paste",
                    shortcut ="Ctrl+V" ),

            'delete': qthelper.action( self, handler = self.on_delete_action,
                    icon = ":/images/delete.png",
                    text = "&Delete",
                    shortcut = QtGui.QKeySequence.Delete )

        }
        self.undoAction = qthelper.action( self, handler = self.on_undo_action,
                    icon = ":/images/undo.png",
                    text = "&Undo",
                    shortcut = QtGui.QKeySequence.Undo )

        self.redoAction = qthelper.action( self, handler = self.on_redo_action,
                    icon = ":/images/redo.png",
                    text = "&Redo",
                    shortcut = QtGui.QKeySequence.Redo )


        class ShowHideFactory(object):
                def __init__( self, window, elements ):
                    self.window = window
                    self.elements = elements
                def __call__( self ):
                    ballview = self.window.get_active_view()
                    if ballview is not None:
                        ballview.toggle(self.elements)
                        ballview.refreshFromModel()

        self.showhide_actions = {
            'geom': qthelper.action( self, handler = ShowHideFactory( self ,['geom']),
                    text = "Show/Hide Geometry" ,icon = ":/images/show-ballgeom.png"),
            'strand': qthelper.action( self, handler = ShowHideFactory( self ,['strand']),
                    text = "Show/Hide Strands" ,icon = ":/images/show-strand.png"),
            'marker': qthelper.action( self, handler = ShowHideFactory( self ,['marker']),
                    text = "Show/Hide Markers" ,icon = ":/images/show-marker.png"),
            'shadow': qthelper.action( self, handler = ShowHideFactory( self ,['shadow']),
                    text = "Show/Hide Shadows" ,icon = ":/images/show-shadow.png")

        }

        self.bgcolour_actions = { 'black': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(0,0,0) ), text = "Black", icon=":/images/black.png"),
                'grey75': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(64,64,64) ), text = "75% Grey",icon=":/images/grey64.png"),
                'grey50': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(128,128,128) ), text = "50% Grey",icon=":/images/grey128.png"),
                'grey25': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(192,192,192) ), text = "25% Grey",icon=":/images/grey192.png"),
                'white': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(255,255,255) ), text = "White",icon=":/images/white.png")}

        self.view_action_group = QtGui.QActionGroup(self)
        self.view_actions = { 
            ballview.TOOL_SELECT: qthelper.action( self,
                    handler = self.on_select_tool_action,
                    icon = ":/images/strand.png",
                    text = "&Strand Mode",
                    shortcut = QtGui.QKeySequence( Qt.Key_Space),
                    checkable = True,
                    status_tip = "Click a Goo, hold, move to another Goo and release to connect them." ),
            ballview.TOOL_PAN: qthelper.action( self,
                    handler = self.on_pan_tool_action,
                    icon = ":/images/zoom.png",
                    text = "&Zoom and Pan view (F)",
                    shortcut = 'F',
                    checkable = True ),
            ballview.TOOL_MOVE: qthelper.action( self,
                    handler = self.on_move_tool_action,
                    icon = ":/images/tool-move.png",
                    text = "&Select, Move and Resize",
                    shortcut = 'T',
                    checked = True,
                    checkable = True )
            }

        for action in self.view_actions.itervalues():
            self.view_action_group.addAction( action )
		
        self.additem_actions = {
        'part':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','part',{}),
                    icon = ":/images/part.png",
                    text = "&Add a Part" ),

        'strand':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','strand',{}),
                    icon = ":/images/strand.png",
                    text = "&Add strand" ),

        'detachstrand':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','detachstrand',{}),
                    icon = ":/images/detach.png",
                    text = "&Add detachstrand" ),

        'particles':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','particles',{}),
                    icon = ":/images/particles.png",
                    text = "&Add Particles"),

        'marker':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','marker',{}),
                    icon = ":/images/marker.png",
                    text = "&Add Marker"),

        'shadow':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','shadow',{}),
                    icon = ":/images/shadow.png",
                    text = "&Add Shadow"),

        'splat':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','splat',{}),
                    icon = ":/images/splat.png",
                    text = "&Add Splat"),

        'sin':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','sinvariance',{}),
                    icon = ":/images/sin.png",
                    text = "&Add sine animation"),

        'eventsound':qthelper.action( self,
                    handler = AddItemFactory(self, 'ball','sound',{}),
                    icon = ":/images/update-level-resources.png",
                    text = "&Add Event Sound")

        }

        self.actionTimer = QtCore.QTimer( self )
        self.connect( self.actionTimer, QtCore.SIGNAL("timeout()"), self.onRefreshAction )
        self.actionTimer.start( 250 )    # Refresh action enabled flag every 250ms.

        self.statusTimer = QtCore.QTimer( self )
        self.connect( self.statusTimer, QtCore.SIGNAL("timeout()"),
                      self._on_refresh_element_status )
        self.statusTimer.start( 300 )    # Refresh element status every 300ms.

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.newBallAction)
        self.fileMenu.addAction(self.editBallAction)
        self.fileMenu.addAction(self.cloneBallAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.playTC10Action)
        self.fileMenu.addAction(self.playLevelAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.changeWOGDirAction)
        self.separatorRecent = self.fileMenu.addSeparator()
        for recentaction in self.recentfile_actions:
            self.fileMenu.addAction(recentaction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAct)
        
        self.editMenu = self.menuBar().addMenu(self.tr("&Edit"))
        self.editMenu.addAction( self.undoAction)
        self.editMenu.addAction( self.redoAction)
        self.editMenu.addSeparator()
        self.editMenu.addAction( self.common_actions['cut'] )
        self.editMenu.addAction( self.common_actions['copy'] )
        self.editMenu.addAction( self.common_actions['paste'] )
        self.editMenu.addSeparator()
        self.editMenu.addAction( self.common_actions['delete'] )
        
        self.menuBar().addSeparator()
        self.resourceMenu = self.menuBar().addMenu(self.tr("&Resources"))
        self.resourceMenu.addAction( self.updateLevelResourcesAction )
        self.resourceMenu.addAction( self.importResourcesAction )
        self.resourceMenu.addSeparator()
        self.resourceMenu.addAction( self.cleanResourcesAction )

        self.menuBar().addSeparator()

        # @todo add Windows menu. Take MDI example as model.                
        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.aboutAct)

    def createToolBars(self):
        self.fileToolBar = self.addToolBar(self.tr("File"))
        self.fileToolBar.setObjectName("fileToolbar")
       # self.fileToolBar.addAction(self.changeWOGDirAction)
        self.fileToolBar.addAction(self.newBallAction)
        self.fileToolBar.addAction(self.editBallAction)
        self.fileToolBar.addAction(self.cloneBallAction)
        self.fileToolBar.addSeparator()
        self.fileToolBar.addAction(self.saveAction)
        self.fileToolBar.addAction(self.playTC1Action)
        self.fileToolBar.addAction(self.playTC10Action)
        self.fileToolBar.addAction(self.playTC100Action)
        self.fileToolBar.addAction(self.playTCVisualDebug)
        self.fileToolBar.addAction(self.playLevelAction)
        self.fileToolBar.addSeparator()
        self.fileToolBar.addAction(self.goomodAction)

        self.editToolbar = self.addToolBar(self.tr("Edit"))
        self.editToolbar.setObjectName("editToolbar")
        self.editToolbar.addAction( self.undoAction)
        self.editToolbar.addAction( self.redoAction)
        self.editToolbar.addSeparator()
        self.editToolbar.addAction( self.common_actions['cut'] )
        self.editToolbar.addAction( self.common_actions['copy'] )
        self.editToolbar.addAction( self.common_actions['paste'] )
        self.editToolbar.addSeparator()
        self.editToolbar.addAction( self.common_actions['delete'] )

        self.resourceToolBar = self.addToolBar(self.tr("Resources"))
        self.resourceToolBar.setObjectName("resourceToolbar")
        self.resourceToolBar.addAction( self.updateLevelResourcesAction )
        self.resourceToolBar.addAction( self.importResourcesAction )
        self.resourceToolBar.addSeparator()
        self.resourceToolBar.addAction( self.cleanResourcesAction )


        self.ballViewToolBar = self.addToolBar(self.tr("Ball View"))
        self.ballViewToolBar.setObjectName("ballViewToolbar")

        for name in ('move', 'pan'):
            action = self.view_actions[name]
            self.ballViewToolBar.addAction( action )

        self.bgcolourToolBar = self.addToolBar(self.tr("Background Colour"))
        self.bgcolourToolBar.setObjectName("bgcolourToolbar")

        for key in ['white','grey25','grey50','grey75','black']:
            self.bgcolourToolBar.addAction( self.bgcolour_actions[key])

        self.showhideToolBar = self.addToolBar(self.tr("Show/Hide"))
        self.showhideToolBar.setObjectName("showhideToolbar")
        for action in ('geom','strand','marker','shadow'):
            self.showhideToolBar.addAction( self.showhide_actions[action] )
            

        self.addItemToolBar = QtGui.QToolBar(self.tr("Add Item"))
        self.addItemToolBar.setObjectName("addItemToolbar")
        self.addToolBar(Qt.LeftToolBarArea, self.addItemToolBar)

        additem_action_list=['part',
                             'strand','detachstrand',
                             'particles',
                             'marker','shadow','splat',
                             'sin','eventsound'
                            ]

        for name in additem_action_list:
            if name not in self.additem_actions:
                self.addItemToolBar.addSeparator()
            else:
                self.addItemToolBar.addAction( self.additem_actions[name] )
            
    

    def createStatusBar(self):
        self.statusBar().showMessage(self.tr("Ready"))
        self._mousePositionLabel = QtGui.QLabel()
        self.statusBar().addPermanentWidget( self._mousePositionLabel )

    def createElementTreeView(self, name, tree_meta, sibling_tabbed_dock = None ):
        dock = QtGui.QDockWidget( self.tr( name ), self )
        dock.setObjectName(name+'_tab')
        dock.setAllowedAreas( Qt.RightDockWidgetArea )
        element_tree_view = metatreeui.MetaWorldTreeView( self.common_actions,self.group_icons, dock  )
        tree_model = metatreeui.MetaWorldTreeModel( tree_meta, self.group_icons,
                                                    element_tree_view )
        element_tree_view.setModel( tree_model )
        dock.setWidget( element_tree_view )
        self.addDockWidget( Qt.RightDockWidgetArea, dock )
        if sibling_tabbed_dock: # Stacks the dock widget together
            self.tabifyDockWidget( sibling_tabbed_dock, dock )
        dock.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        self.tree_view_by_element_world[tree_meta] = element_tree_view
        return dock, element_tree_view
        
    def createDockWindows(self):
        self.group_icons = {}
        for group in 'game image resource info ball particles strand goomod material sin part marker splat shadow detach'.split():
            self.group_icons[group] = QtGui.QIcon( ":/images/group-%s.png" % group )
        self.tree_view_by_element_world = {} # map of all tree views
        ball_dock, self.ballTree = self.createElementTreeView( 'Ball', metawog.TREE_BALL_MAIN )
        resource_dock, self.ballResourceTree = self.createElementTreeView( 'Resource',
                                                                            metawog.TREE_BALL_RESOURCE,
                                                                            ball_dock )
        addin_dock, self.addinTree = self.createElementTreeView( 'Addin',
                                                                            metawog.TREE_BALL_ADDIN,
                                                                            resource_dock )
        dep_dock, self.depTree = self.createElementTreeView( 'Depends',
                                                                            metawog.TREE_BALL_DEPENDANCY,
                                                                            addin_dock )

        ball_dock.raise_() # Makes the ball the default active tab
        
        dock = QtGui.QDockWidget(self.tr("Properties"), self)
        dock.setAllowedAreas( Qt.RightDockWidgetArea )
        dock.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        dock.setObjectName('properties')

        self.propertiesList = metaelementui.MetaWorldPropertyListView( self.statusBar(),
                                                                       dock )

        self.propertiesListModel = metaelementui.MetaWorldPropertyListModel(0, 2, 
            self.propertiesList)  # nb rows, nb cols
        self.propertiesList.setModel( self.propertiesListModel )
        dock.setWidget(self.propertiesList)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _readSettings( self ):
        """Reads setting from previous session & restore window state."""
        settings = QtCore.QSettings()
        settings.beginGroup( "MainWindow" )
        self._wog_path = unicode( settings.value( "wog_path", QtCore.QVariant(u'') ).toString() )
        if self._wog_path==u'.':
            self._wog_path=u''
        elif self._wog_path!=u'':
            self._wog_path=os.path.normpath(self._wog_path)
        self._goomod_path = unicode( settings.value( "goomod_path", QtCore.QVariant(u'') ).toString() )
        if self._goomod_path==u'.':
            self._goomod_path=u''
        elif self._goomod_path!=u'':
            self._goomod_path=os.path.normpath(self._goomod_path)

        self._last_level_name = settings.value( "last_level_name", QtCore.QVariant(u'') ).toString()
        self.playTCVisualDebug.setChecked( settings.value( "visual_debug", QtCore.QVariant(False) ).toBool() )
        if settings.value( "wasMaximized", False ).toBool():
            self.showMaximized()
        else:
            self.resize( settings.value( "size", QtCore.QVariant( QtCore.QSize(640,480) ) ).toSize() )
            self.move( settings.value( "pos", QtCore.QVariant( QtCore.QPoint(200,200) ) ).toPoint() )
        windowstate = settings.value("windowState",None);
        if windowstate is not None:
           self.restoreState(windowstate.toByteArray())

        self.recentFiles = settings.value( "recent_files" ).toStringList()
        self._updateRecentFiles()
        settings.endGroup()

    def _writeSettings( self ):
        """Persists the session window state for future restoration."""
        # Settings should be stored in HKEY_CURRENT_USER\Software\WOGCorp\WooBLE
        settings = QtCore.QSettings() #@todo makes helper to avoid QVariant conversions
        settings.beginGroup( "MainWindow" )
        settings.setValue( "wog_path", QtCore.QVariant( QtCore.QString(self._wog_path or u'') ) )
        settings.setValue( "goomod_path", QtCore.QVariant( QtCore.QString(self._goomod_path or u'') ) )
        settings.setValue( "last_level_name", QtCore.QVariant( QtCore.QString(self._last_level_name or u'') ) )
        settings.setValue( "visual_debug", QtCore.QVariant(self.playTCVisualDebug.isChecked()) )
        settings.setValue( "wasMaximized",QtCore.QVariant( self.isMaximized()))
        settings.setValue( "size", QtCore.QVariant( self.size() ) )
        settings.setValue( "pos", QtCore.QVariant( self.pos() ) )
        settings.setValue("windowState", self.saveState())
        settings.setValue("recent_files",self.recentFiles)
        settings.endGroup()
       
    def closeEvent( self, event ):
        """Called when user close the main window."""
        #@todo check if user really want to quit

        for subwin in self.mdiArea.subWindowList():
            if not subwin.close():
                event.ignore()
                return
            
        self._writeSettings()
        self.actionTimer.stop
        self.statusTimer.stop
        QtGui.QMainWindow.closeEvent(self,event)
        event.accept()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    # Set keys for settings
    app.setOrganizationName( "WOGCorp" )
    app.setOrganizationDomain( "goofans.com" )
    app.setApplicationName( "WooBLE" )

    if LOG_TO_FILE:
        saveout = sys.stdout
        saveerr = sys.stderr
        fout = open(APP_NAME_LOWER+'.log', 'a')
        sys.stdout = fout
        sys.stderr = fout
        print ""
        print "------------------------------------------------------"
        print APP_NAME_PROPER+" started ",datetime.now(), "File Logging Enabled"

    mainwindow = MainWindow()
    mainwindow.show()
    appex = app.exec_()

    if LOG_TO_FILE:
        sys.stdout = saveout
        sys.stderr = saveerr
        fout.close()
    
    sys.exit(appex)