using System;
using System.ComponentModel;
using System.Windows.Media;
using Mygod.IO;
using Mygod.WorldOfGoo.Cursor.Annotations;

namespace Mygod.WorldOfGoo.Cursor
{
    public sealed class Settings : INotifyPropertyChanged
    {
        private Settings()
        {
            settingsFile = new IniFile("Settings.ini");
            settingsSection = new IniSection(settingsFile, "Settings");
            foregroundData = new ColorData(settingsSection, "Foreground", Colors.Black);
            borderData = new ColorData(settingsSection, "Border", Color.FromRgb(0xb8, 0xb8, 0xb8));
            exhaledRadiusData = new DoubleData(settingsSection, "ExhaledRadius", 9);
            inhaledRadiusData = new DoubleData(settingsSection, "InhaledRadius", 10);
            RefreshRateData = new DoubleData(settingsSection, "RefreshRate", 60);
            borderThicknessData = new DoubleData(settingsSection, "BorderThickness", 3);
            breathDurationData = new DoubleData(settingsSection, "BreathDuration", 20.0 / 9);
            lengthData = new Int32Data(settingsSection, "Length", 85);
            shrinkRateData = new DoubleData(settingsSection, "ShrinkRate", 200.0);
            ShowOriginalCursorData = new YesNoData(settingsSection, "ShowOriginalCursor", false);
            smootherCurveData = new YesNoData(settingsSection, "SmootherCurve", true);
            foregroundData.DataChanged += OnPropertyChanged;
            borderData.DataChanged += OnPropertyChanged;
            exhaledRadiusData.DataChanged += OnPropertyChanged;
            inhaledRadiusData.DataChanged += OnPropertyChanged;
            RefreshRateData.DataChanged += OnPropertyChanged;
            borderThicknessData.DataChanged += OnPropertyChanged;
            breathDurationData.DataChanged += OnPropertyChanged;
            lengthData.DataChanged += OnPropertyChanged;
            shrinkRateData.DataChanged += OnPropertyChanged;
            ShowOriginalCursorData.DataChanged += OnPropertyChanged;
            smootherCurveData.DataChanged += OnPropertyChanged;
        }

        public static readonly Settings Current = new Settings();

        private readonly IniFile settingsFile;
        private readonly IniSection settingsSection;
        private readonly ColorData foregroundData, borderData;
        private readonly DoubleData exhaledRadiusData, inhaledRadiusData, borderThicknessData, breathDurationData, shrinkRateData;
        public readonly DoubleData RefreshRateData;
        private readonly Int32Data lengthData;
        public readonly YesNoData ShowOriginalCursorData;
        private readonly YesNoData smootherCurveData;

        public Color Foreground { get { return foregroundData.Get(); } set { foregroundData.Set(value); } }
        public Color Border { get { return borderData.Get(); } set { borderData.Set(value); } }
        public double ExhaledRadius { get { return exhaledRadiusData.Get(); } set { exhaledRadiusData.Set(value); } }
        public double InhaledRadius { get { return inhaledRadiusData.Get(); } set { inhaledRadiusData.Set(value); } }
        public double BorderThickness { get { return borderThicknessData.Get(); } set { borderThicknessData.Set(value); } }
        public double BreathDuration { get { return breathDurationData.Get(); } set { breathDurationData.Set(value); } }
        public double ShrinkRate { get { return shrinkRateData.Get(); } set { shrinkRateData.Set(value); } }
        public double RefreshRate { get { return RefreshRateData.Get(); } set { RefreshRateData.Set(value); } }
        public int Length { get { return lengthData.Get(); } set { lengthData.Set(value); } }
        public bool ShowOriginalCursor { get { return ShowOriginalCursorData.Get(); } set { ShowOriginalCursorData.Set(value); } }
        public bool SmootherCurve { get { return smootherCurveData.Get(); } set { smootherCurveData.Set(value); } }
        public event PropertyChangedEventHandler PropertyChanged;

        [NotifyPropertyChangedInvocator]
        private void OnPropertyChanged(string propertyName)
        {
            var handler = PropertyChanged;
            if (handler != null) handler(this, new PropertyChangedEventArgs(propertyName));
        }
        private void OnPropertyChanged(object sender, EventArgs e)
        {
            OnPropertyChanged(((StringData) sender).DataKey);
        }

        public void ResetToDefault()
        {
            foregroundData.ResetToDefault();
            borderData.ResetToDefault();
            exhaledRadiusData.ResetToDefault();
            inhaledRadiusData.ResetToDefault();
            RefreshRateData.ResetToDefault();
            borderThicknessData.ResetToDefault();
            breathDurationData.ResetToDefault();
            shrinkRateData.ResetToDefault();
            lengthData.ResetToDefault();
            ShowOriginalCursorData.ResetToDefault();
            smootherCurveData.ResetToDefault();
        }
    }
}
