"""Describes the structure and constraints of elements used in data file of WOG."""

from metaworld import *

# Declares all file types
TREE_GLOBAL_RESOURCE = describe_tree( 'game.resources' )
TREE_GLOBAL_FILES = describe_tree ('game.files')
TREE_GLOBAL_TEXT = describe_tree( 'game.text' )

TREE_MOVIE_MOVIE = describe_tree( 'movie.movie' )
TREE_MOVIE_RESOURCE = describe_tree( 'movie.resource' )
TREE_MOVIE_TEXT = describe_tree ('movie.text')
TREE_MOVIE_DEPENDANCY = describe_tree('movie.dep')

# Declares the world hierarchy
WORLD_MOVIE = describe_world( 'movie', trees_meta = [
    TREE_MOVIE_MOVIE,
    TREE_MOVIE_RESOURCE,
    TREE_MOVIE_TEXT,
    ] )

WORLD_GLOBAL = describe_world( 'game',
                               child_worlds = [ WORLD_MOVIE ],
                               trees_meta = [
    TREE_GLOBAL_RESOURCE,
    TREE_GLOBAL_TEXT,
    TREE_GLOBAL_FILES
    ] )


ANIMATIONS_ORIGINAL = ['ball_counter','ball_counter_ocd','blink','closer','discovery','hairblow',
                     'happyTreeDance','islandhairblow','island_name_in','island_name_loop',
                     'island_name_out','level_name_popup','ocdFlagWave','rot_1rps','treeBlow_leaf1',
                     'treeBlow_leaf2','treeBlow_leaf3','treeBlow_trunk']
ANIMATIONS_GLOBAL = []

#@DaB
FILE_ELEMENT= describe_element('file', attributes = [
                        string_attribute('name',mandatory = True),
                        string_attribute('type',mandatory = True),
                        string_attribute('hash'),
                        int_attribute('size')])
FOLDER_ELEMENT = describe_element('folder', attributes = [
        string_attribute('name',mandatory = True)],elements=[
        FILE_ELEMENT])
FOLDER_ELEMENT.add_elements([FOLDER_ELEMENT])
TREE_GLOBAL_FILES.add_elements ([
    describe_element('folder', exact_occurrence = 1,
      attributes = [ string_attribute('name',mandatory = True)],
      elements=[FILE_ELEMENT,FOLDER_ELEMENT])])

LANGUAGE_ATTRIBUTES=[]
for lang in ['de','es','fr','it','nl','pl']:
    LANGUAGE_ATTRIBUTES.append(string_attribute(lang,allow_empty=True,remove_empty=True))

ANIM_KEYFRAME= describe_element ('keyframe', min_occurrence=1, groups='keyframe', attributes = [
      real_attribute( 'time', min_value = 0 , mandatory=True ,display_id = True),
      xy_attribute( 'position', position=True, allow_empty=True,remove_empty=True), #map_to = ('x','y')
      scale_attribute( 'scale', min_value = 0,allow_empty=True,remove_empty=True),#, map_to = ('scale-x', 'scale-y')
      angle_degrees_attribute( 'angle', allow_empty=True,remove_empty=True) ,
      int_attribute( 'alpha', min_value = 0, max_value = 255, init = 255,allow_empty=True,remove_empty=True),
      rgb_attribute('color',allow_empty=True,remove_empty=True),
      enum_attribute( 'interpolation', ('none', 'linear'), allow_empty=True,remove_empty=True),
      reference_attribute( 'sound', reference_family = 'sound', reference_world = WORLD_MOVIE ,allow_empty=True,remove_empty=True) ] )

MOVIE_ACTOR = describe_element ('actor', min_occurrence = 1, groups='actor',attributes = [
      string_attribute( 'name', allow_empty=True,remove_empty=True,display_id = True ),
      enum_attribute( 'type', values = ('image', 'text') , init='image', mandatory=True ),
      real_attribute('depth', min_value=0,mandatory=True,init=0),
      bool_attribute('visible',allow_empty=True,remove_empty=True),
      bool_attribute('loop',allow_empty=True,remove_empty=True),
      reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_MOVIE, allow_empty=True,remove_empty=True,display_id = True),
      reference_attribute( 'text', reference_family = 'TEXT_LEVELNAME_STR', reference_world = WORLD_MOVIE, allow_empty=True,remove_empty=True,display_id = True),
      reference_attribute( 'font', reference_family = 'font', reference_world = WORLD_GLOBAL, allow_empty=True,remove_empty=True ),
      enum_attribute( 'align', ('right', 'center', 'left'), allow_empty=True,remove_empty=True ),
      real_attribute( 'labelMaxWidth', init = -1, allow_empty=True,remove_empty=True),
      real_attribute( 'labelWrapWidth', init = -1, allow_empty=True,remove_empty=True)
      ],  elements=[ ANIM_KEYFRAME ] )


TREE_MOVIE_MOVIE.add_elements( [
    describe_element( 'movie', exact_occurrence = 1, groups = 'camera',
        elements = [ MOVIE_ACTOR ] ) ] )

def _describe_resource_file( tree_meta, resource_world, is_global = False ):
    if is_global:
        resources_element = describe_element( 'Resources', min_occurrence = 1 )
    else:
        resources_element = describe_element( 'Resources', exact_occurrence = 1, read_only = True )
    resources_element.add_attributes( [
        identifier_attribute( 'id', mandatory = True, read_only = True, tooltip="Resource Id for this level\nMust be scene_{Levelname} (read only)",
                              reference_family = 'resources',
                              reference_world = resource_world ),
        ] )
    resources_element.add_elements( [
        describe_element( 'Image', groups = 'image', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'image',
                display_id = True, reference_world = resource_world ),
            path_attribute( 'path', strip_extension = '.png', mandatory = True )
            ] ),
        describe_element( 'Sound', groups = 'resource', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'sound',
                display_id = True, reference_world = resource_world ),
            path_attribute( 'path', strip_extension = '.ogg', mandatory = True )
            ] ),
        describe_element( 'SetDefaults', read_only = True, groups = 'resource', 
                          attributes = [
            string_attribute( 'path', mandatory = True, read_only = True ),
            string_attribute( 'idprefix', mandatory = True, allow_empty = True, read_only = True )
            ] )
        ] )
    if is_global:
        resources_element.add_elements( [
            describe_element( 'font', groups = 'resource', attributes = [
                identifier_attribute( 'id', mandatory = True, reference_family = 'font',
                    display_id = True, reference_world = resource_world ),
                path_attribute( 'path', strip_extension = '.png', mandatory = True ) # @todo also check existence of .txt
                ] )
        ] )
    
    tree_meta.add_elements( [
        # DUPLICATED FROM GLOBAL SCOPE => makes FACTORY function ?
        describe_element( 'ResourceManifest', exact_occurrence = 1, groups = 'resource',
                          attributes = [], elements = [
            resources_element
            ] )
        ] )

_describe_resource_file( TREE_MOVIE_RESOURCE, WORLD_MOVIE )

TREE_MOVIE_TEXT.add_elements( [ describe_element( 'strings', groups = 'text', exact_occurrence = 1, attributes = [],
        elements = [
        describe_element( 'string', groups = 'text', attributes = [
            identifier_attribute( 'id', mandatory = True, display_id = True,
                reference_family = 'TEXT_LEVELNAME_STR', reference_world = WORLD_MOVIE ),
            text_attribute( 'text', mandatory = True,tooltip="Use | symbol (pipe) to get new pages on signs, and new lines in labels" ),
            text_attribute( 'de' ,allow_empty=True,remove_empty=True),
            text_attribute( 'es' ,allow_empty=True,remove_empty=True),
            text_attribute( 'fr' ,allow_empty=True,remove_empty=True),
            text_attribute( 'it' ,allow_empty=True,remove_empty=True),
            text_attribute( 'nl' ,allow_empty=True,remove_empty=True),
            text_attribute( 'pt' ,allow_empty=True,remove_empty=True)
            ] )
        ] )
    ] )

GLOBAL_TREE_TEXT = describe_element( 'strings', exact_occurrence = 1, attributes = [], elements = [
        describe_element( 'string',min_occurrence=1 , attributes = [
            identifier_attribute( 'id', mandatory = True, display_id = True,
                reference_family = 'text', reference_world = WORLD_GLOBAL ),
            string_attribute( 'text', mandatory = True ),
            string_attribute( 'de' ),
            string_attribute( 'es' ),
            string_attribute( 'fr' ),
            string_attribute( 'it' ),
            string_attribute( 'nl' ),
            string_attribute( 'pt' )
            ] )
        ] )

TREE_GLOBAL_TEXT.add_elements( [GLOBAL_TREE_TEXT] )

DEP_IMAGE = describe_element('image',groups = 'image',read_only = True,attributes=[
      string_attribute('id',read_only = True),
      identifier_attribute('path',read_only = True,display_id=True,reference_family="imagedep",reference_world=WORLD_MOVIE)
      ,bool_attribute('found',read_only = True,mandatory=True,default=False)
])

DEP_SOUND = describe_element('sound',groups = 'resource',read_only = True, attributes=[
      string_attribute('id',read_only = True),
      identifier_attribute('path',read_only = True,display_id=True,reference_family="sounddep",reference_world=WORLD_MOVIE)
      ,bool_attribute('found',read_only = True,mandatory=True,default=False)
])

TREE_MOVIE_DEPENDANCY.add_elements([
        describe_element( 'dependancy',groups="goomod",
            read_only = True,exact_occurrence = 1, attributes = [],
            elements=[DEP_IMAGE,DEP_SOUND])
        ])

_describe_resource_file( TREE_GLOBAL_RESOURCE, WORLD_GLOBAL, is_global = True )


MOVIE_MOVIE_TEMPLATE = """\
<movie>
    <actor type="image" depth="0">
        <keyframe time="0" position="0,0" scale="1,1" alpha="255"/>
        <keyframe time="1"/>
    </actor>
</movie>"""

MOVIE_RESOURCE_TEMPLATE = """\
<ResourceManifest>
	<Resources id="movie_NewTemplate" >
		<SetDefaults path="./" idprefix="" />
	</Resources>
</ResourceManifest>
"""

MOVIE_TEXT_TEMPLATE ="""\
<strings spec-version="1.1"/>
"""

MOVIE_DEPENDANCY_TEMPLATE ="""\
<dependancy/>
"""

XSL_ADD_TEMPLATE="""\
<xsl:transform version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <!-- Copy everything not matched by another rule -->
  <xsl:template match="* | comment()">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>

  <!-- Append -->
  <xsl:template match="%(path)s">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates/>
      %(xml_data)s
    </xsl:copy>
  </xsl:template>
</xsl:transform>"""

#@DaB - New Resource Tree - Only has Fonts in
# to eliminate all the useless images and sounds appearing in the completer boxes.
GLOBAL_FONT_RESOURCES = """\
<ResourceManifest>
<Resources id="init">
<font  id="FONT_OUTLINE_18" path="res/fonts/TwCenMTCondensedExtraBold18"/>
<font  id="FONT_LOADING"                 path="res/fonts/TwCenMTCondensedExtraBold18"/>
<font  id="FONT_OUTLINE_26"              path="res/fonts/TwCenMTCondensedExtraBold26"/>
<font  id="FONT_SIGNPOST"                path="res/fonts/TwCenMTCondensedExtraBold36"/>
<font  id="FONT_BIGWHITE_52"             path="res/fonts/TwCenMTCondensedExtraBold52"/>
<font  id="FONT_INGAME36"                path="res/fonts/wogSmall"/>
<font  id="FONT_TITLE"                   path="res/fonts/wogBig"/>
<font  id="FONT_STAT"                    path="res/fonts/wog150numbers"/>
<font  id="FONT_CONSOLE"                 path="res/fonts/console"/>
</Resources>
</ResourceManifest>
"""

if __name__ == "__main__":
    print_world_meta( WORLD_GLOBAL )

