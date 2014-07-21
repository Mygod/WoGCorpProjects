using System;
using System.IO;
using System.Xml.Linq;

namespace Mygod.WorldOfGoo
{
    static class Extensions
    {
        internal static XElement GetElement(this XContainer xc, XName name, string filePath)
        {
            var r = xc.Element(name);
            if (r == null) throw Exceptions.XmlElementDoesNotExist(filePath, name.LocalName);
            return r;
        }
    }

    static class Exceptions
    {
        public static NotSupportedException NotSupported { get { return new NotSupportedException(); } }

        public static FileFormatException FileFormatError(string path, string msg)
        {
            return new FileFormatException(new Uri(path), msg);
        }

        public static FileFormatException XmlElementDoesNotExist(string path, string elementName)
        {
            return FileFormatError(path, string.Format(Resrc.ExceptionXmlElementDoesNotExist, elementName));
        }
    }
}
