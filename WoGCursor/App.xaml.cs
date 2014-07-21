using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using System.Windows;
using System.Windows.Threading;
using Microsoft.VisualBasic.ApplicationServices;
using Microsoft.Win32;
using Mygod.Windows;
using VBStartupEventArgs = Microsoft.VisualBasic.ApplicationServices.StartupEventArgs;

namespace Mygod.WorldOfGoo.Cursor
{
    public sealed partial class App
    {
        private void OnUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
        {
            e.Handled = true;
            OnError(e.Exception);
        }

        public static void OnError(Exception e)
        {
            if (e == null || e is ThreadAbortException) return;
            var msg = e.GetMessage();
            File.WriteAllText("crash.log", msg);
            MessageBox.Show(
                "Something really TERRIBLE happened! Here are the details: (you can see it later in crash.log)" +
                Environment.NewLine + msg, "ERROR", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    public sealed class Program : WindowsFormsApplicationBase
    {
        private static readonly string RegistryKey = "EnableSecureUIAPaths",
                                       RegistryKeyBackup = RegistryKey + "_WoGCursor";

        [STAThread]
        public static void Main(string[] args)
        {
            AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
            if (args.Length == 1 && "-u".Equals(args[0], StringComparison.InvariantCultureIgnoreCase))
            {
                Uninstall();
                return;
            }
            new Program().Run(args);
        }
        private Program()
        {
            IsSingleInstance = true;
        }

        protected override bool OnStartup(VBStartupEventArgs e)
        {
            var app = new App();
            app.InitializeComponent();
            app.Run();
            return false;
        }

        private static readonly string[] Files =
        {
            "crash.log", "MygodLibrary.dll", "MygodLibrary.pdb", "Settings.ini",
            "World of Goo Cursor.exe", "World of Goo Cursor.pdb"
        };

        public static void Uninstall()
        {
            using (var key = Registry.LocalMachine.OpenSubKey
                                (@"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", true))
            {
                var val = (int)key.GetValue(RegistryKeyBackup, -1);
                key.DeleteValue(RegistryKeyBackup, false);
                if (val < 0) key.DeleteValue(RegistryKey);
                else key.SetValue(RegistryKey, val);
            }
            var store = new X509Store(StoreName.Root, StoreLocation.LocalMachine);
            store.Open(OpenFlags.ReadWrite);
            store.Remove(new X509Certificate2(CurrentApp.ReadResourceBytes("/Mygod.cer")));
            store.Close();
            MessageBox.Show(@"Uninstallation finished.
Some files are not deleted. You can delete them manually:" + 
                Files.Where(file => File.Exists(Path.Combine(CurrentApp.Directory, file)))
                     .Aggregate(string.Empty, (s, n) => s + Environment.NewLine + n),
                "Uninstall", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private static void OnUnhandledException(object sender, System.UnhandledExceptionEventArgs e)
        {
            App.OnError(e.ExceptionObject as Exception);
        }
    }
}
