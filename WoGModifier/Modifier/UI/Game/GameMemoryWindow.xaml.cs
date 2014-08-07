using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    internal partial class GameMemoryWindow
    {
        public GameMemoryWindow()
        {
            InitializeComponent();
            timer = new DispatcherTimer(TimeSpan.FromMilliseconds(100), DispatcherPriority.Render, Update, Dispatcher);
            EditEnabled = false;
        }

        private WorldOfGooMemoryEditor editor;
        private readonly DispatcherTimer timer;
        private Process process;

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        public void Show(Game game)
        {
            Show();
            FileName.Text = Path.GetFileName(game.FilePath);
            EditEnabled = false;
            timer.IsEnabled = true;
        }

        private bool EditEnabled
        {
            set
            {
                if (value)
                {
                    editor = new WorldOfGooMemoryEditor(process);
                    Status.BorderBrush = Brushes.Lime;
                    process.EnableRaisingEvents = true;
                    process.Exited += (sender, e) => EditEnabled = false;
                }
                else
                {
                    process = null;
                    Dispatcher.Invoke(() => Status.BorderBrush = Brushes.Red);
                }
                Dispatcher.Invoke(() => EditBallsCollectedButton.IsEnabled = EditBallsRequiredButton.IsEnabled = EditMovesUsedButton.IsEnabled
                    = GooBallsUndraggable.IsEnabled = Letterboxed.IsEnabled = Paused.IsEnabled = value);
                // = MenuEnabled.IsEnabled = ShowBallsInTank.IsEnabled
            }
        }

        private void Update(object sender, EventArgs e)
        {
            if (process == null)
            {
                var text = FileName.Text;
                if (text.EndsWith(".exe")) text = text.Substring(0, text.Length - 4);
                var processes = Process.GetProcessesByName(text);
                if (processes.Length == 0) return;
                process = processes[0];
                EditEnabled = true;
            }
            BallsCollected.Text = editor.Balls.ToString(CultureInfo.InvariantCulture);
            BallsRequired.Text = editor.BallsRequired.ToString(CultureInfo.InvariantCulture);
            MovesUsed.Text = editor.Moves.ToString(CultureInfo.InvariantCulture);
            GooBallsUndraggable.IsChecked = editor.Undraggable;
            Letterboxed.IsChecked = editor.Letterboxed;
            //MenuEnabled.IsChecked = editor.MenuEnabled;
            Paused.IsChecked = editor.Paused;
            //ShowBallsInTank.IsChecked = editor.ShowBallsInTank;
        }

        private void CheckBoxStateChanged(object sender, RoutedEventArgs e)
        {
            var box = (CheckBox) e.OriginalSource;
            switch (int.Parse(box.Tag.ToString(), CultureInfo.InvariantCulture))
            {
                case 0:
                    Topmost = box.IsChecked == true;
                    break;
                case 1:
                    editor.Undraggable = box.IsChecked == true;
                    break;
                case 2:
                    editor.Letterboxed = box.IsChecked == true;
                    break;
                case 3:
                    //editor.MenuEnabled = box.IsChecked == true;
                    break;
                case 4:
                    editor.Paused = box.IsChecked == true;
                    break;
                case 5:
                    //editor.ShowBallsInTank = box.IsChecked == true;
                    break;
            }
        }

        private void EditFileName(object sender, RoutedEventArgs e)
        {
            var result = Dialog.Input(Resrc.EnterNewValueTitle, FileName.Text);
            if (string.IsNullOrWhiteSpace(result) || result == FileName.Text) return;
            FileName.Text = result;
            EditEnabled = false;
        }

        private void EditBallsCollected(object sender, RoutedEventArgs e)
        {
            var result = Dialog.Input(Resrc.EnterNewValueTitle, BallsCollected.Text, EnterType.Int32);
            if (!string.IsNullOrWhiteSpace(result) && result != BallsCollected.Text) editor.Balls = int.Parse(result);
        }

        private void EditBallsRequired(object sender, RoutedEventArgs e)
        {
            var result = Dialog.Input(Resrc.EnterNewValueTitle, BallsRequired.Text, EnterType.Int32);
            if (!string.IsNullOrWhiteSpace(result) && result != BallsRequired.Text)
                editor.BallsRequired = int.Parse(result);
        }

        private void EditMovesUsed(object sender, RoutedEventArgs e)
        {
            var result = Dialog.Input(Resrc.EnterNewValueTitle, MovesUsed.Text, EnterType.Int32);
            if (!string.IsNullOrWhiteSpace(result) && result != MovesUsed.Text) editor.Moves = int.Parse(result);
        }
    }
}
