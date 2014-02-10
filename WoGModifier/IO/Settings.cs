using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using Mygod.IO;
using Mygod.Security.Cryptography;
using Mygod.Windows;

namespace Mygod.WorldOfGoo.IO
{
    /// <summary>
    /// Wrapper between Settings.ini.
    /// </summary>
    public static class Settings
    {
        static Settings()
        {
            SettingsFile = new IniFile("Settings.ini");
            SettingsSection = new IniSection(SettingsFile, "Settings");
            RecentPathsData = new StringListData(SettingsFile, "RecentPaths");
            RecentPathsCapacityData = new Int32Data(RecentPathsData, "Capacity", 10);
            RecentPathsCapacityData.DataChanged += (sender, e) => 
                { RecentPaths = RecentPaths.Distinct().Take(RecentPathsCapacity).ToList(); };
            GamePathsData = new StringListData(SettingsFile, "GamePaths");
            ProfilePathsData = new StringListData(SettingsFile, "ProfilePaths");
            ThumbnailMaxHeightData = new DoubleData(SettingsSection, "ThumbnailMaxHeight", 48);
            GooBallTesterVisualDebugEnabledData = new BooleanData(SettingsSection, "GooBallTesterVisualDebugEnabled", false);
            ConsoleDebuggerEnabledData = new BooleanData(SettingsSection, "ConsoleDebuggerEnabled", false);
            LoadGooBallThumbnailData = new BooleanData(SettingsSection, "LoadGooBallThumbnail", true);
            QuickHelpViewedData = new BooleanData(SettingsSection, "QuickHelpViewed", false);
            ProfileBackupsDirectoryData = new StringData(SettingsSection, "ProfileBackupsDirectory", 
                Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Backups"));
            ThemeData = new StringData(SettingsSection, "Theme", "Generic");
            LanguageData = new StringData(SettingsSection, "Language", Thread.CurrentThread.CurrentUICulture.Name);
            BinFileEditorData = new StringData(SettingsSection, "BinFileEditor", "notepad");
            Alias = new StringDictionaryData(SettingsFile, "Alias");
        }
        private static readonly IniFile SettingsFile;
        private static readonly IniSection SettingsSection;
        internal static readonly StringListData RecentPathsData;
        private static readonly StringListData GamePathsData, ProfilePathsData;
        internal static readonly Int32Data RecentPathsCapacityData;
        internal static readonly DoubleData ThumbnailMaxHeightData;
        private static readonly BooleanData GooBallTesterVisualDebugEnabledData, ConsoleDebuggerEnabledData, QuickHelpViewedData;
        internal static readonly BooleanData LoadGooBallThumbnailData;
        internal static readonly StringData ProfileBackupsDirectoryData;
        private static readonly StringData ThemeData, LanguageData, BinFileEditorData;
        private static readonly StringDictionaryData Alias;

        internal static int RecentPathsCapacity 
            { get { return RecentPathsCapacityData.Get(); } set { RecentPathsCapacityData.Set(value); } }
        internal static List<string> RecentPaths { get { return RecentPathsData.Get(); } set { RecentPathsData.Set(value); } }
        internal static List<string> GamePaths { get { return GamePathsData.Get(); } set { GamePathsData.Set(value); } }
        internal static List<string> ProfilePaths { get { return ProfilePathsData.Get(); } set { ProfilePathsData.Set(value); } }
        internal static double ThumbnailMaxHeight
        {
            get { return ThumbnailMaxHeightData.Get(); } 
            set { ThumbnailMaxHeightData.Set(value); }
        }
        internal static bool GooBallTesterVisualDebugEnabled
            { get { return GooBallTesterVisualDebugEnabledData.Get(); } set { GooBallTesterVisualDebugEnabledData.Set(value); } }
        internal static bool LoadGooBallThumbnail
            { get { return LoadGooBallThumbnailData.Get(); } set { LoadGooBallThumbnailData.Set(value); } }
        internal static bool ConsoleDebuggerEnabled
            { get { return ConsoleDebuggerEnabledData.Get(); } set { ConsoleDebuggerEnabledData.Set(value); } }
        internal static bool QuickHelpViewed { get { return QuickHelpViewedData.Get(); } set { QuickHelpViewedData.Set(value); } }
        internal static string ProfileBackupsDirectory 
            { get { return ProfileBackupsDirectoryData.Get(); } set { ProfileBackupsDirectoryData.Set(value); } }
        internal static string Theme { get { return ThemeData.Get(); } set { ThemeData.Set(value); } }
        internal static string Language { get { return LanguageData.Get(); } set { LanguageData.Set(value); } }
        internal static string BinFileEditor { get { return BinFileEditorData.Get(); } set { BinFileEditorData.Set(value); } }

        public static bool CheatingFeaturesEnabled
        {
            get
            {
                try
                {
                    return File.Exists(Path.Combine(Path.GetDirectoryName(CurrentApp.Path) ?? String.Empty, "cheating.on"));
                }
                catch (NullReferenceException)
                {
                    return true;
                }
            }
        }

        public static string GetAlias(IHasAlias file)
        {
            return Alias.Get(MD5Helper.CalculateMD5(file.FilePath));
        }
        public static void SetAlias(IHasAlias file, string alias)
        {
            Alias.Set(MD5Helper.CalculateMD5(file.FilePath), alias);
        }
    }

    static class Globalization
    {
        /// <summary>
        /// 处理数据并本地化。
        /// </summary>
        /// <typeparam name="T">要本地化的数据类型。</typeparam>
        /// <param name="exchange">将文化名称（如zh-CN）转为数据类型的方法。</param>
        /// <param name="validCheck">检查数据是否合法。</param>
        /// <returns>如果某项数据通过数据检查就返回该项数据。</returns>
        public static T GetLocalizedValue<T>(Func<string, T> exchange, Func<T, bool> validCheck) where T : class
        {
            if (string.IsNullOrWhiteSpace(Settings.Language)) return exchange(null);
            var result = exchange(Settings.Language);
            if (validCheck(result)) return result;
            return Settings.Language.Split('-').Select(exchange).FirstOrDefault(validCheck) ?? exchange(null);
        }

        /// <summary>
        /// 获取本地化后的路径。
        /// </summary>
        /// <param name="dirFile">传递目录+文件名（不含扩展名）。如：C:\Hello。</param>
        /// <param name="extension">传递扩展名。如：txt。</param>
        /// <returns>返回本地化后的路径。</returns>
        public static string GetLocalizedPath(string dirFile, string extension)
        {
            return GetLocalizedValue(s => dirFile + '.' + (s == null ? string.Empty : (s + '.')) + extension, File.Exists);
        }
    }
}
