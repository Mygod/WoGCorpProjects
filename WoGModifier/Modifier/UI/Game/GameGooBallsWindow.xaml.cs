using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Linq;
using Mygod.Windows;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;
using Mygod.Xml.Linq;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    partial class GameGooBallsWindow
    {
        public GameGooBallsWindow(Game g)
        {
            DataContext = game = g;
            tester = new Lazy<GameGooBallsTesterWindow>(() => new GameGooBallsTesterWindow(game) { Owner = this });
            InitializeComponent();
            GooBallList.ItemsSource = g.Res.Balls;
            g.Properties.Config.LanguageChanged += RefreshDisplay;
            Settings.ThumbnailMaxHeightData.DataChanged += RefreshDisplay;
            Settings.LoadGooBallThumbnailData.DataChanged += RefreshDisplay;
        }

        private void RefreshDisplay(object sender, EventArgs e)
        {
            GooBallList.Items.Refresh();
        }

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly Game game;
        private readonly Lazy<GameGooBallsTesterWindow> tester;
        private IEnumerable<GooBall> SelectedGooBalls { get { return GooBallList.SelectedItems.OfType<GooBall>(); } }

        private void GooBallsOperation(OperationType type)
        {
            new SelectFeaturesDialog().RefreshAndShow(Features.GooBallFeatures, SelectedGooBalls, type);
        }
        private void ProcessGooBalls(object sender, ExecutedRoutedEventArgs e)
        {
            GooBallsOperation(OperationType.Process);
        }
        private void ReverseGooBalls(object sender, ExecutedRoutedEventArgs e)
        {
            GooBallsOperation(OperationType.Reverse);
        }
        private void RestoreGooBalls(object sender, ExecutedRoutedEventArgs e)
        {
            GooBallsOperation(OperationType.Restore);
        }

        private void GooBallListMouseWheel(object sender, MouseWheelEventArgs e)
        {
            if (!Keyboard.IsKeyDown(Key.LeftCtrl) && !Keyboard.IsKeyDown(Key.RightCtrl)) return;
            e.Handled = true;
            Settings.ThumbnailMaxHeight += (double)(e.Delta << 3) / Mouse.MouseWheelDeltaForOneLine;
            if (Settings.ThumbnailMaxHeight < 0) Settings.ThumbnailMaxHeight = 0;
        }

        private void GooBallsProperties(object sender, ExecutedRoutedEventArgs e)
        {
            var s = new StringBuilder(1024);
            foreach (var gooBall in SelectedGooBalls)
            {
                var path = Path.Combine(gooBall.DirectoryPath, R.ModifiedXml);
                if (!File.Exists(path)) continue;
                var root = XDocument.Load(path).Element(R.Modified);
                if (root == null) throw Exceptions.XmlElementDoesNotExist(path, R.Modified);
                var elements = from element in root.Elements(R.Feature)
                               let ct = element.GetAttributeValue<int>(R.ModifiedTimes) where ct != 0
                               select new { ID = element.GetAttributeValue(R.ID), ModifiedTimes = ct };
                s.AppendFormat(Resrc.EditDetails, Resrc.GooBall, gooBall.ID);
                foreach (var em in elements)
                {
                    var feature = Features.GooBallFeatures.ContainsKey(em.ID) ? Features.GooBallFeatures[em.ID] : null;
                    s.AppendFormat(Resrc.FeatureEditDetails, feature == null ? "???" :
                        (em.ModifiedTimes > 0 ? feature.Process : feature.Reverse).Name, Math.Abs(em.ModifiedTimes));
                }
                s.AppendLine();
            }
            new TextWindow(Resrc.Properties, s.ToString()).ShowDialog();
        }

        private void CopyGooBalls(object sender, ExecutedRoutedEventArgs e)
        {
            Kernel.SetClipboardText(SelectedGooBalls.Aggregate(string.Empty,
                                        (current, gooBall) => current + gooBall.ID + Environment.NewLine));
        }

        private void CheckAddTestGooBallNumbersBox(object sender, RoutedEventArgs e)
        {
            int i;
            if (string.IsNullOrWhiteSpace(AddTestGooBallNumbersBox.Text) ||
                !int.TryParse(AddTestGooBallNumbersBox.Text, out i)) AddTestGooBallNumbersBox.Text = "0";
        }

        private void AddTestGooBall(object sender, RoutedEventArgs e)
        {
            tester.Value.Process(SelectedGooBalls.Select(i => i.ID), int.Parse(AddTestGooBallNumbersBox.Text));
        }

        private void EditGooBallFile(object sender, RoutedEventArgs e)
        {
            foreach (var gooBall in SelectedGooBalls)
                gooBall.Edit(((MenuItem)sender).Tag.ToString(), Settings.BinFileEditor);
        }

        private static T Search<T>(DependencyObject source) where T : DependencyObject
        {
            while (source != null && !(source is T)) source = VisualTreeHelper.GetParent(source);
            return source as T;
        }

        private void DragGooBall(object sender, MouseButtonEventArgs e)
        {
            if (Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl) ||
                Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt) ||
                Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift)) return;
            var item = Search<ListBoxItem>(e.OriginalSource as DependencyObject);
            if (item == null) return;
            var goo = (GooBall)GooBallList.ItemContainerGenerator.ItemFromContainer(item);
            if (!GooBallList.SelectedItems.Contains(goo)) GooBallList.SelectedItem = goo;
            DragSourceHelper.DoDragDrop(item, e.GetPosition(item), DragDropEffects.Link,
                new KeyValuePair<string, object>(R.GooBalls, new DraggableGooBalls
                    (SelectedGooBalls.Select(i => i.ID), int.Parse(AddTestGooBallNumbersBox.Text))));
        }

        private void DeleteBalls(object sender, ExecutedRoutedEventArgs e)
        {
            if (Dialog.YesNoQuestion(this, Resrc.DeleteConfirm, Resrc.DeleteConfirmDetails, yesDefault: false))
                foreach (var ball in SelectedGooBalls.ToList()) ball.Remove();
        }
    }

    [Serializable]
    internal class DraggableGooBalls
    {
        public DraggableGooBalls(IEnumerable<string> gooBalls, int number)
        {
            GooBallIDs = gooBalls.ToArray();
            Number = number;
        }

        public readonly string[] GooBallIDs;
        public readonly int Number;
    }
}
