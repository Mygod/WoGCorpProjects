using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;

namespace Mygod.WorldOfGoo.Modifier.UI.Dialogs
{
    sealed partial class SelectFeaturesDialog
    {
        internal SelectFeaturesDialog()
        {
            InitializeComponent();
        }

        private List<Level> levels;
        private List<GooBall> balls;
        internal OperationType CurrentType;

        internal void RefreshAndShow(Dictionary<string, Feature> fts, IEnumerable<Level> levelsToEdit, OperationType type)
        {
            levels = levelsToEdit.ToList();
            if (levels.Count <= 0) return;
            FeatureList.ItemsSource = from f in fts select f.Value;
            balls = null;
            CurrentType = type;
            ShowDialog();
        }
        internal void RefreshAndShow(Dictionary<string, Feature> fts, IEnumerable<GooBall> ballsToEdit, OperationType type)
        {
            balls = ballsToEdit.ToList();
            if (balls.Count <= 0) return;
            FeatureList.ItemsSource = from f in fts select f.Value;
            levels = null;
            CurrentType = type;
            ShowDialog();
        }

        private void Accept(object sender, RoutedEventArgs e)
        {
            if (levels == null) GooBallCheat(); else LevelCheat();
            Close();
        }

        private void LevelCheat()
        {
            Close();
            new ProcessingWindow(levels[0].GameParent).LevelBatchProcess(FeatureList.SelectedItems.Cast<Feature>().ToList(), levels, CurrentType);
        }

        private void GooBallCheat()
        {
            Close();
            new ProcessingWindow(balls[0].GameParent).GooBallBatchProcess(FeatureList.SelectedItems.Cast<Feature>().ToList(), balls, CurrentType);
        }
    }

    public class FeatureDisplayInfoSelector : DataTemplateSelector
    {
        public override DataTemplate SelectTemplate(object item, DependencyObject container)
        {
            var dialog = (SelectFeaturesDialog) Window.GetWindow(container);
            if (dialog != null) return (DataTemplate) dialog.TryFindResource(dialog.CurrentType.ToString() + "Template");
            return base.SelectTemplate(item, container);
        }
    }
}
