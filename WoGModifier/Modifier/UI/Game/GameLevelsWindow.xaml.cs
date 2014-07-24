using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Xml.Linq;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;
using Mygod.Xml.Linq;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class GameLevelsWindow
    {
        public GameLevelsWindow(Game g)
        {
            DataContext = game = g;
            InitializeComponent();
            LevelList.ItemsSource = g.Res.Levels;
            g.Properties.Config.LanguageChanged += RefreshDisplay;
        }

        private void RefreshDisplay(object sender, EventArgs e)
        {
            LevelList.Items.Refresh();
        }

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly Game game;
        private IEnumerable<Level> SelectedLevels { get { return LevelList.SelectedItems.OfType<Level>(); } }

        private void ExecuteLevel(object sender, RoutedEventArgs e)
        {
            Kernel.Execute(game, SelectedLevels.FirstOrDefault());
        }

        private void LevelsOperation(OperationType type)
        {
            new SelectFeaturesDialog().RefreshAndShow(Features.LevelFeatures, SelectedLevels, type);
        }
        private void ProcessLevels(object sender, ExecutedRoutedEventArgs e)
        {
            LevelsOperation(OperationType.Process);
        }
        private void ReverseLevels(object sender, ExecutedRoutedEventArgs e)
        {
            LevelsOperation(OperationType.Reverse);
        }
        private void RestoreLevels(object sender, ExecutedRoutedEventArgs e)
        {
            LevelsOperation(OperationType.Restore);
        }

        private void EditLevelFile(object sender, RoutedEventArgs e)
        {
            foreach (var level in SelectedLevels) level.Edit(((MenuItem)sender).Tag.ToString(), Settings.BinFileEditor);
        }

        private void LevelsProperties(object sender, ExecutedRoutedEventArgs e)
        {
            var s = new StringBuilder(1024);
            foreach (var level in SelectedLevels)
            {
                var path = Path.Combine(level.DirectoryPath, R.ModifiedXml);
                if (!File.Exists(path)) continue;
                var root = XDocument.Load(path).Element(R.Modified);
                if (root == null) throw Exceptions.XmlElementDoesNotExist(path, R.Modified);
                var elements = from element in root.Elements(R.Feature)
                               let ct = element.GetAttributeValue<int>(R.ModifiedTimes)
                               where ct != 0 select new { ID = element.GetAttributeValue(R.ID), ModifiedTimes = ct };
                s.AppendFormat(Resrc.EditDetails, Resrc.Level, level.ID);
                foreach (var em in elements)
                {
                    var feature = Features.LevelFeatures.ContainsKey(em.ID) ? Features.LevelFeatures[em.ID] : null;
                    s.AppendFormat(Resrc.FeatureEditDetails, feature == null ? "???" :
                        (em.ModifiedTimes > 0 ? feature.Process : feature.Reverse).Name, Math.Abs(em.ModifiedTimes));
                }
                s.AppendLine();
            }
            new TextWindow(Resrc.Properties, s.ToString()).ShowDialog();
        }

        private void CopyLevels(object sender, ExecutedRoutedEventArgs e)
        {
            Kernel.SetClipboardText(SelectedLevels.Aggregate(string.Empty, (current, level) => 
                current + level.LocalizedName + " (" + level.ID + ')' + Environment.NewLine));
        }

        private void SortLevels(object sender, ExecutedRoutedEventArgs e)
        {
            LevelList.ItemsSource = LevelList.ItemsSource is IOrderedEnumerable<KeyValuePair<string, Level>>
                ? (IEnumerable) game.Res.Levels : game.Res.Levels.OrderBy(p => p.LocalizedName);
        }

        private void PlayMusic(object sender, ExecutedRoutedEventArgs e)
        {
            ((MainWindow) Application.Current.MainWindow).PlayMusic((Level) LevelList.SelectedItem);
        }

        private void DeleteLevels(object sender, ExecutedRoutedEventArgs e)
        {
            if (Dialog.YesNoQuestion(this, Resrc.DeleteConfirm, Resrc.DeleteConfirmDetails, yesDefault: false))
                foreach (var level in SelectedLevels.ToList()) level.Remove();
        }

        public void SelectLevel(IEnumerable<Level> levels)
        {
            LevelList.SelectedItems.Clear();
            Level lastLevel = null;
            foreach (var level in levels) LevelList.SelectedItems.Add(lastLevel = level);
            if (lastLevel != null) LevelList.ScrollIntoView(lastLevel);
        }

        private void SearchLevel(object sender, ExecutedRoutedEventArgs e)
        {
            var result = Dialog.Input(Resrc.EnterIDTitle, validCheck: game.Res.Levels.Contains, list: game.Res.Levels);
            if (result != null) LevelList.ScrollIntoView(LevelList.SelectedItem =
                game.Res.Levels.FirstOrDefault(level => level.ID == result));
        }
    }
}
