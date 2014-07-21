using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Threading;
using Mygod.Collections.ObjectModel;
using Mygod.Runtime.Serialization.Plist;
using Mygod.WorldOfGoo.IO;

namespace Mygod.WorldOfGoo
{
    public sealed class Profile : ObservableKeyedCollection<int, ProfilePlayer>, IGameBinFile, IHasAlias
    {
        public Profile(string profilePath, UnhandledExceptionEventHandler refreshError = null, bool flushNow = true)
        {
            FilePath = profilePath;
            CollectionChanged += OnPlayersChanged;
            if (refreshError != null) RefreshError += refreshError;
            if (flushNow) Refresh();
        }

        private void OnPlayersChanged(object sender, NotifyCollectionChangedEventArgs e)
        {
            if (e.NewItems != null) foreach (INotifyPropertyChanged item in e.NewItems)
                item.PropertyChanged += OnPlayerPropertyChanged;
            if (e.OldItems != null) foreach (INotifyPropertyChanged item in e.OldItems)
                item.PropertyChanged -= OnPlayerPropertyChanged;
            IsSaved = false;
        }

        public static string NewVersionProfilePath
        {
            get
            {
                var path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                                        R.ProfilePath);
                return File.Exists(path) ? path : null;
            }
        }
        public static string OldVersionProfilePath
        {
            get
            {
                var path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                                        R.ProfilePath);
                return File.Exists(path) ? path : null;
            }
        }

        private List<ProfileItem> profileContent;
        public string CountryCode
        {
            get
            {
                if (IsRefreshing) throw new InvalidOperationException();
                var item = profileContent.SingleOrDefault(s => s.Key == "countrycode");
                return item == null ? string.Empty : item.Value;
            }
            set
            {
                if (value.Contains(',')) throw new FormatException();
                var item = profileContent.SingleOrDefault(s => s.Key == "countrycode");
                if (item == null) profileContent.Add(new ProfileItem("countrycode", value)); else item.Value = value;
                OnPropertyChanged("CountryCode");
            }
        }
        public bool Fullscreen
        {
            get
            {
                if (IsRefreshing) throw new InvalidOperationException();
                var item = profileContent.SingleOrDefault(s => s.Key == "fullscreen");
                return (item == null ? R.True : item.Value) == R.True;
            }
            set
            {
                var item = profileContent.SingleOrDefault(s => s.Key == "fullscreen");
                if (item == null) profileContent.Add(new ProfileItem("fullscreen", value ? R.True : R.False));
                else item.Value = value ? R.True : R.False;
                OnPropertyChanged("Fullscreen");
            }
        }
        public int MostRecentPlayerProfile
        {
            get
            {
                if (IsRefreshing) throw new InvalidOperationException();
                var item = profileContent.SingleOrDefault(s => s.Key == "mrpp");
                return item == null ? 0 : Convert.ToInt32(item.Value);
            }
            set
            {
                if (value < 0 || value > 2) throw new ArgumentOutOfRangeException("value");
                var item = profileContent.SingleOrDefault(s => s.Key == "mrpp");
                if (item == null)
                    profileContent.Add(new ProfileItem("mrpp", value.ToString(CultureInfo.InvariantCulture)));
                else item.Value = value.ToString(CultureInfo.InvariantCulture);
                OnPropertyChanged("MostRecentPlayerProfile");
                OnPropertyChanged("MostRecentPlayer");
            }
        }
        public ProfilePlayer MostRecentPlayer
        {
            get
            {
                if (IsRefreshing) throw new InvalidOperationException(); return this[MostRecentPlayerProfile];
            }
        }

        public string Alias
        {
            get { return Settings.GetAlias(this); }
            set
            {
                Settings.SetAlias(this, value);
                OnPropertyChanged("Alias");
            }
        }

        public override string ToString()
        {
            if (IsRefreshing) return "0.";
            return profileContent.Aggregate(string.Empty, (current, content) => current + content) +
                   this.Aggregate(string.Empty, (current, player) => current + player) + ",0.";
        }

        private bool isPlistFormat;

        public IGameDirectory Parent { get { throw Exceptions.NotSupported; } }

        public string FilePath { get; private set; }

        public void Save()
        {
            Save(null, isPlistFormat);
        }
        public void Save(string path, bool? isPlist = null)
        {
            if (IsRefreshing) throw new InvalidOperationException();
            if (path == null) path = FilePath;
            if (!isPlist.HasValue) isPlist = path.ToLower().EndsWith(".plist");
            if (isPlist.Value) new BinaryPlistWriter().WriteObject(path, new Dictionary<string, byte[]>
                { { "pers2.dat", Encoding.UTF8.GetBytes(ToString()) } });
            else BinaryFile.WriteAllText(path, ToString());
            IsSaved = true;
        }
        public void Refresh()
        {
            if (isRefreshing) return;
            IsRefreshing = true;
            Task.Factory.StartNew(dispatcher =>
            {
                try
                {
                    profileContent = new List<ProfileItem>();
                    Clear();
                    string input;
                    try
                    {
                        input = BinaryFile.ReadAllText(FilePath, false);
                        isPlistFormat = false;
                    }
                    catch
                    {
                        input = Encoding.UTF8.GetString
                            ((byte[]) new BinaryPlistReader().ReadObject(FilePath)["pers2.dat"]);
                        isPlistFormat = true;
                    }
                    var position = 0;
                    while (position < input.Length)
                    {
                        var length = ReadInt32(input, ref position);
                        if (length == 0) break;
                        position++; // read ,
                        var key = input.Substring(position, length);
                        position += length;
                        length = ReadInt32(input, ref position);
                        if (length == 0) break;
                        position++; // read ,
                        var value = input.Substring(position, length);
                        position += length;
                        if (key.StartsWith("profile_"))
                            Add(new ProfilePlayer(this, key, value, dispatcher as Dispatcher));
                        else profileContent.Add(new ProfileItem(key, value));
                    }
                }
                catch (Exception exc)
                {
                    if (RefreshError != null) RefreshError(this, new UnhandledExceptionEventArgs(exc, false));
                }
                finally
                {
                    IsRefreshing = false;
                    IsSaved = true;
                    initialized = true;
                }
            }, Dispatcher.CurrentDispatcher);
        }
        private static int ReadInt32(string input, ref int position)
        {
            var i = position;
            while (char.IsDigit(input[position])) position++;
            var result = input.Substring(i, position - i);
            return string.IsNullOrEmpty(result) ? 0 : int.Parse(result);
        }

        private void OnPlayerPropertyChanged(object sender, PropertyChangedEventArgs e)
        {
            IsSaved = false;
        }

        private bool isSaved = true;
        public bool IsSaved
        {
            get
            {
                return isRefreshing || isSaved;
            }
            set
            {
                if (IsRefreshing) return;
                isSaved = value;
                OnPropertyChanged("IsSaved");
            }
        }

        private bool isRefreshing, initialized;
        public bool IsRefreshing
        {
            get { return !initialized || isRefreshing; }
            private set { isRefreshing = value; OnPropertyChanged("IsRefreshing"); }
        }

        public event EventHandler Refreshing, Refreshed;
        public event UnhandledExceptionEventHandler RefreshError;

        protected override int GetKeyForItem(ProfilePlayer item)
        {
            return item.PlayerNumber;
        }

        protected override void OnPropertyChanged(string propertyName)
        {
            if (propertyName == "IsRefreshing")
                if (IsRefreshing)
                {
                    if (Refreshing != null) Refreshing(this, new EventArgs());
                    if (!isSaved) OnPropertyChanged("IsSaved");
                }
                else
                {
                    if (Refreshed != null) Refreshed(this, new EventArgs());
                }
            else if (propertyName != "IsSaved" && propertyName != "Alias") IsSaved = false;
            base.OnPropertyChanged(propertyName);
        }
    }

    public class ProfileItem
    {
        protected ProfileItem() { }
        public ProfileItem(string key, string value)
        {
            Key = key; 
            // ReSharper disable DoNotCallOverridableMethodsInConstructor
            Value = value;
            // ReSharper restore DoNotCallOverridableMethodsInConstructor
        }

        public string Key;
        public virtual string Value { get; set; }

        public override string ToString()
        {
            string k = Key, v = Value;
            return Encoding.UTF8.GetBytes(k).LongLength + "," + k + Encoding.UTF8.GetBytes(v).LongLength + "," + v;
        }
    }

    public sealed class ProfilePlayer : ProfileItem, INotifyPropertyChanged
    {
        public ProfilePlayer(Profile parent, string key, string value = "New Player,0,0,0,0,_,_,0", Dispatcher d = null)
        {
            Parent = parent;
            if (d != null) dispatcher = d;
            Key = key;
            Value = value;  // Set a new player if ignores
            parent.PropertyChanged += (sender, e) =>
            {
                if (e.PropertyName == "MostRecentPlayerProfile") OnPropertyChanged("IsMostRecentPlayer");
            };
        }
        public ProfilePlayer(Profile parent, int num, string value = "New Player,0,0,0,0,_,_,0")
            : this(parent, "profile_" + (num - 1), value)
        {
        }
        public override string Value
        {
            get
            {
                List<PlayedLevel> played = new List<PlayedLevel>(), skipped = new List<PlayedLevel>();
                StringBuilder playeds = new StringBuilder(1024), skippeds = new StringBuilder(1024);
                foreach (var l in PlayedLevels)
                    if (l.Skipped)
                    {
                        skipped.Add(l);
                        skippeds.Append(l);
                    }
                    else
                    {
                        played.Add(l);
                        playeds.Append(l);
                    }
                return string.Format("{0},{1},{2},{3},{4}{5},{6}_{7},_{8},{9},_{10},_{11}",
                                     PlayerName, playerFlag, TotalPlaySeconds, played.Count, playeds, skipped.Count,
                                     skippeds, WoGCorpBalls.Aggregate(string.Empty, (current, data) => current + data) +
                                        WoGCorpStrands.Aggregate(string.Empty, (current, data) => current + data)
                                        .TrimEnd(':'),
                                     OnlinePlayerKey, NewlyCollectedGooBalls, GameCentrePlayerKey,
                                     GameCentrePlayerName);
            } 
            set
            {
                if (PlayedLevels != null) PlayedLevels.CollectionChanged -= OnCollectionChanged;
                PlayedLevels = dispatcher.Invoke(() => new AdvancedGameKeyedCollection<PlayedLevel>());
                PlayedLevels.CollectionChanged += OnCollectionChanged;
                if (WoGCorpBalls != null) WoGCorpBalls.CollectionChanged -= OnCollectionChanged;
                WoGCorpBalls = new ObservableCollection<WoGCorpBall>();
                WoGCorpBalls.CollectionChanged += OnCollectionChanged;
                if (WoGCorpStrands != null) WoGCorpStrands.CollectionChanged -= OnCollectionChanged;
                WoGCorpStrands = new ObservableCollection<WoGCorpStrand>();
                WoGCorpStrands.CollectionChanged += OnCollectionChanged;
                var content = value.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries);
                PlayerName = content[0];
                playerFlag = Convert.ToInt32(content[1]);
                TotalPlaySeconds = Convert.ToInt32(content[2]);
                int t = Convert.ToInt32(content[3]), i, j = 0;
                for (i = 4; i <= t * 4; i += 4) PlayedLevels.Add(new PlayedLevel(this, content[i],
                    int.Parse(content[i + 1]), int.Parse(content[i + 2]), int.Parse(content[i + 3])));
                var u = Convert.ToInt32(content[i]) + ++i;
                for (; i < u; i++) PlayedLevels.Add(new PlayedLevel(this, content[i]));
                var towerData = content[i].TrimStart('_').Split(new[] { ':' }, StringSplitOptions.RemoveEmptyEntries);
                while (j < towerData.Length) switch (towerData[j])
                    {
                        case "b":
                            WoGCorpBalls.Add(new WoGCorpBall(towerData[j + 1], towerData[j + 2], towerData[j + 3],
                                                             towerData[j + 4], towerData[j + 5]));
                            j += 6;
                            break;
                        case "s":
                            WoGCorpStrands.Add(new WoGCorpStrand(towerData[j + 1], towerData[j + 2], towerData[j + 3],
                                                                 towerData[j + 4], towerData[j + 5], towerData[j + 6]));
                            j += 7;
                            break;
                        default:
                            j++;
                            break;
                    }
                OnlinePlayerKey = content[i + 1].TrimStart('_');
                NewlyCollectedGooBalls = int.Parse(content[i + 2]);
                if (content.Length <= i + 3) GameCentrePlayerKey = GameCentrePlayerName = null;
                else
                {
                    if (!content[i + 3].StartsWith("_") || !content[i + 4].StartsWith("_")) throw new FormatException();
                    GameCentrePlayerKey = content[i + 3].Substring(1);
                    GameCentrePlayerName = content[i + 4].Substring(1);
                }
            }
        }

        public override string ToString()
        {
            string k = Key, v = Value;
            return Encoding.UTF8.GetBytes(k).LongLength + "," + k + Encoding.UTF8.GetBytes(v).LongLength + "," + v;
        }

        private readonly Dispatcher dispatcher = Dispatcher.CurrentDispatcher;

        private void OnCollectionChanged(object sender, NotifyCollectionChangedEventArgs e)
        {
            if (e.Action == NotifyCollectionChangedAction.Add || e.Action == NotifyCollectionChangedAction.Replace ||
                e.Action == NotifyCollectionChangedAction.Reset)
                foreach (INotifyPropertyChanged item in e.NewItems) item.PropertyChanged += OnInsidePropertyChanged;
            if (e.Action == NotifyCollectionChangedAction.Remove || e.Action == NotifyCollectionChangedAction.Replace ||
                e.Action == NotifyCollectionChangedAction.Reset)
                foreach (INotifyPropertyChanged item in e.OldItems) item.PropertyChanged -= OnInsidePropertyChanged;
            Parent.IsSaved = false;
        }

        private void OnInsidePropertyChanged(object sender, PropertyChangedEventArgs e)
        {
            Parent.IsSaved = false;
        }

        public Profile Parent { get; private set; }
        public bool IsMostRecentPlayer
        {
            get { return Parent.MostRecentPlayerProfile == PlayerNumber; }
        }

        public void SetAsMostRecentPlayer()
        {
            var pre = IsMostRecentPlayer;
            Parent.MostRecentPlayerProfile = PlayerNumber;
            if (pre != IsMostRecentPlayer) OnPropertyChanged("IsMostRecentPlayer");
        }

        public AdvancedGameKeyedCollection<PlayedLevel> PlayedLevels { get; private set; }
        public ObservableCollection<WoGCorpBall> WoGCorpBalls { get; private set; }
        public ObservableCollection<WoGCorpStrand> WoGCorpStrands { get; private set; }

        public int PlayerNumber { get { return Convert.ToInt32(Key.Substring(8)); } }
        private string playerName;
        public string PlayerName
        {
            get { return playerName; }
            set
            {
                playerName = value;
                OnPropertyChanged("PlayerName");
            }
        }
        private string onlinePlayerKey;
        public string OnlinePlayerKey
        {
            get { return onlinePlayerKey; }
            set
            {
                onlinePlayerKey = value;
                OnPropertyChanged("OnlinePlayerKey");
            }
        }

        private int playerFlag;
        private int totalPlaySeconds;
        public int TotalPlaySeconds
        {
            get { return totalPlaySeconds; }
            set
            {
                totalPlaySeconds = value;
                OnPropertyChanged("TotalPlaySeconds");
            }
        }
        private int newlyCollectedGooBalls;
        public int NewlyCollectedGooBalls
        {
            get { return newlyCollectedGooBalls; }
            set
            {
                OnPropertyChanged("NewlyCollectedGooBalls");
                newlyCollectedGooBalls = value;
            }
        }
        public bool OnlinePlayEnabled
        {
            get { return (playerFlag & 1) > 0; }
            set
            {
                if (value) playerFlag |= 1;
                else playerFlag &= 0x1E;
                OnPropertyChanged("OnlinePlayEnabled");
            }
        }
        public bool WorldOfGooCorporationUnlocked
        {
            get { return (playerFlag & 2) > 0; }
            set
            {
                if (value) playerFlag |= 2;
                else playerFlag &= 0x1D;
                OnPropertyChanged("WorldOfGooCorporationUnlocked");
            }
        }
        public bool WorldOfGooCorporationDestroyed
        {
            get { return (playerFlag & 4) > 0; }
            set
            {
                if (value) playerFlag |= 4;
                else playerFlag &= 0x1B;
                OnPropertyChanged("WorldOfGooCorporationDestroyed");
            }
        }
        public bool WhistleFound
        {
            get { return (playerFlag & 8) > 0; }
            set
            {
                if (value) playerFlag |= 8;
                else playerFlag &= 0x17;
                OnPropertyChanged("WhistleFound");
            }
        }
        public bool DeliveranceUnlocked
        {
            get { return (playerFlag & 16) > 0; }
            set
            {
                if (value) playerFlag |= 0x10;
                else playerFlag &= 0xF;
                OnPropertyChanged("DeliveranceUnlocked");
            }
        }

        private string gameCentrePlayerKey, gameCentrePlayerName;
        public string GameCentrePlayerKey
        {
            get { return gameCentrePlayerKey; }
            set
            {
                gameCentrePlayerKey = value;
                OnPropertyChanged("GameCentrePlayerKey");
            }
        }
        public string GameCentrePlayerName
        {
            get { return gameCentrePlayerName; }
            set
            {
                gameCentrePlayerName = value;
                OnPropertyChanged("GameCentrePlayerName");
            }
        }

        public event PropertyChangedEventHandler PropertyChanged;
        private void OnPropertyChanged(string propertyName)
        {
            if (PropertyChanged != null) PropertyChanged(this, new PropertyChangedEventArgs(propertyName));
        }
    }

    public sealed class PlayedLevel : INotifyPropertyChanged, IGameItem
    {
        public PlayedLevel(ProfilePlayer parent, string ln, int mg, int fm, int fs)
        {
            Parent = parent;
            levelID = ln;
            mostGoos = mg; 
            fewestMoves = fm;
            fewestSeconds = fs;
        }
        public PlayedLevel(ProfilePlayer parent, string ln) : this(parent, ln, 0, 9999, 9999)
        {
            Skipped = true;
        }

        private void OnPropertyChanged(string name)
        {
            Parent.Parent.IsSaved = false;
            if (PropertyChanged != null) PropertyChanged(this, new PropertyChangedEventArgs(name));
        }

        private readonly string levelID;
        private int mostGoos, fewestMoves, fewestSeconds;
        private bool skipped;

        public ProfilePlayer Parent { get; private set; }

        public string LevelID { get { return levelID; } }
        public int MostGoos
        {
            get { return Skipped ? -1 : mostGoos; }
            set
            {
                Skipped = (mostGoos = value) < 0;
                OnPropertyChanged("MostGoos");
            }
        }
        public int FewestMoves
        {
            get { return Skipped ? -1 : fewestMoves; }
            set
            {
                Skipped = (fewestMoves = value) < 0;
                OnPropertyChanged("FewestMoves");
            }
        }
        public int FewestSeconds
        {
            get { return Skipped ? -1 : fewestSeconds; }
            set
            {
                Skipped = (fewestSeconds = value) < 0;
                OnPropertyChanged("FewestSeconds");
            }
        }
        public bool Skipped
        {
            get { return skipped; } 
            set
            {
                if (skipped == value) return;
                skipped = value;
                OnPropertyChanged("Skipped");
                OnPropertyChanged("MostGoos");
                OnPropertyChanged("FewestMoves");
                OnPropertyChanged("FewestSeconds");
            }
        }
        string IGameItem.ID { get { return LevelID; } }

        public override string ToString()
        {
            if (Skipped) return LevelID + ',';
            return string.Format("{0},{1},{2},{3},", LevelID, MostGoos, FewestMoves, FewestSeconds);
        }

        public event PropertyChangedEventHandler PropertyChanged;
    }
    
    public abstract class WoGCorpData : INotifyPropertyChanged
    {
        protected string DataType, BallType;

        protected void OnPropertyChanged(string name)
        {
            if (PropertyChanged != null) PropertyChanged(this, new PropertyChangedEventArgs(name));
        }

        public override string ToString()
        {
            switch (DataType)
            {
                case "b": return (this as WoGCorpBall).ToString();
                case "s": return (this as WoGCorpStrand).ToString();
                default:  return base.ToString();
            }
        }

        public event PropertyChangedEventHandler PropertyChanged;

/*
        public string ShowText
        {
            get
            {
                switch (DataType)
                {
                    case "b":
                        var ball = this as WoGCorpBall;
                        return string.Format("P({0},{1})　V({2},{3})", ball.CoordinateX, ball.CoordinateY,
                                             ball.VelocityX, ball.VelocityY);
                    case "s":
                        var strand = this as WoGCorpStrand;
                        return string.Format("{0}-{1}　SC: {2}　NL: {3}　{4}", strand.StartPoint, strand.EndPoint,
                                             strand.SpringConstant, strand.NaturalLength,
                                             strand.IsBall ? "Connected" : "Built");
                    default:
                        return ToString();
                }
            }
        }
*/
    }
    public sealed class WoGCorpBall : WoGCorpData
    {
        public WoGCorpBall(string type = "Drained", double cx = 0, double cy = 0, double vx = 0, double vy = 0)
        {
            DataType = "b";
            BallType = type;
            CoordinateX = cx;
            CoordinateY = cy;
            VelocityX = vx;
            VelocityY = vy;
        }
        public WoGCorpBall(string type, string cx, string cy, string vx, string vy)
            : this(type, double.Parse(cx), double.Parse(cy), double.Parse(vx), double.Parse(vy))
        {
        }

        private double coordinateX, coordinateY, velocityX, velocityY;
        public double CoordinateX
        {
            get { return coordinateX; }
            set
            {
                coordinateX = value;
                OnPropertyChanged("CoordinateX");
            }
        }
        public double CoordinateY
        {
            get { return coordinateY; }
            set
            {
                coordinateY = value;
                OnPropertyChanged("CoordinateY");
            }
        }
        public double VelocityX { get { return velocityX; } set { velocityX = value; OnPropertyChanged("VelocityX"); } }
        public double VelocityY { get { return velocityY; } set { velocityY = value; OnPropertyChanged("VelocityY"); } }

        public override string ToString()
        {
            return string.Format("b:{0}:{1}:{2}:{3}:{4}:", BallType, CoordinateX, CoordinateY, VelocityX, VelocityY);
        }
    }
    public sealed class WoGCorpStrand : WoGCorpData
    {
        public WoGCorpStrand(string type = "Drained", int sp = 0, int ep = 1, double sc = 9, double nl = 110,
                             bool ib = false)
        {
            DataType = "s";
            BallType = type;
            StartPoint = sp;
            EndPoint = ep;
            SpringConstant = sc;
            NaturalLength = nl;
            IsBall = ib;
        }
        public WoGCorpStrand(string type, string sp, string ep, string sc, string nl, string ib)
            : this(type, int.Parse(sp), int.Parse(ep), double.Parse(sc), double.Parse(nl), int.Parse(ib) == 1)
        {
        }
        private int startPoint, endPoint;
        public int StartPoint
        {
            get { return startPoint; }
            set
            {
                startPoint = value;
                OnPropertyChanged("StartPoint");
            }
        }
        public int EndPoint
        {
            get { return endPoint; }
            set
            {
                endPoint = value; OnPropertyChanged("EndPoint");
            }
        }

        private double springConstant, naturalLength;
        public double SpringConstant
            { get { return springConstant; } set { springConstant = value; OnPropertyChanged("SpringConstant"); } }
        public double NaturalLength
            { get { return naturalLength; } set { naturalLength = value; OnPropertyChanged("NaturalLength"); } }

        private bool isBall;
        public bool IsBall { get { return isBall; } set { isBall = value; OnPropertyChanged("IsBall"); } }

        public override string ToString()
        {
            return string.Format("s:{0}:{1}:{2}:{3}:{4}:{5}:", BallType, StartPoint, EndPoint, SpringConstant,
                                 NaturalLength, IsBall ? 1 : 0);
        }
    }
}
