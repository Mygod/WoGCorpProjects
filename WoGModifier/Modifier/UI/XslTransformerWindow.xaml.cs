using System;
using System.IO;
using System.Windows;
using System.Xml;
using System.Xml.Xsl;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class XslTransformerWindow
    {
        public XslTransformerWindow()
        {
            InitializeComponent();
        }

        private readonly XslCompiledTransform transform = new XslCompiledTransform();

        private void Transform(object sender, RoutedEventArgs e)
        {
            try
            {
                transform.Load(XmlReader.Create(new StringReader(Xsl.Text)), new XsltSettings(true, true),
                                                new XmlUrlResolver());
                var writer = new StringWriter();
                transform.Transform(XmlReader.Create(new StringReader(Source.Text)), null, 
                    XmlWriter.Create(writer, new XmlWriterSettings { Indent = true }), new XmlUrlResolver());
                Result.Text = writer.ToString();
            }
            catch (Exception exc)
            {
                Dialog.Error(this, Resrc.XslTransformFailed, e: exc);
            }
        }
    }
}
