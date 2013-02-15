# To change this template, choose Tools | Templates
# and open the template in the editor.

from __future__ import with_statement
import xml.etree.ElementTree
import struct
import os.path

#For Converting a MOVIE or ANIMATION into movie.binltl format.
def exportBIN(self,element,directory,filename):
        if not os.path.isdir( directory ):
            os.makedirs( directory )
        output_path = os.path.join( directory, filename )
        if element.tag == 'movie':
            movie = binltl_Movie()
            movie.fromxml(element)
            file( output_path, 'wb' ).write( movie.packed("<") )
            file( output_path+"64", 'wb' ).write( movie.packed64() )
            file( os.path.splitext(output_path)[0]+".binbig", 'wb' ).write( movie.packed(">") )

        elif element.tag=='actor':
            animation = binltl_Animation()
            animation.fromxml(element)
            animation.loop = True  #standalone animations always loop
            animation.movielength = animation.length
            #Todo? Possible additional processing based on...
            # startposition = (0,0)
            # startscale = (1,1)
            file( output_path, 'wb' ).write( animation.packed() )
            file( output_path+"64", 'wb' ).write( animation.packed64() )
            file( os.path.splitext(output_path)[0]+".binbig", 'wb' ).write( animation.packed(">") )
        else:
            print "Cannot export ",element.tag,"as .binltl"

def exportXML(self,element,directory,filename):
        if not os.path.isdir( directory ):
            os.makedirs( directory )
        output_path = os.path.join( directory, filename )
        if element.tag == 'movie':
            movie = binltl_Movie()
            movie.fromxml(element)
            outputelement = movie.toXML()
            xml_data = xml.etree.ElementTree.tostring(outputelement,'utf-8')
            file( output_path, 'wb' ).write( CREATED_BY + xml_data.replace('><','>\n<') )
        elif element.tag=='actor':
            animation = binltl_Animation()
            animation.fromxml(element)
            animation.loop = True  #standalone animations always loop
            animation.movielength = animation.length
            outputelement = animation.toXML()
            xml_data = xml.etree.ElementTree.tostring(outputelement,'utf-8')
            file( output_path, 'wb' ).write( CREATED_BY + xml_data.replace('><','>\n<') )


class binltl_KeyFrame(object):
    def __init__(self, x=-1, y = -1, angle =-1,alpha=-1,color='255,255,255,255',nextFrame=-1,sound='', soundIdx=-1, interpolation='none', empty=False):
        if isinstance(x,binltl_KeyFrame):
            self.empty = x.empty
            self.x = x.x
            self.y = x.y
            self.angle = x.angle
            self.alpha = x.alpha
            self.color = x.color
            self.nextFrame = x.nextFrame
            self.soundIdx = x.soundIdx
            self.sound=x.sound
            self.interpolation = x.interpolation
        else:
            self.empty = empty
            self.x = x
            self.y = y
            self.angle = angle
            self.alpha = alpha
            self.color = color
            self.nextFrame = nextFrame
            self.soundIdx = soundIdx
            self.sound=sound
            self.interpolation = interpolation
    @property
    def interp(self):
        return ['none','linear'].index(self.interpolation)
    def packed(self,endianchar):
        return struct.pack(endianchar+"ffflllll", self.x,self.y,self.angle,self.alpha,self.colorstrToInt(self.color,endianchar),self.nextFrame,self.soundIdx,self.interp)
    def packed64(self):
        return struct.pack("<ffflllll", self.x,self.y,self.angle,self.alpha,self.colorstrToInt(self.color,"<"),self.nextFrame,self.soundIdx,self.interp)

#    def colorToInt(self,color):
#        return struct.pack("BBBB", color[0],color[1],color[2],color[3])

    def colorstrToInt(self,colorstr, endianchar):
        colorraw = colorstr.split(',')
        color = [int(c) for c in colorraw]
        return struct.unpack(endianchar+ "l",struct.pack("BBBB", color[2],color[1],color[0],255))[0]

#    def intToColor(self,rgb_int):
#        return struct.unpack("BBBB", rgb_int)


class binltl_Transform(object):
    def __init__(self ):
            self.keyFrames = []
            self.soundTable = ''
            self.transform_type = ''

    def addFinalFrame(self):
        print "Adding final frame to ",self.transform_type
        if self.transform_type=='sound':
            self.keyFrames.append(binltl_KeyFrame(empty=False))
            return
        kf = None
        for i,keyframe in enumerate(reversed(self.keyFrames)):
            if not keyframe.empty:
                print "Found used frame",i,keyframe
                kf = keyframe
                break
        if kf is not None:
            print "Adding Frame - ", kf
            newkf = binltl_KeyFrame(kf)
            self.keyFrames.append(newkf)
            newkf.interpolation='none'
            print "newkf=",newkf.x,newkf.y,newkf.angle,newkf.alpha,newkf.empty
        else:
           print "AddFinalFrame: unused transform", self.transform_type,".. How's that happened?"


    def clean(self):
        #print "Clean Transform : ",self.transform_type
        # Claning a transform means...
        # if last frame is empty,
        if self.transform_type!='sound':
            if self.keyFrames[-1].empty:
                print "last frame is empty"
                kf = None
                for i,keyframe in enumerate(reversed(self.keyFrames)):
                    if not keyframe.empty:
                        print "previous frame",i,keyframe
                        kf = keyframe
                        break
                if kf is not None:
                     #and the previous used frame is interpolated..
                    if kf.interp==1:
                        # clone the value(s) from the previous used frame
                        print "Cleaning with ",kf
                        newkf = binltl_KeyFrame(kf)
                        self.keyFrames.pop()
                        self.keyFrames.append(newkf)
                else:
                   print "Clean: unused transform", self.transform_type,".. How's that happened?"

        # ensureing the last frame is set to interplation 'none'
        self.keyFrames[-1].interpolation='none'
        #if self.keyFrames[-1].empty:
        #    print "fixing empty last frame"
        #    self.keyFrames[-1].empty=False

        nextframe = -1
        i = len(self.keyFrames)
        for keyframe in reversed(self.keyFrames):
            keyframe.nextFrame = nextframe
            i-=1
            if not keyframe.empty:
                nextframe = i

    def addFrameToElement(self,element,nFrame):
            keyframe = self.keyFrames[nFrame]
            if keyframe.empty:
                return
            if self.transform_type=='translate':
                element.set('position',str(keyframe.x)+","+str(keyframe.y))
            elif self.transform_type=='rotate':
                element.set('angle',str(keyframe.angle))
            elif self.transform_type=='scale':
                element.set('scale',str(keyframe.x)+","+str(keyframe.y))
            elif self.transform_type=='alpha':
                element.set('alpha',str(keyframe.alpha))
            elif self.transform_type=='color':
                element.set('color',str(keyframe.color))
            elif self.transform_type=='sound':
                element.set('sound',str(keyframe.sound))

            # Interpolation is "tricky"
            # For now.. if any transform is "linear" set it
            if keyframe.interpolation=='linear':
                element.set('interpolation','linear')

    def toXML(self):
        self.clean()
        transform = xml.etree.ElementTree._ElementInterface('transform',{'type':self.transform_type})
        for i,keyframe in enumerate(self.keyFrames):
            if not keyframe.empty:
                element = xml.etree.ElementTree._ElementInterface('keyframe',{'frame':str(i)})
                if self.transform_type=='translate':
                    element.set('x',str(keyframe.x))
                    element.set('y',str(keyframe.y))
                elif self.transform_type=='rotate':
                    element.set('angle',str(keyframe.angle))
                elif self.transform_type=='scale':
                    element.set('x',str(keyframe.x))
                    element.set('y',str(keyframe.y))
                elif self.transform_type=='alpha':
                    element.set('alpha',str(keyframe.alpha))
                elif self.transform_type=='color':
                    element.set('color',str(keyframe.color))
                elif self.transform_type=='sound':
                    element.set('sound',str(keyframe.sound))
                if keyframe.interpolation=='linear':
                    element.set('interpolation','linear')
                    element.set('nextframe',str(keyframe.nextFrame))
                transform.append(element)
        return transform


    def fromxml(self, element, transform_type):
            self.transform_type = transform_type
            self.keyFrames = []
            self.soundTable = ''
            for keyframe in element.findall('keyframe'):
                if transform_type=='translate':
                    pos = keyframe.get('position',None)
                    if pos is not None:
                        framex,framey = pos.split(',')
                        self.keyFrames.append(binltl_KeyFrame(x=float(framex), y=float(framey),interpolation = keyframe.get('interpolation','none')))
                    else:
                        self.keyFrames.append(binltl_KeyFrame(empty=True))
                elif transform_type=='scale':
                    scale = keyframe.get('scale',None)
                    if scale is not None :
                        framex,framey = scale.split(',')
                        self.keyFrames.append(binltl_KeyFrame(x=float(framex), y=float(framey),interpolation = keyframe.get('interpolation','none')))
                    else:
                        self.keyFrames.append(binltl_KeyFrame(empty=True))
                elif transform_type=='rotate':
                    framex = keyframe.get('angle',None)
                    if framex is not None:
                        self.keyFrames.append(binltl_KeyFrame(angle=float(framex),interpolation = keyframe.get('interpolation','none')))
                    else:
                        self.keyFrames.append(binltl_KeyFrame(empty=True))
                elif transform_type=='color':
                    framex = keyframe.get('color',None)
                    if framex is not None:
                        self.keyFrames.append(binltl_KeyFrame(color=framex,interpolation = keyframe.get('interpolation','none')))
                    else:
                        self.keyFrames.append(binltl_KeyFrame(empty=True))
                elif transform_type=='alpha':
                    framex = keyframe.get('alpha',None)
                    if framex is not None:
                        self.keyFrames.append(binltl_KeyFrame(alpha=int(framex),interpolation = keyframe.get('interpolation','none')))
                    else:
                        self.keyFrames.append(binltl_KeyFrame(empty=True))
                elif transform_type=='sound':
                    framex = keyframe.get('sound',None)
                    if framex is not None:
                        # get soundidx
                        self.keyFrames.append(binltl_KeyFrame(sound = framex, soundIdx=len(self.soundTable)))
                        self.soundTable+=framex+'\x00'
                    else:
                        self.keyFrames.append(binltl_KeyFrame(empty=True))
                else:
                    print "Unrecognised Transform Type : ",transform_type, element
                    self.keyFrames.append(binltl_KeyFrame(empty=True))

            #clean up soundtable
            if len(self.soundTable)==0:
                self.soundTable='\x00\x00\x00\x00'
            else:
                while (len(self.soundTable)%4) != 0:
                    self.soundTable+='\x00'

            #finally sort out nextFrame
            # last frame's nextFrame will always be -1
            # Although pointless since IGNORED!!!

    def fromraw(self, data, ppXForm, transform_type, nFrames,pStringTable):
            self.keyFrames = []
            self.soundTable = ''
            self.transform_type = transform_type

            for i in range(nFrames):
                pXForm = struct.unpack("L",data[ppXForm:ppXForm+4])[0]
                ppXForm+=4
                if pXForm==0:
                    self.keyFrames.append(binltl_KeyFrame(empty=True))
                else:
                    x,y,angle,alpha,color,nextFrame,soundIdx,interp = struct.unpack("ffflllll",data[pXForm:pXForm+32])
                    interpolation = ['none','linear'][interp]
                    if transform_type=='translate':
                        newkeyframe = binltl_KeyFrame(x=x,y=y,interpolation=interpolation)
                    elif transform_type=='rotate':
                        newkeyframe = binltl_KeyFrame(angle=angle,interpolation=interpolation)
                    elif transform_type=='scale':
                        newkeyframe = binltl_KeyFrame(x=x,y=y,interpolation=interpolation)
                    elif transform_type=='alpha':
                        newkeyframe = binltl_KeyFrame(alpha=alpha,interpolation=interpolation)
                    elif transform_type=='color':
                        newkeyframe = binltl_KeyFrame(color=color,interpolation=interpolation)
                    elif transform_type=='sound':
                        psound = pStringTable+soundIdx
                        sound = data[psound:data.find('\x00',psound)]
                        newkeyframe = binltl_KeyFrame(sound = sound, soundIdx = soundIdx)
                    self.keyFrames.append(newkeyframe)

    def packed(self,endianchar):
        # concat all the packed data for each keyframe
        output=''
        for keyframe in self.keyFrames:
            if not keyframe.empty:
                output+=keyframe.packed(endianchar)
        return output

    def packed64(self):
        # concat all the packed data for each keyframe
        output=''
        for keyframe in self.keyFrames:
            if not keyframe.empty:
                output+=keyframe.packed("<")
        return output


    def nframesUsed(self):
        nused=0
        for keyframe in self.keyFrames:
            if not keyframe.empty:
                nused+=1
        return nused

    def framesUsed(self):
        used=[]
        for keyframe in self.keyFrames:
            used.append(not keyframe.empty)
        return used

    def isSound(self):
        return (self.transform_type=='sound')


class binltl_Animation(object):
        def __init__(self):
            self.frameTimes = []
            self.transforms = {}
            self.transform_types = []
            self.otherframes = {}
            self.otherframe_types = []
            self.movielength = 0
            self.loop = False

        def addToElement(self, element):
            for i in range(self.numFrames):
                newkeyframe = xml.etree.ElementTree._ElementInterface('keyframe',{'time':str(self.frameTimes[i])})
                for transform in self.transforms.values():
                    transform.addFrameToElement(newkeyframe,i)
                for transform in self.otherframes.values():
                    transform.addFrameToElement(newkeyframe,i)
                element.append(newkeyframe)


        def toXML(self):
            self.clean()
            animation = xml.etree.ElementTree._ElementInterface('animation',{})
            # 2 tags
            # Frame timings
            frametimes = xml.etree.ElementTree._ElementInterface('frame-timings',{})
            for i in range(self.numFrames):
                frametimes.append(xml.etree.ElementTree._ElementInterface('timing',{'frame':str(i),'time':str(self.frameTimes[i])}))
            animation.append(frametimes)
            # Transforms
            transformelement = xml.etree.ElementTree._ElementInterface('transforms',{})
            for tname in self.transform_types:
                transformelement.append(self.transforms[tname].toXML())
            for transform in self.otherframes.values():
                transformelement.append(transform.toXML())
            animation.append(transformelement)
            return animation

        @property
        def length(self):
            return self.frameTimes[-1]

        def fromxml(self, xmlinfo):
            if isinstance(xmlinfo,xml.etree.ElementTree._ElementInterface):
                element = xml.etree.ElementTree.fromstring(xml.etree.ElementTree.tostring(xmlinfo))
            else:
                element = xml.etree.ElementTree.fromstring(xmlinfo)

            #and has... stuff
            self.loop = element.get('loop','false')=='true'
            self.frameTimes = []
            transform_raw = []
            for keyframe in element.findall('keyframe'):
                for key in keyframe.keys():
                    if key not in transform_raw:
                        transform_raw.append(key)
                self.frameTimes.append(float(keyframe.get('time')))

            # translate attributes found into transform types
            # as a by-product this also correctly orders transforms for output
            transform_translation = [('scale','scale'),('angle','rotate'),('position','translate')]
            self.transform_types = [b for a,b in transform_translation if a in transform_raw]
            self.otherframe_types = [entry for entry in ['alpha','color','sound'] if entry in transform_raw]
            self.transforms = {}
            for transform in self.transform_types:
                newtransform = binltl_Transform()
                newtransform.fromxml(element,transform)
                self.transforms[transform] = newtransform
            self.otherframes = {}
            for otherframe_type in self.otherframe_types:
                newtransform = binltl_Transform()
                newtransform.fromxml(element,otherframe_type)
                self.otherframes[otherframe_type] = newtransform

        def fromraw(self,data):
            self.transforms = {}
            self.transform_types = []
            self.otherframes = {}
            self.otherframe_types = []

            hasColor,hasAlpha,hasSound,hasTransform,nTransforms,nFrames = struct.unpack("LLLLLL",data[:24])
            pTransformTypes, pFrameTimes, pppXForm,ppAlphaFrames, ppColorFrames, ppSoundFrames = struct.unpack("LLLLLL",data[24:48])
            pStringTable = struct.unpack("L",data[48:52])[0]
            stringtable = data[pStringTable:]
            framepointers = {'alpha':ppAlphaFrames,'color':ppColorFrames,'sound':ppSoundFrames}

            if hasAlpha==1:
                self.otherframe_types.append('alpha')

            if hasColor==1:
                self.otherframe_types.append('color')

            if hasSound==1:
                self.otherframe_types.append('sound')

            self.frameTimes = []
            for i in range(nFrames):
                self.frameTimes.append(struct.unpack("f",data[pFrameTimes:pFrameTimes+4])[0])
                pFrameTimes+=4

            for i in range(nTransforms):
                transformid = struct.unpack("L",data[pTransformTypes:pTransformTypes+4])[0]
                pTransformTypes+=4
                transformtype = ['scale','rotate','translate'][transformid]
                self.transform_types.append(transformtype)
                ppXForm =struct.unpack("L",data[pppXForm:pppXForm+4])[0]
                pppXForm+=4
                newtransform = binltl_Transform()
                newtransform.fromraw(data, ppXForm,transformtype, nFrames,pStringTable)
                self.transforms[transformtype] = newtransform

            for otherframes in self.otherframe_types:
                pointer = framepointers[otherframes]
                newtransform = binltl_Transform()
                newtransform.fromraw(data, pointer, otherframes, nFrames,pStringTable)
                self.otherframes[otherframes] = newtransform

        @property
        def numFrames(self):
            return len(self.frameTimes)

        @property
        def numTransforms(self):
            return len(self.transforms)

        @property
        def numOtherFrames(self):
            return len(self.otherframe_types)

        @property
        def hasTransform(self):
            if len(self.transforms)>0:
                return 1
            return 0

        def has(self,frametype):
            if (frametype in self.otherframe_types):
                if self.otherframes[frametype].nframesUsed() > 0:
                    return 1
            return 0

        @property
        def hasColor(self):
            return self.has('color')
        @property
        def hasAlpha(self):
            return self.has('alpha')
        @property
        def hasSound(self):
            return self.has('sound')

        def clean(self):
            if not self.loop:
              if len(self.frameTimes)>1:
                 if self.movielength > self.frameTimes[-1]:
                    # setFinalFrame
                    # Duplicate last used frame in all transforms at movielength
                    # and set interpolation none
                    self.frameTimes.append(self.movielength)
                    for transformtype in self.transform_types:
                        self.transforms[transformtype].addFinalFrame()
                    for transformtype in self.otherframe_types:
                        self.otherframes[transformtype].addFinalFrame()
            
            print  self.frameTimes
            for transformtype in self.transform_types:
                self.transforms[transformtype].clean()
            for transformtype in self.otherframe_types:
                self.otherframes[transformtype].clean()

            # for each transform check for open-ended interpolation to / past last frame

        def packed(self,endianchar):
            #Clean up / Tweak Animation for output
            self.clean()
            pointer=4*6 + 4*7
#+0x00:      int mHasColor;
#+0x04:      int mHasAlpha;
#+0x08:      int mHasSound;
#+0x0c:      int mHasTransform;
#+0x10:      int mNumTransforms;
#+0x14:      int mNumFrames;
            output = struct.pack(endianchar+"LLLLLL", self.hasColor,self.hasAlpha,self.hasSound, self.hasTransform,self.numTransforms,self.numFrames )
            output += struct.pack(endianchar+"L", pointer) #+0x18:      TransformType *mTransformTypes;
            pointer+= 4*self.numTransforms
            output += struct.pack(endianchar+"L", pointer) #+0x1c:      float *mFrameTimes;
            pointer+= 4*self.numFrames
            output += struct.pack(endianchar+"L", pointer) #+0x20:      keyframe ***mXformFrames;
            pointer+= 4*self.numTransforms + 4*self.numTransforms*self.numFrames
            output += struct.pack(endianchar+"L", pointer) #+0x24:      keyframe **mAlphaFrames;
            pointer+= 4*self.numFrames
            output += struct.pack(endianchar+"L", pointer) #+0x28:      keyframe **mColorFrames;
            pointer+= 4*self.numFrames
            output += struct.pack(endianchar+"L", pointer) #+0x2c:      keyframe **mSoundFrames;
            pointer+= 4*self.numFrames
            output += struct.pack(endianchar+"L", pointer) #+0x30:      const char *pStringTable;
            if self.hasSound==1:
                pointer+= len(self.otherframes['sound'].soundTable)
            else:
                pointer+=4

            # That's the first raft of poiners done, so now we need a bit of data
            #reset pointer to local position
            datapointer = pointer
            pointer = len(output)

            # transform types data
            transform_id = {'scale':0,'rotate':1,'translate':2}
            for transform in self.transform_types:
                output += struct.pack(endianchar+"L", transform_id[transform])
                pointer +=4

            #frame times data
            for time in self.frameTimes:
                output += struct.pack(endianchar+"f", time)
                pointer +=4

            # now back to pointers again **XForm
            pointer+=4*self.numTransforms
            for transform in self.transform_types:
                output += struct.pack(endianchar+"L", pointer)
                pointer += 4*self.numFrames

            # from here on it's just pointers to keyframes..
            # which are all 32bytes long
            # BUT!!!
            # some pointers will be null and those frames skipped in the table so....

            #for each transform retrieve a list of the used frames
            #if a frame is used output pointer increment
            #otherwise output null pointer

            pointer = datapointer
            for transformtype in self.transform_types:
                for used in self.transforms[transformtype].framesUsed():
                    if used:
                        output += struct.pack(endianchar+"L", pointer)
                        pointer += 32
                    else:
                        output += struct.pack(endianchar+"L", 0 )

            for frame_type in ['alpha','color','sound']:
                if self.has(frame_type):
                    for used in self.otherframes[frame_type].framesUsed():
                        if used:
                            output += struct.pack(endianchar+"L", pointer)
                            pointer += 32
                        else:
                            output += struct.pack(endianchar+"L", 0 )
                else:
                    for i in range(self.numFrames):
                        output += struct.pack(endianchar+"L", 0)

            # Back to data
            # and sound table if there is one. (4 nulls if not - per 2DBoy files)
            if self.hasSound==1:
                output += self.otherframes['sound'].soundTable
            else:
                output += '\x00\x00\x00\x00'
            #Now the XForm Frames
            for transformtype in self.transform_types:
                output+=self.transforms[transformtype].packed(endianchar)
            # now alpha , color , sound if present
            for otherframe_type in self.otherframe_types:
                output+=self.otherframes[otherframe_type].packed(endianchar)
            return output

        def packed64(self):
            #Clean up / Tweak Animation for output
            self.clean()
            pointer=4*6 + 8*7
#+0x00:      int mHasColor;
#+0x04:      int mHasAlpha;
#+0x08:      int mHasSound;
#+0x0c:      int mHasTransform;
#+0x10:      int mNumTransforms;
#+0x14:      int mNumFrames;
            output = struct.pack("<LLLLLL", self.hasColor,self.hasAlpha,self.hasSound, self.hasTransform,self.numTransforms,self.numFrames )
            output += struct.pack("<LL", pointer,0) #+0x18:      TransformType *mTransformTypes;
            pointer+= 8*self.numTransforms
            output += struct.pack("<LL", pointer,0) #+0x20:      float *mFrameTimes;
            pointer+= 8*self.numFrames
            output += struct.pack("<LL", pointer,0) #+0x28:      keyframe ***mXformFrames;
            pointer+= 8*self.numTransforms + 8*self.numTransforms*self.numFrames
            output += struct.pack("<LL", pointer,0) #+0x30:      keyframe **mAlphaFrames;
            pointer+= 8*self.numFrames
            output += struct.pack("<LL", pointer,0) #+0x38:      keyframe **mColorFrames;
            pointer+= 8*self.numFrames
            output += struct.pack("<LL", pointer,0) #+0x40:      keyframe **mSoundFrames;
            pointer+= 8*self.numFrames
            output += struct.pack("<LL", pointer,0) #+0x48:      const char *pStringTable;
            if self.hasSound==1:
                pointer+= len(self.otherframes['sound'].soundTable)
            else:
                pointer+=4

            # That's the first raft of poiners done, so now we need a bit of data
            #reset pointer to local position
            datapointer = pointer
            pointer = len(output)

            # transform types data
            transform_id = {'scale':0,'rotate':1,'translate':2}
            for transform in self.transform_types:
                output += struct.pack("<L", transform_id[transform])
                pointer +=4

            #frame times data
            for time in self.frameTimes:
                output += struct.pack("<f", time)
                pointer +=4

            # now back to pointers again **XForm
            pointer+=8*self.numTransforms
            for transform in self.transform_types:
                output += struct.pack("<LL", pointer,0)
                pointer += 8*self.numFrames

            # from here on it's just pointers to keyframes..
            # which are all 32bytes long
            # BUT!!!
            # some pointers will be null and those frames skipped in the table so....

            #for each transform retrieve a list of the used frames
            #if a frame is used output pointer increment
            #otherwise output null pointer

            pointer = datapointer
            for transformtype in self.transform_types:
                for used in self.transforms[transformtype].framesUsed():
                    if used:
                        output += struct.pack("<LL", pointer,0)
                        pointer += 32
                    else:
                        output += struct.pack("<LL",0, 0 )

            for frame_type in ['alpha','color','sound']:
                if self.has(frame_type):
                    for used in self.otherframes[frame_type].framesUsed():
                        if used:
                            output += struct.pack("<LL", pointer,0)
                            pointer += 32
                        else:
                            output += struct.pack("<LL", 0 ,0)
                else:
                    for i in range(self.numFrames):
                        output += struct.pack("<LL", 0,0)

            # Back to data
            # and sound table if there is one. (4 nulls if not - per 2DBoy files)
            if self.hasSound==1:
                output += self.otherframes['sound'].soundTable
            else:
                output += '\x00\x00\x00\x00'
            #Now the XForm Frames
            for transformtype in self.transform_types:
                output+=self.transforms[transformtype].packed64()
            # now alpha , color , sound if present
            for otherframe_type in self.otherframe_types:
                output+=self.otherframes[otherframe_type].packed64()
            return output

class binltl_Movie(object):
    def __init__(self):
            self.length = 0
            self.actors = []
            self.animations = []
    
    def toelement(self):
            element = xml.etree.ElementTree._ElementInterface('movie',{'length':str(self.length)})
            for actor in self.actors:
                new_actor_element = actor.toelement()
                self.animations[actor].addToElement(new_actor_element)
                element.append(new_actor_element)
            return element

    def toXML(self):
            element = xml.etree.ElementTree._ElementInterface('movie',{'length':str(self.length)})
            for actor in self.actors:
                new_actor_element = actor.toXML()
                new_actor_element.append(self.animations[actor].toXML())
                element.append(new_actor_element)
            return element

    def fromxml(self, xmlinfo):
            if isinstance(xmlinfo,xml.etree.ElementTree._ElementInterface):
                element = xml.etree.ElementTree.fromstring(xml.etree.ElementTree.tostring(xmlinfo))
            else:
                element = xml.etree.ElementTree.fromstring(xmlinfo)

            self.actors = []
            self.animations = {}
            self.length = 0
            for actor in element.findall('actor'):
                newactor = binltl_Actor()
                newactor.fromxml(actor)
                newanim = binltl_Animation()
                newanim.fromxml(actor)
                if newanim.length > self.length:
                    self.length = newanim.length
                if newactor.visible:
                    self.actors.append(newactor)
                    self.animations[newactor] = newanim
            self.actors.sort(key= binltl_Actor.depth)

            #tell the animations the movielength so they can clean if necessary
            for actor in self.actors:
                self.animations[actor].movielength = self.length

    def fromraw(self,data):
            length, nActors, pActors, ppAnims,pStringTable = struct.unpack("fLLLL", data[:20])
            stringtable = data[pStringTable:]
            self.actors = []
            self.animations = {}
            pointer = 20
            self.length = 0
            pAnim = struct.unpack("L", data[ppAnims:ppAnims+4])[0]
            for i in range(nActors):
                #print "Actor ",i, "  pAnim :",pAnim
                newactor = binltl_Actor()
                newactor.fromraw(data[pointer:pointer+32],stringtable)
                pointer+=32
                self.actors.append(newactor)
                ppAnims+=4
                if i == nActors-1:
                    nAnim = len(data)
                else:
                    nAnim = struct.unpack("L", data[ppAnims:ppAnims+4])[0]
                newanim = binltl_Animation()
                #print "pAnim",pAnim,"  nAnim",nAnim
                newanim.fromraw(data[pAnim:nAnim])
                self.animations[newactor] = newanim
                if newanim.length > self.length:
                    self.length = newanim.length
                pAnim = nAnim

            for actor in self.actors:
                self.animations[actor].movielength = self.length


    @property
    def numActors(self):
        return len(self.actors)

    def packed(self,endianchar):

#+0x00:       float length;
#+0x04:       int numActors;
#+0x08:       BinActor *pActors;
#+0x0c:       BinImageAnimation **ppAnims;
            output = struct.pack(endianchar+"fLLL", self.length, self.numActors,20,20+32*self.numActors)

            pointer= 20+(32+4)*self.numActors
            actorop = ''
            animop = ''
            animpointers = []
            stringTable = ''
            for actor in self.actors:
                print "packing Actor ",actor.name
                if actor.type=='image':
                    actor.imageidx=len(stringTable)
                    stringTable+=actor.image + '\x00'
                else:
                    actor.textidx=len(stringTable)
                    stringTable+="$" + actor.text + '\x00'
                    actor.fontidx=len(stringTable)
                    stringTable+=actor.font + '\x00'
                actorop+=actor.packed(endianchar)
                newanim = self.animations[actor].packed(endianchar)
                animop+=newanim
                animpointers.append(pointer)
                pointer+=len(newanim)

            output+= struct.pack(endianchar+"L", pointer)   # const char *pStringTable;
            output+= actorop
            for animpointer in animpointers:
                output+= struct.pack(endianchar+"L", animpointer)
            output+= animop

            #clean up soundtable
            if len(stringTable)==0:
                stringTable='\x00\x00\x00\x00'
            else:
                while (len(stringTable)%4) != 0:
                    stringTable+='\x00'

            output+= stringTable
            return output

    def packed64(self):

#+0x00:       float length;
#+0x04:       int numActors;
#+0x08:       BinActor *pActors;
#+0x10:       BinImageAnimation **ppAnims;
            output = struct.pack("<fLLLLL", self.length, self.numActors,32,0,32+32*self.numActors,0)
            pointer= 32+(32+8)*self.numActors
            actorop = ''
            animop = ''
            animpointers = []
            stringTable = ''
            for actor in self.actors:
                print "packing Actor ",actor.name
                if actor.type=='image':
                    actor.imageidx=len(stringTable)
                    stringTable+=actor.image + '\x00'
                else:
                    actor.textidx=len(stringTable)
                    stringTable+="$" + actor.text + '\x00'
                    actor.fontidx=len(stringTable)
                    stringTable+=actor.font + '\x00'
                actorop+=actor.packed64()
                newanim = self.animations[actor].packed64()
                animop+=newanim
                animpointers.append(pointer)
                pointer+=len(newanim)

            output+= struct.pack("<LL", pointer,0)   # const char *pStringTable;
            output+= actorop
            for animpointer in animpointers:
                output+= struct.pack("<LL", animpointer,0)
            output+= animop

            #clean up soundtable
            if len(stringTable)==0:
                stringTable='\x00\x00\x00\x00'
            else:
                while (len(stringTable)%4) != 0:
                    stringTable+='\x00'

            output+= stringTable
            return output


class binltl_Actor(object):
    def __init__(self):
            self.type = ''
            self.image = None
            self.text = None
            self.font = None
            self.name = ''
            self.labelMaxWidth = -1
            self.labelWrapWidth = -1
            self.align = ''
            self._depth = 0
            self.imageidx =0
            self.textidx = 0
            self.fontidx=0
            self.visible = True
            self.loop = False
            
    def depth(self):
        return self._depth
    
    def toelement(self):
            attrib = {'type':self.type,'depth':str(self._depth)}
            if self.type=='image':
                attrib['image'] = self.image
            else:
                attrib['text'] = self.text
                attrib['font'] = self.font
                attrib['align'] = self.align
                if self.labelMaxWidth !=-1:
                    attrib['labelMaxWidth'] = str(self.labelMaxWidth)
                if self.labelWrapWidth !=-1:
                    attrib['labelWrapWidth'] = str(self.labelWrapWidth)
            element = xml.etree.ElementTree._ElementInterface('actor',attrib)
            return element

    def toXML(self):
            attrib = {'type':self.type,'depth':str(self._depth)}
            if self.type=='image':
                attrib['image'] = self.image
            else:
                attrib['text'] = "$" + self.text
                attrib['font'] = self.font
                attrib['align'] = self.align
                if self.labelMaxWidth !=-1:
                    attrib['labelMaxWidth'] = str(self.labelMaxWidth)
                if self.labelWrapWidth !=-1:
                    attrib['labelWrapWidth'] = str(self.labelWrapWidth)
            element = xml.etree.ElementTree._ElementInterface('actor',attrib)
            return element

    def fromxml(self, xmlinfo):
            if isinstance(xmlinfo,xml.etree.ElementTree._ElementInterface):
                element = xml.etree.ElementTree.fromstring(xml.etree.ElementTree.tostring(xmlinfo))
            else:
                element = xml.etree.ElementTree.fromstring(xmlinfo)

            self.type = element.get('type','image')
            self.image = element.get('image',None)
            self.text = element.get('text',None)

            if element.get('name','')!='':
                self.name = element.get('name','')
            elif self.type=='image':
                self.name = self.image
            else:
                self.name = self.text

            self.font = element.get('font',None)
            self.labelMaxWidth = float(element.get('labelMaxWidth',-1))
            self.labelWrapWidth = float(element.get('labelWrapWidth',-1))
            self.align = element.get('align','center')
            self._depth = float(element.get('depth',0))
            self.visible = element.get('visible','true')=='true'
            self.loop = element.get('loop','false')=='true'
            self.imageidx =0
            self.textidx = 0
            self.fontidx=0

    def fromraw(self, data,stringtable):
        atype,self.imageidx,self.textidx,self.fontidx,self.labelMaxWidth, self.labelWrapWidth, alignment, self._depth = struct.unpack("LLLLffLf",data[:32])
        self.type = ['image','text'][atype]
        self.align = ['left','center','right'][alignment]
        if self.type=='image':
            self.image = stringtable[self.imageidx:stringtable.find('\x00',self.imageidx)]
        else:
            self.text = stringtable[self.textidx+1:stringtable.find('\x00',self.textidx)]
            self.font = stringtable[self.fontidx:stringtable.find('\x00',self.fontidx)]

        #@todo : Autodetect Loop from movielength vs last frametime?

    @property
    def alignment(self):
        return ['left','center','right'].index(self.align)

    @property
    def typeid(self):
        return ['image','text'].index(self.type)

    def packed(self,endianchar):
#+0x00:       ActorType mType;
#+0x04:       int mImageStrIdx;
#+0x08:       int mLabelTextStrIdx;
#+0x0c:       int mFontStrIdx;
#+0x10:       float mLabelMaxWidth;
#+0x14:       float mLabelWrapWidth;
#+0x18:       AlignmentH mLabelJustification;
#+0x1c:       float mDepth;
        return struct.pack(endianchar+"LLLLffLf", self.typeid,self.imageidx,self.textidx,
                self.fontidx,self.labelMaxWidth,self.labelWrapWidth,self.alignment, self._depth )

    def packed64(self):
        return struct.pack("<LLLLffLf", self.typeid,self.imageidx,self.textidx,
                self.fontidx,self.labelMaxWidth,self.labelWrapWidth,self.alignment, self._depth )


