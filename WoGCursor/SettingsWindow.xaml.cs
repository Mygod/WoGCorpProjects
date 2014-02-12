using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Security.Principal;
using System.Windows;
using Mygod.Windows;

namespace Mygod.WorldOfGoo.Cursor
{
    public sealed partial class SettingsWindow
    {
        public SettingsWindow()
        {
            parent = (MainWindow) Application.Current.MainWindow;
            InitializeComponent();
        }

        private readonly MainWindow parent;
        private bool showing;

        private void OnActivate(object sender, EventArgs e)
        {
            if (!showing) parent.SetPaused(true);
        }

        private void OnDeactivate(object sender, EventArgs e)
        {
            if (!showing) parent.SetPaused(false);
        }

        private void ResetToDefault(object sender, RoutedEventArgs e)
        {
            Settings.ResetToDefault();
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

        private void Uninstall(object sender, RoutedEventArgs e)
        {
            showing = true;
            if (new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator))
            {
                var result = MessageBox.Show(this, "Are you sure to uninstall this application?", "Uninstall", 
                                             MessageBoxButton.YesNo, MessageBoxImage.Question, MessageBoxResult.No);
                if (result == MessageBoxResult.Yes)
                {
                    parent.NotifyIcon.Visible = false;
                    Program.Uninstall();
                    Application.Current.Shutdown();
                }
                else showing = false;
            }
            else
                try
                {
                    parent.NotifyIcon.Visible = false;
                    Process.Start(new ProcessStartInfo(CurrentApp.Path, "-u") { Verb = "runas" });
                    Application.Current.Shutdown();
                }
                catch (Win32Exception)  // UAC canceled
                {
                    parent.NotifyIcon.Visible = true;
                    showing = false;
                }
        }
    }
}
