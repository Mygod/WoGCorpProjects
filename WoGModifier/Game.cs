using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Threading;
using System.Xml.Linq;
using Mygod.Collections.ObjectModel;
using Mygod.WorldOfGoo.IO;
using Mygod.Xml.Linq;

namespace Mygod.WorldOfGoo
{
    #region Interfaces & Common Classes

    public interface IGameDirectory
    {
        string DirectoryPath { get; }
        Game GameParent { get; }
    }
    public interface IGameFile
    {
        IGameDirectory Parent { get; }
        string FilePath { get; }
        void Save();
    }
    public interface IGameItem
    {
        string ID { get; }
    }
    public interface IGameBinFile : IGameFile
    {
    }
    public interface IGameBinXmlFile : IGameFile
    {
        string GetXmlString();
    }
    public interface IHasAlias : IGameFile
    {
        string Alias { get; set; }
    }
    public interface IHasTag
    {
        object Tag { get; set; }
    }

    [Serializable]
    public class GameKeyedCollection<TItem> : ObservableKeyedCollection<string, TItem> where TItem : IGameItem
    {
        protected override string GetKeyForItem(TItem item)
        {
            return item.ID;
        }
    }

    [Serializable]
    public class AdvancedGameKeyedCollection<TItem> : AdvancedObservableKeyedCollection<string, TItem>
        where TItem : IGameItem, INotifyPropertyChanged
    {
        protected override string GetKeyForItem(TItem item)
        {
            return item.ID;
        }
    }

    #endregion

    public sealed class Game : IGameDirectory, IHasAlias, IHasTag, INotifyPropertyChanged
    {
        public Game(string path, Dispatcher dispatcher = null)
        {
            if (!File.Exists(path)) throw new FileNotFoundException();
            Dispatcher = dispatcher ?? Dispatcher.CurrentDispatcher;
            FilePath = path;
            Resources = new ResourceManifests(this);
            SupportedLanguages = new HashSet<string>(new[] { Properties.Config.Language });
        }

        public IGameDirectory Parent { get { return this; } }
        public Dispatcher Dispatcher { get; private set; }

        public string FilePath { get; private set; }
        public string DirectoryPath { get { return Path.GetDirectoryName(FilePath); } }
        Game IGameDirectory.GameParent { get { return this; } }

        public HashSet<string> SupportedLanguages { get; private set; }

        private PropertiesDirectory properties;
        public PropertiesDirectory Properties
            { get { return properties ?? (properties = new PropertiesDirectory(this)); } }
        private ResourcesDirectory res;
        public ResourcesDirectory Res { get { return res ?? (res = new ResourcesDirectory(this)); } }

        public ResourceManifests Resources { get; private set; }

        public string Alias
        {
            get { return Settings.GetAlias(this); }
            set
            {
                Settings.SetAlias(this, value);
                OnPropertyChanged("Alias");
            }
        }

        public Process Execute(bool outputConsole = false, Level levelToExecute = null)
        {
            var fileName = Path.GetFileNameWithoutExtension(FilePath) ?? string.Empty;
            if (Process.GetProcessesByName(fileName).LongLength > 0) return null;
            return Process.Start(new ProcessStartInfo("cmd", "/c \"" + FilePath + "\" " +
                (levelToExecute == null ? string.Empty : levelToExecute.ID) +
                (outputConsole ? '>' + R.ConsoleOutput : string.Empty))
                    { WorkingDirectory = DirectoryPath, CreateNoWindow = true, UseShellExecute = false });
        }
        public void Refresh()
        {
            properties = null;
            res = null;
            Resources = new ResourceManifests(this);
        }

        public override string ToString()
        {
            return "World of Goo: " + FilePath;
        }
        void IGameFile.Save()
        {
            throw Exceptions.NotSupported;
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged(string propertyName)
        {
            var handler = PropertyChanged;
            if (handler != null) handler(this, new PropertyChangedEventArgs(propertyName));
        }

        private object tag;
        public object Tag { get { return tag; } set { tag = value; OnPropertyChanged("Tag"); } }
    }

    #region Resource Manifest

    public sealed class ResourceManifests : GameKeyedCollection<ResourceBase>
    {
        public ResourceManifests(IGameDirectory parent)
        {
            CurrentDispatcher = parent.GameParent.Dispatcher;
        }
    }

    public sealed class ResourceManifest : GameKeyedCollection<Resources>, IGameBinXmlFile
    {
        public ResourceManifest(IGameDirectory parent, string fileName = "resources.xml.bin")
        {
            Parent = parent;
            CurrentDispatcher = parent.GameParent.Dispatcher;
            FilePath = Path.Combine(parent.DirectoryPath, fileName);
            var doc = XDocument.Parse(BinaryFile.ReadAllText(FilePath));
            var root = doc.Element("ResourceManifest");
            if (root == null) throw Exceptions.XmlElementDoesNotExist(FilePath, "ResourceManifest");
            foreach (var e in root.Elements().Where(e => e.Name == "Resources").Select(e => new Resources(this, e))) 
                if (Contains(e.ID))
                {
                    var r = this[e.ID];
                    foreach (var i in e.Where(i => !r.Contains(i.ID))) r.Add(i);
                }
                else Add(e);
        }

        public IGameDirectory Parent { get; private set; }
        public string FilePath { get; private set; }

        public string GetXmlString()
        {
            var doc = new XDocument(new XComment(" This file has been edited by World of Goo Modifier by Mygod "));
            var e = new XElement("materials");
            doc.Add(e);
            e.Add(this.Select(i => (object)i.GetElement()).ToArray());
            return doc.ToString();
        }
        public void Save()
        {
            BinaryFile.WriteAllText(FilePath, GetXmlString());
        }
    }

    public sealed class Resources : GameKeyedCollection<ResourceBase>, IGameItem
    {
        public Resources(ResourceManifest parent, XElement e)
        {
            Parent = parent;
            CurrentDispatcher = parent.Parent.GameParent.Dispatcher;
            ID = e.GetAttributeValue("id");
            if (ID == null) throw new FileFormatException(new Uri(Parent.FilePath),
                                                          string.Format(Resrc.ExceptionXmlAttributeDoesNotExist, "id"));
            string idPrefix = string.Empty, pathPrefix = string.Empty;
            foreach (var i in e.Elements())
            {
                ResourceBase r;
                switch (i.Name.LocalName.ToLower())
                {
                    case "setdefaults":
                        idPrefix = i.GetAttributeValue("idprefix") ?? string.Empty;
                        pathPrefix = i.GetAttributeValue("path") ?? string.Empty;
                        continue;
                    case "font":
                        r = new FontResource(this, i, idPrefix, pathPrefix);
                        if (!Contains(r.ID)) Add(r);
                        continue;
                    case "image":
                        r = new ImageResource(this, i, idPrefix, pathPrefix);
                        if (!Contains(r.ID)) Add(r);
                        continue;
                    case "sound":
                        r = new SoundResource(this, i, idPrefix, pathPrefix);
                        if (!Contains(r.ID)) Add(r);
                        continue;
                    default:
                        throw new FileFormatException(new Uri(Parent.FilePath),
                                                      string.Format(Resrc.ExceptionXmlElementCannotRecognize,
                                                      i.Name.LocalName));
                }
            }
        }

        public ResourceManifest Parent { get; private set; }

        public string ID { get; private set; }

        public XElement GetElement()
        {
            var result = new XElement("Resources", new XAttribute("id", ID));
            result.Add(this.Select(res => (object) res.GetElement()).ToArray());
            return result;
        }
    }

    public abstract class ResourceBase : IGameItem
    {
        protected ResourceBase(Resources parent, XElement e, string idPrefix, string pathPrefix)
        {
            pathPrefix = pathPrefix.TrimStart('.');
            if (!pathPrefix.EndsWith("/", StringComparison.Ordinal)) pathPrefix += '/';
            Parent = parent;
            LocalizationPaths = new Dictionary<string, string>();
            foreach (var a in e.Attributes())
            {
                var name = a.Name.LocalName.ToLower();
                switch (name)
                {
                    case "id":
                        ID = idPrefix + a.Value;
                        break;
                    case "path":
                        DefaultPath = pathPrefix + a.Value;
                        break;
                    default:
                        if (!LocalizationPaths.ContainsKey(name))
                        {
                            parent.Parent.Parent.GameParent.SupportedLanguages.Add(name);
                            LocalizationPaths.Add(name, a.Value);
                        }
                        break;
                }
            }
            if (ID == null) throw new FileFormatException(new Uri(Parent.Parent.FilePath),
                                                          string.Format(Resrc.ExceptionXmlAttributeDoesNotExist, "id"));
            var m = Parent.Parent.Parent.GameParent.Resources;
            if (!m.Contains(ID)) m.Add(this);
        }

        protected abstract string Extension { get; }
        protected abstract string ElementName { get; }
        public string LocalizedPath
        {
            get
            {
                var gd = Parent.Parent.Parent.GameParent.DirectoryPath;
                var language = Parent.Parent.Parent.GameParent.Properties.Config.Language;
                string p;
                if (LocalizationPaths.ContainsKey(language))
                {
                    p = Path.Combine(gd, LocalizationPaths[language]);
                    if (File.Exists(p + '.' + language + Extension)) return p + '.' + language + Extension;
                    if (File.Exists(p + Extension)) return p + Extension;
                }
                p = Path.Combine(gd, DefaultPath);
                if (File.Exists(p + '.' + language + Extension)) return p + '.' + language + Extension;
                return p + Extension;
            }
        }

        public string DefaultPath { get; set; }
        public Dictionary<string, string> LocalizationPaths { get; private set; }

        protected Resources Parent { get; private set; }
        public string ID { get; private set; }

        public XElement GetElement()
        {
            var result = new XElement(ElementName, new XAttribute("id", ID), new XAttribute("path", DefaultPath));
            foreach (var pair in LocalizationPaths) result.Add(new XAttribute(pair.Key, pair.Value));
            return result;
        }

        public override string ToString()
        {
            return ID;
        }
    }
    public sealed class FontResource : ResourceBase
    {
        public FontResource(Resources parent, XElement e, string idPrefix, string pathPrefix)
            : base(parent, e, idPrefix, pathPrefix)
        {
        }

        protected override string Extension { get { throw Exceptions.NotSupported; } }  // multi-file type font
        protected override string ElementName { get { return "font"; } }
    }
    public sealed class ImageResource : ResourceBase
    {
        public ImageResource(Resources parent, XElement e, string idPrefix, string pathPrefix)
            : base(parent, e, idPrefix, pathPrefix)
        {
        }

        protected override string Extension { get { return ".png"; } }
        protected override string ElementName { get { return "Image"; } }
    }
    public sealed class SoundResource : ResourceBase
    {
        public SoundResource(Resources parent, XElement e, string idPrefix, string pathPrefix)
            : base(parent, e, idPrefix, pathPrefix)
        {
        }

        protected override string Extension { get { return ".ogg"; } }
        protected override string ElementName { get { return "Sound"; } }
    }

    #endregion

    #region PropertiesDirectory

    public sealed class PropertiesDirectory : IGameDirectory
    {
        public PropertiesDirectory(IGameDirectory parent)
        {
            GameParent = parent.GameParent;
            DirectoryPath = Path.Combine(parent.DirectoryPath, "properties");
        }

        public string DirectoryPath { get; private set; }
        public Game GameParent { get; private set; }

        private Config config;
        public Config Config { get {  return config ?? (config = new Config(this)); } }
        private Materials materials;
        public Materials Materials { get { return materials ?? (materials = new Materials(this)); } }
        private ResourceManifest resources;
        public ResourceManifest Resources { get { return resources ?? (resources = new ResourceManifest(this)); } }
        private Text text;
        public Text Text { get { return text ?? (text = new Text(this)); } }
    }

    public sealed class ConfigParam : IGameItem
    {
        public ConfigParam(IGameFile parent, XElement e)
        {
            Name = e.GetAttributeValue("name");
            Value = e.GetAttributeValue("value");
            if (string.IsNullOrEmpty(Name)) throw new FileFormatException(new Uri(parent.FilePath),
                                                string.Format(Resrc.ExceptionXmlAttributeDoesNotExist, "name"));
        }

        public string Name { get; private set; }
        public string Value { get; set; }

        string IGameItem.ID { get { return Name; } }
    }
    public sealed class Config : GameKeyedCollection<ConfigParam>, IGameFile
    {
        public Config(IGameDirectory parent)
        {
            Parent = parent;
            CurrentDispatcher = parent.GameParent.Dispatcher;
            FilePath = Path.Combine(parent.DirectoryPath, "config.txt");
            var xml = XDocument.Parse(File.ReadAllText(FilePath)).Element("config");
            if (xml == null) throw new FileFormatException(new Uri(FilePath),
                                string.Format(Resrc.ExceptionXmlElementDoesNotExist, "config"));
            foreach (var i in from e in xml.Nodes().OfType<XElement>() where e.Name == "param"
                              let i = new ConfigParam(this, e) where !Contains(i.Name) select i) Add(i);
        }

        public IGameDirectory Parent { get; private set; }
        public string FilePath { get; private set; }

        public event EventHandler LanguageChanged;

        public string Language
        {
            get { return this["language"].Value; }
            set { this["language"].Value = value; if (LanguageChanged != null) LanguageChanged(this, new EventArgs()); }
        }
        public int ScreenWidth
        {
            get { return int.Parse(this["screen_width"].Value, CultureInfo.InvariantCulture); }
            set { this["screen_width"].Value = value.ToString(CultureInfo.InvariantCulture); }
        }
        public int ScreenHeight
        {
            get { return int.Parse(this["screen_height"].Value, CultureInfo.InvariantCulture); } 
            set { this["screen_height"].Value = value.ToString(CultureInfo.InvariantCulture); }
        }
        public int UIInset
        {
            get { return int.Parse(this["ui_inset"].Value, CultureInfo.InvariantCulture); }
            set { this["ui_inset"].Value = value.ToString(CultureInfo.InvariantCulture); }
        }

        public void Save()
        {
            var writer = new StreamWriter(FilePath, false, Encoding.UTF8);
            writer.Write(Resrc.PropertiesConfigFile, Language, ScreenWidth.ToString(CultureInfo.InvariantCulture), 
                         ScreenHeight.ToString(CultureInfo.InvariantCulture),
                         UIInset.ToString(CultureInfo.InvariantCulture));
            writer.Close();
        }
    }

    public sealed class Material : IGameItem, INotifyPropertyChanged
    {
        public Material(IGameFile parent, string id, double friction = 0, double bounce = 0, double minbouncevel = 0,
                        double stickiness = 0)
        {
            ID = id;
            if (string.IsNullOrEmpty(ID)) throw new FileFormatException(new Uri(parent.FilePath),
                                            string.Format(Resrc.ExceptionXmlAttributeDoesNotExist, "id"));
            this.friction = friction;
            this.bounce = bounce;
            minimumBounceVelocity = minbouncevel;
            this.stickiness = stickiness;
        }
        public Material(IGameFile parent, XElement e)
            : this(parent, e.GetAttributeValue("id"), e.GetAttributeValueWithDefault("friction", 0.0),
                   e.GetAttributeValueWithDefault("bounce", 0.0), e.GetAttributeValueWithDefault("minbouncevel", 0.0),
                   e.GetAttributeValueWithDefault("stickiness", 0.0))
        {
        }
        public Material(Material copy, string id)
        {
            ID = id;
            Friction = copy.Friction;
            Bounce = copy.Bounce;
            MinimumBounceVelocity = copy.MinimumBounceVelocity;
            Stickiness = copy.Stickiness;
        }

        private double friction, bounce, minimumBounceVelocity, stickiness;

        public string ID { get; private set; }
        public double Friction { get { return friction; } set { friction = value; OnPropertyChanged("Friction"); } }
        public double Bounce { get { return bounce; } set { bounce = value; OnPropertyChanged("Bounce"); } }
        public double MinimumBounceVelocity
        {
            get { return minimumBounceVelocity; } 
            set { minimumBounceVelocity = value; OnPropertyChanged("MinimumBounceVelocity"); }
        }
        public double Stickiness
            { get { return stickiness; } set { stickiness = value; OnPropertyChanged("Stickiness"); } }

        public event PropertyChangedEventHandler PropertyChanged;
        private void OnPropertyChanged(string propertyName)
        {
            if (PropertyChanged != null) PropertyChanged(this, new PropertyChangedEventArgs(propertyName));
        }

        public XElement GetElement()
        {
            return new XElement("material", new XAttribute("id", ID), new XAttribute("friction", Friction),
                                new XAttribute("bounce", Bounce), new XAttribute("minbouncevel", MinimumBounceVelocity),
                                new XAttribute("stickiness", Stickiness));
        }
    }
    public sealed class Materials : GameKeyedCollection<Material>, IGameBinXmlFile
    {
        public Materials(IGameDirectory parent)
        {
            Parent = parent;
            CurrentDispatcher = parent.GameParent.Dispatcher;
            FilePath = Path.Combine(parent.DirectoryPath, "materials.xml.bin");
            var xml = XDocument.Parse(BinaryFile.ReadAllText(FilePath)).Element("materials");
            if (xml == null) throw new FileFormatException(new Uri(FilePath), 
                string.Format(Resrc.ExceptionXmlElementDoesNotExist, "materials"));
            foreach (var i in from e in xml.Nodes().OfType<XElement>() where e.Name == "material"
                              let i = new Material(this, e) where !Contains(i.ID) select i) Add(i);
        }

        public IGameDirectory Parent { get; private set; }
        public string FilePath { get; private set; }

        public string GetXmlString()
        {
            var doc = new XDocument();
            doc.Add(new XComment(" This file has been edited by World of Goo Modifier by Mygod "));
            var e = new XElement("materials");
            doc.Add(e);
            e.Add(this.Select(i => (object)i.GetElement()).ToArray());
            return doc.ToString();
        }
        public void Save()
        {
            BinaryFile.WriteAllText(FilePath, GetXmlString());
        }
    }

    public sealed class SpecificLanguageString : IGameItem
    {
        public SpecificLanguageString(Game parent, string language, string value)
        {
            if (parent != null) parent.SupportedLanguages.Add(language);
            Language = language;
            Value = value.Replace("|", Environment.NewLine);
        }

        public string Language { get; private set; }
        public string Value { get; set; }
        string IGameItem.ID { get { return Language; } }

        public override string ToString()
        {
            return Value;
        }
    }
    public class TextItem : GameKeyedCollection<SpecificLanguageString>, IGameItem
    {
        public TextItem(Text parent, string id, params SpecificLanguageString[] texts)
        {
            Parent = parent;
            CurrentDispatcher = parent.Parent.GameParent.Dispatcher;
            ID = id;
            if (texts != null) foreach (var text in texts)
                Add(new SpecificLanguageString(parent.Parent.GameParent, text.Language, text.Value));
        }
        public TextItem(Text parent, XElement e)
        {
            Parent = parent;
            CurrentDispatcher = parent.Parent.GameParent.Dispatcher;
            foreach (var a in e.Attributes())
            {
                var name = a.Name.LocalName.ToLower();
                if (name == "id") ID = a.Value;
                else if (!Contains(name)) Add(new SpecificLanguageString(Parent.Parent.GameParent, name, a.Value));
            }
            if (ID == null) throw new FileFormatException(new Uri(parent.FilePath),
                                string.Format(Resrc.ExceptionXmlAttributeDoesNotExist, "id"));
        }

        public string ID { get; private set; }
        public string DefaultValue
        {
            get { return Contains("text") ? this["text"].Value : null; }
            set
            {
                if (Contains("text")) this["text"].Value = value; 
                else Add(new SpecificLanguageString(Parent.Parent.GameParent, "text", value));
            }
        }

        public Text Parent { get; private set; }

        public string LocalizedText
        {
            get
            {
                var language = Parent.Parent.GameParent.Properties.Config.Language.ToLower();
                return Contains(language) ? this[language].Value : DefaultValue;
            }
        }

        public XElement GetElement()
        {
            var result = new XElement("string", new XAttribute("id", ID));
            foreach (var text in this)
                result.Add(new XAttribute(text.Language, text.Value.Replace(Environment.NewLine, "|")));
            return result;
        }

        public override string ToString()
        {
            return ID;
        }
    }
    public sealed class Text : GameKeyedCollection<TextItem>, IGameBinXmlFile
    {
        public Text(IGameDirectory parent)
        {
            Parent = parent;
            CurrentDispatcher = parent.GameParent.Dispatcher;
            FilePath = Path.Combine(parent.DirectoryPath, "text.xml.bin");
            var xe = XDocument.Parse(BinaryFile.ReadAllText(FilePath)).GetElement("strings", FilePath);
            foreach (var i in from e in xe.Nodes().OfType<XElement>() where e.Name == "string"
                              select new TextItem(this, e))
            {
                if (!Contains(i.ID)) Add(i);
                else
                {
                    var item = this[i.ID];
                    foreach (var j in i.Where(j => !item.Contains(j.Language))) 
                        item.Add(new SpecificLanguageString(Parent.GameParent, j.Language, j.Value));
                }
            }
        }

        public IGameDirectory Parent { get; private set; }
        public string FilePath { get; private set; }

        public string GetXmlString()
        {
            if (FilePath == null) throw Exceptions.NotSupported;
            var doc = new XDocument();
            doc.Add(new XComment(" This file has been edited by World of Goo Modifier by Mygod "));
            var e = new XElement("strings");
            doc.Add(e);
            e.Add(this.Select(i => (object)i.GetElement()).ToArray());
            return doc.ToString();
        }
        public void Save()
        {
            BinaryFile.WriteAllText(FilePath, GetXmlString());
        }
    }

    #endregion

    #region ResourcesDirectory

    public sealed class ResourcesDirectory : IGameDirectory
    {
        public ResourcesDirectory(IGameDirectory parent)
        {
            GameParent = parent.GameParent;
            DirectoryPath = Path.Combine(parent.DirectoryPath, "res");
        }

        public Game GameParent { get; private set; }
        public string DirectoryPath { get; private set; }

        private Levels levels;
        public Levels Levels { get { return levels ?? (levels = new Levels(this)); } }
        private GooBalls balls;
        public GooBalls Balls { get { return balls ?? (balls = new GooBalls(this)); } }
        private Islands islands;
        public Islands Islands { get { return islands ?? (islands = new Islands(this)); } }
    }

    public sealed class Level : IGameDirectory, IGameItem
    {
        public Level(IGameDirectory parent, string id)
        {
            GameParent = parent.GameParent;
            ID = id;
            DirectoryPath = Path.Combine(parent.DirectoryPath, id);
        }

        private string GetFileName(string file)
        {
            return ID + '.' + file + ".bin";
        }
        internal string GetPath(string file)
        {
            return Path.Combine(DirectoryPath, GetFileName(file));
        }
        public string Read(string file)
        {
            return BinaryFile.ReadAllText(GetPath(file));
        }
        public void Write(string file, string value)
        {
            BinaryFile.WriteAllText(GetPath(file), value);
        }
        public void Edit(string file, string editorPath)
        {
            BinaryFile.Edit(Path.Combine(DirectoryPath, ID + '.' + file + ".bin"), editorPath);
        }
        public string LevelXml { get { return Read(R.Level); } set { Write(R.Level, value); } }
        public string SceneXml { get { return Read(R.Scene); } set { Write(R.Scene, value); } }
        public string ResrcXml { get { return Read(R.Resrc); } set { Write(R.Resrc, value); } }
        public bool IsValid
        {
            get
            {
                return File.Exists(GetPath(R.Level)) && File.Exists(GetPath(R.Scene)) && File.Exists(GetPath(R.Resrc));
            }
        }

        private ResourceManifest resources;
        public ResourceManifest Resources
            { get { return resources ?? (resources = new ResourceManifest(this, GetFileName(R.Resrc))); } }

        private TextItem localizedNameItem;
        private TextItem LocalizedNameItem
        {
            get
            {
                if (localizedNameItem != null) return localizedNameItem;
                string findID;
                switch (ID)
                {
                    case "IslandUi":
                        return localizedNameItem = new TextItem(GameParent.Properties.Text,
                            new XElement("string", new XAttribute("id", "IslandUi"),
                            new XAttribute("text", "Islands UI"), new XAttribute("cn", "章节按钮")));
                    case "MapWorldView":
                        return localizedNameItem = new TextItem(GameParent.Properties.Text,
                            new XElement("string", new XAttribute("id", "MapWorldView"),
                            new XAttribute("text", "Map World View"), new XAttribute("cn", "World of Goo 主地图")));
                    case "MoonUnlocker":
                        return localizedNameItem = new TextItem(GameParent.Properties.Text,
                            new XElement("string", new XAttribute("id", "MoonUnlocker"),
                            new XAttribute("text", "Moon Unlocker"),
                            new XAttribute("cn", "月球解锁器（汉化版第一章隐藏关卡）")));
                    case "wogc":
                        findID = "WOG_CORP_NAME";
                        break;
                    case "wogc3d":
                        findID = "WOG_CORP_3D_NAME";
                        break;
                    case "wogcd":
                        findID = "WOG_CORP_D_NAME";
                        break;
                    default:
                        var il = GameParent.Res.Islands.FindLevel(ID);
                        if (il != null && GameParent.Properties.Text.Contains(il.Name)) findID = il.Name;
                        else
                        {
                            var island = GameParent.Res.Islands.FirstOrDefault(i => i.Map == ID);
                            findID = island == null ? "LEVEL_NAME_" + ID.ToUpper()
                                                    : "CHAPTER" + island.Number + "_NAME";
                        }
                        break;
                }
                if (GameParent.Properties.Text.Contains(findID))
                    return localizedNameItem = GameParent.Properties.Text[findID];
                findID = "LEVEL_NAME_" + ID.ToUpper();
                return localizedNameItem = GameParent.Properties.Text.Contains(findID)
                            ? GameParent.Properties.Text[findID] : null;
            }
        }
        public string LocalizedName
        {
            get
            {
                return LocalizedNameItem == null ? ID : LocalizedNameItem.LocalizedText
                    .Replace(Environment.NewLine, GameParent.Properties.Config.Language == "cn" ? string.Empty : " ");
            }
        }

        public string ID { get; private set; }
        public string DirectoryPath { get; private set; }
        public Game GameParent { get; private set; }

        public void Remove()
        {
            GameParent.Res.Levels.Remove(this);
            Directory.Delete(DirectoryPath, true);
        }

        public override string ToString()
        {
            return ID;
        }
    }
    public sealed class Levels : GameKeyedCollection<Level>, IGameDirectory
    {
        public Levels(IGameDirectory parent)
        {
            GameParent = parent.GameParent;
            CurrentDispatcher = parent.GameParent.Dispatcher;
            DirectoryPath = Path.Combine(parent.DirectoryPath, "levels");
            foreach (var level in new DirectoryInfo(DirectoryPath).EnumerateDirectories()
                .Select(dir => new Level(this, dir.Name)).Where(level => level.IsValid)) Add(level);
        }

        public Game GameParent { get; private set; }
        public string DirectoryPath { get; private set; }

        public static readonly SortedSet<string> OriginalLevelsID = new SortedSet<string>
        {
            "AB3", "BeautyAndTheTentacle", "BeautySchool", "BlusteryDay", "BulletinBoardSystem", "BurningMan", "Chain",
            "Deliverance", "Drool", "EconomicDivide", "FistyReachesOut", "FlyAwayLittleOnes", "FlyingMachine",
            "GeneticSortingMachine", "GoingUp", "GracefulFailure", "GrapeVineVirus", "GraphicProcessingUnit", "HangLow",
            "HelloWorld", "HTInnovationCommittee", "ImmigrationNaturalizationUnit", "ImpaleSticky",
            "IncinerationDestination", "InfestyTheWorm", "IvyTower", "LeapHole", "MistysLongBonyRoad", "MOM",
            "ObservatoryObservationStation", "OdeToBridgeBuilder", "ProductLauncher", "RedCarpet",
            "RegurgitationPumpingStation", "RoadBlocks", "SecondHandSmoke", "SuperFuseChallengeTime", "TheServer",
            "ThirdWheel", "ThrusterTest", "TowerOfGoo", "Tumbler", "UpperShaft", "VolcanicPercolatorDaySpa",
            "WaterLock", "WeatherVane", "Whistler", "wogc", "wogc3d", "wogcd", "YouHaveToExplodeTheHead"
        };
    }

    public sealed class GooBall : IGameDirectory, IGameItem
    {
        public GooBall(IGameDirectory parent, string id)
        {
            GameParent = parent.GameParent;
            ID = id;
            DirectoryPath = Path.Combine(parent.DirectoryPath, id);
            thumbnailUri = new Lazy<string>(() =>
            {
                var root = XDocument.Parse(BallsXml).Element("ball");
                if (root == null) return null;
                var body = root.Elements("part").FirstOrDefault(i => i.GetAttributeValue("name") == "body");
                if (body == null) return null;
                var resName = "ball_" + ID;
                if (!Resources.Contains(resName)) return null;
                var res = Resources[resName];
                var image = body.GetAttributeValue("image").Split(',').FirstOrDefault(res.Contains);
                if (image == null) return null;
                var r = res[image] as ImageResource;
                if (r == null) return null;
                var path = Path.Combine(GameParent.DirectoryPath, r.LocalizedPath.TrimStart('/'));
                if (File.Exists(path)) return path;
                return null;
            });
        }

        public string DirectoryPath { get; private set; }
        public Game GameParent { get; private set; }
        public string ID { get; private set; }
        private readonly Lazy<string> thumbnailUri;
        public string ThumbnailUri { get { return thumbnailUri.Value; } }
        
        private string GetPath(string file)
        {
            return Path.Combine(DirectoryPath, file + ".xml.bin");
        }
        public string Read(string file)
        {
            return BinaryFile.ReadAllText(GetPath(file));
        }
        public void Write(string file, string value)
        {
            BinaryFile.WriteAllText(GetPath(file), value);
        }
        public void Edit(string file, string editorPath)
        {
            BinaryFile.Edit(GetPath(file), editorPath);
        }
        public string BallsXml { get { return Read(R.Balls); } set { Write(R.Balls, value); } }
        public string ResourcesXml { get { return Read(R.Resources); } set { Write(R.Resources, value); } }
        public bool IsValid { get { return File.Exists(GetPath(R.Balls)) && File.Exists(GetPath(R.Resources)); } }

        private ResourceManifest resources;
        public ResourceManifest Resources { get { return resources ?? (resources = new ResourceManifest(this)); } }

        public void Remove()
        {
            GameParent.Res.Balls.Remove(this);
            Directory.Delete(DirectoryPath, true);
        }

        public override string ToString()
        {
            return ID;
        }
    }
    public sealed class GooBalls : GameKeyedCollection<GooBall>, IGameDirectory
    {
        public GooBalls(IGameDirectory parent)
        {
            GameParent = parent.GameParent;
            CurrentDispatcher = parent.GameParent.Dispatcher;
            DirectoryPath = Path.Combine(parent.DirectoryPath, R.Balls);
            foreach (var ball in new DirectoryInfo(DirectoryPath).EnumerateDirectories()
                .Select(dir => new GooBall(this, dir.Name)).Where(ball => ball.IsValid)) Add(ball);
        }

        public Game GameParent { get; private set; }
        public string DirectoryPath { get; private set; }
    }

    public sealed class Islands : ObservableKeyedCollection<int, Island>, IGameDirectory
    {
        public Islands(IGameDirectory parent)
        {
            CurrentDispatcher = parent.GameParent.Dispatcher;
            DirectoryPath = Path.Combine(parent.DirectoryPath, "islands");
            GameParent = parent.GameParent;
            for (var i = 1; i <= 5; i++) Add(new Island(this, i));
        }

        public string DirectoryPath { get; private set; }
        public Game GameParent { get; private set; }

        public IslandLevel FindLevel(string id)
        {
            var p = this.FirstOrDefault(island => island.Contains(id));
            return p == null ? null : p[id];
        }

        public void SwapIslands(int a, int b)
        {
            if (a == b) return;
            Island x = this[a], y = this[b];
            Remove(x);
            Remove(y);
            x.Number = b;
            y.Number = a;
            var t = x.FilePath;
            x.FilePath = y.FilePath;
            y.FilePath = t;
            if (x.Number < y.Number)
            {
                Insert(x.Number - 1, x);
                Insert(y.Number - 1, y);
            }
            else
            {
                Insert(y.Number - 1, y);
                Insert(x.Number - 1, x);
            }
        }

        protected override int GetKeyForItem(Island item)
        {
            return item.Number;
        }
    }
    public sealed class Island : GameKeyedCollection<IslandLevel>, IGameBinXmlFile
    {
        public Island(IGameDirectory parent, int number, string xml = null)
        {
            Parent = parent;
            CurrentDispatcher = parent.GameParent.Dispatcher;
            this.number = number;
            FilePath = Path.Combine(parent.DirectoryPath, string.Format("island{0}.xml.bin", number));
            var root = XDocument.Parse(xml ?? BinaryFile.ReadAllText(FilePath)).Element("island");
            if (root == null) throw new FileFormatException(new Uri(FilePath), 
                string.Format(Resrc.ExceptionXmlElementDoesNotExist, "island"));
            name = root.GetAttributeValue("name");
            map = root.GetAttributeValue("map");
            icon = root.GetAttributeValue("icon");
            foreach (var level in root.Elements("level").Select(e => new IslandLevel(this, e))) Add(level);
        }

        public IGameDirectory Parent { get; private set; }
        public string FilePath { get; set; }

        private int number;
        public int Number { get { return number; } internal set { number = value; OnPropertyChanged("Number"); } }

        private string name, map, icon;
        public string Name { get { return name; } set { name = value; OnPropertyChanged("Name"); } }
        public string Map { get { return map; } set { map = value; OnPropertyChanged("Map"); } }
        public string Icon { get { return icon; } set { icon = value; OnPropertyChanged("Icon"); } }

        public string GetXmlString()
        {
            var doc = new XDocument();
            var root = new XElement("island", new XAttribute("map", Map), new XAttribute("icon", Icon));
            doc.Add(root);
            if (!string.IsNullOrEmpty(Name)) root.Add(new XAttribute("name", Name));
            foreach (var i in this) root.Add(i.GetElement());
            return doc.ToString();
        }
        public void Save()
        {
            BinaryFile.WriteAllText(FilePath, GetXmlString());
        }
    }
    public sealed class IslandLevel : IGameItem, INotifyPropertyChanged
    {
        public IslandLevel(IslandLevel level, string id)
        {
            ID = id;
            name = level.name;
            text = level.text;
            ocd = level.ocd;
            depends = level.depends;
            cutscene = level.cutscene;
            onComplete = level.onComplete;
            skipEndOfLevelSequence = level.skipEndOfLevelSequence;
        }
        public IslandLevel(IGameFile parent, string id, string name = null, string text = null, string ocd = null,
                           string depends = null, string cutscene = null, string oncomplete = null,
                           bool skipeolsequence = false)
        {
            if (id == null) throw new FileFormatException(new Uri(parent.FilePath), string.Format(Resrc.ExceptionXmlAttributeDoesNotExist, "id"));
            ID = id;
            this.name = name;
            this.text = text;
            this.ocd = ocd;
            this.depends = depends;
            this.cutscene = cutscene;
            onComplete = oncomplete;
            skipEndOfLevelSequence = skipeolsequence;
        }
        public IslandLevel(IGameFile parent, XElement e)
            : this(parent, e.GetAttributeValue("id"), e.GetAttributeValue("name"), e.GetAttributeValue("text"),
                   e.GetAttributeValue("ocd"), e.GetAttributeValue("depends"), e.GetAttributeValue("cutscene"),
                   e.GetAttributeValue("oncomplete"), e.GetAttributeValue("skipeolsequence") == R.True)
        {
        }

        private string name, text, ocd, depends, cutscene, onComplete;
        private bool skipEndOfLevelSequence;
        public string ID { get; private set; }
        public string Name { get { return name; } set { name = value; OnPropertyChanged("Name"); } }
        public string Text { get { return text; } set { text = value; OnPropertyChanged("Text"); } }
        public string OCD { get { return ocd; } set { ocd = value; OnPropertyChanged("OCD"); } }
        public string Depends { get { return depends; } set { depends = value; OnPropertyChanged("Depends"); } }
        public string Cutscene { get { return cutscene; } set { cutscene = value; OnPropertyChanged("Cutscene"); } }
        public string OnComplete
            { get { return onComplete; } set { onComplete = value; OnPropertyChanged("OnComplete"); } }
        public bool SkipEndOfLevelSequence
        {
            get { return skipEndOfLevelSequence; } 
            set { skipEndOfLevelSequence = value; OnPropertyChanged("SkipEndOfLevelSequence"); }
        }

        public event PropertyChangedEventHandler PropertyChanged;
        private void OnPropertyChanged(string propertyName)
        {
            PropertyChanged(this, new PropertyChangedEventArgs(propertyName));
        }

        public XElement GetElement()
        {
            var result = new XElement("level", new XAttribute("id", ID), new XAttribute("name", Name),
                                      new XAttribute("text", Text));
            if (!string.IsNullOrWhiteSpace(OCD)) result.Add(new XAttribute("ocd", OCD));
            if (!string.IsNullOrWhiteSpace(Depends)) result.Add(new XAttribute("depends", Depends));
            if (!string.IsNullOrWhiteSpace(Cutscene)) result.Add(new XAttribute("cutscene", Cutscene));
            if (!string.IsNullOrWhiteSpace(OnComplete)) result.Add(new XAttribute("oncomplete", OnComplete));
            if (SkipEndOfLevelSequence)
                result.Add(new XAttribute("skipeolsequence", SkipEndOfLevelSequence ? R.True : R.False));
            return result;
        }
    }

    #endregion
}
