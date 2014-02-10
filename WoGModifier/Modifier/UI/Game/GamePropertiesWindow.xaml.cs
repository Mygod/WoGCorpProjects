using System.ComponentModel;
using System.Windows;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class GamePropertiesWindow
    {
        public GamePropertiesWindow(Game g)
        {
            DataContext = (game = g).Properties.Config;
            game.Properties.Text.DoNothing();
            InitializeComponent();
        }

        private readonly Game game;

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private void Save(object sender, RoutedEventArgs e)
        {
            game.Properties.Config.Save();
        }
    }
}
