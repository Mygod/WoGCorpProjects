using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows.Controls;
using System.Windows.Input;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    internal partial class PlayerLevelsWindow
    {
        public PlayerLevelsWindow(ProfilePlayer p)
        {
            DataContext = player = p;
            InitializeComponent();
            TotalText.DataContext = LevelRecordGrid.ItemsSource = p.PlayedLevels;
            p.PlayedLevels.ItemPropertyChanged += UpdateTotal;
        }

        private void UpdateTotal(object sender, PropertyChangedEventArgs e)
        {
            var expression = TotalText.GetBindingExpression(TextBlock.TextProperty);
            if (expression != null) expression.UpdateTarget();
        }

        private readonly ProfilePlayer player;

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private void PlayedLevelSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = LevelRecordGrid.SelectedItem != null;
        }

        private void SinglePlayedLevelSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = LevelRecordGrid.SelectedItems.Count == 1;
        }

        private IEnumerable<PlayedLevel> SelectedLevels { get { return LevelRecordGrid.SelectedItems.OfType<PlayedLevel>(); } }

        private void EditMostGoos(object sender, ExecutedRoutedEventArgs e)
        {
            var str = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().MostGoos.ToString(), EnterType.Int32);
            if (str == null) return;
            var i = int.Parse(str);
            foreach (var level in SelectedLevels) level.MostGoos = i;
        }

        private void EditFewestMoves(object sender, ExecutedRoutedEventArgs e)
        {
            var str = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().FewestMoves.ToString(), EnterType.Int32);
            if (str == null) return;
            var i = int.Parse(str);
            foreach (var level in SelectedLevels) level.FewestMoves = i;
        }

        private void EditFewestSeconds(object sender, ExecutedRoutedEventArgs e)
        {
            var str = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().FewestSeconds.ToString(), EnterType.Int32);
            if (str == null) return;
            var i = int.Parse(str);
            foreach (var level in SelectedLevels) level.FewestSeconds = i;
        }

        private void SkipLevels(object sender, ExecutedRoutedEventArgs e)
        {
            foreach (var level in SelectedLevels) level.Skipped = true;
        }

        private void AddPlayedLevel(object sender, ExecutedRoutedEventArgs e)
        {
            var id = Dialog.Input(Resrc.EnterIDTitle, validCheck: i => !player.PlayedLevels.Contains(i));
            if (id != null) player.PlayedLevels.Add(new PlayedLevel(player, id));
        }

        private void CopyPlayedLevel(object sender, ExecutedRoutedEventArgs e)
        {
            var level = SelectedLevels.First();
            if (level == null) return;
            var id = Dialog.Input(Resrc.EnterIDTitle, level.LevelID, validCheck: i => !player.PlayedLevels.Contains(i));
            if (id != null) player.PlayedLevels.Add(new PlayedLevel(player, id, level.MostGoos, level.FewestMoves, level.FewestSeconds));
        }

        private void RemovePlayedLevel(object sender, ExecutedRoutedEventArgs e)
        {
            foreach (var level in SelectedLevels.ToList()) player.PlayedLevels.Remove(level);
        }
    }
}
