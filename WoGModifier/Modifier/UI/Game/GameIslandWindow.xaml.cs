using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using Mygod.Windows.Controls;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    internal partial class GameIslandWindow
    {
        public GameIslandWindow(Island i)
        {
            DataContext = island = i;
            InitializeComponent();
            IslandLevelGrid.ItemsSource = i;
            NameColumn.ItemsSource = SubtitleColumn.ItemsSource = island.Parent.GameParent.Properties.Text;
            NameColumn.DisplayMemberPath = SubtitleColumn.DisplayMemberPath = "ID";
        }

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly Island island;
        private IEnumerable<IslandLevel> SelectedLevels
            { get { return IslandLevelGrid.SelectedItems.OfType<IslandLevel>(); } }

        private void IslandLevelSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = IslandLevelGrid.SelectedItem != null;
        }

        private void SingleIslandLevelSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = IslandLevelGrid.SelectedItems.Count == 1;
        }

        private void EditIslandXml(object sender, RoutedEventArgs e)
        {
            BinaryFile.Edit(island, Settings.BinFileEditor);
        }

        private void SaveIsland(object sender, ExecutedRoutedEventArgs e)
        {
            island.Save();
        }

        private void EditIslandLevelsName(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().Name,
                                     list: NameColumn.ItemsSource, displayMemberPath: NameColumn.DisplayMemberPath);
            if (value != null) foreach (var level in SelectedLevels) level.Name = value;
        }

        private void EditIslandLevelsText(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().Text,
                                     list: SubtitleColumn.ItemsSource,
                                     displayMemberPath: SubtitleColumn.DisplayMemberPath);
            if (value != null) foreach (var level in SelectedLevels) level.Text = value;
        }

        private void EditIslandLevelsOCD(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().OCD, list: OCDColumn.ItemsSource, 
                                     filterMode: AutoCompleteFilterMode.StartsWith);
            if (value != null) foreach (var level in SelectedLevels) level.OCD = value;
        }

        private void EditIslandLevelsDepends(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().Depends);
            if (value != null) foreach (var level in SelectedLevels) level.Depends = value;
        }

        private void EditIslandLevelsCutscene(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().Cutscene);
            if (value != null) foreach (var level in SelectedLevels) level.Cutscene = value;
        }

        private void EditIslandLevelsOnComplete(object sender, ExecutedRoutedEventArgs e)
        {
            var value = Dialog.Input(Resrc.EnterNewValueTitle, SelectedLevels.First().OnComplete,
                                     list: OnCompleteColumn.ItemsSource);
            if (value != null) foreach (var level in SelectedLevels) level.OnComplete = value;
        }

        private void EditIslandLevelsSkipEndOfLevelSequence(object sender, ExecutedRoutedEventArgs e)
        {
            var result = Dialog.YesNoCancelQuestion(this, Resrc.EnterSkipEndOfLevelSequenceInstruction,
                Resrc.EnterSkipEndOfLevelSequenceText, yesDefault: SelectedLevels.First().SkipEndOfLevelSequence);
            if (result.HasValue) foreach (var level in SelectedLevels) level.SkipEndOfLevelSequence = result.Value;
        }

        private void AddIslandLevel(object sender, ExecutedRoutedEventArgs e)
        {
            var id = Dialog.Input(Resrc.EnterIDTitle, validCheck: i => !island.Contains(i),
                                  list: island.Parent.GameParent.Res.Levels);
            if (id != null) island.Add(new IslandLevel(island, id));
        }

        private void CopyIslandLevel(object sender, ExecutedRoutedEventArgs e)
        {
            var level = SelectedLevels.First();
            if (level == null) return;
            var id = Dialog.Input(Resrc.EnterIDTitle, level.ID, validCheck: i => !island.Contains(i),
                                  list: island.Parent.GameParent.Res.Levels);
            if (id != null) island.Add(new IslandLevel(level, id));
        }

        private void RemoveIslandLevels(object sender, ExecutedRoutedEventArgs e)
        {
            foreach (var level in SelectedLevels.ToList()) island.Remove(level);
        }

        private void DisplayNameText(object sender, RoutedEventArgs e)
        {
            foreach (var level in SelectedLevels
                .Where(level => island.Parent.GameParent.Properties.Text.Contains(level.Name)))
                Program.App.MainWindow.DisplayText(island.Parent.GameParent, level.Name);
        }

        private void DisplayTextText(object sender, RoutedEventArgs e)
        {
            foreach (var level in SelectedLevels
                .Where(level => island.Parent.GameParent.Properties.Text.Contains(level.Text)))
                Program.App.MainWindow.DisplayText(island.Parent.GameParent, level.Text);
        }

        private void ShowSelectedLevels(object sender, RoutedEventArgs e)
        {
            Program.App.MainWindow.ShowAndSelectLevel(island.Parent.GameParent, 
                SelectedLevels.Select(level => island.Parent.GameParent.Res.Levels[level.ID]));
        }
    }
}
