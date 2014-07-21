using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Threading;
using System.Windows;
using System.Windows.Markup;
using System.Windows.Shell;
using System.Windows.Threading;
using Microsoft.VisualBasic.ApplicationServices;
using Microsoft.WindowsAPICodePack.Dialogs;
using Mygod.Windows;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.IO;
using Mygod.WorldOfGoo.Modifier.UI;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;
using VBStartupEventArgs = Microsoft.VisualBasic.ApplicationServices.StartupEventArgs;
using StartupEventArgs = System.Windows.StartupEventArgs;
using UnhandledExceptionEventArgs = System.UnhandledExceptionEventArgs;

namespace Mygod.WorldOfGoo.Modifier
{
    sealed partial class App
    {
        public App()
        {
            Dispatcher = base.Dispatcher;
            Log.Initialize();
            ServicePointManager.ServerCertificateValidationCallback += (sender, certificate, chain, errors) => true;
        }

        // ReSharper disable MemberCanBePrivate.Global
        public static ResourceDictionary Theme
        {
            get
            {
                var result = new ResourceDictionary();
                try
                {
                    var themePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, R.ThemeDirectory, Settings.Theme + R.Baml);
                    if (File.Exists(themePath))
                    {
                        result = (ResourceDictionary)
                            BamlReader.Load(new FileStream(themePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite));
                        if (result.Count == 0 && result.MergedDictionaries.Count == 1)
                            result = result.MergedDictionaries.FirstOrDefault();
                    }
                    else
                    {
                        themePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, R.ThemeDirectory, Settings.Theme + R.Xaml);
                        if (File.Exists(themePath))
                        {
                            result = (ResourceDictionary)XamlReader.Load(new FileStream(themePath, FileMode.Open, FileAccess.Read, 
                                FileShare.ReadWrite));
                            if (result.Count == 0 && result.MergedDictionaries.Count == 1)
                                result = result.MergedDictionaries.FirstOrDefault();
                        }
                    }
                }
                catch (Exception e)
                {
                    Log.Error.Write(e);
                }
                return result;
            }
        }
        // ReSharper restore MemberCanBePrivate.Global

        public new static Dispatcher Dispatcher;
        public static readonly List<string> GamePaths = new List<string>(), ProfilePaths = new List<string>();

        internal new MainWindow MainWindow
        {
            get { return (MainWindow)base.MainWindow; } private set { base.MainWindow = value; }
        }

        private void ApplicationStartup(object sender, StartupEventArgs e)
        {
            var path = Globalization.GetLocalizedPath(Path.Combine(CurrentApp.Directory, "Resources/Texts"), "xaml");
            if (File.Exists(path)) Resources.MergedDictionaries[1] = (ResourceDictionary)XamlReader.Load(
                new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite));
            JumpList.SetJumpList(this, new JumpList(new List<JumpItem>
                {
                    new JumpTask { Title = Resrc.JumpListSelectBinFiles, CustomCategory = Resrc.JumpListCategory,
                                   Arguments = "-selectbinfiles" },
                    new JumpTask { Title = Resrc.JumpListTechSupport, CustomCategory = Resrc.JumpListCategory, 
                                   ApplicationPath = R.TechSupportUrl }
                }, true, true));
            Resources.MergedDictionaries.Add(FindResource("Styles") as ResourceDictionary);
            ApplicationStartup(e.Args);
        }
        public void ApplicationStartup(IEnumerable<string> args, bool first = true)
        {
            var type = ArgumentType.Invalid;
            foreach (var arg in args) switch (type)
            {
                case ArgumentType.Game:
                    lock (GamePaths) GamePaths.Add(arg);
                    type = ArgumentType.Invalid;
                    break;
                case ArgumentType.Profile:
                    lock (ProfilePaths) ProfilePaths.Add(arg);
                    type = ArgumentType.Invalid;
                    break;
                default:
                    var lower = arg.Trim().ToLower();
                    if (lower.StartsWith("-g", StringComparison.Ordinal)) type = ArgumentType.Game;
                    else if (lower.StartsWith("-p", StringComparison.Ordinal)) type = ArgumentType.Profile;
                    else if (lower.StartsWith("-selectbinfiles", StringComparison.Ordinal))
                    {
                        var dialog = new CommonOpenFileDialog { Title = Resrc.OpenBinFileTitle, Multiselect = true };
                        dialog.Filters.Add(Resrc.OpenBinFileFilter);
                        if (dialog.ShowDialog() != CommonFileDialogResult.Ok) return;
                        foreach (var path in dialog.FileNames) BinaryFile.Edit(path, Settings.BinFileEditor, false);
                    }
                    else if (File.Exists(arg))
                    {
                        var fileName = arg;
                        while (fileName.ToLowerInvariant().EndsWith(".lnk", StringComparison.Ordinal))
                            fileName = Kernel.GetShortcutTarget(fileName);
                        var l = fileName.ToLower();
                        if (l.EndsWith(".exe", StringComparison.Ordinal)) lock (GamePaths) GamePaths.Add(fileName);
                        else if (l.EndsWith(".dat", StringComparison.Ordinal) || l.EndsWith(".plist", StringComparison.Ordinal)
                            || l.EndsWith(R.BackupExtension, StringComparison.Ordinal)) lock (ProfilePaths) ProfilePaths.Add(fileName);
                        else BinaryFile.Edit(fileName, Settings.BinFileEditor, false);
                    }
                    break;
            }
            if (first)
            {
                MainWindow = new MainWindow();
                lock (GamePaths) GamePaths.AddRange(Settings.GamePaths);
                lock (ProfilePaths) ProfilePaths.AddRange(Settings.ProfilePaths);
                MainWindow.ActivateAndLoadPaths(false, true);
                MainWindow.Show();
            }
            else MainWindow.ActivateAndLoadPaths();
        }

        private void ErrorOccurred(object sender, DispatcherUnhandledExceptionEventArgs e)
        {
            e.Handled = true;
            if (e.Exception is ThreadAbortException) return;
            switch (Dialog.Fatal(e.Exception))
            {
                case TaskDialogResult.Yes:
                    Process.Start(Assembly.GetEntryAssembly().Location);
                    goto default;
                case TaskDialogResult.No:
                    break;
                default:
                    Shutdown(-1);
                    break;
            }
        }

        private enum ArgumentType { Invalid, Game, Profile }

        private void ApplicationExit(object sender, ExitEventArgs e)
        {
            Log.Performance.Dispose();  // output log
        }
    }

    sealed class Program : WindowsFormsApplicationBase
    {
        static Program()
        {
            AppDomain.CurrentDomain.SetData("PRIVATE_BINPATH", "Resources\\Libraries");
            var m = typeof(AppDomainSetup).GetMethod("UpdateContextProperty",
                                                     BindingFlags.NonPublic | BindingFlags.Static);
            var fusion = typeof(AppDomain).GetMethod("GetFusionContext",
                                                     BindingFlags.NonPublic | BindingFlags.Instance);
            m.Invoke(null, new[] { fusion.Invoke(AppDomain.CurrentDomain, null), "PRIVATE_BINPATH",
                                   "Resources\\Libraries" });
        }

        [STAThread]
        public static void Main(string[] args)
        {
            Thread.CurrentThread.CurrentUICulture = Thread.CurrentThread.CurrentCulture = new CultureInfo(Settings.Language);
            new Program().Run(args);
        }
        private Program()
        {
            IsSingleInstance = true;
        }

        public static readonly Stopwatch StartupTime = Stopwatch.StartNew();
        public static App App;
        public static bool Closing;

        public static void CloseAll()
        {
            Closing = true;
            foreach (Window win in App.Windows)
                try
                {
                    win.Close();
                }
                catch (InvalidOperationException) { }
        }

        private static void Crashed(object sender, UnhandledExceptionEventArgs e)
        {
            var ex = e.ExceptionObject as Exception;
            if (ex == null) return;
            IO.Log.Crash.Write(ex);
            MessageBox.Show(ex.Message, "* FATAL *", MessageBoxButton.OK, MessageBoxImage.Error);
        }

        protected override bool OnStartup(VBStartupEventArgs e)
        {
            AppDomain.CurrentDomain.UnhandledException += Crashed;
            App = new App();
            App.InitializeComponent();
            App.Run();
            return false;
        }

        protected override void OnStartupNextInstance(StartupNextInstanceEventArgs e)
        {
            App.ApplicationStartup(e.CommandLine, false);
        }
    }
}
