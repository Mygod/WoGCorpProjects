# The Goo Movie GUI.
# The following workflow is expected:
# 1) User load a movie
# 2) main windows display the scene layout
#    right-side-top-dock display:
#   - movie tree
#   - level resources tree (a list in fact)
# 3) user select an element in one of the tree, related properties are displayed in
#    right-side-down-dock property list
# 4) user edit properties in property list
#
# Later on, provides property edition via scene layout display
# Add toolbar to create new element
#
# In memory, we keep track of two things:

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
import movview
from shutil import copy2
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import qthelper
import editleveldialog_ui
import newleveldialog_ui
import goomov_rc #IGNORE:W0611
import shutil
import zipfile
import errors
import movie_binltl
import time
import hashlib
from datetime import datetime
LOG_TO_FILE = False
APP_NAME_UPPER = 'GOOVIE MAKER'
APP_NAME_LOWER = 'goovie maker'
APP_NAME_PROPER = 'Goovie Maker'
STR_DIR_STUB='movie'
CURRENT_VERSION = "v0.06 Beta"
CREATED_BY = '<!-- Created by ' + APP_NAME_PROPER + ' ' + CURRENT_VERSION + ' -->\n'
ISSUE_LEVEL_NONE = 0
ISSUE_LEVEL_ADVICE = 1
ISSUE_LEVEL_WARNING = 2
ISSUE_LEVEL_CRITICAL =4
PLATFORM_WIN=0
PLATFORM_LINUX=1
PLATFORM_MAC=2
MAXRECENTFILES=4
#print "platform=",sys.platform
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

def _insertChildTag( parent_element, new_element_meta , mandatory_attributes, insert_attribute ):
                    """Adds the specified child tag to the specified element and update the tree view."""

                    assert parent_element is not None
                    # build the list of attributes with their initial values.
                    for attribute_meta in new_element_meta.attributes:
                        if attribute_meta.mandatory:
                          if attribute_meta.type == metaworld.IDENTIFIER_TYPE:
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
                    matchvalue = float(mandatory_attributes[insert_attribute])
                    insert_at = None
                    for i,element in enumerate(parent_element):
                        value = element.get_native(insert_attribute)
                        if value is not None:
                            if value>matchvalue:
                                insert_at = i
                                break
                    child_element = parent_element.make_child( new_element_meta,
                                                               mandatory_attributes ,insert_index = insert_at)
                    # Select new item in tree view
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
                            attrib = self.attrib.copy()
                            if self.parent=='movie':
                               root = model.movie_root
                            elif self.parent=='resource':
                                root = model.resource_root
                            elif self.parent=='addin':
                                root = model.addin_root
                            elif self.parent=='text':
                                root = model.text_root
                            elif self.parent=='actor':
                                selected_elements=model.selected_elements
                                cgparent = None
                                #print selected_elements
                                for element in selected_elements:
                                    if element.tag== 'actor':
                                        cgparent = element
                                        break
                                    elif element.tag=='keyframe':
                                        # check to see if they are part of a cg
                                        pelement = element.parent
                                        if pelement is not None:
                                            if pelement.tag=='actor':
                                                cgparent = pelement
                                                break
                                if cgparent is None:
                                    QtGui.QMessageBox.warning(self.window,'No actor selected','You must select an actor to add this keyframe to')
                                    return
                                root = cgparent
                                # now the interesting bit
                                # check the current time in the view, if after the last child add blank on end
                                # if between 2 frames... tween if interpolation is linear
                                # set up attribs for new frame
                                # get current time
                                time = model.view.time
                                #print time
                                maxframetime = 0
                                maxframe = None
                                frametimes = []
                                for keyframe in root:
                                    ftime = keyframe.get_native('time')
                                    frametimes.append(ftime)
                                    if ftime > maxframetime:
                                        maxframetime = ftime
                                        maxframe = keyframe
                                addattime = time
                                #print time,frametimes
                                if time in frametimes:
                                #    print "add at existing : +1 frame ", 1/model.view.fps
                                    addattime += 1/model.view.fps
                                if len(frametimes)==0:
                                    # first frame to be added... set defaults
                                   attrib['position'] = '0,0'
                                   attrib['angle'] = '0'
                                   attrib['scale'] = '1,1'
                                   attrib['alpha'] = '255'
                                   attrib['time']= '0'
                                elif addattime < maxframetime:
                                   x,y = movview._interpolateValues(root,'position',(None,None),addattime)
                                   angle = movview._interpolateValue(root,'angle',None,addattime)
                                   scalex,scaley = movview._interpolateValues(root,'scale',(None,None),addattime)
                                   alpha= movview._interpolateValue(root,'alpha',None,addattime)


                                   if x is not None and y is not None:
                                        attrib['position'] = ','.join([str(x),str(y)])
                                   if angle is not None:
                                        attrib['angle'] = str(angle)
                                   if scalex is not None and scaley is not None:
                                        attrib['scale'] = ','.join([str(scalex),str(scaley)])
                                   if alpha is not None:
                                        attrib['alpha'] = str(int(alpha))
                                   attrib['time']=str(addattime)
                                   kf = model.view._getPreviousKeyFrame(root,addattime)
                                   if kf is not None:
                                #       print "previous kf:",kf, " at ",kf.get('time')
                                       value = kf.get('interpolation',None)
                                       if value is not None:
                                            attrib['interpolation'] = value
                                #else no aditional attributs add a blank frame
                                   rootmbt = root.meta.find_immediate_child_by_tag(self.itemtag)
                                   if rootmbt is not None:
                                        _insertChildTag(root,rootmbt,attrib,'time')
                                   return
                                else:
                                   attrib['time']=str(addattime)

                            else:
                                print "Unknown Parent in AddItemFactory", self.parent
                            rootmbt = root.meta.find_immediate_child_by_tag(self.itemtag)
                            if rootmbt is not None:
                                _appendChildTag(root,rootmbt,attrib)

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

        self._loadUnPackedTree( self.global_world, metawog.TREE_GLOBAL_FILES,
                                               app_path(), 'files.%s.xml' % PLATFORM_STRING[ON_PLATFORM] ,'')
        self._processOriginalFiles()
    
	self._loadTree( self.global_world, metawog.TREE_GLOBAL_RESOURCE,
                                               self._properties_dir, 'resources.xml.bin' )
        
        self._readonly_resources = set()    # resources in resources.xml that have expanded defaults idprefix & path
        self._loadTree( self.global_world, metawog.TREE_GLOBAL_TEXT,
                                           self._properties_dir, 'text.xml.bin' )

        self._movies = self._loadDirList( os.path.join( self._res_dir, 'movie' ),
                                          filename_filter = '%s.movie.binltl' )

        xml_movies = self._loadDirList( os.path.join( self._res_dir, 'movie' ),
                                          filename_filter = '%s.movie.xml' )

        for xml_movie in xml_movies:
            if xml_movie not in self._movies:
                self._movies.append(xml_movie)

        self._movies.sort(key=unicode.lower)

        self.models_by_name = {}
        self.__is_dirty = False
        self._initializeGlobalReferences()

        self.modified_worlds_to_check = set()
        louie.connect( self._onElementAdded, metaworld.ElementAdded )
        louie.connect( self._onElementAboutToBeRemoved, metaworld.ElementAboutToBeRemoved )
        louie.connect( self._onElementUpdated, metaworld.AttributeUpdated )
        self.pixmap_cache = PixmapCache( self._wog_dir, self._universe )
        window.statusBar().showMessage(self.tr("Game Model : Complete"))

    def backupTestFiles(self):
        files_to_backup = ['movie/2dboyLogo/2dboyLogo.movie.binltl',
                'movie/2dboyLogo/2dboyLogo.resrc.bin',
                'movie/credits/credits.movie.binltl',
                'movie/credits/credits.resrc.bin',
                'levels/MapWorldView/MapWorldView.level.bin']
        backup_folder = os.path.join(self._res_dir,'movie','GooVieTemp')
        for file in files_to_backup:
            input_file = os.path.join(self._res_dir,file)
            output_file = os.path.join(backup_folder,file)
            output_path = os.path.split(output_file)[0]
            if not os.path.isfile(output_file):
                if os.path.isfile(input_file):
                    if not os.path.isdir(output_path):
                        os.makedirs(output_path)
                    copy2(input_file, output_file)

    def restoreTestFiles(self):
        files_to_restore = ['movie/2dboyLogo/2dboyLogo.movie.binltl',
                'movie/2dboyLogo/2dboyLogo.resrc.bin',
                'movie/credits/credits.movie.binltl',
                'movie/credits/credits.resrc.bin',
                'levels/MapWorldView/MapWorldView.level.bin']
        backup_folder = os.path.join(self._res_dir,'movie','GooVieTemp')
        for file in files_to_restore:
            input_file = os.path.join(backup_folder,file)
            output_file = os.path.join(self._res_dir,file)
            output_path = os.path.split(output_file)[0]
            if os.path.isfile(input_file):
               if not os.path.isdir(output_path):
                    os.makedirs(output_path)
               try:
                    copy2(input_file, output_file)
                    os.remove(input_file)
               except:
                    print "Unable to restore", file

    @property
    def _resources_tree( self ):
        return self.global_world.find_tree( metawog.TREE_GLOBAL_RESOURCE )

    @property
    def _files_tree( self ):
        return self.global_world.find_tree( metawog.TREE_GLOBAL_FILES )

    @property
    def _texts_tree( self ):
        return self.global_world.find_tree( metawog.TREE_GLOBAL_TEXT )

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

    def _loadFileList( self, directory, filename_filter ):
        if not os.path.isdir( directory ):
            raise GameModelException( tr('LoadFileList',
                'Directory "%1" does not exist. You likely provided an incorrect World of Goo directory.' ).arg( directory ) )
        def is_valid_file( entry ):
            """Accepts the directory only if it contains a specified file."""
            if entry.endswith(filename_filter):
                file_path = os.path.join( directory, entry )
                return os.path.isfile( file_path )
            return False
        files = [ entry for entry in os.listdir( directory ) if is_valid_file( entry ) ]
        files.sort(key=unicode.lower)
        return files
        
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
    def names( self ):
        return self._movies

    def getModel( self, name ):
        if name not in self.models_by_name:
            dir = os.path.join( self._res_dir, STR_DIR_STUB, name )

            world = self.global_world.make_world( metawog.WORLD_MOVIE,
                                                        name,
                                                        MovieWorld,
                                                        self )
            if not os.path.isfile(os.path.join(dir, name + '.movie.xml')):
                if os.path.isfile(os.path.join(dir, name + '.movie.binltl')):
                    movie = movie_binltl.binltl_Movie()
                    data = file( os.path.join(dir, name + '.movie.binltl'), 'rb' ).read()
                    movie.fromraw(data)
                    movie_element= movie.toelement()
                    xml_data = xml.etree.ElementTree.tostring(movie_element,'utf-8')
                    file( os.path.join(dir, name + '.movie.xml'), 'wb' ).write( xml_data )
                # XML doesn't exist...
                # Convert binltl to XML...
                # Save XML


            #@DaB Prepare addin template
            self._loadUnPackedTree (world, metawog.TREE_MOVIE_TEXT,
                            dir, name + '.text.xml', metawog.MOVIE_TEXT_TEMPLATE)

            self._loadUnPackedTree (world, metawog.TREE_MOVIE_MOVIE,
                            dir, name + '.movie.xml', metawog.MOVIE_MOVIE_TEMPLATE)

            self._loadTree( world, metawog.TREE_MOVIE_RESOURCE,
                            dir, name + '.resrc.bin' )

            self._processSetDefaults(world.find_tree(metawog.TREE_MOVIE_RESOURCE))

            #Find any Global Strings and Localize them
            root = world.text_root
            rootmbt = root.meta.find_immediate_child_by_tag('string')
            elements_with_text=[]
            for element_with_text in world.movie_root.findall('.//actor'):
                if element_with_text.get('type','')=='text':
                    elements_with_text.append(element_with_text)

            for element_with_text in elements_with_text:
                tid = element_with_text.get('text')
                if tid is not None:
                  if not world.is_valid_reference(metawog.WORLD_MOVIE, 'TEXT_LEVELNAME_STR',tid):
                    if  world.is_valid_reference( metawog.WORLD_GLOBAL, 'text',tid):
                        global_text_element = world.resolve_reference( metawog.WORLD_GLOBAL, 'text' ,tid)
                        local_attrib = global_text_element.attrib.copy()
                        new_text = _appendChildTag(root,rootmbt,local_attrib,keepid=True)
                        #print tid,"is Global Text ... Localized as ",new_text.get('id')
                        element_with_text.set('text',new_text.get('id'))
                    # SPECIAL FOR GOOVIE
                    # IF TEXT IS "EXE" GENERATED... Create Local and use id as text
                    elif tid in metaworld.MOVIE_EXE_TEXT:
                        local_attrib={'id':tid,'text':tid}
                        new_text = _appendChildTag(root,rootmbt,local_attrib,keepid=True)
                        print tid,"is Exe Generated Text ... Localized"
                        element_with_text.set('text',tid)
                    else:
                        print "Text resource ",tid,"not found locally or Globally."

            #world._buildDependancyTree()
            #world.make_tree_from_xml( metawog.TREE_LEVEL_DEPENDANCY, metawog.LEVEL_DEPENDANCY_TEMPLATE )

            if world.isReadOnly:
               world.clean_dirty_tracker()
            world.clear_undo_queue()
            self.models_by_name[name] = world

        return self.models_by_name[name]

    def selectMovie( self, name ):
        """Activate the specified level and load it if required.
           Returns the activated LevelWorld.
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



    def previewMovie( self, model ):
        """Overwrites 2dboylogo movie and Starts WOG."""
        # Check for level_text
        # Update GLOBAL_TEXT_TREE  (self._texts_tree)
        #print "in gamemodel_previewMovie"
        self.backupTestFiles()

        local_text_ids = []
        for text_element in model.text_root.findall('string'):
            local_text_ids.append(text_element.get('id'))
        
        for text_element in self._texts_tree.root.findall('string'):
            if text_element.get('id') in local_text_ids:
                text_element.parent.remove(text_element)

        # Because GLOBAL_TEXT and LOCAL_TEXT are different meta+types
        # we cannot just clone the local element and appned it to the global tree
        # we need to add a new child to the global_tree with the attributes of the local element
        root = self._texts_tree.root
        rootmbt = root.meta.find_immediate_child_by_tag('string')
        for text_element in model.text_root.findall('string'):
            #print "appending",text_element.get('id'),text_element
            local_attrib = text_element.attrib.copy()
            _appendChildTag(root,rootmbt,local_attrib,keepid=True)
        # Save Text Tree
        self._savePackedData(self._properties_dir, 'text.xml.bin', self._texts_tree )

        # output this movie as 2dboylogo.movie.binltl
        # and 2dboylogo.resrc.bin , but rewrite resources id
        self.outputMovie(model,'2dboyLogo')
        self.outputMovie(model,'credits')

        # disable music in MapWorldView
        filename = os.path.join(self._res_dir,"levels","MapWorldView","MapWorldView.level.bin")
        if os.path.isfile(filename):
            xml_data = wogfile.decrypt_file_data(filename)
            element = xml.etree.ElementTree.fromstring(xml_data)
            for music in element.findall('.//music'):
                element.remove(music)
            xml_data = xml.etree.ElementTree.tostring(element,"utf-8")
            wogfile.encrypt_file_data(filename,xml_data)

        #Launch
        if ON_PLATFORM==PLATFORM_MAC:
            subp = subprocess.Popen( os.path.join(self._wog_path,u'Contents',u'MacOS',u'World of Goo'), cwd = self._wog_dir )
        else:
            subp = subprocess.Popen( self._wog_path, cwd = self._wog_dir )
        print subp.wait()
            # Don't wait for process end...
            # @Todo ? Monitor process so that only one can be launched ???
        self.restoreTestFiles()

    def outputMovie(self,model,output_name):
        output_path = os.path.join(self._res_dir,'movie',output_name)
        #print "in output movie... ",output_path,output_name
        movie_binltl.exportBIN(self, model.movie_root, output_path, output_name+'.movie.binltl')
        new_res_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_RESOURCE,
                                                                        model.resource_root.tree.to_xml() )
        for resource_element in new_res_tree.root.findall( './/Resources' ):
                resource_element.set( 'id', 'movie_%s' % output_name )
        self._savePackedData( output_path, output_name+'.resrc.bin', new_res_tree )

    def new( self, name ):
        """Creates a new blank level with the specified name.
           May fails with an IOError or OSError."""
        return self._addNew( name,
            self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_MOVIE,
                                                          metawog.MOVIE_MOVIE_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_RESOURCE,
                                                          metawog.MOVIE_RESOURCE_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_TEXT,
                                                          metawog.MOVIE_TEXT_TEMPLATE ) ,
            self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_DEPENDANCY,
                                                          metawog.MOVIE_DEPENDANCY_TEMPLATE ) )


    def clone( self, cloned_name, new_name ):
        #Clone an existing level and its resources.
           model = self.getModel( cloned_name )
           dir = os.path.join( self._res_dir, STR_DIR_STUB, new_name )
           if not os.path.isdir( dir ):
                os.mkdir( dir )

           #new cloning method... #2
           # worked or balls... might be going back to the old Nitrozark way..
           # which didn't work right... Hmmm.!

            #get xml from existing
            #make unattached trees from it
           new_movie_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_MOVIE,
                                                                        model.movie_root.tree.to_xml() )

           new_res_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_RESOURCE,
                                                                        model.resource_root.tree.to_xml() )

           new_text_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_TEXT,
                                                                        model.text_root.tree.to_xml() )

            #change stuff
           for resource_element in new_res_tree.root.findall( './/Resources' ):
                resource_element.set( 'id', 'movie_%s' % new_name )

           for resource_element in new_res_tree.root.findall( './/Image' ):
                self.transferResource(resource_element,cloned_name,new_name)

           for resource_element in new_res_tree.root.findall( './/Sound' ):
                self.transferResource(resource_element,cloned_name,new_name)
                #resid = resource_element.get('id')
                #resource_element.set('id',resid.replace('_'+cloned_name.upper()+'_','_'+new_name.upper()+'_',1))

           for resource_element in new_text_tree.root.findall( './/string' ):
                resid = resource_element.get('id')
                resource_element.set('id',resid.replace('_'+cloned_name.upper()+'_','_'+new_name.upper()+'_',1))

           self._res_swap(new_movie_tree.root,'_'+cloned_name.upper()+'_','_'+new_name.upper()+'_')

            #save out new trees
           self._saveUnPackedData( dir, new_name + '.text.xml', new_text_tree )
           self._saveUnPackedData( dir, new_name+'.movie.xml', new_movie_tree )
           self._savePackedData( dir, new_name+'.resrc.bin', new_res_tree )

           self._movies.append( unicode(new_name) )
           self._movies.sort(key=unicode.lower)
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
            newfile = os.path.join(self._wog_dir,'res','music',fname.replace(' ',''))
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
                    if attribute.reference_family in ['image','sound','TEXT_LEVELNAME_STR']:
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
           #@DaB Check if there's text and write file if needed.
           textfile = os.path.join(goomod_dir, 'text.xml')
           if model.hasText:
               files_to_goomod.append(textfile)
               self._saveUnPackedData( goomod_dir, 'text.xml', model.text_root.tree )
           else:
               # if no text required, remove the goomod text.xml file if it exists.
               if os.path.exists(textfile):
                   os.remove(textfile)

           files_to_goomod.append(os.path.join(compile_dir, name + '.level.xml'))
           self._saveUnPackedData( compile_dir, name + '.level.xml', model.level_root.tree )
           files_to_goomod.append(os.path.join(compile_dir, name + '.resrc.xml'))
           self._saveUnPackedData( compile_dir, name + '.resrc.xml', model.resource_root.tree )
           files_to_goomod.append(os.path.join(compile_dir, name + '.scene.xml'))
           self._saveUnPackedData( compile_dir, name + '.scene.xml', model.scene_root.tree )

           #That's the level xml taken care of... now lets see if there are any resources to copy
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

            for anim in element.findall('anim'):
                files_to_copy.add("res/anim/" + anim.get('id','')+".anim.binltl")

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
        
        
    def _addNew( self, name, movie_tree, resource_tree, text_tree=None, dependancy_tree=None ):
        """Adds a new level using the specified level, scene and resource tree.
           The level directory is created, but the level xml files will not be saved immediately.
        """
        dir_path = os.path.join( self._res_dir, STR_DIR_STUB, name )
        if not os.path.isdir( dir_path ):
             os.mkdir( dir_path )

                
        # Fix the hard-coded level name in resource tree: <Resources id="scene_NewTemplate" >
        for resource_element in resource_tree.root.findall( './/Resources' ):
            resource_element.set( 'id', 'movie_%s' % name )
        # Creates and register the new level
        world = self.global_world.make_world( metawog.WORLD_MOVIE, name,
                                                    MovieWorld, self, is_dirty = True )
        treestoadd = [movie_tree,resource_tree]
        if text_tree is not None:
            treestoadd.append(text_tree)
        if dependancy_tree is not None:
            treestoadd.append(dependancy_tree)

        world.add_tree( treestoadd )

        self.models_by_name[name] = world
        self._movies.append( unicode(name) )
        self._movies.sort(key=unicode.lower)
        self.__is_dirty = True
        
class BallModel(metaworld.World):
    def __init__( self, universe, world_meta, ball_name, game_model ):
        metaworld.World.__init__( self, universe, world_meta, ball_name )
        self.game_model = game_model
        self.is_dirty = False

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

class MovieWorld(ThingWorld):
    def __init__( self, universe, world_meta, name, game_model, is_dirty = False ):
        ThingWorld.__init__(self, universe, world_meta, name, game_model, is_dirty = is_dirty )
        self.__dirty_tracker = metaworldui.DirtyWorldTracker( self, is_dirty )
        self._importError = None
        self._movieissues = ''
        self._resrcissues = ''
        self._globalissues = ''
        self._animationissues = ''

        self._movie_issue_level = ISSUE_LEVEL_NONE
        self._resrc_issue_level = ISSUE_LEVEL_NONE
        self._global_issue_level = ISSUE_LEVEL_NONE
        self._animation_issue_level = ISSUE_LEVEL_NONE

        self._dependancyissues = ''
        self._dependancy_issue_level = ISSUE_LEVEL_NONE
        self._view = None

    @property
    def movie_root( self ):
        return self.find_tree( metawog.TREE_MOVIE_MOVIE ).root

    @property
    def resource_root( self ):
        return self.find_tree( metawog.TREE_MOVIE_RESOURCE ).root

    @property
    def text_root( self ):
        return self.find_tree( metawog.TREE_MOVIE_TEXT ).root

    @property
    def dependancy_root( self ):
        return self.find_tree( metawog.TREE_MOVIE_DEPENDANCY ).root

    @property
    def is_dirty( self ):
        return self.__dirty_tracker.is_dirty

    @property
    def isReadOnly( self ):
        return False
        return self.name.lower() in ''.split()

    @property
    def hasText(self):
       return self.find_tree( metawog.TREE_MOVIE_TEXT ).root.find('string') is not None

    @property
    def view( self ):
        return self._view

    def setView (self, newview):
        self._view = newview

    def hasAnimationIssues(self, actor):
        tIssue = ISSUE_LEVEL_NONE
        if self.element_issue_level(actor):
            tIssue |= ISSUE_LEVEL_CRITICAL
        if self.hasanimation_issue(actor):
            tIssue |= self._animation_issue_level
        return tIssue
        
    def getAnimationIssues(self,actor):
        txtIssue = ''
        if self.element_issue_level(actor):
            txtIssue = txtIssue + '<p>Actor:<br>' + self.element_issue_report(actor) + '</p>'
        if self.animation_issue_report!='':
            txtIssue+= '<p>Animation Checks:<br>' + self.animation_issue_report + '</p>'
        return txtIssue

    #@DaB - Issue checking used when saving the level, or making a goomod
    def hasIssues (self):
		#Checks all 3 element trees for outstanding issues
		# Returns True if there are any.
        #self._buildDependancyTree()
        tIssue = ISSUE_LEVEL_NONE
        if self.element_issue_level(self.movie_root):
            tIssue |= ISSUE_LEVEL_CRITICAL
        if self.element_issue_level(self.resource_root):
            tIssue |= ISSUE_LEVEL_CRITICAL
        if self.element_issue_level(self.text_root):
            tIssue |= ISSUE_LEVEL_CRITICAL
        #If we have a tree Issue.. don't perform the extra checks
        #because that can cause rt errors (because of the tree issues)
        #and then we don't see a popup.
        if tIssue==ISSUE_LEVEL_CRITICAL:
            #ensure old issues don't get redisplayed is we do "bail" here
            self._movieissues = ''
            self._resrcissues = ''
            self._globalissues = ''
            return tIssue
        if self.hasmovie_issue():
            tIssue |= self._level_issue_level
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
        if self.element_issue_level(self.movie_root):
            txtIssue = txtIssue + '<p>Movie Tree:<br>' + self.element_issue_report(self.movie_root) + '</p>'
        if self.movie_issue_report!='':
            txtIssue+= '<p>Movie Checks:<br>' + self.movie_issue_report + '</p>'
        if self.element_issue_level(self.resource_root):
            txtIssue = txtIssue + '<p>Resource Tree:<br>' + self.element_issue_report(self.resource_root) + '</p>'
        if self.resrc_issue_report!='':
            txtIssue+= '<p>Resource Checks:<br>' + self.resrc_issue_report + '</p>'
        if self.global_issue_report!='':
            txtIssue+= '<p>Global Checks:<br>' + self.global_issue_report + '</p>'
        if self.element_issue_level(self.text_root):
            txtIssue = txtIssue + '<p>Text Tree:<br>' + self.element_issue_report(self.text_root) + '</p>'
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

    def hasanimation_issue(self,actor):
        #actor has no name
        self._animation_issue_level=ISSUE_LEVEL_NONE
        self._animationissues=''
        hasAlpha = False
        hasColor = False
        firstframe=True
        for keyframe in actor.getchildren():
            time =keyframe.get_native('time')
            if firstframe:
                mintime=time
                maxtime=time
                firstframe=False
            elif time>maxtime:
                maxtime = time
            elif time <mintime:
                mintime=time
            alpha = keyframe.get_native('alpha',None)
            color = keyframe.get_native('color',None)
            interp = keyframe.get('interpolation','none')
            #print "keyframe",time,alpha,color,interp

            if alpha is not None:
                hasAlpha=True
                if alpha < 255:
                    if color is None and interp=='linear':
                        self.addAnimationError(601,time)
                    elif color is None and interp=='none':
                        self.addAnimationError(602,time)
                    elif interp!='linear':
                        self.addAnimationError(603,time)
            if color is not None:
                hasColor = True

        if hasColor and not hasAlpha:
           self.addAnimationError(604,None)

        #No Frame at 0 time
        #print "mintime=",mintime
        if mintime > 0.0:
           self.addAnimationError(605,None)

        #Start Position not 0,0
        x,y = movview._interpolateValues(actor,'position',(0,0),0)
        if x!=0 or y!=0:
            self.addAnimationError(606,None)

        #Start <> End
        ex,ey = movview._interpolateValues(actor,'position',(0,0),maxtime)
        if ex!=x or ey!=y:
            self.addAnimationError(607,'position')

        if movview._interpolateValue(actor,'angle',0,0) != movview._interpolateValue(actor,'angle',0,maxtime):
            self.addAnimationError(607,'angle')

        x,y = movview._interpolateValues(actor,'scale',(0,0),0)
        ex,ey = movview._interpolateValues(actor,'scale',(0,0),maxtime)
        if ex!=x or ey!=y:
            self.addAnimationError(607,'scale')

        if movview._interpolateValue(actor,'alpha',0,0) != movview._interpolateValue(actor,'alpha',0,maxtime):
            self.addAnimationError(607,'alpha')

        r,g,b = movview._interpolateValues(actor,'color',(255,255,255),0)
        er,eg,eb = movview._interpolateValues(actor,'color',(255,255,255),maxtime)
        if er!=r or eg!=g or eb!=b:
            self.addAnimationError(607,'color')

        return self._animation_issue_level!=ISSUE_LEVEL_NONE

    def hasmovie_issue(self):
        # rules for "DUMBASS" proofing (would normally use a much ruder word)

        root = self.movie_root
        self._movieissues=''
        self._movie_issue_level = ISSUE_LEVEL_NONE
         
        return self._movie_issue_level!=ISSUE_LEVEL_NONE


    def addMovieError(self,error_num,subst):
        error = errors.ERROR_INFO[error_num]
        self._movie_issue_level,self._movieissues = self.addError(self._movie_issue_level,self._movieissues,error,error_num,subst)

    def addAnimationError(self,error_num,subst):
        print "Animation Error",error_num
        error = errors.ERROR_INFO[error_num]
        self._animation_issue_level,self._animationissues = self.addError(self._animation_issue_level,self._animationissues,error,error_num,subst)

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
        resources['TEXT_LEVELNAME_STR'] =  self._get_all_resource_ids(self.text_root,"string")
        unused = {'image':set(),'sound':set(),'TEXT_LEVELNAME_STR':set()}
        for restype in unused.keys():
            unused[restype] = resources[restype]-used[restype]
        return unused

    def _remove_unused_resources(self,unused):
        self.suspend_undo()
        for family,unusedset in unused.items():
          for unusedid in unusedset:
            element = self.resolve_reference(metawog.WORLD_MOVIE, family, unusedid)
            if element is not None:
                element.parent.remove(element)
        self.activate_undo()

    def _get_used_resources(self):
        used = {'image':set(),'sound':set(),'TEXT_LEVELNAME_STR':set()}
        self._get_used_inner(self.movie_root,used)
        return used

    def _get_used_inner(self,root_element,used):
        #go through scene and level root
        #store the resource id of any that do
        oftype = ['image','sound','TEXT_LEVELNAME_STR']
        for element in root_element:
            for attribute_meta in element.meta.attributes:
                if attribute_meta.type == metaworld.REFERENCE_TYPE:
                    if attribute_meta.reference_family in oftype:
                        if element.get(attribute_meta.name):
                            if attribute_meta.is_list:
                                for res in element.get(attribute_meta.name).split(','):
                                    used[attribute_meta.reference_family].add(res)
                            else:
                                used[attribute_meta.reference_family].add(element.get(attribute_meta.name))
            self._get_used_inner(element,used)

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

        text_resources = set()
        for resource in self.text_root.findall('.//string'):
            text_resources.add(resource.get('id'))

        unused_texts = text_resources.difference(used_resources['TEXT_LEVELNAME_STR'])
        if len(unused_texts)!=0:
            for unused in unused_texts:
               self.addResourceError(205,unused)

        return self._resrc_issue_level != ISSUE_LEVEL_NONE

    @property
    def movie_issue_report(self):
        return self._movieissues
    @property
    def animation_issue_report(self):
        return self._animationissues

    @property
    def resrc_issue_report(self):
        return self._resrcissues
    @property
    def global_issue_report(self):
        return self._globalissues

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
        
    def _buildDependancyTree(self):
        self.suspend_undo()

        dependancy_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_MOVIE_DEPENDANCY, metawog.MOVIE_DEPENDANCY_TEMPLATE )

        current={'imagedep':set(),'sounddep':set()}
	ball_trace=''
        self._recursion = []

        self.game_model.global_world.refreshFromFiles()
          
        self._addDependancies(self.movie_root,dependancy_tree.root,current,ball_trace)

        for element in self.resource_root.findall('.//Image'):
            child_attrib = {'found':"true"}
            for attribute in element.meta.attributes:
               child_attrib[attribute.name]=element.get(attribute.name)
            if child_attrib['path'] not in current['imagedep']:
                child_element = metaworld.Element( metawog.DEP_IMAGE, child_attrib)
                dependancy_tree.root._children.append( child_element )
                child_element._parent = dependancy_tree.root
                current['imagedep'].add(child_attrib['path'])

        for element in self.resource_root.findall('.//Sound'):
            child_attrib = {'found':"true"}
            for attribute in element.meta.attributes:
               child_attrib[attribute.name]=element.get(attribute.name)
            if child_attrib['path'] not in current['sounddep']:
                child_element = metaworld.Element( metawog.DEP_SOUND, child_attrib)
                dependancy_tree.root._children.append( child_element )
                child_element._parent = dependancy_tree.root
                current['sounddep'].add(child_attrib['path'])

        self._removeOriginalDependancies(dependancy_tree.root)
        old_tree = self.find_tree(metawog.TREE_MOVIE_DEPENDANCY)
        if old_tree is None:
            self.add_tree( [dependancy_tree] )
        else:
            old_tree.set_root(dependancy_tree.root)
        self.activate_undo()
        self.__dirty_tracker.clean_tree(metawog.TREE_MOVIE_DEPENDANCY)
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
        elif element.tag in ['dependancy']:
                remove=False
        else:
            print "Unknown Dependancy Tag", element.tag

        if remove and len(element.getchildren())==0 and element.get_native('found',False):
             index = element.parent._children.index( element )
             del element.parent._children[index]
             element._parent = None
             del element

    def _addDependancies(self,element,dep_element,current):
        #run through the attributes of the element
        # add nodes at this level for any direct deps
        for attribute_meta in element.meta.attributes:
            if attribute_meta.type == metaworld.REFERENCE_TYPE:
             if attribute_meta.reference_family in ['image','sound']:
                attribute_value = attribute_meta.get(element)
                if attribute_value is not None:
                  if attribute_meta.is_list:
                      references=attribute_value.split(',')
                  else:
                      references=[attribute_value]
                  for reference in references:
                   if reference.strip()!='' and not self._isNumber(reference):
                    try:
                        res_element = self.resolve_reference( attribute_meta.reference_world, attribute_meta.reference_family, reference )
                    except ValueError:
                        res_element = None
                        
                    new_dep_meta = dep_element.meta.find_immediate_child_by_tag(attribute_meta.reference_family)
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
                        self._addDependancies(res_element,child_element,current)

        #now run through child elements
        for child_element in element.getchildren():
            self._addDependancies(child_element,dep_element,current)

    def hasDependancies(self):
        return len(self.dependancy_root.getchildren())>0

    def hasdependancy_issue(self):
        # things to check
        self._dependancyissues = ''
        self._dependancy_issue_level = ISSUE_LEVEL_NONE
 
        return self._dependancy_issue_level != ISSUE_LEVEL_NONE

    @property
    def dependancy_issue_report(self):
        return self._dependancyissues

    def _cleanmovietree(self):
        self.suspend_undo()
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

    def saveModifiedElements( self ):
        """Save the modified scene, level, resource tree."""
        if not self.isReadOnly:  # Discards change made on read-only level
            name = self.name
            dir = os.path.join( self.game_model._res_dir, STR_DIR_STUB, name )
            if not os.path.isdir( dir ):
                os.mkdir( dir )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_MOVIE_TEXT):
                self.game_model._saveUnPackedData( dir, name + '.text.xml',
                                                 self.text_root.tree )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_MOVIE_MOVIE):

                if not self.element_issue_level(self.movie_root):
                  #clean tree caused an infinite loop when there was a missing ball
                  # so only clean trees with no issues
                  self._cleanmovietree()
                
                self.game_model._saveUnPackedData( dir, name + '.movie.xml',
                                                 self.movie_root.tree )
            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_MOVIE_RESOURCE):
                self.game_model._savePackedData( dir, name + '.resrc.bin',
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
        image_element = self.resolve_reference( metawog.WORLD_MOVIE, 'image', image_id )
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
           png -> res/levels/{name}
           ogg -> res/music/{name}  for compatability with Soultaker's Volume control add-in
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
        #if fileext=='png':
        newfile = os.path.join(self.game_model._wog_dir,'res',STR_DIR_STUB,self.name,fname.replace(' ',''))
        #else:
        #    newfile = os.path.join(self.game_model._wog_dir,'res','music',fname.replace(' ',''))
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
        resmap = {'png':('Image','IMAGE_MOVIE_%s_%s','image'),'ogg':('Sound','SOUND_MOVIE_%s_%s','sound')}
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
                meta_element = metawog.TREE_MOVIE_RESOURCE.find_element_meta_by_tag( resmap[ext][0] )
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
        self.recentfiles = None
        self.createMDIArea()
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.createDockWindows()
        self.setWindowTitle(self.tr("World of Goo Movie Maker"))
        self.playing = False
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
        if self.open_view_by_name( name ):
            self._setRecentFile( name )
        
    def edit( self ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = editleveldialog_ui.Ui_EditLevelDialog()
            ui.setupUi( dialog )
            for name in self._game_model.names:
                ui.levelList.addItem( name )
            if dialog.exec_() and ui.levelList.currentItem:
                name = unicode( ui.levelList.currentItem().text() )
                if self.open_view_by_name( name ):
                    self._setRecentFile( name )
                
    def open_view_by_name( self, name ):
        try:
            world = self._game_model.selectMovie( name )
        except GameModelException, e:
            QtGui.QMessageBox.warning(self, self.tr("Failed to load level! ("+APP_NAME_PROPER+" "+CURRENT_VERSION+")"),
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
        """Adds a new MDI GraphicView window for the specified level."""
        view = movview.GraphicView(self, world, self.view_actions, self.common_actions )
        sub_window = self.mdiArea.addSubWindow( view )
        self.connect( view, QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'),
                      self._updateMouseScenePosInStatusBar )

        self.connect( sub_window, QtCore.SIGNAL('aboutToActivate()'),
                      view.selectOnSubWindowActivation )

        world.set_selection(world.movie_root)
        world.setView(view)
        view.show()

    def _updateMouseScenePosInStatusBar( self, x, y ):
        """Called whenever the mouse move in the movview."""
		# Round displayed coordinate to 2dp (0.01)
        x = round(x,2)
        y = -round(y,2) # Reverse transformation done when mapping to scene (in Qt 0 = top, in WOG 0 = bottom)
        self._mousePositionLabel.setText( self.tr('x: %1 y: %2').arg(x).arg(y) )

    def _findWorldMDIView( self, world ):
        """Search for an existing MDI window for level name.
           Return the GraphicView widget, or None if not found."""
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
                        QtGui.QMessageBox.warning(self, self.tr("Can not save World Of Goo standard levels!"),
                              self.tr('You can not save changes made to levels that come with World Of Goo.\n'
                                      'Instead, clone the level using the "Clone selected level" tool.\n'
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
                        QtGui.QMessageBox.warning(self, self.tr("Failed saving levels ("+APP_NAME_PROPER+" "+CURRENT_VERSION+")"), unicode(e))

       return False

    def saveIT(self):
       if self.saveCurrent():
         QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)
         model = self.getCurrentModel()
         issue_level = model.hasIssues()
         QtGui.QApplication.restoreOverrideCursor()
         if issue_level>=ISSUE_LEVEL_WARNING:
            txtIssue = self.tr("""<p>There are unresolved issues with this level that may cause problems.<br>
                                    You should fix these before you try to play or make a goomod.</p>""")
            txtIssue = txtIssue + self.tr(model.getIssues())
            txtIssue = txtIssue + self.tr( '<br>The level has been saved!')
            QtGui.QMessageBox.warning(self, self.tr("This level has issues!"),
                  txtIssue )

    def playMovieStart(self):
        model = self.getCurrentModel()
        if model:
            model.view._setTime(0)
            model.view.refreshFromModel()
            self.startTime = time.time()
            self.play()

    def playMovie(self):
        if self.playing:
            self.stop()
            return
        model = self.getCurrentModel()
        if model:
            if (model.view.time+0.1)>=model.view.movielength:
                model.view._setTime(0)
            model.view.refreshFromModel()
            self.startTime = time.time() - model.view.time
            self.play()
    
    def stop(self):
            self.movieTimer.stop
            self.playing = False
            self.movieActions['playpause'].setIcon ( QtGui.QIcon ( ':/images/playmovie.png' ) )
            
    def play(self):
            self.playing = True
            self.movieActions['playpause'].setIcon ( QtGui.QIcon ( ':/images/pause.png' ) )
            self.movieTimer = QtCore.QTimer( self )
            self.movieTimer.setSingleShot(True)
            self.connect( self.movieTimer, QtCore.SIGNAL("timeout()"), self.playMovieAction )
            self.movieTimer.start( 20 )


    def playMovieAction(self):
        if not self.playing:
            return
        window = self.mdiArea.activeSubWindow()
        if window:
            view = window.widget()
            ctime = view.time
            #print ctime,view.movielength
            if ctime > view.movielength:
                self.stop()
            else:
                view._setTime(time.time() - self.startTime)
                self.movieTimer.start( 20 )


    def saveAndPlayLevel(self):
		#@DaB only save current level, and don't "play" if it has "Issues"
        if self.saveCurrent(): #returns false if there are issues
            model = self.getCurrentModel()
            if model:
                issue_level = model.hasIssues()
                if issue_level>=ISSUE_LEVEL_CRITICAL:
                    txtIssue = self.tr("""<p>There are CRITICAL issues with this movie that will cause World of Goo to crash.<br>
                                       You must fix these before you try to play the move in the game.</p>""")
                    txtIssue = txtIssue + self.tr(model.getIssues())
                    txtIssue = txtIssue + self.tr( '<br>The movie has been saved!')
                    QtGui.QMessageBox.warning(self, self.tr("This movie has CRITICAL issues!"),
                          txtIssue )
                elif issue_level>ISSUE_LEVEL_NONE:
                    txtIssue = self.tr("""<p>There are Advice/Warnings for this movie that may cause problems.<br>
                                        You should fix these before you try to play the movie.</p>""")
                    txtIssue = txtIssue + self.tr(model.getIssues())
                    txtIssue = txtIssue + self.tr( '<br>Click OK to Play anyway, or click Cancel to go back.')
                    ret = QtGui.QMessageBox.warning(self, self.tr("This movie has warnings!"),
                        txtIssue,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret==QtGui.QMessageBox.Ok:
                        self._game_model.previewMovie( model )
                else:
                    self._game_model.previewMovie( model )
            else:
                self.statusBar().showMessage(self.tr("You must select a movie to play"), 2000)

    def exportMovie(self):
      if self.saveCurrent(): #returns false if it failed
        if self._game_model:
            model = self.getCurrentModel()
            if model is not None:
		self.statusBar().showMessage(self.tr("Checking for Cloned Files : " + model.name), 2000)
                clonedfiles = model.checkClonedFiles()
                if clonedfiles is not None:
                    txtIssue = self.tr("""<p>This movie uses renamed / moved copies of original World of Goo files.<br>
                                        GooVie will not include the following files in a goomod.</p>
                                        <p>%s</p>
                                        <p>If you want GooVie to automatically fix this, click OK<br>Otherwise click Cancel to abort creating the movie</p>"""
                                        % self.tr("<br>".join(clonedfiles.keys())) )
                    ret = QtGui.QMessageBox.warning(self, self.tr("This movie uses cloned files!"),
                        txtIssue,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret==QtGui.QMessageBox.Cancel:
                        return False

                    model.fixClonedFiles(clonedfiles)                

		dir = os.path.normpath(os.path.join( os.path.split( self._wog_path )[0],'res', STR_DIR_STUB, model.name ))
                filename = model.name + ".movie.binltl"
                movie_binltl.exportBIN(self, model.movie_root, dir, filename)
                #self.statusBar().showMessage(self.tr("Movie exported to " + os.path.join(dir,filename)), 2000)
      return False

    def exportXML(self):
      if self.saveCurrent(): #returns false if it failed
        if self._game_model:
            model = self.getCurrentModel()
            if model is not None:
		self.statusBar().showMessage(self.tr("Checking for Cloned Files : " + model.name), 2000)
                clonedfiles = model.checkClonedFiles()
                if clonedfiles is not None:
                    txtIssue = self.tr("""<p>This movie uses renamed / moved copies of original World of Goo files.<br>
                                        GooVie will not include the following files in a goomod.</p>
                                        <p>%s</p>
                                        <p>If you want GooVie to automatically fix this, click OK<br>Otherwise click Cancel to abort creating the movie</p>"""
                                        % self.tr("<br>".join(clonedfiles.keys())) )
                    ret = QtGui.QMessageBox.warning(self, self.tr("This movie uses cloned files!"),
                        txtIssue,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret==QtGui.QMessageBox.Cancel:
                        return False

                    model.fixClonedFiles(clonedfiles)

		dir = os.path.normpath(os.path.join( os.path.split( self._wog_path )[0],'res', STR_DIR_STUB, model.name ))
                filename = model.name + ".moviex.xml"
                movie_binltl.exportXML(self, model.movie_root, dir, filename)
                #self.statusBar().showMessage(self.tr("Movie exported to " + os.path.join(dir,filename)), 2000)
      return False


    def exportAnimation(self):
      if self.saveCurrent(): #returns false if it failed
        if self._game_model:
            model = self.getCurrentModel()
            if model is not None:
                selected_elements=model.selected_elements
                actor = None
                for element in selected_elements:
                    if element.tag== 'actor':
                        actor = element
                        break
                    elif element.tag=='keyframe':
                        actor = element.parent
                        break
                    elif element.tag=='movie':
                        if len(element)==1:
                            actor = element.find('actor')
                            break
                if actor == None:
                    QtGui.QMessageBox.warning(self, self.tr("Export Animation"),
                                     self.tr('You must select an actor to export') )
                    return False

                if model.hasAnimationIssues(actor)!=ISSUE_LEVEL_NONE:
                    txtIssue = self.tr("""<p>There are issues which may affect exporting this animation.<br>
                                        You should fix these before you try to use it in a level</p>""")
                    txtIssue = txtIssue + self.tr(model.getAnimationIssues(actor))
                    txtIssue = txtIssue + self.tr( '<br>Click OK to Export anyway, or click Cancel to go back.')
                    ret = QtGui.QMessageBox.warning(self, self.tr("Animation warnings!"),
                        txtIssue,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret==QtGui.QMessageBox.Cancel:
                        return False

                filename = actor.get('name',model.name) + ".anim.binltl"
                dir = os.path.normpath(os.path.join( os.path.split( self._wog_path )[0],'res', 'anim' ))
                filename = QtGui.QFileDialog.getSaveFileName(self, self.tr("Save animation File"),
                        os.path.join(dir,filename), self.tr("Animation (*.anim.binltl)"));
                if filename!='':
                    dirfile = os.path.split(str(filename))
                    movie_binltl.exportBIN(self, actor, dirfile[0], dirfile[1])
                    self.statusBar().showMessage(self.tr("Animation exported to " + str(filename)), 2000)
      return False


    def new( self ):
        """Creates a new blank level."""
        new_name = self._pickNewName( is_cloning = False )
        if new_name:
            try:
                self._game_model.new( new_name )
                world = self._game_model.selectMovie( new_name )
                self._addGraphicView( world )
            except (IOError,OSError), e:
                QtGui.QMessageBox.warning(self, self.tr("Failed to create the new movie! ("+APP_NAME_PROPER+" "+CURRENT_VERSION+")"),
                                          unicode(e))

    def _pickNewName( self, is_cloning = False ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = newleveldialog_ui.Ui_NewLevelDialog()
            ui.setupUi( dialog )
            reg_ex = QtCore.QRegExp( '[0-9A-Za-z][0-9A-Za-z]+' )
            validator = QtGui.QRegExpValidator( reg_ex, dialog )
            ui.levelName.setValidator( validator )
            if is_cloning:
                dialog.setWindowTitle(tr("NewLevelDialog", "Cloning Movie"))
     
            if dialog.exec_():
                new_name = str(ui.levelName.text())
                existing_names = [name.lower() for name in self._game_model.names]
                if new_name.lower() not in existing_names:
                    return new_name
                QtGui.QMessageBox.warning(self, self.tr("Can not create movie!"),
                    self.tr("There is already a movie named '%1'").arg(new_name))
        return None

    def clone( self ):
        """Clone the selected movie."""
        current_model = self.getCurrentModel()
        if current_model:
            new_name = self._pickNewName( is_cloning = True )
            if new_name:
                try:
                    self._game_model.clone( current_model.name, new_name )
                    world = self._game_model.selectMovie( new_name )
                    self._addGraphicView( world )
                    self._setRecentFile( new_name )
                except (IOError,OSError), e:
                    QtGui.QMessageBox.warning(self, self.tr("Failed to create the new cloned movie! ("+APP_NAME_PROPER+" "+CURRENT_VERSION+")"),unicode(e))

                                              

    def updateResources( self ):
        """Adds the required resource in the level based on existing file."""
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
                unusedlist="The following resources are unused\n"+unusedlist+"\nDo you want to remove them?"
                ret = QtGui.QMessageBox.warning(self, self.tr("Clean Resources"),
                        unusedlist,QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                if ret==QtGui.QMessageBox.Ok:
                    model._remove_unused_resources(unused)
                noproblems = False

            clonedfiles = model.checkClonedFiles()
            if clonedfiles is not None:
                    txtIssue = self.tr("""<p>This level uses renamed / moved copies of original World of Goo files.<br>
                                        WooGLE will not include the following files in a goomod.</p>
                                        <p>%s</p>
                                        <p>If you want WooGLE to automatically fix this, click OK<br>Otherwise click Cancel</p>"""
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
                        self.tr( 'Select the Images to import...' ),
                        dir,
                        self.tr( 'Images and Sounds (*.png *.ogg)' ) )

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
        QtGui.QMessageBox.about(self, self.tr("About World of Goo Movie Maker " + CURRENT_VERSION),
            self.tr("""<p>World of Goo Movie Maker <b>(Goovie Maker)</b> helps you create new movies for World of Goo.<p>
            <p>Download Page:<br>
            <a href="http://goofans.com/download/utility/world-of-goo-movie-maker">http://goofans.com/download/utility/world-of-goo-movie-maker</a></p>
            <p>FAQ, Tutorial and Reference Guide:<br>
            <a href="http://goofans.com/developers/world-of-goo-movie-maker">http://goofans.com/developers/world-of-goo-movie-maker</a></p>
            <p>Copyright 2010-, DaftasBrush</p>
            <p>&nbsp;<br>Based very loosely on the Original WoGEdit Sourceforge project: (v0.5)
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
            on_clipboard = set()
            clipboard_element = xml.etree.ElementTree._ElementInterface('WooGLEClipboard',{})
            for element in elements:
                on_clipboard.add(element.tag)
                xml_data= element.to_xml_with_meta()
                clipboard_element.append(xml.etree.ElementTree.fromstring(xml_data))
            clipboard = QtGui.QApplication.clipboard()
            if len(on_clipboard)==1:
                clipboard_element.set('type', list(on_clipboard)[0])
            else:
                clipboard_element.set('type',"Various")
            scene = self.get_active_view().scene
            # bounding rect of selected items
            i=0
            mybrect=[0,0,0,0]
            for item in scene.selectedItems():
                if i==0:
                    brect = item.mapToScene(item.boundingRect()).boundingRect()
                    mybrect=[brect.left(),brect.right(),brect.bottom(),brect.top()]
                else:
                    brect = item.mapToScene(item.boundingRect()).boundingRect()
                    if brect.left()<mybrect[0]:
                        mybrect[0]=brect.left()
                    if brect.right()>mybrect[1]:
                        mybrect[1]=brect.right()
                    if brect.bottom()<mybrect[2]:
                        mybrect[2]=brect.bottom()
                    if brect.top()>mybrect[3]:
                        mybrect[3]=brect.top()
                i+=1
            
            clipboard_element.set('posx',str((mybrect[0]+mybrect[1])*0.5))
            clipboard_element.set('posy',str(-(mybrect[2]+mybrect[3])*0.5))
            xml_data =  xml.etree.ElementTree.tostring(clipboard_element,'utf-8')
            clipboard.setText( xml_data )
            if not is_cut_action:
                self.statusBar().showMessage( 
                    self.tr('%d Element "%s" copied to clipboard' %
                            (len(elements),clipboard_element.get('type'))), 1000 )
            self.common_actions['paste'].setText("Paste In Place ("+clipboard_element.get('type')+")")
            self.common_actions['pastehere'].setText("Paste Here ("+clipboard_element.get('type')+")")
            return elements


    def on_pasteto_action(self):
        clipboard = QtGui.QApplication.clipboard()
        xml_data = unicode(clipboard.text())
        world = self.getCurrentModel()
        if world is None or not xml_data:
            return
        clipboard_element = xml.etree.ElementTree.fromstring(xml_data)
        view = self.get_active_view()
        paste_posx,paste_posy = view._last_pos.x(),-view._last_pos.y()
        copy_posx,copy_posy = float(clipboard_element.get('posx',0)),float(clipboard_element.get('posy',0))
        pasted_elements = []
        for clip_child in clipboard_element.getchildren():
          xml_data = xml.etree.ElementTree.tostring(clip_child,'utf-8')
          for element in [tree.root for tree in world.trees]:
                child_elements = element.make_detached_child_from_xml( xml_data )
                if child_elements:
                    pasted_elements.extend(child_elements)
                    for child_element in child_elements:
                        # find the pos attribute in the meta
                        # set it to view._last_release_at
                        pos_attribute = self._getPositionAttribute(child_element)
                        imagepos_attribute = self._getImageposAttribute(child_element)
                        if pos_attribute is not None:
                            old_pos = pos_attribute.get_native(child_element,(0,0))
                            if clipboard_element.__len__()==1:
                                pos_attribute.set_native(child_element,[view._last_pos.x(),-view._last_pos.y()])
                            else:
                                pos_attribute.set_native(child_element,[old_pos[0]+paste_posx-copy_posx,old_pos[1]+paste_posy-copy_posy])

                            if imagepos_attribute is not None:
                                old_imagepos = imagepos_attribute.get_native(child_element,None)
                                if old_imagepos is not None:
                                    if clipboard_element.__len__()==1:
                                        new_posx = old_imagepos[0]+view._last_pos.x()-old_pos[0]
                                        new_posy = old_imagepos[1]-view._last_pos.y()-old_pos[1]
                                    else:
                                        new_posx = old_imagepos[0]+paste_posx-copy_posx
                                        new_posy = old_imagepos[1]+paste_posy-copy_posy
                                    imagepos_attribute.set_native(child_element,[new_posx,new_posy])
                                    
                        element.safe_identifier_insert( len(element), child_element )
                    break
        if len(pasted_elements)>=1:
            world.set_selection( pasted_elements )


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
        clipboard_element = xml.etree.ElementTree.fromstring(xml_data)
        pasted_elements = []
        for clip_child in clipboard_element.getchildren():
          xml_data = xml.etree.ElementTree.tostring(clip_child,'utf-8')
          for element in elements:
             while element is not None:
                child_elements = element.make_detached_child_from_xml( xml_data )
                if child_elements:
                    for child_element in child_elements:
                        element.safe_identifier_insert( len(element), child_element )
                    pasted_elements.extend(child_elements)
                    break
                element = element.parent
        if element is not None:
          if len(pasted_elements)>=1:
            element.world.set_selection( pasted_elements )

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
        previous_element = None
        for element in list(world.selected_elements):
            if element.meta.read_only:
                #messagebox
                QtGui.QMessageBox.warning(self, self.tr("Cannot delete read only element!"),
                              self.tr('This element is read only.\n'
                                      'It cannot be deleted' ) )

                return 0
            elif not element.is_root():
                if element.previous_element() not in list(world.selected_elements):
                    previous_element = element.previous_element()

                deleted_elements.append( element.tag )
                element.parent.remove( element )
                
        if is_cut_action:
            return len(deleted_elements)
        if deleted_elements:
            self.statusBar().showMessage( 
                self.tr('Deleted %d element(s)' % len(deleted_elements)), 1000 )
            world.set_selection( previous_element )

    def _on_view_tool_actived( self, tool_name ):
        active_view = self.get_active_view()
        if active_view is not None:
            active_view.tool_activated( tool_name )

    def on_select_tool_action(self):
        self._on_view_tool_actived( movview.TOOL_SELECT )

    def on_pan_tool_action(self):
        self._on_view_tool_actived( movview.TOOL_PAN )

    def on_move_tool_action(self):
        self._on_view_tool_actived( movview.TOOL_MOVE )

    def onRefreshAction( self ):
        """Called multiple time per second. Used to refresh enabled flags of actions."""
        has_wog_dir = self._game_model is not None
        #@DaB - Now that save and "save and play" only act on the
		# current level it's better if that toolbars buttons
 		# change state based on the current level, rather than all levels
	currentModel = self.getCurrentModel()
        is_selected = currentModel is not None
        can_select = is_selected and self.view_actions[movview.TOOL_MOVE].isChecked()

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


        self.editAction.setEnabled( has_wog_dir )
        self.newAction.setEnabled( has_wog_dir )
        self.cloneAction.setEnabled( is_selected )
        self.saveAction.setEnabled( can_save and True or False )
        self.playAction.setEnabled( is_selected )
        self.exportMovieAction.setEnabled (can_import)
        self.exportAnimAction.setEnabled (can_import)

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
        self.updateResourcesAction.setEnabled( can_import )
        self.addTextResourceAction.setEnabled (can_import)


        self.movieToolBar.setEnabled( can_select )
        self.addItemToolBar.setEnabled( can_select )

        #self.showhideToolBar.setEnabled( is_selected )
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
            self.view_actions[movview.TOOL_MOVE].setChecked( True )
        
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

        self.editAction = qthelper.action( self, handler = self.edit,
            icon = ":/images/icon-wog-level.png",
            text = "&Edit existing movie...",
            shortcut = "Ctrl+L",
            status_tip = "Select a movie to edit" )

        self.newAction = qthelper.action(self, handler = self.new,
            icon = ":/images/icon-wog-new-level2.png",
            text = "&New movie...",
            shortcut = QtGui.QKeySequence.New,
            status_tip = "Creates a new movie" )

        self.cloneAction = qthelper.action( self, handler = self.clone,
            icon = ":/images/icon-wog-clone-level.png",
            text = "&Clone selected movie...",
            shortcut = "Ctrl+D",
            status_tip = "Clone the selected movie" )
        
        self.saveAction = qthelper.action( self, handler = self.saveIT,
            icon = ":/images/save.png",
            text = "&Save...",
            shortcut = QtGui.QKeySequence.Save,
            status_tip = "Saves the Movie XML" )
        
        self.playAction = qthelper.action( self, handler = self.saveAndPlayLevel,
            icon = ":/images/play.png",
            text = "&Save XML and Preview Movie...",
            shortcut = "Ctrl+P",
            status_tip = "Save and play movie in the game" )

        self.exportMovieAction = qthelper.action( self, handler = self.exportMovie,
            icon = ":/images/export.png",
            text = "&Export to .binltl",
            status_tip = "Export to .binltl" )

        self.exportAnimAction = qthelper.action( self, handler = self.exportAnimation,
            icon = ":/images/export-anim.png",
            text = "&Export an animation .binltl",
            status_tip = "Export an animation .binltl" )

        self.exportXMLAction = qthelper.action( self, handler = self.exportXML,
            icon = ":/images/goomod.png",
            text = "&Export an movie as XML for goomod",
            status_tip = "&Export an movie as XML for goomod" )


        self.updateResourcesAction = qthelper.action( self,
            handler = self.updateResources,
            icon = ":/images/update-level-resources.png",
            text = "&Update movie resources...",
            shortcut = "Ctrl+U",
            status_tip = "Adds automatically all .png & .ogg files in the movie directory" )

        self.cleanResourcesAction = qthelper.action( self,
            handler = self.cleanResources,
            icon = ":/images/cleanres.png",
            text = "&Clean Resources",
            status_tip = "Removes any unused resource from the movie." )

        self.importResourcesAction = qthelper.action( self,
            handler = self.importResources,
            icon = ":/images/importres.png",
            text = "&Import resources...",
            shortcut = "Ctrl+I",
            status_tip = "Adds files (png & ogg) to the movie resources" )

        self.addTextResourceAction =  qthelper.action( self,
                    handler=AddItemFactory(self,'text', 'string',{}),
                    icon = ":/images/text.png",
                    text = "&Add Text Resource")


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
                    text = "Paste &In Place",
                    shortcut ="Ctrl+Shift+V" ),
            'pastehere': qthelper.action( self, handler = self.on_pasteto_action,
                    icon = ":/images/paste.png",
                    text = "&Paste Here",shortcut = QtGui.QKeySequence.Paste ),

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

        self.movieActions = {
        "playstart": qthelper.action( self, handler = self.playMovieStart,
            icon = ":/images/playstart.png",
            text = "&Play from Start",
            shortcut = "Ctrl+P",
            status_tip = "Play from Start" ),
        "playpause": qthelper.action( self, handler = self.playMovie,
            icon = ":/images/playmovie.png",
            text = "&Play / Pause",
            shortcut = "Ctrl+P",
            status_tip = "Play / Pause" )}

        class ShowHideFactory(object):
                def __init__( self, window, elements ):
                    self.window = window
                    self.elements = elements
                def __call__( self ):
                    lv = self.window.get_active_view()
                    if lv is not None:
                      for elementtype in self.elements:
                        currentstate = lv.get_element_state(elementtype)
                        newstate = 2 - currentstate
                        lv.set_element_state(elementtype,newstate)
                      lv.refreshFromModel()

        self.view_action_group = QtGui.QActionGroup(self)
        self.view_actions = { 
            movview.TOOL_SELECT: qthelper.action( self,
                    handler = self.on_select_tool_action,
                    icon = ":/images/strand.png",
                    text = "&Strand Mode",
                    shortcut = QtGui.QKeySequence( Qt.Key_Space),
                    checkable = True,
                    status_tip = "Click a Goo, hold, move to another Goo and release to connect them." ),
            movview.TOOL_PAN: qthelper.action( self,
                    handler = self.on_pan_tool_action,
                    icon = ":/images/zoom.png",
                    text = "&Zoom and Pan view (F)",
                    shortcut = 'F',
                    checkable = True ),
            movview.TOOL_MOVE: qthelper.action( self,
                    handler = self.on_move_tool_action,
                    icon = ":/images/tool-move.png",
                    text = "&Select, Move and Resize",
                    shortcut = 'T',
                    checked = True,
                    checkable = True )
            }

        self.bgcolour_actions = { 'black': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(0,0,0) ), text = "Black", icon=":/images/black.png"),
                'grey75': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(64,64,64) ), text = "75% Grey",icon=":/images/grey64.png"),
                'grey50': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(128,128,128) ), text = "50% Grey",icon=":/images/grey128.png"),
                'grey25': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(192,192,192) ), text = "25% Grey",icon=":/images/grey192.png"),
                'white': qthelper.action( self, handler = BGColourFactory( self ,QtGui.QColor(255,255,255) ), text = "White",icon=":/images/white.png")}

        for action in self.view_actions.itervalues():
            self.view_action_group.addAction( action )
		
        self.additem_actions = {
        'image':    qthelper.action( self,
                    handler = AddItemFactory(self, 'movie','actor',{'type':'image'}),
                    icon = ":/images/actor-image.png",
                    text = "&Add Image Actor"),

        'text':    qthelper.action( self,
                    handler=AddItemFactory(self,'movie', 'actor',{'type':'text'}),
                    icon = ":/images/actor-text.png",
                    text = "&Add Text Actor"),

        'keyframe':qthelper.action( self,
                    handler = AddItemFactory(self, 'actor','keyframe',{}),
                    icon = ":/images/addkeyframe.png",
                    text = "&Add Key Frame")

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
        self.fileMenu.addAction(self.newAction)
        self.fileMenu.addAction(self.editAction)
        self.fileMenu.addAction(self.cloneAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.playAction)
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
        self.editMenu.addAction( self.common_actions['pastehere'] )
        self.editMenu.addSeparator()
        self.editMenu.addAction( self.common_actions['delete'] )
        
        self.menuBar().addSeparator()
        self.resourceMenu = self.menuBar().addMenu(self.tr("&Resources"))
        self.resourceMenu.addAction( self.updateResourcesAction )
        self.resourceMenu.addAction( self.importResourcesAction )
        self.resourceMenu.addAction( self.additem_actions['text'] )
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
        self.fileToolBar.addAction(self.newAction)
        self.fileToolBar.addAction(self.editAction)
        self.fileToolBar.addAction(self.cloneAction)
        self.fileToolBar.addSeparator()
        self.fileToolBar.addAction(self.saveAction)
        self.fileToolBar.addAction(self.playAction)
        self.fileToolBar.addSeparator()
        self.fileToolBar.addAction(self.exportMovieAction)
        self.fileToolBar.addAction(self.exportAnimAction)
        self.fileToolBar.addAction(self.exportXMLAction)


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
        self.resourceToolBar.addAction( self.updateResourcesAction )
        self.resourceToolBar.addAction( self.importResourcesAction )
        self.resourceToolBar.addAction( self.addTextResourceAction )
        self.resourceToolBar.addSeparator()
        self.resourceToolBar.addAction( self.cleanResourcesAction )

        self.movieToolBar = self.addToolBar(self.tr("Movie"))
        self.movieToolBar.setObjectName("movieToolbar")
        self.movieToolBar.addAction( self.movieActions['playstart'] )
        self.movieToolBar.addAction( self.movieActions['playpause'] )

        self.viewToolBar = self.addToolBar(self.tr("View"))
        self.viewToolBar.setObjectName("viewToolbar")

        for name in ('move', 'pan'):
            action = self.view_actions[name]
            self.viewToolBar.addAction( action )

        self.bgcolourToolBar = self.addToolBar(self.tr("Background Colour"))
        self.bgcolourToolBar.setObjectName("bgcolourToolbar")
        for key in ['white','grey25','grey50','grey75','black']:
            self.bgcolourToolBar.addAction( self.bgcolour_actions[key])


        self.addItemToolBar = QtGui.QToolBar(self.tr("Add Item"))
        self.addItemToolBar.setObjectName("addItemToolbar")
        self.addToolBar(Qt.LeftToolBarArea, self.addItemToolBar)

        additem_action_list=['image','text','sep1','keyframe']

        for name in additem_action_list:
            if name not in self.additem_actions:
                self.addItemToolBar.addSeparator()
            else:
                self.addItemToolBar.addAction( self.additem_actions[name] )
            
        #self.addToolBarBreak(Qt.LeftToolBarArea)
        #self.addGooToolBar = QtGui.QToolBar(self.tr("Add Goo"))
        #self.addGooToolBar.setObjectName("addGooToolbar")
        #self.addToolBar(Qt.LeftToolBarArea, self.addGooToolBar)
        #for action in self.addgoo_actions:
        #    self.addGooToolBar.addAction( action )

        #self.showhideToolBar = self.addToolBar(self.tr("Show/Hide"))
        #self.showhideToolBar.setObjectName("showhideToolbar")

        #for elementtype in ('camera','fields','geom','gfx','goos','particles','labels'):
        #    self.showhideToolBar.addAction( self.showhide_actions[elementtype] )

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
        for group in 'camera game image resource text info ball goomod material anim actor keyframe'.split():
            self.group_icons[group] = QtGui.QIcon( ":/images/group-%s.png" % group )
        self.tree_view_by_element_world = {} # map of all tree views
        movie_dock, self.movieTree = self.createElementTreeView( 'Movie', metawog.TREE_MOVIE_MOVIE )
        resource_dock, self.resourceTree = self.createElementTreeView( 'Resource',
                                                                            metawog.TREE_MOVIE_RESOURCE,
                                                                            movie_dock )
        text_dock, self.textTree = self.createElementTreeView( 'Text',
                                                                            metawog.TREE_MOVIE_TEXT,
                                                                            resource_dock )

      #  dep_dock, self.depTree = self.createElementTreeView( 'Depends',
      #                                                                      metawog.TREE_MOVIE_DEPENDANCY,
      #                                                                      text_dock )

        movie_dock.raise_() # Makes the scene the default active tab
        
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
        # Settings should be stored in HKEY_CURRENT_USER\Software\WOGCorp\WOG Editor
        settings = QtCore.QSettings() #@todo makes helper to avoid QVariant conversions
        settings.beginGroup( "MainWindow" )
        settings.setValue( "wog_path", QtCore.QVariant( QtCore.QString(self._wog_path or u'') ) )
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
       # if self._game_model:
       #     self._game_model.restoreTestFiles()
            
        QtGui.QMainWindow.closeEvent(self,event)
        event.accept()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    # Set keys for settings
    app.setOrganizationName( "WOGCorp" )
    app.setOrganizationDomain( "goofans.com" )
    app.setApplicationName( "Goovie Maker" )

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