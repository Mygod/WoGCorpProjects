namespace Mygod.WorldOfGoo.Modifier.UI
{
    sealed partial class TextWindow
    {
        public TextWindow(string title, string properties)
        {
            InitializeComponent();
            Title = title;
            TextBox.Text = properties;
        }

        public static void Show(string title, string properties)
        {
            new TextWindow(title, properties).Show();
        }
    }
}
