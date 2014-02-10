using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Baml2006;
using System.Windows.Controls;
using System.Xaml;
using System.Xml;
using System.Xml.Linq;
using System.Xml.XPath;
using System.Xml.Xsl;
using IronPython.Hosting;
using IronRuby;
using IrrKlang;
using IWshRuntimeLibrary;
using Microsoft.Scripting.Hosting;
using Mygod.IO;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.IO;
using Mygod.WorldOfGoo.Modifier.UI;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;
using File = System.IO.File;

namespace Mygod.WorldOfGoo.Modifier
{
    static class Kernel
    {
        public static void TrySet<T>(TextBox textBox, IIniData<T> data)
        {
            try
            {
                data.Set((T)Convert.ChangeType(textBox.Text, typeof(T)));
            }
            catch
            {
                textBox.Text = data.Get().ToString();
            }
        }

        public static bool Execute(Game game, Level level = null)
        {
            var p = game.Execute(Settings.ConsoleDebuggerEnabled, level);
            if (p == null) return false;
            if (Settings.ConsoleDebuggerEnabled) new GameDebuggingWindow(game, p).Show();
            return true;
        }

        internal static bool BatchProcessLevel(Level level, IEnumerable<Subfeature> subfeatures, XDocument doc, XElement root,
                                               string docPath, StringBuilder warning, StringBuilder error)
        {
            var modified = false;
            foreach (var subfeature in subfeatures)
            {
                try
                {
                    var param = new OperationParams(level.DirectoryPath);
                    subfeature.Execute(param);
                    if (!param.Edited) throw new Warning(subfeature.NothingChanged);
                    modified = true;
                    #region 修改次数记录模块
                    var f = root.Elements(R.Feature).SingleOrDefault(n => n.GetAttribute(R.ID) == subfeature.ID);
                    if (f == null) root.Add(f = new XElement(R.Feature, new XAttribute(R.ID, subfeature.ID), 
                                                             new XAttribute(R.ModifiedTimes, 0)));
                    var i = int.Parse(f.GetAttribute(R.ModifiedTimes), CultureInfo.InvariantCulture)
                        + (subfeature.Type == OperationType.Process ? 1 : -1);
                    if (i != 0) f.SetAttribute(R.ModifiedTimes, i.ToString(CultureInfo.InvariantCulture));
                    else f.Remove(); //remove extra nodes
                    #endregion
                }
                catch (Warning w)
                {
                    warning.AppendFormat(Resrc.WarningDetails, subfeature.Name, Resrc.Level, level.LocalizedName, w.Message);
                }
                catch (Exception e)
                {
                    error.AppendFormat(Resrc.ErrorDetails, subfeature.Name, Resrc.Level, level.LocalizedName, e.Message);
                }
            }
            if (!modified) return false;
            if (!root.Elements(R.Feature).Any()) File.Delete(docPath); else File.WriteAllText(docPath, doc.GetString());
            return true;
        }

        internal static bool BatchProcessGooBall(GooBall gooBall, IEnumerable<Subfeature> subfeatures, XDocument doc, XElement root,
                                                 string docPath, StringBuilder warning, StringBuilder error)
        {
            var modified = false;
            foreach (var subfeature in subfeatures)
            {
                try
                {
                    var param = new OperationParams(gooBall.DirectoryPath);
                    subfeature.Execute(param);
                    if (!param.Edited) throw new Warning(subfeature.NothingChanged);
                    modified = true;
                    #region 修改次数记录模块
                    var f = root.Elements(R.Feature).SingleOrDefault(n => n.GetAttribute(R.ID) == subfeature.ID);
                    if (f == null)
                        root.Add(f = new XElement(R.Feature, new XAttribute(R.ID, subfeature.ID), new XAttribute(R.ModifiedTimes, 0)));
                    var i = int.Parse(f.GetAttribute(R.ModifiedTimes), CultureInfo.InvariantCulture)
                        + (subfeature.Type == OperationType.Process ? 1 : -1);
                    if (i != 0) f.SetAttribute(R.ModifiedTimes, i.ToString(CultureInfo.InvariantCulture));
                    else f.Remove(); //remove extra nodes
                    #endregion
                }
                catch (Warning w)
                {
                    warning.AppendFormat(Resrc.WarningDetails, subfeature.Name, Resrc.GooBall, gooBall.ID, w.Message);
                }
                catch (Exception e)
                {
                    error.AppendFormat(Resrc.ErrorDetails, subfeature.Name, Resrc.GooBall, gooBall.ID, e.Message);
                }
            }
            if (!modified) return false;
            if (!root.Elements(R.Feature).Any()) File.Delete(docPath); else File.WriteAllText(docPath, doc.GetString());
            return true;
        }

        private static readonly Dictionary<string, ISoundSource> Sources = new Dictionary<string, ISoundSource>(100);

        internal static void Play2DLooped(this ISoundEngine engine, string fileName)
        {
            ISoundSource source;
            if (Sources.ContainsKey(fileName)) source = Sources[fileName];
            else
            {
                using (var fs = new FileStream(fileName, FileMode.Open)) source = engine.AddSoundSourceFromIOStream(fs, Path.GetRandomFileName());
                Sources.Add(fileName, source);
            }
            engine.Play2D(source, true, false, false);
        }

        /*internal static IntPtr GetHwnd(this Window window)
        {
            return new WindowInteropHelper(window).Handle;
        }*/

        internal static string GetTitle(string path)
        {
            if (path.Length <= 18) return path;
            return path.Substring(0, 3) + "..." + path.Substring(path.Length - 12);
        }

        public static void SetClipboardText(string text)
        {
            try
            {
                Clipboard.SetText(text);
            }
            catch (COMException e)
            {
                Log.Error.Write(e); // sometimes get the error but still succeed... THAT'S INTERSTING!
                // Dialog.Error(null, Resrc.CopyFailed, e: e);
            }
        }

        private static readonly string[] Units = new[] { null, "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB", "BB", "NB", "DB", "CB" };

        private static string GetUnit(int index)
        {
            return index == 0 ? Resrc.Byte : Units[index];
        }

        public static string GetSize(long size)
        {
            double byt = size;
            byte i = 0;
            while (byt > 1000)
            {
                byt /= 1024;
                i++;
            }
            var bytesstring = size.ToString("N");
            return byt.ToString("N") + " " + GetUnit(i) + " (" + bytesstring.Remove(bytesstring.Length - 3) + ' ' + GetUnit(0) + ')';
        }
        
        /// <summary>
        /// 获取快捷方式目标。
        /// </summary>
        /// <param name="shortcutPath">快捷方式路径。</param>
        /// <returns>返回快捷方式指向的路径。</returns>
        public static string GetShortcutTarget(string shortcutPath)
        {
            return ((IWshShortcut)new WshShell().CreateShortcut(shortcutPath)).TargetPath;
        }
    }

    static class Features
    {
        private static void Load()
        {
            var s = Stopwatch.StartNew();
            try
            {
                const int acceptableVersion = 4;
                var path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Resources/Features.xml");
                var doc = XDocument.Load(path);
                var root = doc.GetElement("Features", path);
                if (root.GetAttribute("Version") != acceptableVersion.ToString(CultureInfo.InvariantCulture))
                    throw Exceptions.FileFormatError(path, string.Format(Resrc.ExceptionFeaturesXmlVersionIncorrect, acceptableVersion));
                Strings = new FeaturesText(root.GetElement("Strings", path));
                var e = root.Element("LevelEditor");
                if (e == null) throw Exceptions.XmlElementDoesNotExist(path, "LevelEditor");
                levelFeatures = (from node in e.Elements("Feature") select new Feature(node)).ToDictionary(feature => feature.ID);
                e = root.Element("GooBallEditor");
                if (e == null) throw Exceptions.XmlElementDoesNotExist(path, "GooBallEditor");
                gooBallFeatures = (from node in e.Elements("Feature") select new Feature(node)).ToDictionary(feature => feature.ID);
                gooBallTester = new CreatableLevel(R.GooBallTesterLevelName, root.Element("GooBallTester"));
                materialTester = new CreatableLevel(R.MaterialTesterLevelName, root.Element("MaterialTester"));
                gooBallTestHelper = new CreatableGooBall(R.GooBallTestHelperGooBallName, root.Element("GooBallTestHelper"));
            }
            catch (ThreadAbortException)
            {
                Application.Current.Shutdown();
            }
            catch (Exception e)
            {
                App.Dispatcher.Invoke((Action)(() =>
                {
                    Dialog.Error(Application.Current.MainWindow, Resrc.FeaturesParseError,Resrc.FeaturesParseErrorDetails, e);
                    Application.Current.Shutdown(-2);
                }));
            }
            finally
            {
                Log.Performance.Write("Load Features.xml", s.Elapsed);
            }
        }
        public static void StartLoad()
        {
            task = new Task(Load);
            task.Start();
        }

        private static void WaitTillComplete()
        {
            if (!task.IsCompleted) task.Wait(); 
        }

        private static Task task;
        private static Dictionary<string, Feature> levelFeatures, gooBallFeatures;
        private static CreatableLevel gooBallTester, materialTester;
        private static CreatableGooBall gooBallTestHelper;

        public static FeaturesText Strings { get; private set; }
        public static Dictionary<string, Feature> LevelFeatures { get { WaitTillComplete(); return levelFeatures; } }
        public static Dictionary<string, Feature> GooBallFeatures { get { WaitTillComplete(); return gooBallFeatures; } }
        public static CreatableLevel GooBallTester { get { WaitTillComplete(); return gooBallTester; } }
        public static CreatableLevel MaterialTester { get { WaitTillComplete(); return materialTester; } }
        public static CreatableGooBall GooBallTestHelper { get { WaitTillComplete(); return gooBallTestHelper; } }
    }
    sealed class CreatableLevel : IGameItem
    {
        public CreatableLevel(string id, XContainer e)
        {
            ID = id;
            var element = e.Element("Level");
            if (element != null) level = new XDocument(element.Elements()).GetString();
            element = e.Element("Scene");
            if (element != null) scene = new XDocument(element.Elements()).GetString();
            element = e.Element("Resrc");
            if (element != null) resrc = new XDocument(element.Elements()).GetString();
        }

        public string ID { get; private set; }
        private readonly string level, scene, resrc;

        public Level CreateAt(Levels levels, object[] levelArgs = null, object[] sceneArgs = null)
        {
            Level result;
            if (!levels.Contains(ID))
            {
                result = new Level(levels, ID);
                Directory.CreateDirectory(result.DirectoryPath);
                levels.Add(result);
            }
            result = levels[ID];
            result.LevelXml = levelArgs == null ? level : string.Format(level, levelArgs);
            result.SceneXml = sceneArgs == null ? scene : string.Format(scene, sceneArgs);
            result.ResrcXml = resrc;
            return result;
        }
    }
    sealed class CreatableGooBall : IGameItem
    {
        public CreatableGooBall(string id, XContainer e)
        {
            ID = id;
            var element = e.Element("Balls");
            if (element != null) balls = new XDocument(element.Elements()).GetString();
            element = e.Element("Resources");
            if (element != null) resources = new XDocument(element.Elements()).GetString();
        }

        public string ID { get; private set; }
        private readonly string balls, resources;

        public GooBall CreateAt(GooBalls gooBalls, params object[] ballsArgs)
        {
            GooBall result;
            if (!gooBalls.Contains(ID))
            {
                result = new GooBall(gooBalls, ID);
                Directory.CreateDirectory(result.DirectoryPath);
                gooBalls.Add(result);
            }
            result = gooBalls[ID];
            result.BallsXml = ballsArgs == null ? balls : string.Format(balls, ballsArgs);
            result.ResourcesXml = resources;
            return result;
        }
    }

    // An easier version of Text
    internal sealed class FeaturesTextItem : GameKeyedCollection<SpecificLanguageString>, IGameItem
    {
        public FeaturesTextItem(XElement e)
        {
            foreach (var a in e.Attributes())
            {
                var name = a.Name.LocalName.ToLower();
                if (name == "id") ID = a.Value;
                else if (!Contains(name)) Add(new SpecificLanguageString(null, name, a.Value.Replace("|", Environment.NewLine)));
            }
            if (ID == null) throw new FileFormatException(null, string.Format(Resrc.ExceptionXmlAttributeDoesNotExist, "id"));
        }

        public string ID { get; private set; }

        private string DefaultValue
        {
            get { return Contains("text") ? this["text"].Value : null; }
            //set { if (Contains("text")) this["text"].Value = value; else Add(new SpecificLanguageString(null, "text", value)); }
        }
        public string LocalizedText
        {
            get
            {
                var language = Globalization.GetLocalizedValue(s => s == null ? string.Empty : s.ToLower(), Contains);
                return Contains(language) ? this[language].Value : DefaultValue;
            }
        }
    }
    internal sealed class FeaturesText : GameKeyedCollection<FeaturesTextItem>
    {
        public FeaturesText(XContainer xe)
        {
            foreach (var i in xe.Nodes().OfType<XElement>().Where(e => e.Name.LocalName.ToLower() == "string")
                .Select(e => new FeaturesTextItem(e)))
            {
                if (!Contains(i.ID)) Add(i);
                else
                {
                    var item = this[i.ID];
                    foreach (var j in i.Where(j => !item.Contains(j.Language)))
                        item.Add(new SpecificLanguageString(null, j.Language, j.Value));
                }
            }
        }
    }

    sealed class Feature
    {
        public Feature(XElement node)
        {
            ID = node.GetAttribute("ID") ?? "Unknown";
            Process = new Subfeature(this, OperationType.Process, node.Element("Process"));
            Reverse = new Subfeature(this, OperationType.Reverse, node.Element("Reverse"));
            Restore = new Subfeature(this, OperationType.Restore, node.Element("Restore"));
        }

        public readonly string ID;
        public Subfeature Process { get; private set; }
        public Subfeature Reverse { get; private set; }
        public Subfeature Restore { get; private set; }
    }
    sealed class Subfeature : Operation
    {
        public Subfeature(Feature parent, OperationType type, XElement node)
        {
            this.parent = parent;
            Type = type;
            name = node.GetAttribute("Name") ?? (type == OperationType.Restore ? parent.Reverse.name : null);
            description = node.GetAttribute("Description") ?? (type == OperationType.Restore ? parent.Reverse.description : null);
            nothingChanged = node.GetAttribute("NothingChanged") ?? (type == OperationType.Restore ? parent.Reverse.nothingChanged : null);
            tip = node.GetAttribute("Tip") ?? (type == OperationType.Restore ? parent.Reverse.tip : null);
            operations = new OperationGroup(node.Elements());
        }

        private readonly Feature parent;
        public string ID { get { return parent.ID; } }
        private readonly string name, nothingChanged, description, tip;
        public string Name
        {
            get { return Features.Strings[name != null && Features.Strings.Contains(name) ? name : ID + Type + "Name"].LocalizedText; }
        }
        public string NothingChanged
        {
            get
            {
                var key = nothingChanged != null && Features.Strings.Contains(nothingChanged) ? nothingChanged
                    : ID + Type + "NothingChanged";
                return Features.Strings.Contains(key) ? Features.Strings[key].LocalizedText : null;
            }
        }
        public string Description
        {
            get
            {
                var n = name != null && Features.Strings.Contains(name) ? name : (ID + Type + "Description");
                if (!Features.Strings.Contains(n) && Type == OperationType.Restore) n = (ID + OperationType.Reverse + "Description");
                return Features.Strings[n].LocalizedText;
            }
        }
        public string Tip
        {
            get
            {
                var n = name != null && Features.Strings.Contains(name) ? name : (ID + Type + "Tip");
                if (!Features.Strings.Contains(n) && Type == OperationType.Restore) n = (ID + OperationType.Reverse + "Tip");
                return Features.Strings[n].LocalizedText;
            }
        }
        private readonly OperationGroup operations;
        public readonly OperationType Type;

        public override void Execute(OperationParams param)
        {
            operations.Execute(param);
        }
    }
    enum OperationType
    {
        Process, Reverse, Restore
    }

    class OperationParams
    {
        public OperationParams(string directory)
        {
            Directory = directory;
        }

        public readonly string Directory;
        public bool Edited;
    }
    class FileOperationParams : OperationParams
    {
        public FileOperationParams(OperationParams param, string path, string content) : base(param.Directory)
        {
            Path = path;
            SourceContent = Content = content;
        }

        public string Content;
        public readonly string Path, SourceContent;
    }
    class XmlOperationParams : FileOperationParams
    {
        public XmlOperationParams(FileOperationParams param) : base(param, param.Path, param.Content)
        {
            Document = XDocument.Parse(param.Content);
        }

        public readonly XDocument Document;
        public XElement XmlCurrentNode;
        public bool Modified;
    }

    abstract class Operation
    {
        public abstract void Execute(OperationParams param);
    }
    abstract class IfOperation : Operation
    {
        protected OperationGroup Then, Else;
    }

    sealed class OperationGroup : Operation
    {
        public OperationGroup(IEnumerable nodes)
        {
            // ReSharper disable PossibleNullReferenceException
            foreach (XElement node in nodes) switch (node.Name.LocalName)
            {
                case "RegexReplace":
                    operations.Add(new RegexReplaceOperation(node.GetAttribute("Pattern"), node.GetAttribute("Replacement")));
                    break;
                case "Replace":
                    operations.Add(new ReplaceOperation(node.GetAttribute("Old"), node.GetAttribute("New")));
                    break;
                case "Warning":
                    operations.Add(new WarningOperation(node.GetAttribute("Message")));
                    break;
                case "SetAttribute":
                    operations.Add(new SetAttributeOperation(node.GetAttribute("Name"), node.GetAttribute("Value")));
                    break;
                case "MatrixMultiplyAttribute":
                    operations.Add(new MatrixMultiplyAttributeOperation(node.GetAttribute("Name"), node.GetAttribute("Value"),
                                                                        node.GetAttribute("Default")));
                    break;
                case "SelectNodes":
                    operations.Add(new SelectNodesOperation(from n in node.Element("Nodes").Elements("Node")
                                                            select new Node(n.GetAttribute("XPath"), n.GetAttribute("Contains")),
                                                            new OperationGroup(node.Element("Operations").Elements())));
                    break;
                case "CreateElement":
                    operations.Add(new CreateElementOperation(node.GetAttribute("XPath"), node.GetAttribute("ElementName"),
                                                              new OperationGroup(node.Elements())));
                    break;
                case "RemoveElement":
                    operations.Add(new RemoveElementOperation(node.GetAttribute("XPath"), node.GetAttribute("WhichContains")));
                    break;
                case "IfAttribute":
                    operations.Add(new IfAttributeOperation(new OperationGroup(node.Element("Then").Elements()),
                                                            new OperationGroup(node.Element("Else").Elements()),
                                                            node.GetAttribute("Name"), node.GetAttribute("Value"),
                                                            Convert.ToBoolean(node.GetAttribute("IfNull"))));
                    break;
                case "IfContains":
                    operations.Add(new IfContainsOperation(new OperationGroup(node.Element("Then").Elements()),
                                                           new OperationGroup(node.Element("Else").Elements()),
                                                           node.GetAttribute("Value")));
                    break;
                case "IfEdited":
                    operations.Add(new IfEditedOperation(new OperationGroup(node.Element("Then").Elements()),
                                                         new OperationGroup(node.Element("Else").Elements())));
                    break;
                case "ExecuteXsl":
                    operations.Add(new ExecuteXslOperation(node.GetAttribute("Path")));
                    break;
                case "ExecuteIronPython":
                    operations.Add(new ExecuteIronPythonOperation(node.GetAttribute("Script")));
                    break;
                case "ExecuteIronRuby":
                    operations.Add(new ExecuteIronRubyOperation(node.GetAttribute("Script")));
                    break;
                case "Modify":
                    operations.Add(new ModifyOperation(node.GetAttribute("File"), new OperationGroup(node.Elements())));
                    break;
                default:
                    Trace.WriteLine(string.Format("未知的元素名 {0}！", node.Name));
                    break;
            }
            // ReSharper restore PossibleNullReferenceException
        }

        private readonly List<Operation> operations = new List<Operation>();

        public override void Execute(OperationParams param)
        {
            foreach (var o in operations) o.Execute(param);
        }
    }

    sealed class ModifyOperation : Operation
    {
        public ModifyOperation(string file, OperationGroup group)
        {
            this.file = file;
            operations = group;
        }

        private readonly string file;
        private readonly OperationGroup operations;

        private static readonly HashSet<string> BallFiles = new HashSet<string>("balls,resources".Split(','));

        public override void Execute(OperationParams param)
        {
            var path = Path.Combine(param.Directory, BallFiles.Contains(file) ? file + ".xml.bin"
                : (new DirectoryInfo(param.Directory).Name + '.' + file + ".bin"));
            var p = new FileOperationParams(param, path, BinaryFile.ReadAllText(path));
            operations.Execute(p);
            if (p.Content == p.SourceContent) return;
            BinaryFile.WriteAllText(path, p.Content);
            param.Edited = true;
        }
    }

    sealed class RegexReplaceOperation : Operation
    {
        public RegexReplaceOperation(string pattern, string r)
        {
            regex = new Regex(pattern);
            replacement = r;
        }

        private readonly string replacement;
        private readonly Regex regex;

        public override void Execute(OperationParams param)
        {
            var p = (FileOperationParams) param;
            p.Content = regex.Replace(p.Content, replacement);
        }
    }
    sealed class ReplaceOperation : Operation
    {
        public ReplaceOperation(string o, string n)
        {
            old = o; New = n;
        }

        private readonly string old, New;

        public override void Execute(OperationParams param)
        {
            var p = (FileOperationParams)param;
            p.Content = p.Content.Replace(old, New);
        }
    }

    sealed class SelectNodesOperation : Operation
    {
        public SelectNodesOperation(IEnumerable<Node> nodes, OperationGroup operations)
        {
            this.nodes = nodes; this.operations = operations;
        }

        private readonly IEnumerable<Node> nodes;
        private readonly OperationGroup operations;

        public override void Execute(OperationParams param)
        {
            var pa = (FileOperationParams) param;
            var p = new XmlOperationParams(pa);
            foreach (var node in nodes.Select(node => (from n in p.Document.XPathSelectElements(node.XPath)
                                                       where node.Contains == null || new XDocument(n).GetString().Contains(node.Contains)
                                                       select n)).SelectMany(node => node).Distinct())
            {
                p.XmlCurrentNode = node;
                operations.Execute(p);
            }
            if (p.Modified) pa.Content = p.Document.GetString();
        }
    }
    sealed class CreateElementOperation : Operation
    {
        public CreateElementOperation(string xpath, string en, OperationGroup operations)
        {
            xPath = xpath; elementName = en; this.operations = operations;
        }

        private readonly string xPath, elementName;
        private readonly OperationGroup operations;

        public override void Execute(OperationParams param)
        {
            var pa = (FileOperationParams) param;
            var p = new XmlOperationParams(pa);
            foreach (var root in p.Document.XPathSelectElements(xPath))
            {
                root.Add(p.XmlCurrentNode = new XElement(elementName));
                p.Modified = true;
                operations.Execute(p);
            }
            if (p.Modified) pa.Content = p.Document.GetString();
        }
    }
    sealed class RemoveElementOperation : Operation
    {
        public RemoveElementOperation(string xp, string wc = null)
        {
            xPath = xp; 
            whichContains = wc;
        }

        private readonly string xPath, whichContains;

        public override void Execute(OperationParams param)
        {
            var pa = (FileOperationParams)param;
            var p = new XmlOperationParams(pa);
            foreach (var node in p.Document.XPathSelectElements(xPath).Where(n => n.GetString().Contains(whichContains)))
            {
                node.Remove();
                p.Modified = true;
            }
            if (p.Modified) pa.Content = p.Document.GetString();
        }
    }

    sealed class SetAttributeOperation : Operation
    {
        public SetAttributeOperation(string n, string v)
        {
            name = n; value = v;
        }

        private readonly string name, value;

        public override void Execute(OperationParams param)
        {
            var p = (XmlOperationParams) param;
            if (p.XmlCurrentNode == null) throw new NotSupportedException();
            var e = p.XmlCurrentNode;
            e.SetAttribute(name, value);
            p.Modified = true;
        }
    }
    sealed class MatrixMultiplyAttributeOperation : Operation
    {
        public MatrixMultiplyAttributeOperation(string n, string value, string d = null)
        {
            name = n;
            matrix = value.Split(';').Select(row => row.Split(',').Select(double.Parse).ToArray()).ToArray();
            if (matrix.Length <= 1) throw new NotSupportedException();
            Default = d;
        }

        private readonly string name, Default;
        private readonly double[][] matrix;

        public override void Execute(OperationParams param)
        {
            var p = (XmlOperationParams)param;
            if (p.XmlCurrentNode == null) throw new NotSupportedException();
            var att = p.XmlCurrentNode.GetAttribute(name) ?? Default;
            if (att == null) return;
            att += ",1";
            double[] vector = att.Split(',').Select(double.Parse).ToArray(), transformed = new double[vector.Length];
            if (vector.Length != matrix.Length) throw new NotSupportedException();
            for (var y = 0; y < vector.Length; y++) for (var x = 0; x < vector.Length; x++) transformed[y] += matrix[y][x] * vector[x];
            for (var x = 0; x < vector.Length - 1; x++) transformed[x] /= transformed[vector.Length - 1];
            p.XmlCurrentNode.SetAttribute(name, vector.Take(vector.Length - 1).Skip(1)
                .Aggregate(vector[0].ToString(CultureInfo.InvariantCulture), (c, s) => c + ',' + s));
            p.Modified = true;
        }
    }

    sealed class IfAttributeOperation : IfOperation
    {
        public IfAttributeOperation(OperationGroup t, OperationGroup e, string n, string v, bool i)
        {
            Then = t; Else = e; name = n; value = v; ifNull = i;
        }

        private readonly string name, value;
        private readonly bool ifNull;

        public override void Execute(OperationParams param)
        {
            var p = (XmlOperationParams)param;
            if (p.XmlCurrentNode == null) throw new NotSupportedException();
            var a = p.XmlCurrentNode.GetAttribute(name);
            if (a == value || a == null && ifNull) Then.Execute(p); else Else.Execute(p);
        }
    }
    sealed class IfContainsOperation : IfOperation
    {
        public IfContainsOperation(OperationGroup t, OperationGroup e, string v)
        {
            Then = t; Else = e; value = v;
        }

        private readonly string value;

        public override void Execute(OperationParams param)
        {
            var p = (FileOperationParams) param;
            if (p.Content.Contains(value)) Then.Execute(p); else Else.Execute(p);
        }
    }
    sealed class IfEditedOperation : IfOperation
    {
        public IfEditedOperation(OperationGroup t, OperationGroup e)
        {
            Then = t; Else = e;
        }

        public override void Execute(OperationParams param)
        {
            var p = (FileOperationParams)param;
            var x = p as XmlOperationParams;
            if (p.Content != p.SourceContent || (x != null && x.Modified)) Then.Execute(p); else Else.Execute(p);
        }
    }

    static class ScriptHelper
    {
        public static string GetScriptPath(string name)
        {
            return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Scripts", name);
        }
    }
    sealed class ExecuteXslOperation : Operation
    {
        public ExecuteXslOperation(string path)
        {
            transform.Load(XmlReader.Create(new StreamReader(File.OpenRead(ScriptHelper.GetScriptPath(path)))), 
                           new XsltSettings(true, true), new XmlUrlResolver());
        }

        private readonly XslCompiledTransform transform = new XslCompiledTransform(true);

        public override void Execute(OperationParams param)
        {
            var p = (FileOperationParams)param;
            var writer = new StringWriter();
            transform.Transform(XmlReader.Create(new StringReader(p.Content)), null,
                XmlWriter.Create(writer, new XmlWriterSettings { Indent = true }), new XmlUrlResolver());
            p.Content = writer.ToString();
        }
    }
    sealed class ExecuteIronPythonOperation : Operation
    {
        static ExecuteIronPythonOperation()
        {
            Engine = Python.CreateEngine();
            Engine.CreateScriptSourceFromFile(ScriptHelper.GetScriptPath("Initialization.py")).Execute(Engine.Runtime.Globals);
        }

        public ExecuteIronPythonOperation(string script)
        {
            code = Engine.CreateScriptSourceFromFile(ScriptHelper.GetScriptPath(script));
        }

        private static readonly ScriptEngine Engine;
        private readonly ScriptSource code;

        public override void Execute(OperationParams param)
        {
            var p = (FileOperationParams)param;
            Engine.Runtime.Globals.SetVariable("input", p.Content);
            code.Execute(Engine.Runtime.Globals);
            try
            {
                if (!Engine.Runtime.Globals.GetVariable("edited")) return;
            }
            catch
            {
                return;
            }
            var output = Engine.Runtime.Globals.GetVariable("output");
            if (output is string) p.Content = output;
            else
            {
                var document = output as XDocument;
                if (document != null) p.Content = document.GetString();     // dynamic does not support the normal way
            }
        }
    }
    sealed class ExecuteIronRubyOperation : Operation
    {
        static ExecuteIronRubyOperation()
        {
            Engine = Ruby.CreateEngine();
            Engine.CreateScriptSourceFromFile(ScriptHelper.GetScriptPath("Initialization.rb")).Execute(Engine.Runtime.Globals);
        }

        public ExecuteIronRubyOperation(string script)
        {
            code = Engine.CreateScriptSourceFromFile(ScriptHelper.GetScriptPath(script));
        }

        private static readonly ScriptEngine Engine;
        private readonly ScriptSource code;

        public override void Execute(OperationParams param)
        {
            var p = (FileOperationParams)param;
            Engine.Runtime.Globals.SetVariable("input", p.Content);
            code.Execute(Engine.Runtime.Globals);
            try
            {
                if (!Engine.Runtime.Globals.GetVariable("edited")) return;
            }
            catch
            {
                return;
            }
            var output = Engine.Runtime.Globals.GetVariable("output");
            if (output is string) p.Content = output;
            else
            {
                var document = output as XDocument;
                if (document != null) p.Content = document.GetString();     // dynamic does not support the normal way
            }
        }
    }

    sealed class WarningOperation : Operation
    {
        public WarningOperation(string message)
        {
            warning = new Warning(Features.Strings[message].LocalizedText);
        }

        private readonly Warning warning;

        public override void Execute(OperationParams param)
        {
            throw warning;
        }
    }

    sealed class Node
    {
        public Node(string xpath, string contains = null)
        {
            XPath = xpath; Contains = contains;
        }
        public readonly string XPath, Contains;
    }

    [Serializable]
    sealed class Warning : Exception
    {
        public Warning(string m) : base(m)
        {
        }
    }

    public static class BamlReader
    {
        public static object Load(Stream stream)
        {
            using (var reader = new Baml2006Reader(stream)) using (var writer = new XamlObjectWriter(reader.SchemaContext))
            {
                while (reader.Read()) writer.WriteNode(reader);
                return writer.Result;
            }
        }
    }

    public class MemoryEditor
    {
        [DllImportAttribute("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenProcess(int dwDesiredAccess, bool bInheritHandle, int dwProcessId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern void CloseHandle(IntPtr hObject);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ReadProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, [Out] byte[] lpBuffer, int dwSize,
                                                     out int lpNumberOfBytesRead);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, int nSize, 
                                                      IntPtr lpNumberOfBytesWritten);

        public MemoryEditor(int processID)
        {
            process = OpenProcess(0x1fffff, true, processID);
        }
        ~MemoryEditor()
        {
            CloseHandle(process);
        }

        private readonly IntPtr process;

        private byte[] ReadProcessMemory(IntPtr memoryAddress, int bytesToRead)
        {
            var buffer = new byte[bytesToRead];
            int bytesRead;
            if (!ReadProcessMemory(process, memoryAddress, buffer, bytesToRead, out bytesRead)) Trace.WriteLine("Failed to read memory.");
            return buffer;
        }
        public byte[] ReadProcessMemory(MemoryAddress memoryAddress, int bytesToRead)
        {
            return ReadProcessMemory(GetAddress(memoryAddress), bytesToRead);
        }

        private void WriteProcessMemory(IntPtr memoryAddress, byte[] bytesToWrite)
        {
            WriteProcessMemory(process, memoryAddress, bytesToWrite, bytesToWrite.Length, IntPtr.Zero);
            //bytesWritten = ptrBytesWritten.ToInt32();
        }
        public void WriteProcessMemory(MemoryAddress memoryAddress, byte[] bytesToWrite)
        {
            WriteProcessMemory(GetAddress(memoryAddress), bytesToWrite);
        }

        private IntPtr GetAddress(MemoryAddress memoryAddress)
        {
            return new IntPtr(memoryAddress.Offsets.Aggregate(memoryAddress.StartAddress + 0x400000, 
                (current, offset) => BitConverter.ToInt32(ReadProcessMemory(new IntPtr(current), 4), 0) + offset));
        }
    }

    public struct MemoryAddress
    {
        public MemoryAddress(int startAddress, params int[] offsets)
        {
            StartAddress = startAddress;
            Offsets = offsets;
        }

        public readonly int StartAddress;
        public readonly int[] Offsets;
    }

    public class WorldOfGooMemoryEditor
    {
        public WorldOfGooMemoryEditor(Process process)
        {
            editor = new MemoryEditor(process.Id);
        }

        private readonly MemoryEditor editor;

        private static readonly MemoryAddress BallsAddress = new MemoryAddress(0x00217860, 0x8, 0x74, 0xb8),
                                              BallsRequiredAddress = new MemoryAddress(0x00217860, 0x8, 0x74, 0xb4),
                                              MovesAddress = new MemoryAddress(0x00217860, 0x8, 0x1a4),
                                              PausedAddress = new MemoryAddress(0x00217860, 0xc, 0x34),
                                              UndraggableAddress = new MemoryAddress(0x00217860, 0xc, 0x44),
                                              //MenuEnabledAddress = new MemoryAddress(0x00217860, 0x12c, 0x2e0, 0x74),
                                              //ShowBallsInTankAddress = new MemoryAddress(0x00217860, 0x128, 0xd0, 0x390),
                                              LetterboxedAddress = new MemoryAddress(0x00217860, 0x8, 0x74, 0x28);
        public int Balls
        {
            get { return BitConverter.ToInt32(editor.ReadProcessMemory(BallsAddress, 4), 0); }
            set { editor.WriteProcessMemory(BallsAddress, BitConverter.GetBytes(value)); }
        }
        public int BallsRequired
        {
            get { return BitConverter.ToInt32(editor.ReadProcessMemory(BallsRequiredAddress, 4), 0); }
            set { editor.WriteProcessMemory(BallsRequiredAddress, BitConverter.GetBytes(value)); }
        }
        public int Moves
        {
            get { return BitConverter.ToInt32(editor.ReadProcessMemory(MovesAddress, 4), 0); }
            set { editor.WriteProcessMemory(MovesAddress, BitConverter.GetBytes(value)); }
        }
        public bool Paused
        {
            get { return editor.ReadProcessMemory(PausedAddress, 1)[0] == 1; }
            set { editor.WriteProcessMemory(PausedAddress, new[] { value ? (byte)1 : (byte)0 }); }
        }
        public bool Undraggable
        {
            get { return editor.ReadProcessMemory(UndraggableAddress, 1)[0] == 1; }
            set { editor.WriteProcessMemory(UndraggableAddress, new[] { value ? (byte)1 : (byte)0 }); }
        }
        public bool Letterboxed
        {
            get { return editor.ReadProcessMemory(LetterboxedAddress, 1)[0] == 1; }
            set { editor.WriteProcessMemory(LetterboxedAddress, new[] { value ? (byte)1 : (byte)0 }); }
        }
        /*public bool MenuEnabled
        {
            get { return editor.ReadProcessMemory(MenuEnabledAddress, 1)[0] == 1; }
            set { editor.WriteProcessMemory(MenuEnabledAddress, new[] { value ? (byte)1 : (byte)0 }); }
        }
        public bool ShowBallsInTank
        {
            get { return editor.ReadProcessMemory(ShowBallsInTankAddress, 1)[0] == 1; }
            set { editor.WriteProcessMemory(ShowBallsInTankAddress, new[] { value ? (byte)1 : (byte)0 }); }
        }*/
    }

    internal static class BooleanBox
    {
        public static readonly object True = true, False = false;
    }
}
