using System;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using Microsoft.WindowsAPICodePack.Dialogs;
using Mygod.WorldOfGoo.IO;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class OptionsWindow
    {
        public OptionsWindow()
        {
            openProgramDialog.Filters.Add(Resrc.OpenProgramFilter);
            InitializeComponent();
            RecentPathsCapacity.Text = Settings.RecentPathsCapacity.ToString(CultureInfo.InvariantCulture);
            ThumbnailMaxHeight.Text = Settings.ThumbnailMaxHeight.ToString(CultureInfo.InvariantCulture);
            Settings.ThumbnailMaxHeightData.DataChanged += (sender, e) =>
                ThumbnailMaxHeight.Text = Settings.ThumbnailMaxHeight.ToString(CultureInfo.InvariantCulture);
            LoadGooBallThumbnail.IsChecked = Settings.LoadGooBallThumbnail;
            ConsoleDebuggerEnabled.IsChecked = Settings.ConsoleDebuggerEnabled;
            var themePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, R.ThemeDirectory);
            Theme.ItemsSource = (from i in new DirectoryInfo(themePath).EnumerateFiles()
                                 let name = i.Name.ToLower() where name.EndsWith(R.Baml) || name.EndsWith(R.Xaml)
                                 select i.Name.Substring(0, i.Name.Length - 5)).Distinct();
            LanguageBox.ItemsSource = CultureInfo.GetCultures(CultureTypes.AllCultures).OrderBy(info => info.Name);
            var watcher = new FileSystemWatcher(themePath, R.ThemeWatcherFilter);
            watcher.Created += UpdateThemes;
            watcher.Deleted += UpdateThemes;
            watcher.Renamed += UpdateThemes;
            watcher.EnableRaisingEvents = true;
            GC.KeepAlive(watcher);
            Theme.SelectedItem = Settings.Theme;
            LanguageBox.SelectedItem = new CultureInfo(Settings.Language);
            BinFileEditor.Text = Settings.BinFileEditor;
        }

        private void UpdateThemes(object sender, FileSystemEventArgs e)
        {
            Theme.Items.Refresh();
        }

        private void Hide(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private void RecentPathsCapacityChanged(object sender, RoutedEventArgs e)
        {
            Kernel.TrySet<int>(RecentPathsCapacity, Settings.RecentPathsCapacityData);
        }

        private void ThumbnailMaxHeightChanged(object sender, RoutedEventArgs e)
        {
            Kernel.TrySet<double>(ThumbnailMaxHeight, Settings.ThumbnailMaxHeightData);
        }

        private void LoadGooBallThumbnailChanged(object sender, RoutedEventArgs e)
        {
            Settings.LoadGooBallThumbnail = LoadGooBallThumbnail.IsChecked == true;
        }

        private void ConsoleDebuggerEnabledChanged(object sender, RoutedEventArgs e)
        {
            Settings.ConsoleDebuggerEnabled = ConsoleDebuggerEnabled.IsChecked == true;
        }

        private void ThemeChanged(object sender, SelectionChangedEventArgs e)
        {
            Settings.Theme = (string) Theme.SelectedItem;
        }

        private void LanguageChanged(object sender, SelectionChangedEventArgs e)
        {
            Settings.Language = ((CultureInfo)LanguageBox.SelectedItem).Name;
        }

        private void BinFileEditorChanged(object sender, TextChangedEventArgs e)
        {
            Settings.BinFileEditor = BinFileEditor.Text;
        }

        private readonly CommonOpenFileDialog openProgramDialog = new CommonOpenFileDialog
            { Title = Resrc.OpenProgramTitle, EnsureFileExists = true };

        private void BrowseBinFileEditor(object sender, RoutedEventArgs e)
        {
            if (openProgramDialog.ShowDialog() == CommonFileDialogResult.Ok)
                BinFileEditor.Text = openProgramDialog.FileName;
        }
    }
}
