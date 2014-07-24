using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    partial class BackupProfileWindow
    {
        private class Backup
        {
            public Backup(FileInfo info)
            {
                Info = info;
            }
            public FileInfo Info { get; private set; }
            public string Name
            {
                get
                {
                    return Info.Name.Substring(0, Info.Name.Length - R.BackupExtension.Length)
                        .Replace("%1", "\\").Replace("%2", "/").Replace("%3", ":").Replace("%4", "*")
                        .Replace("%5", "?").Replace("%6", "\"").Replace("%7", "<").Replace("%8", ">")
                        .Replace("%9", "|").Replace("%0", "%");
                }
                set
                {
                    // ReSharper disable PossibleNullReferenceException
                    Info.MoveTo(Path.Combine(Info.Directory.FullName, value + R.BackupExtension));
                    // ReSharper restore PossibleNullReferenceException
                }
            }
            public string Time { get { return Info.LastWriteTime.ToString(CultureInfo.InvariantCulture); } }
            public string Size { get { return Helper.GetSize(Info.Length, Resrc.Byte); } }
            public static string GetFileName(string backupName)
            {
                return backupName.Replace("%", "%0").Replace("\\", "%1").Replace("/", "%2").Replace(":", "%3")
                    .Replace("*", "%4").Replace("?", "%5").Replace("\"", "%6").Replace("<", "%7").Replace(">", "%8")
                    .Replace("|", "%9");
            }
        }

        private readonly MainWindow parent;

        private readonly ObservableCollection<Backup> backups = new ObservableCollection<Backup>();

        public BackupProfileWindow(MainWindow p)
        {
            parent = p;
            p.Tree.SelectedItemChanged += SelectedItemChanged;
            InitializeComponent();
            BackupList.ItemsSource = backups;
            Directory.CreateDirectory(Settings.ProfileBackupsDirectory);
            StartWatcher();
            RefreshFiles();
            SelectedItemChanged();
        }

        private void SelectedItemChanged(object sender = null, EventArgs e = null)
        {
            NewBackupButton.IsEnabled = parent.Tree.SelectedItem is Profile;
            DeleteBackupsButton.IsEnabled = BackupList.SelectedItem != null;
            RenameBackupButton.IsEnabled = BackupList.SelectedItems.Count == 1;
            OverwriteBackupsButton.IsEnabled = NewBackupButton.IsEnabled && DeleteBackupsButton.IsEnabled;
            RestoreBackupButton.IsEnabled = NewBackupButton.IsEnabled && RenameBackupButton.IsEnabled;
        }

        private string SelectedProfile
        {
            get
            {
                var profile = parent.Tree.SelectedItem as Profile;
                return profile == null ? null : profile.FilePath;
            }
        }
        private string SelectedProfileDirectory { get { return Path.GetDirectoryName(SelectedProfile); } }

        private void RefreshFiles(object sender = null, FileSystemEventArgs e = null)
        {
            Dispatcher.Invoke(() => 
            {
                if (e == null || e.ChangeType == WatcherChangeTypes.Renamed)
                {
                    backups.Clear();
                    foreach (var backup in from info in new DirectoryInfo(Settings.ProfileBackupsDirectory)
                        .EnumerateFiles('*' + R.BackupExtension, SearchOption.AllDirectories) select new Backup(info))
                        backups.Add(backup);
                }
                else switch (e.ChangeType)
                {
                    case WatcherChangeTypes.Created:
                        backups.Add(new Backup(new FileInfo(e.FullPath)));
                        break;
                    case WatcherChangeTypes.Deleted:
                        backups.Remove(backups.FirstOrDefault(b => b.Info.FullName == e.FullPath));
                        break;
                    case WatcherChangeTypes.Changed:
                        backups.Remove(backups.FirstOrDefault(b => b.Info.FullName == e.FullPath));
                        backups.Add(new Backup(new FileInfo(e.FullPath)));
                        break;
                }
            });
        }

        private FileSystemWatcher watcher;

        public void StopWatcher()
        {
            if (watcher != null) watcher.Dispose();
        }

        public void StartWatcher()
        {
            watcher = new FileSystemWatcher(Settings.ProfileBackupsDirectory, '*' + R.BackupExtension);
            watcher.Changed += RefreshFiles;
            watcher.Created += RefreshFiles;
            watcher.Deleted += RefreshFiles;
            watcher.Renamed += RefreshFiles;
            watcher.EnableRaisingEvents = true;
        }

        private void NewBackup(object sender, RoutedEventArgs e)
        {
            var fileName = Dialog.Input(Resrc.EnterBackupNameTitle, Resrc.Backup + ' ' + DateTime.Now);
            if (fileName == null) return;
            fileName = Backup.GetFileName(fileName);
            var path = Path.Combine(Settings.ProfileBackupsDirectory, fileName + R.BackupExtension);
            if (File.Exists(path) && !Dialog.OKCancelQuestion(this, Resrc.OverwriteBackupInstruction,
                Resrc.OverwriteBackupText, okText: Resrc.Overwrite)) return;
            File.Copy(SelectedProfile, path);
            new FileInfo(path).LastWriteTime = DateTime.Now;
            Dialog.Finish(this, Resrc.BackupSuccessfully);
        }

        private void OverwriteBackups(object sender, RoutedEventArgs e)
        {
            if (!Dialog.OKCancelQuestion(this, Resrc.OverwriteBackupInstruction, Resrc.OverwriteBackupText,
                                         Resrc.OverwriteConfirm, Resrc.Overwrite)) return;
            foreach (Backup backup in BackupList.SelectedItems)
            {
                File.Copy(SelectedProfile, backup.Info.FullName, true);
                new FileInfo(backup.Info.FullName).LastWriteTime = DateTime.Now;
            }
            Dialog.Finish(this, Resrc.BackupSuccessfully);
        }

        private void RestoreBackup(object sender, RoutedEventArgs e)
        {
            if (!Dialog.OKCancelQuestion(this, Resrc.RestoreBackupInstruction, Resrc.RestoreBackupText,
                                         Resrc.RestoreBackupConfirm, Resrc.RestoreButton)) return;
            File.Copy(((Backup)BackupList.SelectedItem).Info.FullName, SelectedProfile, true);
            Dialog.Finish(this, Resrc.RestoreBackupSuccessfully);
        }

        private void RenameBackup(object sender, RoutedEventArgs e)
        {
            var backup = (Backup) BackupList.SelectedItem;
            var fileName = Dialog.Input(Resrc.EnterBackupNameTitle, backup.Name);
            if (fileName == null) return;
            fileName = Backup.GetFileName(fileName);
            var path = Path.Combine(Settings.ProfileBackupsDirectory, fileName + R.BackupExtension);
            if (File.Exists(path) && !Dialog.YesNoQuestion(this, Resrc.OverwriteBackupInstruction,
                                                           Resrc.OverwriteBackupText)) return;
            File.Delete(path);
            backup.Info.MoveTo(path);
            Dialog.Finish(this, Resrc.RenameSuccessfully);
        }

        private void DeleteBackups(object sender, RoutedEventArgs e)
        {
            if (!Dialog.OKCancelQuestion(this, Resrc.DeleteBackupInstruction, Resrc.DeleteBackupText,
                                         Resrc.DeleteBackupConfirm, Resrc.Delete)) return;
            foreach (Backup backup in BackupList.SelectedItems) backup.Info.Delete();
            Dialog.Finish(this, Resrc.DeleteBackupSuccessfully);
        }

        private void SetBackupsDirectory(object sender, RoutedEventArgs e)
        {
            var window = sender == null ? Application.Current.MainWindow : this;
            string directoryName;
            do
            {
                directoryName = Dialog.Input(Resrc.EnterBackupsDirectoryTitle, Settings.ProfileBackupsDirectory,
                                             EnterType.Directory);
                if (directoryName == null) return;
            }
            while (SelectedProfile != null && new DirectoryInfo(directoryName).Root.FullName ==
                   new DirectoryInfo(SelectedProfileDirectory).Root.FullName &&
                   !Dialog.YesNoQuestion(this, Resrc.BackupSameVolume, Resrc.BackupSameVolumeDetails,
                                         yesText: Resrc.Continue, noText: Resrc.Reselect));
            Directory.CreateDirectory(directoryName);
            if (BackupList.Items.Count > 0 && Dialog.YesNoQuestion(window, Resrc.CopyBackupsConfirm))
                foreach (Backup backup in BackupList.Items)
                    backup.Info.MoveTo(Path.Combine(directoryName, backup.Info.Name));
            Settings.ProfileBackupsDirectory = directoryName;
            RefreshFiles();
            Dialog.Finish(window, Resrc.EditBackupsDirectorySuccessfully);
        }

        private void WindowClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }
    }
}
