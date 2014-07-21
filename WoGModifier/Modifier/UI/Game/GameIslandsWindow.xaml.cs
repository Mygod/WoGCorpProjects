using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    internal partial class GameIslandsWindow
    {
        public GameIslandsWindow(Game g)
        {
            DataContext = game = g;
            InitializeComponent();
            IslandGrid.ItemsSource = game.Res.Islands;
            MapColumn.ItemsSource = game.Res.Levels;
            IconColumn.ItemsSource = game.Resources.OfType<ImageResource>();
        }

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly Game game;

        private IEnumerable<Island> SelectedIslands
        {
            get { return IslandGrid.SelectedItems.OfType<Island>(); }
        }

        private void IslandSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = IslandGrid.SelectedItem != null;
        }

        private void SingleIslandSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = IslandGrid.SelectedItems.Count == 1;
        }

        private void MultipleIslandSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = IslandGrid.SelectedItems.Count > 1;
        }

        private readonly Dictionary<Island, GameIslandWindow> gameIslandWindows =
            new Dictionary<Island, GameIslandWindow>();

        private void BrowseIslandLevels(object sender, RoutedEventArgs e)
        {
            foreach (var island in SelectedIslands)
            {
                if (!gameIslandWindows.ContainsKey(island)) gameIslandWindows.Add(island, new GameIslandWindow(island));
                gameIslandWindows[island].Show();
                gameIslandWindows[island].Activate();
            }
        }

        private void SaveIslands(object sender, ExecutedRoutedEventArgs e)
        {
            foreach (var island in SelectedIslands) island.Save();
        }

        private void EditIslandsXml(object sender, RoutedEventArgs e)
        {
            foreach (var island in SelectedIslands) BinaryFile.Edit(island, Settings.BinFileEditor);
        }

        private void EditIslandsName(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedIslands.First().Name);
            if (value != null) foreach (var material in SelectedIslands) material.Name = value;
        }

        private void EditIslandsMap(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedIslands.First().Map,
                                     list: MapColumn.ItemsSource);
            if (value != null) foreach (var material in SelectedIslands) material.Map = value;
        }

        private void EditIslandsIcon(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedIslands.First().Icon,
                                     list: IconColumn.ItemsSource);
            if (value != null) foreach (var material in SelectedIslands) material.Icon = value;
        }

        private void CopyIsland(object sender, ExecutedRoutedEventArgs e)
        {
            var island = SelectedIslands.FirstOrDefault();
            if (island == null) return;
            var str = Dialog.Input(Resrc.EnterIslandToCopyNumber, island.Number.ToString(CultureInfo.InvariantCulture),
                                   EnterType.Int32, s =>
            {
                var i = int.Parse(s);
                return i >= 1 && i <= 5 && i != island.Number;
            });
            if (str == null) return;
            var value = int.Parse(str);
            var t = game.Res.Islands[value];
            if (gameIslandWindows.ContainsKey(t))
            {
                gameIslandWindows[t].Close();
                gameIslandWindows.Remove(t);
            }
            game.Res.Islands.Remove(t);
            var target = new Island(game.Res.Islands, value, island.GetXmlString());
            game.Res.Islands.Insert(target.Number - 1, target);
        }

        private void SwapIslands(object sender, ExecutedRoutedEventArgs e)
        {
            var islands = SelectedIslands.ToList();
            for (var i = 1; i < islands.Count; i++)
                game.Res.Islands.SwapIslands(islands[i].Number, islands[i - 1].Number);
        }
    }
}
