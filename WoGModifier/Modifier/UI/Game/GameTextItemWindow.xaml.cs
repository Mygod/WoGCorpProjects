using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows.Input;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class GameTextItemWindow
    {
        public GameTextItemWindow(TextItem i)
        {
            InitializeComponent();
            DataContext = SpecificLanguageStringGrid.ItemsSource = item = i;
        }

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly TextItem item;
        private IEnumerable<SpecificLanguageString> SelectedSpecificLanguageStrings
        {
            get { return SpecificLanguageStringGrid.SelectedItems.OfType<SpecificLanguageString>(); }
        }

        private void SpecificLanguageStringSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = SpecificLanguageStringGrid.SelectedItem == null;
        }

        private void AddSpecificLanguageString(object sender, ExecutedRoutedEventArgs e)
        {
            var id = Dialog.Input(Resrc.EnterIDTitle, validCheck: i => !item.Contains(i));
            if (id != null) item.Add(new SpecificLanguageString(item.Parent.Parent.GameParent, id, string.Empty));
        }

        private void RemoveSpecificLanguageStrings(object sender, ExecutedRoutedEventArgs e)
        {
            foreach (var i in SelectedSpecificLanguageStrings.ToList()) item.Remove(i);
        }
    }
}
