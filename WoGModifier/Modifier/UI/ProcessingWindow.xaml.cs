using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Shell;
using System.Xml.Linq;
using Mygod.WorldOfGoo.Modifier.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;
using Mygod.Xml.Linq;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    sealed partial class ProcessingWindow
    {
        public ProcessingWindow(Game game)
        {
            DataContext = game;
            InitializeComponent();
            Owner = Application.Current.MainWindow;
        }

        private double Progress
        {
            set
            {
                Dispatcher.Invoke(() =>
                {
                    Taskbar.ProgressValue = ProgressBar.Value = value;
                    Taskbar.ProgressState = TaskbarItemProgressState.Normal;
                });
            }
        }
        private string Details { set { Dispatcher.Invoke(() => Taskbar.Description = DetailsBlock.Text = value); } }
        private Task task;
        private bool finished, canceled;

        private void Update(string type, string name, long current, long total, DateTime? start = null)
        {
            var p = (double)current / total;
            var d = string.Format(Resrc.ProcessingDetails, type, name, current, total, p*100);
            if (start != null)
            {
                var used = DateTime.Now - start.Value;
                var remaining = new TimeSpan((long)(used.Ticks * (total - current) / (double)current));
                d += Environment.NewLine + Resrc.UsedTime + used + Environment.NewLine + Resrc.RemainingTime +
                     remaining;
            }
            Progress = p;
            Details = d;
        }

        internal void LevelBatchProcess(List<Feature> features, List<Level> levels, OperationType type)
        {
            task = new Task(() => BatchProcessLevel(features, levels, type));
            ShowDialog();
        }
        internal void GooBallBatchProcess(List<Feature> features, List<GooBall> balls, OperationType type)
        {
            task = new Task(() => BatchProcessGooBall(features, balls, type));
            ShowDialog();
        }

        private void BatchProcessLevel(ICollection<Feature> features, ICollection<Level> levels, OperationType type)
        {
            finished = false;
            canceled = false;
            var start = DateTime.Now;
            long changed = 0, total = 0;
            StringBuilder error = new StringBuilder(1024), warning = new StringBuilder(2048);
            foreach (var level in levels.TakeWhile(level => !canceled))
            {
                XDocument doc;
                var p = Path.Combine(level.DirectoryPath, R.ModifiedXml);
                if (type == OperationType.Restore)
                {
                    try
                    {
                        doc = XDocument.Load(p);
                    }
                    catch
                    {
                        warning.AppendFormat(Resrc.WarningDetails, Resrc.Restore, Resrc.Level, level.ID,
                                             string.Format(Resrc.NoModifiedRecordFound, Resrc.Level));
                        continue;
                    }
                    var root = doc.Element(R.Modified);
                    if (root == null) continue;
                    var selected = features.ToDictionary(f => f.ID);
                    var nodes = from node in root.Elements() let id = node.GetAttributeValue(R.ID)
                                where selected.ContainsKey(id)
                                select new { ID = id, ModifiedTimes = node.GetAttributeValue<int>(R.ModifiedTimes) };
                    var subfeatures = new List<Subfeature>();
                    foreach (var node in nodes)
                    {
                        var feature = selected[node.ID];
                        if (node.ModifiedTimes > 0)
                            for (var i = 0; i < node.ModifiedTimes; i++) subfeatures.Add(feature.Reverse);
                        else if (node.ModifiedTimes < 0)
                            for (var i = 0; i > node.ModifiedTimes; i--) subfeatures.Add(feature.Process);
                    }
                    if (Kernel.BatchProcessLevel(level, subfeatures, doc, root, p, warning, error)) changed++;
                }
                else
                {
                    try
                    {
                        doc = XDocument.Load(p);
                    }
                    catch
                    {
                        doc = XDocument.Parse(Resrc.DefaultModifiedXml);
                    }
                    var root = doc.Element(R.Modified);
                    if (Kernel.BatchProcessLevel(level, from Feature f in features
                                                        select type == OperationType.Process ? f.Process : f.Reverse,
                                                 doc, root, p, warning, error)) changed++;
                    Update(Resrc.Level, level.LocalizedName, ++total, levels.LongCount(), start);
                }
            }
            var span = DateTime.Now - start;
            finished = true;
            Details = Resrc.BatchProcessFinish;
            Dispatcher.Invoke(() =>
            {
                Log.Performance.Write(string.Format(Resrc.BatchProcessLog, features.Count, levels.Count, Resrc.Level),
                                      span);
                if (Dialog.YesNoQuestion(this, Resrc.BatchProcessFinishInstruction,
                        string.Format(Resrc.BatchProcessFinishText, span.TotalSeconds,
                            error.Length > 0 ? string.Format(Resrc.BatchProcessError, Resrc.Level) : 
                            warning.Length > 0 ? string.Format(Resrc.BatchProcessWarning, Resrc.Level) :
                            string.Format(Resrc.BatchProcessSuccessfully, Resrc.Level)), Resrc.Finish))
                    new TextWindow(Resrc.Details, string.Format(Resrc.BatchProcessDetails, Resrc.Level,
                        levels.LongCount(), changed) + Resrc.ErrorStart + error + Resrc.WarningStart + warning, Owner)
                        .Show();
                Close();
            });
        }
        private void BatchProcessGooBall(ICollection<Feature> features, ICollection<GooBall> balls, OperationType type)
        {
            finished = false;
            canceled = false;
            var start = DateTime.Now;
            long changed = 0, total = 0;
            StringBuilder error = new StringBuilder(1024), warning = new StringBuilder(2048);
            foreach (var ball in balls.TakeWhile(ball => !canceled))
            {
                XDocument doc;
                var p = Path.Combine(ball.DirectoryPath, R.ModifiedXml);
                if (type == OperationType.Restore)
                {
                    try
                    {
                        doc = XDocument.Load(p);
                    }
                    catch
                    {
                        warning.AppendFormat(Resrc.WarningDetails, Resrc.Restore, Resrc.GooBall, ball.ID, 
                                             string.Format(Resrc.NoModifiedRecordFound, Resrc.GooBall));
                        continue;
                    }
                    var root = doc.Element(R.Modified);
                    if (root == null) continue;
                    var selected = features.ToDictionary(f => f.ID);
                    var nodes = from node in root.Elements() let id = node.GetAttributeValue(R.ID)
                                where selected.ContainsKey(id)
                                select new { ID = id, ModifiedTimes = node.GetAttributeValue<int>(R.ModifiedTimes) };
                    var subfeatures = new List<Subfeature>();
                    foreach (var node in nodes)
                    {
                        var feature = selected[node.ID];
                        if (node.ModifiedTimes > 0)
                            for (var i = 0; i < node.ModifiedTimes; i++) subfeatures.Add(feature.Reverse);
                        else if (node.ModifiedTimes < 0)
                            for (var i = 0; i > node.ModifiedTimes; i--) subfeatures.Add(feature.Process);
                    }
                    if (Kernel.BatchProcessGooBall(ball, subfeatures, doc, root, p, warning, error)) changed++;
                }
                else
                {
                    try
                    {
                        doc = XDocument.Load(p);
                    }
                    catch
                    {
                        doc = XDocument.Parse(Resrc.DefaultModifiedXml);
                    }
                    var root = doc.Element(R.Modified);
                    if (Kernel.BatchProcessGooBall(ball, from Feature f in features
                                                         select type == OperationType.Process ? f.Process : f.Reverse,
                                                   doc, root, p, warning, error)) changed++;
                }
                Update(Resrc.GooBall, ball.ID, ++total, balls.LongCount(), start);
            }
            var span = DateTime.Now - start;
            finished = true;
            Details = Resrc.BatchProcessFinish;
            Dispatcher.Invoke(() =>
            {
                Log.Performance.Write(string.Format(Resrc.BatchProcessLog, features.Count, balls.Count, Resrc.GooBall),
                                      span);
                if (Dialog.YesNoQuestion(this, Resrc.BatchProcessFinishInstruction,
                                         string.Format(Resrc.BatchProcessFinishText, span.TotalSeconds,
                    error.Length > 0 ? string.Format(Resrc.BatchProcessError, Resrc.GooBall) :
                    warning.Length > 0 ? string.Format(Resrc.BatchProcessWarning, Resrc.GooBall) :
                    string.Format(Resrc.BatchProcessSuccessfully, Resrc.GooBall)), Resrc.Finish))
                    new TextWindow(Resrc.Details, string.Format(Resrc.BatchProcessDetails, Resrc.GooBall,
                        balls.LongCount(), changed) + Resrc.ErrorStart + error + Resrc.WarningStart + warning, Owner)
                        .Show();
                Close();
            });
        }

        private void StartTask(object sender, RoutedEventArgs e)
        {
            task.Start();
        }
        private void TryClose(object sender, CancelEventArgs e)
        {
            if (finished || canceled) return;
            e.Cancel = true;
            if (Dialog.YesNoQuestion(this, Resrc.BatchProcessCancelConfirm, Resrc.BatchProcessCancelConfirmDetails))
                canceled = true;
        }
    }
}
