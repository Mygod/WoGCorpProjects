# To change this template, choose Tools | Templates
# and open the template in the editor.
ISSUE_LEVEL_NONE = 0
ISSUE_LEVEL_ADVICE = 1
ISSUE_LEVEL_WARNING = 2
ISSUE_LEVEL_CRITICAL =4
ERROR_URL = 'http://goofans.com/developers/world-of-goo-level-editor/reference-guide/errors-and-warnings#%d'
ERROR_MORE_INFO = '&nbsp; <a href="'+ERROR_URL+'"><small><i>[more info]</i></small></a>'
ERROR_FRONT=[''
,'Advice: '
,'<b>Warning:</b> '
,''
,'<font color="#BF0000"><b>CRITICAL:</b></font> ']

ERROR_INFO={0:[ISSUE_LEVEL_NONE,''],
#Resource Errors
    201:[ISSUE_LEVEL_WARNING,'Image file extensions must be png (lowercase) %s'],
    202:[ISSUE_LEVEL_ADVICE,'%s unused'],
    203:[ISSUE_LEVEL_WARNING,'Sound file extensions must be ogg (lowercase) %s'],
    204:[ISSUE_LEVEL_ADVICE,'%s unused'],
    205:[ISSUE_LEVEL_ADVICE,'Text resource %s unused'],

# Export Animation Errors / Warnings
    601:[ISSUE_LEVEL_ADVICE,'Frame %s : Alpha does not work without <tt>color</tt> attribute'],
    602:[ISSUE_LEVEL_ADVICE,'Frame %s : Alpha does not work without <tt>color</tt> and <tt>interpolation</tt>'],
    603:[ISSUE_LEVEL_ADVICE,'Frame %s : Alpha does not work without <tt>interpolation</tt>'],
    604:[ISSUE_LEVEL_CRITICAL,'Animation has <tt>color</tt> but no <tt>alpha</tt>'],
    605:[ISSUE_LEVEL_ADVICE,'No keyframe at time=0'],
    606:[ISSUE_LEVEL_ADVICE,'Start position is not (0,0) image will be offset'],
    607:[ISSUE_LEVEL_ADVICE,'Start and end %s do not match']
}
