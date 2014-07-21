using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class GameTextWindow
    {
        public GameTextWindow(Game g)
        {
            DataContext = game = g;
            InitializeComponent();
            TextItemList.ItemsSource = g.Properties.Text;
            g.Properties.Config.LanguageChanged += RefreshDisplay;
        }

        private void RefreshDisplay(object sender, EventArgs e)
        {
            TextItemList.Items.Refresh();
        }

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly Game game;
        private IEnumerable<TextItem> SelectedTextItems
            { get { return TextItemList.SelectedItems.OfType<TextItem>(); } }

        private readonly Dictionary<TextItem, GameTextItemWindow>
            windows = new Dictionary<TextItem, GameTextItemWindow>();

        private void ProcessTextItem(object sender, RoutedEventArgs e)
        {
            foreach (var item in SelectedTextItems) ProcessTextItem(item);
        }
        public void ProcessTextItem(TextItem item)
        {
            if (!windows.ContainsKey(item)) windows.Add(item, new GameTextItemWindow(item));
            windows[item].Show();
            windows[item].Activate();
        }

        private void SaveText(object sender, ExecutedRoutedEventArgs e)
        {
            game.Properties.Text.Save();
        }

        private void AddTextItem(object sender, ExecutedRoutedEventArgs e)
        {
            var id = Dialog.Input(Resrc.EnterIDTitle, validCheck: i => !game.Properties.Text.Contains(i));
            if (id != null) game.Properties.Text.Add(new TextItem(game.Properties.Text, id));
        }

        private void CopyTextItem(object sender, ExecutedRoutedEventArgs e)
        {
            var item = SelectedTextItems.FirstOrDefault();
            if (item == null) return;
            var id = Dialog.Input(Resrc.EnterIDTitle, item.ID, validCheck: i => !game.Properties.Text.Contains(i));
            if (id != null) game.Properties.Text.Add(new TextItem(game.Properties.Text, id, item.ToArray()));
        }

        private void RemoveTextItems(object sender, ExecutedRoutedEventArgs e)
        {
            foreach (var item in SelectedTextItems.ToList()) game.Properties.Text.Remove(item);
        }

        private void EditTextXml(object sender, RoutedEventArgs e)
        {
            BinaryFile.Edit(game.Properties.Text, Settings.BinFileEditor);
        }

        private void SearchTextItem(object sender, ExecutedRoutedEventArgs e)
        {
            var id = Dialog.Input(Resrc.EnterIDTitle, validCheck: i => game.Properties.Text.Contains(i),
                                  list: game.Properties.Text.Select(i => i.ID));
            if (id == null) return;
            TextItemList.SelectedItem = game.Properties.Text[id];
            TextItemList.ScrollIntoView(game.Properties.Text[id]);
            ProcessTextItem(game.Properties.Text[id]);
        }
    }
}
