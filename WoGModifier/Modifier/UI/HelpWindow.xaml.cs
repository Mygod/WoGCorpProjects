using System;
using System.ComponentModel;
using System.IO;
using Mygod.WorldOfGoo.IO;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class HelpWindow
    {
        public HelpWindow()
        {
            InitializeComponent();
            Browser.Source = new Uri(Globalization.GetLocalizedPath(Path.Combine
                                        (AppDomain.CurrentDomain.BaseDirectory, "Resources/Help"), R.HelpExtension));
        }

        private void Hide(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }
    }
}
