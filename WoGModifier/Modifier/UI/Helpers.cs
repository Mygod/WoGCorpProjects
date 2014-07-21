using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Input;
using System.Windows.Media.Imaging;
using Mygod.Windows;
using Mygod.WorldOfGoo.IO;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    internal static class Commands
    {
        public static readonly RoutedCommand
            Quit = new RoutedCommand("Quit", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.F4, ModifierKeys.Alt) }),
            Rename = new RoutedCommand("Rename", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.F2) }),
            SaveAs = new RoutedCommand("SaveAs", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.S, ModifierKeys.Control | ModifierKeys.Shift) }),
            Options = new RoutedCommand("Options", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.K, ModifierKeys.Control) }),
            BackupProfile = new RoutedCommand("BackupProfile", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.F12) }),
            About = new RoutedCommand("About", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.F1, ModifierKeys.Control) }),
            DetailedHelp = new RoutedCommand("DetailedHelp", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.F1, ModifierKeys.Shift) }),
            BrowseLevels = new RoutedCommand("BrowseLevels", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.L, ModifierKeys.Control) }),
            BrowseGooBalls = new RoutedCommand("BrowseGooBalls", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.B, ModifierKeys.Control) }),
            BrowseIslands = new RoutedCommand("BrowseIslands", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.I, ModifierKeys.Control) }),
            BrowseMaterials = new RoutedCommand("BrowseMaterials", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.M, ModifierKeys.Control) }),
            BrowseText = new RoutedCommand("BrowseText", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.T, ModifierKeys.Control) }),
            BrowseWoGCorp = new RoutedCommand("BrowseWoGCorp", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.W, ModifierKeys.Control) }),
            EditMemory = new RoutedCommand("EditMemory", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.E, ModifierKeys.Control) }),
            Default = new RoutedCommand("Default", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.Enter) }),
            ControlDefault = new RoutedCommand("ControlDefault", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.Enter, ModifierKeys.Control) }),
            Refresh = new RoutedCommand("Refresh", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.F5) }),
            Insert = new RoutedCommand("Insert", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.Insert) }),
            Sort = new RoutedCommand("SortLevels", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.F8) }),
            Process = new RoutedCommand("Process", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.P, ModifierKeys.Control) }),
            Restore = new RoutedCommand("Restore", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.R, ModifierKeys.Control) }),
            PlayMusic = new RoutedCommand("PlayMusic", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D, ModifierKeys.Control) }),

            EditItem1 = new RoutedCommand("EditItem1", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D1, ModifierKeys.Control) }),
            EditItem2 = new RoutedCommand("EditItem2", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D2, ModifierKeys.Control) }),
            EditItem3 = new RoutedCommand("EditItem3", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D3, ModifierKeys.Control) }),
            EditItem4 = new RoutedCommand("EditItem4", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D4, ModifierKeys.Control) }),
            EditItem5 = new RoutedCommand("EditItem5", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D5, ModifierKeys.Control) }),
            EditItem6 = new RoutedCommand("EditItem6", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D6, ModifierKeys.Control) }),
            EditItem7 = new RoutedCommand("EditItem7", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.D7, ModifierKeys.Control) }),

            ZoomIn = new RoutedCommand("ZoomIn", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.OemPlus) }),
            ZoomOut = new RoutedCommand("ZoomOut", typeof(MenuItem),
                new InputGestureCollection { new KeyGesture(Key.OemMinus) });
    }

    [ValueConversion(typeof(string), typeof(BitmapImage))]
    public class GooBallThumbnailConverter : IValueConverter
    {
        private static readonly Lazy<BitmapImage> Token = new Lazy<BitmapImage>(() =>
            new BitmapImage(new Uri("/Resources/GooBall.png", UriKind.Relative)));

        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!Settings.LoadGooBallThumbnail) return Token;
            var s = value as string;
            return s == null ? null : new BitmapImage(new Uri(s));
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    [ValueConversion(typeof(BitmapImage), typeof(double))]
    public class GooBallThumbnailHeightConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var s = value as BitmapImage;
            return s == null ? 0 : Math.Min(s.Height, Settings.ThumbnailMaxHeight);
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    [ValueConversion(typeof(string), typeof(string))]
    public class LanguageNameConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null) return null;
            var str = value.ToString().ToLower();
            if (str == "text") return Resrc.DefaultText;
            if (str == "cn") return new CultureInfo("zh-CN").DisplayName;
            try
            {
                return new CultureInfo(str).DisplayName;
            }
            catch (CultureNotFoundException)
            {
                var cul = CultureInfo.GetCultures(CultureTypes.AllCultures)
                                     .FirstOrDefault(c => c.Name.ToLower().Contains(str));
                return cul != null ? cul.DisplayName : Resrc.UnknownLanguage;
            }
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    [ValueConversion(typeof(string), typeof(string))]
    public class FirstLineConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null) return null;
            var str = value.ToString();
            var i = str.IndexOf('\r');
            if (i < 0) return str;
            return str.Substring(0, i) + "...";
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    internal class TreeItemTemplateSelector : DataTemplateSelector
    {
        public override DataTemplate SelectTemplate(object item, DependencyObject container)
        {
            if (item is Game) return (DataTemplate)Application.Current.Resources["GameTemplate"];
            if (item is Profile) return (DataTemplate)Application.Current.Resources["ProfileTemplate"];
            return base.SelectTemplate(item, container);
        }
    }

    [ValueConversion(typeof(string), typeof(BitmapImage))]
    public class ImagePathConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var s = value as string;
            if (s == null) throw Exceptions.NotSupported;
            return s.ToLower().EndsWith(".exe", StringComparison.Ordinal) ? IconExtractor.GetBitmapSource(s)
                                                                          : new BitmapImage(new Uri(s));
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    [ValueConversion(typeof(int), typeof(int))]
    public class AddOneConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!(value is int)) throw Exceptions.NotSupported;
            return (int)value + 1;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!(value is int)) throw Exceptions.NotSupported;
            return (int)value - 1;
        }
    }

    [ValueConversion(typeof(bool), typeof(Visibility))]
    public class CollapsedWhileTrueConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null) value = false;
            if (!(value is bool)) return null;
            return (bool)value ? Visibility.Collapsed : Visibility.Visible;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!(value is Visibility)) return null;
            return ((Visibility)value) == Visibility.Collapsed;
        }
    }

    [ValueConversion(typeof(bool), typeof(Visibility))]
    public class VisibleWhileTrueConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null) value = false;
            if (!(value is bool)) return null;
            return (bool)value ? Visibility.Visible : Visibility.Collapsed;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!(value is Visibility)) return null;
            return ((Visibility)value) == Visibility.Visible;
        }
    }

    [ValueConversion(typeof(bool), typeof(FontWeight))]
    public class BoldWhileTrueConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!(value is bool)) return null;
            return (bool)value ? FontWeights.Bold : FontWeights.Normal;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    [ValueConversion(typeof(int), typeof(string))]
    public class NoDisplayNegativeConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!(value is int)) return null;
            var i = (int)value;
            return i < 0 ? "-" : i.ToString(CultureInfo.InvariantCulture);
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null) return -1;
            var s = value.ToString().Trim();
            if (s == "-") return -1;
            int i;
            if (!int.TryParse(s, out i)) return -1;
            return i < 0 ? -1 : i;
        }
    }

    public class NoCommaValidationRule : ValidationRule
    {
        public override ValidationResult Validate(object value, CultureInfo cultureInfo)
        {
            if (value == null) return new ValidationResult(false, null);
            var s = value.ToString();
            return new ValidationResult(!s.Contains(","), s);
        }
    }

    [ValueConversion(typeof(double), typeof(double))]
    public class PercentConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is double) return Math.Round(100 * (double) value, 2);
            return null;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is double) return 0.01 * (double)value;
            return null;
        }
    }

    [ValueConversion(typeof(bool), typeof(bool))]
    public class NotConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (!(value is bool)) return null;
            return !(bool)value;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            return Convert(value, targetType, parameter, culture);
        }
    }

    [ValueConversion(typeof(Level), typeof(string))]
    public class IDShower : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var level = value as Level;
            if (level == null) return null;
            if (level.LocalizedName == level.ID) return null;
            return " (" + level.ID + ')';
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    [ValueConversion(typeof(string), typeof(string))]
    public class FileNameConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var path = value as string;
            return path == null ? null : Path.GetFileName(path);
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    [ValueConversion(typeof(GameKeyedCollection<PlayedLevel>), typeof(string))]
    public class LevelsTotalConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var levels = value as AdvancedGameKeyedCollection<PlayedLevel>;
            if (levels == null) return null;
            int og = 0, om = 0, os = 0, cg = 0, cm = 0, cs = 0;
            foreach (var level in levels.Where(level => !level.Skipped))
                if (Levels.OriginalLevelsID.Contains(level.LevelID))
                {
                    og += level.MostGoos;
                    om += level.FewestMoves;
                    os += level.FewestSeconds;
                }
                else
                {
                    cg += level.MostGoos;
                    cm += level.FewestMoves;
                    cs += level.FewestSeconds;
                }
            return string.Format(Resrc.PlayerLevelsTotal, og, om, os, cg, cm, cs, og + cg, om + cm, os + cs);
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    public class AliasFilePathConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            if (values.Length != 2) throw Exceptions.NotSupported;
            var filePath = values[0] as string;
            if (filePath == null) throw Exceptions.NotSupported;
            var alias = values[1] as string;
            if (!string.IsNullOrEmpty(alias)) return alias + " (" + filePath + ")";
            return filePath;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }

    public class TitleAliasFileNameConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            if (values.Length < 3) throw Exceptions.NotSupported;
            var title = (values[0] as string) ?? string.Empty;
            var alias = values[1] as string;
            if (string.IsNullOrEmpty(alias)) alias = values[2] as string;
            if (alias == null) alias = string.Empty;
            var objs = new object[values.Length - 2];
            objs[0] = alias;
            for (var i = 3; i < values.Length; i++) objs[i - 2] = values[i];
            return string.Format(title, objs);
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw Exceptions.NotSupported;
        }
    }
}
