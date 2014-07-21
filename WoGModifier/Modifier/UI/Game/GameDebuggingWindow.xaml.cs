using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class GameDebuggingWindow
    {
        public GameDebuggingWindow(Game game, Process gameProcess)
        {
            DataContext = game;
            InitializeComponent();
            DebugStart = false;
            debugTimer = new DispatcherTimer(TimeSpan.FromSeconds(1), DispatcherPriority.Background, OutputConsole,
                                             App.Dispatcher) { IsEnabled = true };
            outputFile = Path.Combine(game.DirectoryPath, R.ConsoleOutput);
            fileName = Path.GetFileNameWithoutExtension(game.FilePath) ?? string.Empty;
            Task.Factory.StartNew(() =>
            {
                gameProcess.WaitForExit();
                if (DebugStart) Dispatcher.Invoke(() => StopDebugging(null, null));
            retry: 
                try
                {
                    File.Delete(outputFile); 
                    Thread.Sleep(1000);
                } 
                catch
                {
                    goto retry;
                }
            });
        }

        private readonly DispatcherTimer debugTimer;
        private bool debugStart;
        private bool DebugStart
        {
            get { return debugStart; }
            set
            {
                debugStart = value;
                Dispatcher.Invoke(() => Status.BorderBrush = value ? Brushes.Lime : Brushes.Red);
            }
        }

        private readonly string outputFile, fileName;

        private void OutputConsole(object sender, EventArgs e)
        {
            if (DebugStart)
            {
                if (File.Exists(outputFile))
                    using (var reader = new StreamReader(new FileStream(outputFile, FileMode.Open,
                                                                        FileAccess.Read, FileShare.ReadWrite)))
                        OutputBox.Text = reader.ReadToEnd();
            }
            else if (Process.GetProcessesByName(fileName).LongLength > 0) DebugStart = true;
        }

        private void StopDebugging(object sender, EventArgs e)
        {
            debugTimer.IsEnabled = false;
            OutputConsole(sender, e);
            DebugStart = false;
        }

        private void AbortGame(object sender, RoutedEventArgs e)
        {
            if (!DebugStart) return;
            var processes = Process.GetProcessesByName(fileName);
            if (processes.LongLength > 0) foreach (var process in processes) process.Kill();
        }
    }
}
