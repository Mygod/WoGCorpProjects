using System;
using System.ComponentModel;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Mygod.IO;
using Mygod.Windows;

namespace Mygod.WorldOfGoo.Cursor
{
    public sealed class Settings
    {
        static Settings()
        {
            var section = new IniFile("Settings.ini")["Settings"];
            ForegroundData = new ColorData(section, "Foreground", Colors.Black);
            BorderData = new ColorData(section, "Border", Color.FromRgb(0xb8, 0xb8, 0xb8));
            ExhaledRadiusData = new DoubleData(section, "ExhaledRadius", 9);
            InhaledRadiusData = new DoubleData(section, "InhaledRadius", 10);
            RefreshRateData = new DoubleData(section, "RefreshRate", 60);
            BorderThicknessData = new DoubleData(section, "BorderThickness", 3);
            BreathDurationData = new DoubleData(section, "BreathDuration", 20.0 / 9);
            LengthData = new Int32Data(section, "Length", 85);
            ShrinkRateData = new DoubleData(section, "ShrinkRate", 200.0);
            ShowOriginalCursorData = new YesNoData(section, "ShowOriginalCursor");
            SmootherCurveData = new YesNoData(section, "SmootherCurve", true);
            ForegroundData.DataChanged += OnPropertyChanged;
            BorderData.DataChanged += OnPropertyChanged;
            ExhaledRadiusData.DataChanged += OnPropertyChanged;
            InhaledRadiusData.DataChanged += OnPropertyChanged;
            RefreshRateData.DataChanged += OnPropertyChanged;
            BorderThicknessData.DataChanged += OnPropertyChanged;
            BreathDurationData.DataChanged += OnPropertyChanged;
            LengthData.DataChanged += OnPropertyChanged;
            ShrinkRateData.DataChanged += OnPropertyChanged;
            ShowOriginalCursorData.DataChanged += OnPropertyChanged;
            SmootherCurveData.DataChanged += OnPropertyChanged;
            UacIcon = Imaging.CreateBitmapSourceFromHIcon(System.Drawing.SystemIcons.Shield.Handle, Int32Rect.Empty,
                                                          BitmapSizeOptions.FromEmptyOptions());
        }

        private static readonly ColorData ForegroundData, BorderData;
        private static readonly DoubleData ExhaledRadiusData, InhaledRadiusData, BorderThicknessData,
                                           BreathDurationData, ShrinkRateData;
        public static readonly DoubleData RefreshRateData;
        private static readonly Int32Data LengthData;
        public static readonly YesNoData ShowOriginalCursorData;
        private static readonly YesNoData SmootherCurveData;

        public static Color Foreground { get { return ForegroundData.Get(); } set { ForegroundData.Set(value); } }
        public static Color Border { get { return BorderData.Get(); } set { BorderData.Set(value); } }
        public static double ExhaledRadius
            { get { return ExhaledRadiusData.Get(); } set { ExhaledRadiusData.Set(value); } }
        public static double InhaledRadius
            { get { return InhaledRadiusData.Get(); } set { InhaledRadiusData.Set(value); } }
        public static double BorderThickness
            { get { return BorderThicknessData.Get(); } set { BorderThicknessData.Set(value); } }
        public static double BreathDuration
            { get { return BreathDurationData.Get(); } set { BreathDurationData.Set(value); } }
        public static double ShrinkRate { get { return ShrinkRateData.Get(); } set { ShrinkRateData.Set(value); } }
        public static double RefreshRate { get { return RefreshRateData.Get(); } set { RefreshRateData.Set(value); } }
        public static int Length { get { return LengthData.Get(); } set { LengthData.Set(value); } }
        public static bool ShowOriginalCursor
            { get { return ShowOriginalCursorData.Get(); } set { ShowOriginalCursorData.Set(value); } }
        public static bool SmootherCurve
            { get { return SmootherCurveData.Get(); } set { SmootherCurveData.Set(value); } }

        public static bool AutoStartup
        {
            get { return StartupManager.IsStartAtWindowsStartup("WoGCursor"); }
            set { StartupManager.SetStartAtWindowsStartup("WoGCursor", value); OnPropertyChanged("AutoStartup"); }
        }

        public static BitmapSource UacIcon { get; private set; }

        public static event EventHandler<PropertyChangedEventArgs> StaticPropertyChanged;
        private static void OnPropertyChanged(string propertyName)
        {
            var handler = StaticPropertyChanged;
            if (handler != null) handler(null, new PropertyChangedEventArgs(propertyName));
        }
        private static void OnPropertyChanged(object sender, EventArgs e)
        {
            OnPropertyChanged(((StringData) sender).DataKey);
        }

        public static void ResetToDefault()
        {
            ForegroundData.ResetToDefault();
            BorderData.ResetToDefault();
            ExhaledRadiusData.ResetToDefault();
            InhaledRadiusData.ResetToDefault();
            RefreshRateData.ResetToDefault();
            BorderThicknessData.ResetToDefault();
            BreathDurationData.ResetToDefault();
            ShrinkRateData.ResetToDefault();
            LengthData.ResetToDefault();
            ShowOriginalCursorData.ResetToDefault();
            SmootherCurveData.ResetToDefault();
        }
    }
}
