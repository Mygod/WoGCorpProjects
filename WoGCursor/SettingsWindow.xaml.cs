using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Windows;
using Mygod.Windows;

namespace Mygod.WorldOfGoo.Cursor
{
    public partial class SettingsWindow
    {
        public SettingsWindow(MainWindow parent)
        {
            this.parent = parent;
            InitializeComponent();
            AutoStartup.IsChecked = StartupManager.IsStartAtWindowsStartup("WoGCursor");
        }

        private readonly MainWindow parent;

        private void OnActivate(object sender, EventArgs e)
        {
            parent.SetPaused(true);
        }

        private void OnDeactivate(object sender, EventArgs e)
        {
            parent.SetPaused(false);
        }

        private void ResetToDefault(object sender, RoutedEventArgs e)
        {
            Settings.Current.ResetToDefault();
        }

        private void CheckUpdates(object sender, RoutedEventArgs e)
        {
            Process.Start("http://goofans.com/download/other/world-of-goo-cursor");
        }

        private void OnClosing(object sender, CancelEventArgs e)
        {
            e.Cancel = true;
            Hide();
        }

        private void AutoStartupChanged(object sender, RoutedEventArgs e)
        {
            StartupManager.SetStartAtWindowsStartup("WoGCursor", AutoStartup.IsChecked == true);
        }
    }
}
