using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Shell;
using System.Xml.Linq;
using IrrKlang;
using Mygod.Windows;
using Mygod.Windows.Dialogs;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    internal sealed partial class MainWindow
    {
        #region Public

        public MainWindow()
        {
            InitializeComponent();
            Tree.Focus();
            RecentPathsChanged();
            Settings.RecentPathsData.DataChanged += RecentPathsChanged;
        }

        private void StartPreload(object sender, RoutedEventArgs e)
        {
            Log.Performance.Write("Load WoGModifier", Program.StartupTime.Elapsed);
            //Application.Current.Shutdown(); // this line is only for test
            Settings.ProfileBackupsDirectoryData.DataChanged += (sd, ev) =>
            {
                var dialog = Program.App.MainWindow.BackupProfileWindow;
                dialog.StopWatcher();
                Directory.CreateDirectory(Settings.ProfileBackupsDirectory);
                dialog.StartWatcher();
            };
            foreach (var profile in Tree.Items.OfType<Profile>()) profile.Refresh();
            Features.StartLoad();
            if (Settings.QuickHelpViewed) return;
            QuickHelp(sender, null);
            Settings.QuickHelpViewed = true;
        }
        private void Shutdown(object sender, EventArgs e)
        {
            Program.CloseAll();
        }

        private void LoadGame(string filePath, bool loading = false)
        {
            if (!loading && Settings.GamePaths.Contains(filePath)) return;
            try
            {
                var game = new Game(filePath);
                var paths = Settings.RecentPaths;
                paths.Add(filePath);
                Settings.RecentPaths = paths.Distinct().Take(Settings.RecentPathsCapacity).ToList(); 
                paths = Settings.GamePaths;
                paths.Add(filePath);
                Settings.GamePaths = paths.Distinct().ToList();
                if (loading) Tree.Items.Add(game); else Tree.Items.Insert(paths.Count - 1, game);
                JumpList.AddToRecentCategory(new JumpTask { Arguments = "-g \"" + filePath + '"',
                    Description = filePath, IconResourcePath = filePath, IconResourceIndex = 0, Title = Kernel.GetTitle(filePath) });
            }
            catch (Exception e)
            {
                if (IsLoaded) Dialog.Error(this, Resrc.FailedLoadingGame, e: e);
                if (!Settings.GamePaths.Contains(filePath)) return;
                var paths = Settings.GamePaths;
                paths.Remove(filePath);
                Settings.GamePaths = paths.Distinct().ToList();
            }
        }

        private void LoadProfile(string filePath, bool loading = false)
        {
            if (!loading && Settings.ProfilePaths.Contains(filePath)) return;
            try
            {
                var paths = Settings.ProfilePaths;
                paths.Add(filePath);
                Settings.ProfilePaths = paths.Distinct().ToList();
                paths = Settings.RecentPaths;
                paths.Add(filePath);
                Settings.RecentPaths = paths.Distinct().Take(Settings.RecentPathsCapacity).ToList();
                var profile = new Profile(filePath, RefreshProfileError, !loading);
                Tree.Items.Add(profile);
                JumpList.AddToRecentCategory(new JumpTask { Arguments = "-p \"" + filePath + '"',
                    Description = filePath, IconResourcePath = CurrentApp.Path, IconResourceIndex = 0, Title = Kernel.GetTitle(filePath) });
            }
            catch (Exception e)
            {
                LoadProfileError(filePath, e);
            }
        }
        private void LoadProfileError(string filePath, Exception e)
        {
            if (IsLoaded) Dialog.Error(this, Resrc.FailedLoadingProfile, e: e);
            if (!Settings.ProfilePaths.Contains(filePath)) return;
            var paths = Settings.ProfilePaths;
            paths.Remove(filePath);
            Settings.ProfilePaths = paths.Distinct().ToList();
        }
        private void RefreshProfileError(object sender, UnhandledExceptionEventArgs e)
        {
            var profile = sender as Profile;
            if (profile == null) return;
            Dispatcher.Invoke(() =>
            {
                LoadProfileError(profile.FilePath, (Exception) e.ExceptionObject);
                Tree.Items.Remove(profile);
            });
        }

        public void ActivateAndLoadPaths(bool activate = true, bool loading = false)
        {
            List<string> gamePaths = new List<string>(), profilePaths = new List<string>();
            lock (App.GamePaths) 
            {
                gamePaths.AddRange(App.GamePaths);
                App.GamePaths.Clear();
            }
            lock (App.ProfilePaths)
            {
                profilePaths.AddRange(App.ProfilePaths);
                App.ProfilePaths.Clear();
            }
            foreach (var game in gamePaths) LoadGame(game, loading);
            foreach (var profile in profilePaths) LoadProfile(profile, loading);
            if (activate) Activate();
        }

        private void ProcessFile(string path)
        {
            var fileName = path;
            if (fileName.ToLower().EndsWith(".lnk")) fileName = Kernel.GetShortcutTarget(fileName);
            var l = fileName.ToLower();
            if (l.EndsWith(".exe")) LoadGame(fileName);
            else if (l.EndsWith(".dat") || l.EndsWith(".plist") || l.EndsWith(R.BackupExtension)) LoadProfile(fileName);
            else BinaryFile.Edit(fileName, Settings.BinFileEditor, false);
        }
        private void ProcessFiles(IEnumerable<string> fileNames)
        {
            foreach (var path in fileNames) ProcessFile(path);
        }

        private void Remove(Game game, bool removePaths = true)
        {
            if (removePaths)
            {
                var paths = Settings.GamePaths;
                paths.Remove(game.FilePath);
                Settings.GamePaths = paths;
            }
            if (gameLevelsWindows.ContainsKey(game))
            {
                gameLevelsWindows[game].Close();
                gameLevelsWindows.Remove(game);
            }
            if (gameGooBallsWindows.ContainsKey(game))
            {
                gameGooBallsWindows[game].Close();
                gameGooBallsWindows.Remove(game);
            }
            if (gameMaterialsWindows.ContainsKey(game))
            {
                gameMaterialsWindows[game].Close();
                gameMaterialsWindows.Remove(game);
            }
            if (gameIslandsWindows.ContainsKey(game))
            {
                gameIslandsWindows[game].Close();
                gameIslandsWindows.Remove(game);
            }
            if (gameTextWindows.ContainsKey(game))
            {
                gameTextWindows[game].Close();
                gameTextWindows.Remove(game);
            }
            if (gamePropertiesWindows.ContainsKey(game))
            {
                gamePropertiesWindows[game].Close();
                gamePropertiesWindows.Remove(game);
            }
            if (nowPlaying != null && Equals(nowPlaying.GameParent, game)) Stop(this, null);
        }
        private void Remove(Profile profile, bool removePaths = true)
        {
            if (removePaths)
            {
                var paths = Settings.ProfilePaths;
                paths.Remove(profile.FilePath);
                Settings.ProfilePaths = paths;
            }
            if (profilePropertiesWindows.ContainsKey(profile))
            {
                profilePropertiesWindows[profile].Close();
                profilePropertiesWindows.Remove(profile);
            }
            foreach (var player in profile.Where(player => playerPropertiesWindows.ContainsKey(player)))
            {
                playerPropertiesWindows[player].Close();
                playerPropertiesWindows.Remove(player);
            }
        }

        private void CheckNotSavedProfiles(object sender, CancelEventArgs e)
        {
            var profiles = Tree.Items.OfType<Profile>().Where(profile => !profile.IsSaved).ToList();
            if (profiles.Count == 0) return;
            var str = profiles.Aggregate(string.Empty, (c, s) => c + s.FilePath + Environment.NewLine);
            switch (Dialog.YesNoCancelQuestion(this, Resrc.ProfileNotSavedInstruction, str + Resrc.ProfileNotSavedText,
                    yesText: Resrc.Save, noText: Resrc.GiveUp))
            {
                case true:
                {
                    foreach (var profile in profiles) profile.Save();
                    break;
                }
                case null:
                {
                    e.Cancel = true;
                    break;
                }
            }
        }

        private void Paste(Profile profile, int index)
        {
            if (profile.Contains(index))
                if (Dialog.OKCancelQuestion(this, Resrc.OverwritePlayerInstruction, Resrc.OverwritePlayerText, 
                    Resrc.OverwriteConfirm, Resrc.Overwrite))
                    profile.Remove(index);
                else return;
            ProfilePlayer player;
            try
            {
                player = new ProfilePlayer(profile, index, Clipboard.GetText());
            }
            catch (Exception e)
            {
                Dialog.Error(this, Resrc.PastePlayerError, e: e);
                return;
            }
            profile.Add(player);
        }

        #region Play Music

        private ISoundEngine engine;
        private bool isPlaying;
        private bool IsPlaying
        {
            get { return isPlaying; }
            set
            {
#pragma warning disable 665
                if (isPlaying = value)
#pragma warning restore 665
                {
                    PlayButton.Visibility = Visibility.Collapsed;
                    PlayBar.Visibility = PauseButton.Visibility = Visibility.Visible;
                }
                else
                {
                    PlayButton.Visibility = Visibility.Visible;
                    PauseButton.Visibility = Visibility.Collapsed;
                }
            }
        }
        private Level nowPlaying;
        private Random random;
        private Random Random { get { return random ?? (random = new Random()); } }

        public void PlayMusic(Level level)
        {
            try
            {
                var document = XDocument.Parse(level.LevelXml);
                var root = document.Element(R.Level);
                if (root == null) throw Exceptions.XmlElementDoesNotExist(level.GetPath(R.Level), R.Level);
                XElement music = root.Element("music"), sound = root.Element("loopsound");
                var resource = level.Resources.First();
                string musicID = music == null ? null : music.GetAttribute("id"), soundID = sound == null ? null : sound.GetAttribute("id"),
                       musicPath = musicID != null && resource.Contains(musicID) ? resource[musicID].LocalizedPath : null,
                       soundPath = soundID != null && resource.Contains(soundID) ? resource[soundID].LocalizedPath : null;
                if (engine == null) engine = new ISoundEngine();
                engine.StopAllSounds();
                if (musicPath != null)
                    engine.Play2DLooped(Path.Combine(level.GameParent.DirectoryPath, musicPath.Replace('/', '\\').TrimStart('\\')));
                if (soundPath != null)
                    engine.Play2DLooped(Path.Combine(level.GameParent.DirectoryPath, soundPath.Replace('/', '\\').TrimStart('\\')));
                IsPlaying = true;
                NowPlaying.Text = (nowPlaying = level).LocalizedName + " - " + level.GameParent.FilePath;
            }
            catch (Exception exc)
            {
                Dialog.Error(this, Resrc.PlayMusicError, e: exc);
            }
        }

        private void ChangePlayStatus(object sender, RoutedEventArgs e)
        {
            engine.SetAllSoundsPaused(IsPlaying);
            IsPlaying = !IsPlaying;
        }

        private void SetVolume(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (engine != null) engine.SoundVolume = (float) VolumeSlider.Value;
        }

        private void Previous(object sender, RoutedEventArgs e)
        {
            var i = nowPlaying.GameParent.Res.Levels.IndexOf(nowPlaying) - 1;
            if (i < 0) i = nowPlaying.GameParent.Res.Levels.Count;
            PlayMusic(nowPlaying.GameParent.Res.Levels[i]);
        }

        private void Next(object sender, RoutedEventArgs e)
        {
            var i = nowPlaying.GameParent.Res.Levels.IndexOf(nowPlaying) + 1;
            if (i >= nowPlaying.GameParent.Res.Levels.Count) i = 0;
            PlayMusic(nowPlaying.GameParent.Res.Levels[i]);
        }

        private void Stop(object sender, RoutedEventArgs e)
        {
            engine.StopAllSounds();
            IsPlaying = false;
            PlayBar.Visibility = Visibility.Collapsed;
        }

        private void Shuffle(object sender, RoutedEventArgs e)
        {
            int i = nowPlaying.GameParent.Res.Levels.IndexOf(nowPlaying), j = i;
            while (j == i) j = Random.Next(nowPlaying.GameParent.Res.Levels.Count);
            PlayMusic(nowPlaying.GameParent.Res.Levels[j]);
        }

        #endregion

        #region Dragging

        private void OnDragEnter(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop, true))
            {
                e.Effects = e.AllowedEffects & DragDropEffects.Copy;
                DropTargetHelper.DragEnter(this, e.Data, e.GetPosition(this), e.Effects, Resrc.DragFile, Resrc.ProgramName);
            }
            else
            {
                e.Effects = DragDropEffects.None;
                DropTargetHelper.DragEnter(this, e.Data, e.GetPosition(this), e.Effects);
            }
        }
        private void OnDragOver(object sender, DragEventArgs e)
        {
            e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop, true) ? e.AllowedEffects & DragDropEffects.Copy : DragDropEffects.None;
            DropTargetHelper.DragOver(e.GetPosition(this), e.Effects);
        }
        private void OnDragLeave(object sender, DragEventArgs e)
        {
            DropTargetHelper.DragLeave(e.Data);
        }
        private void OnDrop(object sender, DragEventArgs e)
        {
            e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop, true) ? e.AllowedEffects & DragDropEffects.Copy : DragDropEffects.None;
            DropTargetHelper.Drop(e.Data, e.GetPosition(this), e.Effects);
            if (e.Effects != DragDropEffects.Copy) return;
            var files = e.Data.GetData(DataFormats.FileDrop, true) as string[];
            if (files != null) ProcessFiles(files);
        }

        #endregion

        #endregion

        #region CanExecute Methods

        private void IsGame(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = Tree.SelectedItem is Game;
        }
        private void IsNotLoadingGame(object sender, CanExecuteRoutedEventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            e.CanExecute = game != null && game.Tag != BooleanBox.True;
        }
        private void IsProfile(object sender, CanExecuteRoutedEventArgs e)
        {
            var profile = Tree.SelectedItem as Profile;
            e.CanExecute = profile != null && !profile.IsRefreshing;
        }
        private void IsProfilePlayer(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = Tree.SelectedItem is ProfilePlayer;
        }
        private void IsGameOrProfile(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = Tree.SelectedItem is Game || Tree.SelectedItem is Profile;
        }
        private void IsNotLoadingGameOrNotRefreshingProfile(object sender, CanExecuteRoutedEventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            var profile = Tree.SelectedItem as Profile;
            e.CanExecute = game != null && game.Tag != BooleanBox.True || profile != null && !profile.IsRefreshing;
        }
        private void IsGameOrProfilePlayer(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = Tree.SelectedItem is Game || Tree.SelectedItem is ProfilePlayer;
        }
        private void IsNotLoadingGameOrProfilePlayer(object sender, CanExecuteRoutedEventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            e.CanExecute = game != null && game.Tag != BooleanBox.True || Tree.SelectedItem is ProfilePlayer;
        }
        private void IsProfileOrPlayer(object sender, CanExecuteRoutedEventArgs e)
        {
            var profile = Tree.SelectedItem as Profile;
            e.CanExecute = profile != null && !profile.IsRefreshing || Tree.SelectedItem is ProfilePlayer;
        }
        private void FreeItemSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            var profile = Tree.SelectedItem as Profile;
            e.CanExecute = game != null && game.Tag != BooleanBox.True || profile != null && !profile.IsRefreshing
                        || game == null && profile == null && Tree.SelectedItem != null;
        }

        #endregion

        #region Menu

        #region File

        private readonly OpenFileDialog openFileDialog = new OpenFileDialog { Title = Resrc.OpenFileTitle, Filter = Resrc.OpenFileFilter, 
                                                                              Multiselect = true, CheckFileExists = true };
        private readonly SaveFileDialog saveProfileDialog = new SaveFileDialog
            { Title = Resrc.SaveProfileTitle, Filter = Resrc.SaveProfileFilter};

        private void NewProfile(object sender, ExecutedRoutedEventArgs e)
        {
            if (saveProfileDialog.ShowDialog() != true) return;
            BinaryFile.WriteAllText(saveProfileDialog.FileName, R.ProfileDefaultContent);
            LoadProfile(saveProfileDialog.FileName);
        }

        private void FileOpen(object sender, ExecutedRoutedEventArgs e)
        {
            if (openFileDialog.ShowDialog() == true) ProcessFiles(openFileDialog.FileNames);
        }

        private void SearchProfile(object sender, ExecutedRoutedEventArgs e)
        {
            string np = Profile.NewVersionProfilePath, op = Profile.OldVersionProfilePath, 
                   n = np == null ? null : Resrc.ProfileNewVersion + '\n' + np,
                   o = op == null ? null : Resrc.ProfileOldVersion + '\n' + op;
            if (n == null && o == null) Dialog.Information(this, Resrc.SearchProfileFailed, Resrc.SearchProfileText);
            else
            {
                var options = new TaskDialogOptions { MainInstruction = Resrc.SearchProfileFinished, Owner = this, 
                    AllowDialogCancellation = true, Buttons = TaskDialogButtons.Cancel, Title = Resrc.Information,
                    Content = Resrc.SearchProfileText };
                if (n != null) options.CommandButtons = o == null ? new[] { n } : new[] { n, o, Resrc.ProfileLoadBoth };
                else options.CommandButtons = new[] { o };
                var result = TaskDialog.Show(options);
                switch (result.CommandButtonResult)
                {
                    case 0:
                        ProcessFile(n == null ? op : np);
                        break;
                    case 1:
                        ProcessFile(op);
                        break;
                    case 2:
                        ProcessFile(np);
                        ProcessFile(op);
                        break;
                }
            }
        }

        private void SaveAll(object sender, RoutedEventArgs e)
        {
            foreach (var profile in Tree.Items.OfType<Profile>().Where(profile => !profile.IsSaved)) profile.Save();
        }

        private void RemoveItem(object sender, ExecutedRoutedEventArgs e)
        {
            var item = Tree.SelectedItem;
            Tree.Items.Remove(item);
            var game = item as Game;
            if (game != null) Remove(game);
            else
            {
                var profile = item as Profile;
                if (profile != null) Remove(profile);
                else
                {
                    var player = item as ProfilePlayer;
                    if (player == null) return;
                    player.Parent.Remove(player);
                    var p = player.Parent.FirstOrDefault();
                    if (p != null) p.SetAsMostRecentPlayer();
                }
            }
        }

        private void FileClear(object sender, RoutedEventArgs e)
        {
            Tree.Items.Clear();
            Settings.GamePaths = Settings.ProfilePaths = new List<string>();
            foreach (var pair in gameLevelsWindows) pair.Value.Close();
            gameLevelsWindows.Clear();
            foreach (var pair in gameGooBallsWindows) pair.Value.Close();
            gameGooBallsWindows.Clear();
            foreach (var pair in gameMaterialsWindows) pair.Value.Close();
            gameMaterialsWindows.Clear();
            foreach (var pair in gameIslandsWindows) pair.Value.Close();
            gameIslandsWindows.Clear();
            foreach (var pair in gameTextWindows) pair.Value.Close();
            gameTextWindows.Clear();
            foreach (var pair in gamePropertiesWindows) pair.Value.Close();
            gamePropertiesWindows.Clear();
            foreach (var pair in profilePropertiesWindows) pair.Value.Close();
            profilePropertiesWindows.Clear();
            foreach (var pair in playerPropertiesWindows) pair.Value.Close();
            playerPropertiesWindows.Clear();
        }

        private void RecentPathsChanged(object sender = null, EventArgs e = null)
        {
            Dispatcher.Invoke(() =>
            {
                RecentPaths.Items.Clear();
                var i = 0;
                foreach (var item in Settings.RecentPaths.Select(s => new MenuItem {Header = string.Format("_{0} {1}", ++i, s), Tag = s}))
                {
                    item.Click += RecentPathClicked;
                    RecentPaths.Items.Add(item);
                }
            });
        }

        private void RecentPathClicked(object sender, RoutedEventArgs e)
        {
            ProcessFile(((MenuItem) e.OriginalSource).Tag.ToString());
        }

        private void Quit(object sender, ExecutedRoutedEventArgs e)
        {
            Close();
        }

        #endregion

        #region Tools

        private void EditBatchProcessFeatures(object sender, RoutedEventArgs e)
        {
            Process.Start(Settings.BinFileEditor, Path.Combine(CurrentApp.Directory, "Resources/Features.xml"));
        }

        private void CleanupGarbage(object sender, RoutedEventArgs e)
        {
            Dialog.Finish(this, Resrc.GarbageCleanupDone, string.Format(Resrc.GarbageCleanupDetails,
                Kernel.GetSize(Log.Error.Clear() + Log.Crash.Clear() + Log.Performance.Clear())));
        }

        private void XslTransformer(object sender, RoutedEventArgs e)
        {
            new XslTransformerWindow().Show();
        }

        private OptionsWindow optionsWindow;
        private OptionsWindow OptionsWindow { get { return optionsWindow ?? (optionsWindow = new OptionsWindow()); } }
        private void Options(object sender, ExecutedRoutedEventArgs e)
        {
            OptionsWindow.Show();
            OptionsWindow.Activate();
        }

        #endregion

        #region Help

        private HelpWindow helpWindow;
        private HelpWindow HelpWindow { get { return helpWindow ?? (helpWindow = new HelpWindow()); } }
        private void Help(object sender, ExecutedRoutedEventArgs e)
        {
            HelpWindow.Show();
            HelpWindow.Activate();
        }
        
        private void QuickHelp(object sender, ExecutedRoutedEventArgs e)
        {
            Dialog.Information(this, Resrc.WelcomeUseTitle + ' ' + Resrc.Title, string.Format(Resrc.WelcomeUse, Resrc.Title), 
                               Resrc.WelcomeUseTitle);
        }

        private void TechSupportCheckForUpdates(object sender, RoutedEventArgs e)
        {
            Process.Start(R.TechSupportUrl);
        }

        private void About(object sender, ExecutedRoutedEventArgs e)
        {
            new AboutDialog().ShowDialog();
        }

        #endregion

        #endregion

        #region TreeView Context Menu

        #region Public

        private void GenerateContextMenu(object sender, RoutedEventArgs e)
        {
            var si = Tree.SelectedItem;
            if (si == null)
            {
                TreeContextMenu.Opacity = 0;    // won't be shown
                return;
            }
            TreeContextMenu.Opacity = 1;
            var tag = '\0';
            if (si is Game) tag = 'G';
            else if (si is Profile) tag = 'R';
            else if (si is ProfilePlayer) tag = 'L';
            foreach (FrameworkElement i in TreeContextMenu.Items)
                i.Visibility = i.Tag.ToString().Contains(tag) ? Visibility.Visible : Visibility.Collapsed;
        }

        private void SelectCurrentNode(object sender, MouseButtonEventArgs e)
        {
            var i = (e.OriginalSource as DependencyObject).FindVisualParent<TreeViewItem>();
            if (i == null) return;
            i.Focus();
            e.Handled = true;
        }

        private void DefaultOperation(object sender, EventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            if (game != null)
            {
                if (!Kernel.Execute((Game)Tree.SelectedItem)) Dialog.Information(this, Resrc.GameAlreadyRunning, title: Resrc.Failed);
                return;
            }
            var player = Tree.SelectedItem as ProfilePlayer;
            if (player != null) player.SetAsMostRecentPlayer();
        }

        private void BrowseInExplorer(object sender, ExecutedRoutedEventArgs e)
        {
            var file = Tree.SelectedItem as IGameFile;
            if (file != null) Process.Start("explorer", "/select,\"" + file.FilePath + '"');
        }

        private void RefreshItem(object sender, ExecutedRoutedEventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            if (game != null)
            {
                Remove(game, false);
                game.Refresh();
                return;
            }
            var profile = Tree.SelectedItem as Profile;
            if (profile == null || profile.IsRefreshing) return;
            Remove(profile, false);
            profile.Refresh();
        }

        private readonly Dictionary<Game, GamePropertiesWindow> gamePropertiesWindows = new Dictionary<Game, GamePropertiesWindow>();
        private readonly Dictionary<Profile, ProfilePropertiesWindow> profilePropertiesWindows = new Dictionary<Profile, ProfilePropertiesWindow>();
        private readonly Dictionary<ProfilePlayer, PlayerPropertiesWindow> playerPropertiesWindows
            = new Dictionary<ProfilePlayer, PlayerPropertiesWindow>();
        private void Properties(object sender, ExecutedRoutedEventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            if (game != null)
            {
                if (gamePropertiesWindows.ContainsKey(game))
                {
                    gamePropertiesWindows[game].Show();
                    gamePropertiesWindows[game].Activate();
                }
                else
                {
                    var win = new GamePropertiesWindow(game);
                    gamePropertiesWindows.Add(game, win);
                    win.Show();
                }
                return;
            }
            var profile = Tree.SelectedItem as Profile;
            if (profile != null)
            {
                if (profilePropertiesWindows.ContainsKey(profile))
                {
                    profilePropertiesWindows[profile].Show();
                    profilePropertiesWindows[profile].Activate();
                }
                else
                {
                    var win = new ProfilePropertiesWindow(profile);
                    profilePropertiesWindows.Add(profile, win);
                    win.Show();
                }
                return;
            }
            var player = Tree.SelectedItem as ProfilePlayer;
            if (player == null) return;
            if (playerPropertiesWindows.ContainsKey(player))
            {
                playerPropertiesWindows[player].Show();
                playerPropertiesWindows[player].Activate();
            }
            else
            {
                var win = new PlayerPropertiesWindow(player);
                playerPropertiesWindows.Add(player, win);
                win.Show();
            }
        }

        private readonly Dictionary<Game, GameLevelsWindow> gameLevelsWindows = new Dictionary<Game, GameLevelsWindow>();
        private readonly Dictionary<ProfilePlayer, PlayerLevelsWindow> playerLevelsWindows = new Dictionary<ProfilePlayer, PlayerLevelsWindow>();
        private void BrowseLevels(object sender, ExecutedRoutedEventArgs e)
        {
            var game = Tree.SelectedItem as Game;
            if (game != null)
            {
                if (gameLevelsWindows.ContainsKey(game))
                {
                    gameLevelsWindows[game].Show();
                    gameLevelsWindows[game].Activate();
                }
                else
                {
                    game.Tag = BooleanBox.True;
                    Task.Factory.StartNew(() =>
                    {
                        game.Res.Levels.DoNothing();
                        Dispatcher.Invoke(() =>
                        {
                            game.Tag = BooleanBox.False;
                            var win = new GameLevelsWindow(game);
                            gameLevelsWindows.Add(game, win);
                            win.Show();
                        });
                    });
                }
            }
            else
            {
                var player = Tree.SelectedItem as ProfilePlayer;
                if (player == null) return;
                if (playerLevelsWindows.ContainsKey(player))
                {
                    playerLevelsWindows[player].Show();
                    playerLevelsWindows[player].Activate();
                }
                else
                {
                    var win = new PlayerLevelsWindow(player);
                    playerLevelsWindows.Add(player, win);
                    win.Show();
                }
            }
        }
        public void ShowAndSelectLevel(Game game, IEnumerable<Level> levels)
        {
            if (!gameLevelsWindows.ContainsKey(game))
            {
                game.Tag = BooleanBox.True;
                Task.Factory.StartNew(() =>
                {
                    game.Res.Levels.DoNothing();
                    Dispatcher.Invoke(() =>
                    {
                        game.Tag = BooleanBox.False;
                        var win = new GameLevelsWindow(game);
                        gameLevelsWindows.Add(game, win);
                        win.Show();
                        win.Activate();
                        win.SelectLevel(levels);
                    });
                });
            }
            else
            {
                gameLevelsWindows[game].Show();
                gameLevelsWindows[game].Activate();
                gameLevelsWindows[game].SelectLevel(levels);
            }
        }

        private void PastePlayer(object sender, ExecutedRoutedEventArgs e)
        {
            var player = Tree.SelectedItem as ProfilePlayer;
            if (player != null) Paste(player.Parent, player.PlayerNumber);
            else
            {
                var profile = Tree.SelectedItem as Profile;
                if (profile == null) return;
                int result;
                do result = SelectPlayerNumber();
                while (result != 0 && profile.Contains(result - 1) && !Dialog.OKCancelQuestion(this, Resrc.OverwritePlayerInstruction,
                    Resrc.OverwritePlayerText, Resrc.OverwriteConfirm, Resrc.Overwrite));
                if (result == 0) return;
                profile.Remove(result - 1);
                Paste(profile, result);
            }
        }

        private void SetAlias(object sender, ExecutedRoutedEventArgs e)
        {
            var file = Tree.SelectedItem as IHasAlias;
            if (file == null) return;
            var result = Dialog.Input(Resrc.EnterNewValueTitle, file.Alias);
            if (result == null) return;
            file.Alias = result;
        }

        #endregion

        #region Game

        private readonly Dictionary<Game, GameGooBallsWindow> gameGooBallsWindows = new Dictionary<Game, GameGooBallsWindow>();
        private void BrowseGooBalls(object sender, ExecutedRoutedEventArgs e)
        {
            var game = (Game)Tree.SelectedItem;
            if (gameGooBallsWindows.ContainsKey(game))
            {
                gameGooBallsWindows[game].Show();
                gameGooBallsWindows[game].Activate();
            }
            else
            {
                game.Tag = BooleanBox.True;
                Task.Factory.StartNew(() =>
                {
                    foreach (var ball in game.Res.Balls) ball.ThumbnailUri.DoNothing();
                    Dispatcher.Invoke(() =>
                    {
                        game.Tag = BooleanBox.False;
                        var win = new GameGooBallsWindow(game);
                        gameGooBallsWindows.Add(game, win);
                        win.Show();
                    });
                });
            }
        }

        private readonly Dictionary<Game, GameIslandsWindow> gameIslandsWindows = new Dictionary<Game, GameIslandsWindow>();
        private void BrowseIslands(object sender, ExecutedRoutedEventArgs e)
        {
            var game = (Game)Tree.SelectedItem;
            if (gameIslandsWindows.ContainsKey(game))
            {
                gameIslandsWindows[game].Show();
                gameIslandsWindows[game].Activate();
            }
            else
            {
                game.Tag = BooleanBox.True;
                Task.Factory.StartNew(() =>
                {
                    game.Res.Islands.DoNothing();
                    Dispatcher.Invoke(() =>
                    {
                        game.Tag = BooleanBox.False;
                        var win = new GameIslandsWindow(game);
                        gameIslandsWindows.Add(game, win);
                        win.Show();
                    });
                });
            }
        }

        private readonly Dictionary<Game, GameMaterialsWindow> gameMaterialsWindows = new Dictionary<Game, GameMaterialsWindow>();
        private void BrowseMaterials(object sender, ExecutedRoutedEventArgs e)
        {
            var game = (Game)Tree.SelectedItem;
            if (gameMaterialsWindows.ContainsKey(game))
            {
                gameMaterialsWindows[game].Show();
                gameMaterialsWindows[game].Activate();
            }
            else
            {
                game.Tag = BooleanBox.True;
                Task.Factory.StartNew(() =>
                {
                    game.Properties.Materials.DoNothing();
                    Dispatcher.Invoke(() =>
                    {
                        game.Tag = BooleanBox.False;
                        var win = new GameMaterialsWindow(game);
                        gameMaterialsWindows.Add(game, win);
                        win.Show();
                    });
                });
            }
        }

        private readonly Dictionary<Game, GameTextWindow> gameTextWindows = new Dictionary<Game, GameTextWindow>();
        private void BrowseText(object sender, ExecutedRoutedEventArgs e)
        {
            var game = (Game)Tree.SelectedItem;
            if (gameTextWindows.ContainsKey(game))
            {
                gameTextWindows[game].Show();
                gameTextWindows[game].Activate();
            }
            else
            {
                game.Tag = BooleanBox.True;
                Task.Factory.StartNew(() =>
                {
                    game.Properties.Text.DoNothing();
                    Dispatcher.Invoke(() =>
                    {
                        game.Tag = BooleanBox.False;
                        var win = new GameTextWindow(game);
                        gameTextWindows.Add(game, win);
                        win.Show();
                    });
                });
            }
        }
        public void DisplayText(Game game, string name)
        {
            if (!gameTextWindows.ContainsKey(game))
            {
                game.Tag = BooleanBox.True;
                Task.Factory.StartNew(() =>
                {
                    game.Properties.Text.DoNothing();
                    Dispatcher.Invoke(() =>
                    {
                        game.Tag = BooleanBox.False;
                        var win = new GameTextWindow(game);
                        gameTextWindows.Add(game, win);
                        win.ProcessTextItem(game.Properties.Text[name]);
                    });
                });
            }
            else gameTextWindows[game].ProcessTextItem(game.Properties.Text[name]);
        }

        private GameMemoryWindow gameMemoryWindow;
        private GameMemoryWindow GameMemoryWindow { get { return gameMemoryWindow ?? (gameMemoryWindow = new GameMemoryWindow()); } }
        private void EditMemory(object sender, ExecutedRoutedEventArgs e)
        {
            GameMemoryWindow.Show(((Game) Tree.SelectedItem));
        }

        #endregion

        #region Profile

        private BackupProfileWindow backupProfileWindow;
        private BackupProfileWindow BackupProfileWindow
        {
            get
            {
                return backupProfileWindow ?? (backupProfileWindow = new BackupProfileWindow(this));
            }
        }

        private void TreeFold(object sender, RoutedEventArgs e)
        {
            var o = (TreeViewItem)Tree.ItemContainerGenerator.ContainerFromItem(Tree.SelectedItem);
            if (o != null)
            {
                o.IsExpanded = !o.IsExpanded;
                return;
            }
            foreach (var i in Tree.Items.OfType<Profile>())
            {
                o = ((TreeViewItem)Tree.ItemContainerGenerator.ContainerFromItem(i))
                    .ItemContainerGenerator.ContainerFromItem(Tree.SelectedItem) as TreeViewItem;
                if (o == null) continue;
                o.IsExpanded = !o.IsExpanded;
                return;
            }
        }

        private void SaveProfile(object sender, ExecutedRoutedEventArgs e)
        {
            var profile = Tree.SelectedItem as Profile;
            if (profile != null) profile.Save();
        }

        private void SaveAsProfile(object sender, ExecutedRoutedEventArgs e)
        {
            var profile = Tree.SelectedItem as Profile;
            if (profile == null || saveProfileDialog.ShowDialog() != true) return;
            profile.Save(saveProfileDialog.FileName);
            Remove(profile);
            LoadProfile(saveProfileDialog.FileName);
        }

        private void BackupProfile(object sender, ExecutedRoutedEventArgs e)
        {
            BackupProfileWindow.Show();
            BackupProfileWindow.Activate();
        }

        private void EditProfile(object sender, RoutedEventArgs e)
        {
            BinaryFile.Edit((Profile)Tree.SelectedItem, Settings.BinFileEditor);
        }

        private int SelectPlayerNumber()
        {
            var options = new TaskDialogOptions { Title = Resrc.Ask, MainInstruction = Resrc.PasteToInstruction, Owner = this,
                AllowDialogCancellation = true, MainIcon = TaskDialogIcon.Information, Buttons = TaskDialogButtons.Cancel, 
                CommandButtons = new string[3] };
            for (var i = 1; i <= 3; i++) options.CommandButtons[i - 1] = Resrc.PlayerSharp + i;
            var result = TaskDialog.Show(options);
            return result.CommandButtonResult == null ? 0 : (result.CommandButtonResult.Value + 1);
        }

        private void InsertProfilePlayer(object sender, ExecutedRoutedEventArgs e)
        {
            var profile = Tree.SelectedItem as Profile;
            if (profile == null) return;
            int result;
            do result = SelectPlayerNumber();
            while (result != 0 && profile.Contains(result - 1) && !Dialog.OKCancelQuestion(this, Resrc.OverwritePlayerInstruction, 
                Resrc.OverwritePlayerText, Resrc.OverwriteConfirm, Resrc.Overwrite));
            if (result == 0) return;
            profile.Remove(result - 1);
            profile.Add(new ProfilePlayer(profile, result));
        }

        #endregion

        #region ProfilePlayer

        private readonly Dictionary<ProfilePlayer, PlayerWoGCorpWindow> playerWoGCorpWindows
            = new Dictionary<ProfilePlayer, PlayerWoGCorpWindow>();
        private void BrowseWoGCorp(object sender, ExecutedRoutedEventArgs e)
        {
            var player = Tree.SelectedItem as ProfilePlayer;
            if (player == null) return;
            if (playerWoGCorpWindows.ContainsKey(player))
            {
                playerWoGCorpWindows[player].Show();
                playerWoGCorpWindows[player].Activate();
            }
            else
            {
                var win = new PlayerWoGCorpWindow(player);
                playerWoGCorpWindows.Add(player, win);
                win.Show();
            }
        }

        private void CutPlayer(object sender, ExecutedRoutedEventArgs e)
        {
            CopyPlayer(sender, e);
            RemoveItem(sender, e);
        }

        private void CopyPlayer(object sender, ExecutedRoutedEventArgs e)
        {
            var player = Tree.SelectedItem as ProfilePlayer;
            if (player == null) return;
            Kernel.SetClipboardText(player.Value);
        }

        #endregion

        #endregion
    }
}
