using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Text;
using System.Windows;
using Mygod.Windows;
using Mygod.WorldOfGoo.IO;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class GameGooBallsTesterWindow
    {
        public GameGooBallsTesterWindow(Game g)
        {
            DataContext = game = g;
            InitializeComponent();
            GooBallTesterVisualDebug.IsChecked = Settings.GooBallTesterVisualDebugEnabled;
        }

        private readonly Game game;

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private void ClearTestGooBall(object sender, RoutedEventArgs e)
        {
            TestGooBallBox.Text = string.Empty;
            CheckTestGooBall();
        }

        private void TestGooBall(object sender, RoutedEventArgs e)
        {
            if (!CheckTestGooBall()) return;
            if (string.IsNullOrWhiteSpace(TestGooBallBox.Text)) return;
            Features.GooBallTestHelper.CreateAt(game.Res.Balls, TestGooBallBox.Text,
                                                (double) TestGooBallBox.Text.Split(',').LongLength / 20);
            Kernel.Execute(game, Features.GooBallTester.CreateAt
                (game.Res.Levels, new object[] { Settings.GooBallTesterVisualDebugEnabled ? R.True : R.False }));
        }

        private void CheckTestGooBall(object sender, RoutedEventArgs e)
        {
            CheckTestGooBall();
        }

        private bool CheckTestGooBall()
        {
            var balls = TestGooBallBox.Text.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries).ToList();
            StringBuilder error = new StringBuilder(), warning = new StringBuilder(), result = new StringBuilder();
            uint count = 0;
            if ((balls.Count & 1) == 1) balls.RemoveAt(balls.Count - 1);
            for (var i = 0; i < balls.Count; i++)
            {
                var no = i / 2 + 1;
                balls[i] = balls[i].Trim();
                if ((i & 1) == 0)
                {
                    uint j;
                    if (!uint.TryParse(balls[i], out j))
                        error.AppendFormat(Resrc.ErrorGooBallsTesterPositiveIntegerRequired, no);
                    if (j == 0)
                    {
                        balls.RemoveAt(i);
                        balls.RemoveAt(i);
                        i--;
                        continue;
                    }
                    count += j;
                }
                else
                {
                    var ball = game.Res.Balls.FirstOrDefault(p => p.ID == balls[i]);
                    if (ball == null || ball.ID == R.GooBallTestHelperGooBallName)
                        error.AppendFormat(Resrc.ErrorGooBallsTesterNotExist, no);
                }
                result.Append(balls[i]);
                if (i != balls.Count - 1) result.Append(',');
            }
            if (count > 500000) error.Append(Resrc.ErrorGooBallsTesterCountGreaterThan500000);
            else
            {
                if (count > 20000) warning.Append(Resrc.WarningGooBallsTesterCountGreaterThan20000);
                if (count > 1000) warning.Append(Resrc.WarningGooBallsTesterCountGreaterThan1000);
            }
            TestGooBallBox.Text = result.ToString();
            TestGooBallErrorDetails.Text = string.Empty;
            if (error.Length != 0) TestGooBallErrorDetails.Text += Resrc.ErrorStart + error;
            if (warning.Length != 0) TestGooBallErrorDetails.Text += Resrc.WarningStart + warning;
            TestGooBallErrorDetails.Text = TestGooBallErrorDetails.Text.Trim('\r', '\n');
            TestGooBallErrorDetails.Visibility = string.IsNullOrWhiteSpace(TestGooBallErrorDetails.Text)
                                                    ? Visibility.Collapsed : Visibility.Visible;
            return error.Length == 0;
        }

        private void GooBallTesterVisualDebugChanged(object sender, RoutedEventArgs e)
        {
            Settings.GooBallTesterVisualDebugEnabled = GooBallTesterVisualDebug.IsChecked == true;
        }

        private void OnDragEnter(object sender, DragEventArgs e)
        {
            if (!e.Data.GetDataPresent(R.GooBalls, true)) return;
            e.Effects = e.AllowedEffects & DragDropEffects.Link;
            DropTargetHelper.DragEnter(this, e.Data, e.GetPosition(this), e.Effects, Resrc.TestSelectedGooBalls);
            e.Handled = true;
        }
        private void OnDragOver(object sender, DragEventArgs e)
        {
            if (!e.Data.GetDataPresent(R.GooBalls, true)) return;
            e.Effects = e.AllowedEffects & DragDropEffects.Link;
            DropTargetHelper.DragOver(e.GetPosition(this), e.Effects);
            e.Handled = true;
        }
        private void OnDragLeave(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(R.GooBalls, true)) DropTargetHelper.DragLeave(e.Data);
        }
        private void OnDrop(object sender, DragEventArgs e)
        {
            if (!e.Data.GetDataPresent(R.GooBalls)) return;
            e.Effects = e.Data.GetDataPresent(R.GooBalls, true) ? e.AllowedEffects & DragDropEffects.Link
                                                                : DragDropEffects.None;
            if (e.Effects != DragDropEffects.Link) return;
            DropTargetHelper.Drop(e.Data, e.GetPosition(this), e.Effects);
            var gooBalls = (DraggableGooBalls)e.Data.GetData(R.GooBalls, true);
            Process(gooBalls.GooBallIDs, gooBalls.Number);
            e.Handled = true;
        }

        public void Process(IEnumerable<string> ids, int number)
        {
            if (number <= 0) return;
            if (!TestGooBallBox.Text.EndsWith(",")) TestGooBallBox.Text += ",";
            var numbers = number + ",";
            foreach (var ball in ids) TestGooBallBox.Text += numbers + ball + ',';
            CheckTestGooBall();
            Show();
        }
    }
}
