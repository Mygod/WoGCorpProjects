using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Mygod.Windows.Controls;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class PlayerWoGCorpWindow
    {
        public PlayerWoGCorpWindow(ProfilePlayer p)
        {
            InitializeComponent();
            DataContext = player = p;
            RefreshView();
        }
        
        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly ProfilePlayer player;
        private double minX, minY, maxX, maxY;
        private int startPoint = -1, selectedTool;
        private const double Bounds = 100;
        private readonly Dictionary<WoGCorpBall, Image> balls = new Dictionary<WoGCorpBall, Image>(), 
                                                        velocities = new Dictionary<WoGCorpBall, Image>();
        private readonly Dictionary<WoGCorpStrand, Image> strands = new Dictionary<WoGCorpStrand, Image>();

        private void RefreshView()
        {
            var strandBalls = player.WoGCorpStrands.Count(strand => strand.IsBall);
            BallCount.Text = (player.WoGCorpStrands.Select(strand => strand.StartPoint).Union(
                player.WoGCorpStrands.Select(strand => strand.EndPoint)).Count() + strandBalls).ToString()
                + " / " + (player.WoGCorpBalls.Count + strandBalls).ToString();
            if (player.WoGCorpBalls.Count > 0)
            {
                minY = minX = double.MaxValue;
                maxY = maxX = double.MinValue;
                foreach (var ball in player.WoGCorpBalls)
                {
                    double value = ball.CoordinateX - 16 + ball.VelocityX, i = Math.Min(ball.CoordinateX - 16, value);
                    if (i < minX) minX = i;
                    i = Math.Max(ball.CoordinateX - 16, value);
                    if (i > maxX) maxX = i;
                    value = ball.CoordinateY - 16 + ball.VelocityY;
                    i = Math.Min(ball.CoordinateY - 16, value);
                    if (i < minY) minY = i;
                    i = Math.Max(ball.CoordinateY - 16, value);
                    if (i > maxY) maxY = i;
                }
            }
            else minX = minY = maxX = maxY = 0;
            minX -= Bounds;
            minY = Math.Min(minY, 0) - Bounds;
            maxX += Bounds;
            maxY = Math.Max(maxY, 0) + Bounds;
            Shower.Width = Math.Abs(maxX - minX);
            Shower.Height = Math.Abs(maxY - minY);
            Ground.Width = Shower.Width;
            Canvas.SetBottom(Ground, -100.023 - minY);
            ((ImageBrush) Ground.Background).Viewport = new Rect(-((minX + 500.03) % 1479.68), 0, 1479.68, 107.206);
            foreach (var ball in player.WoGCorpBalls)
            {
                if (selectedTool == 1)
                {
                    if (!velocities.ContainsKey(ball))
                    {
                        var newDs = new Image
                        {
                            Width = 32, Source = new BitmapImage(new Uri("/Resources/Detachstrand.png", UriKind.Relative)), 
                            Tag = ball, Stretch = Stretch.Fill, RenderTransform = new RotateTransform {CenterX = 16}
                        };
                        newDs.PreviewMouseLeftButtonDown += OnBallPress;
                        newDs.PreviewMouseLeftButtonUp += OnBallRelease;
                        velocities.Add(ball, newDs);
                        Shower.Children.Add(newDs);
                    }
                    var ds = velocities[ball];
                    Canvas.SetLeft(ds, ball.CoordinateX - 16 - minX);
                    Canvas.SetBottom(ds, ball.CoordinateY - minY);
                    var transform = (RotateTransform)ds.RenderTransform;
                    transform.Angle = 90 - Math.Atan2(ball.VelocityY, ball.VelocityX) * 180 / Math.PI;
                    transform.CenterY = ds.Height = 10 * Math.Sqrt(ball.VelocityX * ball.VelocityX + ball.VelocityY * ball.VelocityY);
                    Shower.Children.Add(ds);
                }
                if (!balls.ContainsKey(ball))
                {
                    var newImage = new Image
                    {
                        Width = 32, Height = 32, Source = new BitmapImage(new Uri("/Resources/GooBall.png", UriKind.Relative)), Tag = ball, 
                        ContextMenu = Resources["BallMenu"] as ContextMenu
                    };
                    newImage.PreviewMouseLeftButtonDown += OnBallPress;
                    newImage.PreviewMouseMove += OnBallMouseMove;
                    newImage.PreviewMouseLeftButtonUp += OnBallRelease;
                    balls.Add(ball, newImage);
                    Shower.Children.Add(newImage);
                }
                var image = balls[ball];
                image.ToolTip = string.Format(Resrc.WoGCorpBallDetails, ball.CoordinateX, ball.CoordinateY, ball.VelocityX, ball.VelocityY);
                Canvas.SetLeft(image, ball.CoordinateX - 16 - minX);
                Canvas.SetBottom(image, ball.CoordinateY - 16 - minY);
            }
            foreach (var strand in player.WoGCorpStrands)
            {
                WoGCorpBall ball1 = player.WoGCorpBalls[strand.StartPoint], ball2 = player.WoGCorpBalls[strand.EndPoint];
                if (!strands.ContainsKey(strand))
                {
                    var newImage = new Image
                    {
                        Width = 32, Source = new BitmapImage(new Uri("/Resources/Strand.png", UriKind.Relative)),
                        Tag = strand, Stretch = Stretch.Fill, RenderTransform = new RotateTransform {CenterX = 16}
                    };
                    Panel.SetZIndex(newImage, -1);
                    DragCanvas.SetCanBeDragged(newImage, false);
                    newImage.PreviewMouseLeftButtonUp += OnStrandRelease;
                    strands.Add(strand, newImage);
                    Shower.Children.Add(newImage);
                }
                SetStrand(strands[strand], ball1.CoordinateX, ball1.CoordinateY, ball2.CoordinateX, ball2.CoordinateY);
            }
            Scroller.ScrollToHorizontalOffset(Scroller.HorizontalOffset);
            Scroller.ScrollToVerticalOffset(Scroller.VerticalOffset);
        }

        private void ShowNewStrand()
        {
            if (startPoint < 0) return;
            var mouse = Mouse.GetPosition(Shower);
            var ball = player.WoGCorpBalls[startPoint];
            SetStrand(NewStrand, ball.CoordinateX, ball.CoordinateY, mouse.X + minX, Shower.Height - mouse.Y + minY);
        }

        private void SetStrand(FrameworkElement image, double ax, double ay, double bx, double by)
        {
            Canvas.SetLeft(image, bx - 16 - minX);
            Canvas.SetBottom(image, by - minY);
            var transform = (RotateTransform)image.RenderTransform;
            transform.Angle = -90 - Math.Atan2(by - ay, bx - ax) * 180 / Math.PI;
            double x = ax - bx, y = ay - by;
            x *= x;
            y *= y;
            transform.CenterY = image.Height = Math.Sqrt(x + y);
        }

        private void OnShowerRelease(object sender, MouseButtonEventArgs e)
        {
            switch (selectedTool)
            {
                case 2:
                {
                    var point = e.GetPosition(Shower);
                    player.WoGCorpBalls.Add(new WoGCorpBall(cx: point.X + minX, cy: Shower.Height - point.Y + minY));
                    RefreshView();
                    break;
                }
                case 4:
                {
                    NewStrand.Visibility = Visibility.Collapsed;
                    break;
                }
            }
        }

        private void Remove(WoGCorpBall ball)
        {
            var count = player.WoGCorpBalls.TakeWhile(b => b != ball).Count();
            player.WoGCorpBalls.Remove(ball);
            foreach (var strand in player.WoGCorpStrands.ToList())
                if (strand.StartPoint == count || strand.EndPoint == count) Remove(strand);
                else
                {
                    if (strand.StartPoint > count) strand.StartPoint--;
                    if (strand.EndPoint > count) strand.EndPoint--;
                }
            Shower.Children.Remove(balls[ball]);
            balls.Remove(ball);
            if (velocities.ContainsKey(ball))
            {
                Shower.Children.Remove(velocities[ball]);
                velocities.Remove(ball);
            }
            RefreshView();
        }
        private void Remove(WoGCorpStrand strand)
        {
            player.WoGCorpStrands.Remove(strand);
            Shower.Children.Remove(strands[strand]);
            strands.Remove(strand);
        }

        private void OnBallPress(object sender, MouseButtonEventArgs e)
        {
            var image = sender as Image;
            if (image == null) return;
            var ball = image.Tag as WoGCorpBall;
            if (ball == null) return;
            switch (selectedTool)
            {
                case 1:
                    image.CaptureMouse();
                    break;
                case 3:
                    Remove(ball);
                    e.Handled = true;
                    break;
                case 4:
                    startPoint = player.WoGCorpBalls.TakeWhile(b => b != ball).Count();
                    NewStrand.Visibility = Visibility.Visible;
                    ShowNewStrand();
                    break;
            }
        }

        private void OnBallMouseMove(object sender, MouseEventArgs e)
        {
            var image = sender as Image;
            if (image == null) return;
            var ball = image.Tag as WoGCorpBall;
            if (ball == null || Mouse.LeftButton != MouseButtonState.Pressed) return;
            switch (selectedTool)
            {
                case 0:
                    double ix = minX, iy = minY, ax = maxX, ay = maxY;
                    var point = e.GetPosition(Shower);
                    ball.CoordinateX = point.X + minX;
                    ball.CoordinateY = Shower.Height - point.Y + minY;
                    RefreshView();
                    if (Math.Abs(minX - ix) > 1e-4 || Math.Abs(minY - iy) > 1e-4 || Math.Abs(maxX - ax) > 1e-4 || Math.Abs(maxY - ay) > 1e-4)
                        break;
                    point = image.TranslatePoint(new Point(16, 16), Scroller);
                    const double dampening = 10;
                    if (point.X < Bounds) Scroller.ScrollToHorizontalOffset(Scroller.HorizontalOffset + (point.X - Bounds) / dampening);
                    if (point.X > Scroller.ActualWidth - Bounds)
                        Scroller.ScrollToHorizontalOffset(Scroller.HorizontalOffset + (Bounds + point.X - Scroller.ActualWidth) / dampening);
                    if (point.Y < Bounds) Scroller.ScrollToVerticalOffset(Scroller.VerticalOffset + (point.Y - Bounds) / dampening);
                    if (point.Y > Scroller.ActualHeight - Bounds)
                        Scroller.ScrollToVerticalOffset(Scroller.VerticalOffset + (Bounds + point.Y - Scroller.ActualHeight) / dampening);
                    break;
                case 3:
                    Remove(ball);
                    break;
            }
        }

        private void OnBallRelease(object sender, MouseButtonEventArgs e)
        {
            var image = sender as Image;
            if (image == null) return;
            var ball = image.Tag as WoGCorpBall;
            if (ball == null) return;
            switch (selectedTool)
            {
                case 0:
                {
                    var point = e.GetPosition(Shower);
                    ball.CoordinateX = point.X + minX;
                    ball.CoordinateY = Shower.Height - point.Y + minY;
                    RefreshView();
                    break;
                }
                case 1:
                {
                    var point = e.GetPosition(image);
                    ball.VelocityX = (point.X - 16) / 10;
                    ball.VelocityY = (16 - point.Y) / 10;
                    RefreshView();
                    break;
                }
                case 4:
                {
                    var endPoint = player.WoGCorpBalls.TakeWhile(b => b != ball).Count();
                    if (startPoint != endPoint && startPoint != -1)
                    {
                        player.WoGCorpStrands.Add(new WoGCorpStrand(sp: startPoint, ep: endPoint));
                        RefreshView();
                    }
                    NewStrand.Visibility = Visibility.Collapsed;
                    startPoint = -1;
                    break;
                }
            }
        }

        private void OnStrandRelease(object sender, MouseButtonEventArgs e)
        {
            if (selectedTool != 5) return;
            var image = sender as Image;
            if (image == null) return;
            var strand = image.Tag as WoGCorpStrand;
            if (strand == null) return;
            Remove(strand);
            RefreshView();
        }

        private void Scroll(object sender, MouseWheelEventArgs e)
        {
            e.Handled = true;
            var delta = e.Delta / 12.0 * (Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt) ? 5 : 1);
            if (Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl))
                ZoomPaner.AnimatedZoomAboutPoint(ZoomPaner.ContentScale + delta / 100, e.GetPosition(Shower));
            else if (Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift))
                Scroller.ScrollToHorizontalOffset(Scroller.ContentHorizontalOffset - delta);
            else Scroller.ScrollToVerticalOffset(Scroller.ContentVerticalOffset - delta);
        }

        private void ScaleToFit(object sender, RoutedEventArgs e)
        {
            ZoomPaner.AnimatedScaleToFit();
        }

        private void ScaleTo100(object sender, RoutedEventArgs e)
        {
            ZoomPaner.AnimatedZoomTo(1);
        }

        private void ZoomIn(object sender, ExecutedRoutedEventArgs e)
        {
            ZoomPaner.AnimatedZoomTo(ZoomPaner.ContentScale + 0.1);
        }

        private void ZoomOut(object sender, ExecutedRoutedEventArgs e)
        {
            ZoomPaner.AnimatedZoomTo(ZoomPaner.ContentScale - 0.1);
        }

        private void ChangeState(object sender, RoutedEventArgs e)
        {
            var source = sender is ToggleButton ? sender : e.OriginalSource;
            var i = -1;
            var iv = selectedTool == 1;
            foreach (ToggleButton button in Toolbar.Children)
            {
                i++;
                if ((button.IsChecked = Equals(button, source)) == true) selectedTool = i;
            }
            Shower.AllowDragging = selectedTool == 0;
            if (iv && selectedTool != 1)
            {
                foreach (var pair in velocities) Shower.Children.Remove(pair.Value);
                RefreshView();
            }
            else if (selectedTool == 1)
            {
                foreach (var pair in velocities) Shower.Children.Add(pair.Value);
                RefreshView();
            }
        }

        private void OnLoad(object sender, RoutedEventArgs e)
        {
            var transform = ZoomPaner.TransformToAncestor(MainGrid);
            Point topLeftFrame = transform.Transform(new Point(0, 0)), 
                  bottomRightFrame = transform.Transform(new Point(ZoomPaner.ActualWidth, ZoomPaner.ActualHeight));
            TaskbarItem.ThumbnailClipMargin = new Thickness
            {
                Left = topLeftFrame.X, Right = MainGrid.ActualWidth - bottomRightFrame.X,
                Top = topLeftFrame.Y, Bottom = MainGrid.ActualHeight - bottomRightFrame.Y
            };
        }

        private void OnShowerMouseMove(object sender, MouseEventArgs e)
        {
            var p = e.GetPosition(Shower);
            CursorX.Text = (p.X + minX).ToString();
            CursorY.Text = (Shower.Height - p.Y + minY).ToString();
            ShowNewStrand();
        }

        private void EditPosition(object sender, RoutedEventArgs e)
        {
            var item = sender as MenuItem;
            if (item == null) return;
            var image = item.CommandTarget as Image;
            if (image == null) return;
            var ball = image.Tag as WoGCorpBall;
            if (ball == null) return;
            var result = Dialog.Input(Resrc.EnterNewValueTitle, ball.CoordinateX + "," + ball.CoordinateY, validCheck: s =>
            {
                var t = s.Split(',');
                if (t.Length != 2) return false;
                double test;
                return double.TryParse(t[0], out test) && double.TryParse(t[1], out test);
            });
            if (string.IsNullOrEmpty(result)) return;
            var r = result.Split(',');
            ball.CoordinateX = double.Parse(r[0]);
            ball.CoordinateY = double.Parse(r[1]);
            RefreshView();
        }

        private void EditVelocity(object sender, RoutedEventArgs e)
        {
            var item = sender as MenuItem;
            if (item == null) return;
            var image = item.CommandTarget as Image;
            if (image == null) return;
            var ball = image.Tag as WoGCorpBall;
            if (ball == null) return;
            var result = Dialog.Input(Resrc.EnterNewValueTitle, ball.VelocityX + "," + ball.VelocityY, validCheck: s =>
            {
                var t = s.Split(',');
                if (t.Length != 2) return false;
                double test;
                return double.TryParse(t[0], out test) && double.TryParse(t[1], out test);
            });
            if (string.IsNullOrEmpty(result)) return;
            var r = result.Split(',');
            ball.VelocityX = double.Parse(r[0]);
            ball.VelocityY = double.Parse(r[1]);
            RefreshView();
        }

        private void BoundKeyPressed(object sender, ExecutedRoutedEventArgs e)
        {
            if (e.Command == Commands.EditItem1) ChangeState(Toolbar.Children[0], null);
            else if (e.Command == Commands.EditItem2) ChangeState(Toolbar.Children[1], null);
            else if (e.Command == Commands.EditItem3) ChangeState(Toolbar.Children[2], null);
            else if (e.Command == Commands.EditItem4) ChangeState(Toolbar.Children[3], null);
            else if (e.Command == Commands.EditItem5) ChangeState(Toolbar.Children[4], null);
            else if (e.Command == Commands.EditItem6) ChangeState(Toolbar.Children[5], null);
        }

        private void IsCheatingFeaturesEnabled(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = Settings.CheatingFeaturesEnabled;
        }
    }
}
