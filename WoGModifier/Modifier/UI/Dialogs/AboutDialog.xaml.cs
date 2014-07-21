using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using Mygod.Windows;
using Mygod.Windows.Controls;

namespace Mygod.WorldOfGoo.Modifier.UI.Dialogs
{
    sealed partial class AboutDialog
    {
        public AboutDialog()
        {
            InitializeComponent();
            Title += Resrc.Title;
            Details.Text = string.Format(Resrc.AboutDetails, Resrc.Title, "Mygod", CurrentApp.CompilationTime);
            if (DateTime.Now.Month == 8 && DateTime.Now.Day == 16)
                Logo.Source = new BitmapImage(new Uri("/Resources/Birthday.png", UriKind.Relative));
        }

        private void TechSupport(object sender, RoutedEventArgs e)
        {
            Process.Start(R.TechSupportUrl);
        }

        private void OK(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void EasterEgg(object sender, MouseButtonEventArgs e)
        {
            var random = new Random();
            var animation = new ColorAnimation(WoGCursor.Border, 
                Color.FromRgb((byte)random.Next(0xB9), (byte)random.Next(0xB9), (byte)random.Next(0xB9)),
                new Duration(TimeSpan.FromSeconds(1)));
            Storyboard.SetTarget(animation, WoGCursor);
            Storyboard.SetTargetProperty(animation, new PropertyPath(WorldOfGooCursor.BorderProperty));
            var s = new Storyboard {Duration = new Duration(TimeSpan.FromSeconds(1))};
            s.Children.Add(animation);
            s.Begin();
        }
    }
}
