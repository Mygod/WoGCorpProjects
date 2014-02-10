using System;
using System.IO;
using System.Xml;
using System.Xml.Linq;

namespace Mygod.WorldOfGoo
{
    static class Extensions
    {
        internal static string GetString(this XDocument doc)
        {
            using (var ms = new MemoryStream(20000))
            {
                using (var xw = XmlWriter.Create(ms, new XmlWriterSettings { Indent = true })) doc.Save(xw);
                ms.Position = 0;    //reset to 0
                using (var sr = new StreamReader(ms)) return sr.ReadToEnd();
            }
        }

        internal static string GetString(this XElement element)
        {
            return new XDocument(element).GetString();
        }

        internal static XElement GetElement(this XContainer xc, XName name, string filePath)
        {
            var r = xc.Element(name);
            if (r == null) throw Exceptions.XmlElementDoesNotExist(filePath, name.LocalName);
            return r;
        }

        internal static string GetAttribute(this XElement e, XName name)
        {
            var attr = e.Attribute(name);
            return attr == null ? null : attr.Value;
        }

        internal static void SetAttribute(this XElement e, XName name, string value)
        {
            var attr = e.Attribute(name);
            if (attr == null) e.Add(new XAttribute(name, value));
            else attr.Value = value;
        }

        internal static void DoNothing<T>(this T t)
        {
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
