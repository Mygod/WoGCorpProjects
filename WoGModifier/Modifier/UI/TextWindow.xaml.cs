using System.Windows;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    sealed partial class TextWindow
    {
        public TextWindow(string title, string properties, Window owner = null)
        {
            InitializeComponent();
            Title = title;
            TextBox.Text = properties;
            Owner = owner;
        }
    }
}
