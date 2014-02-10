using System;
using System.Collections;
using System.Windows;
using Mygod.Windows.Controls;
using Mygod.Windows.Dialogs;
using Mygod.WorldOfGoo.Modifier.IO;

namespace Mygod.WorldOfGoo.Modifier.UI.Dialogs
{
    public static class Dialog
    {
        public static void Information(Window parent, string instruction, string text = null, string title = null, string okText = null)
        {
            TaskDialog.Show(new TaskDialogOptions { Owner = parent, MainInstruction = instruction, Content = text, 
                Title = title ?? Resrc.Information, MainIcon = TaskDialogIcon.Information, CustomButtons = new[] { okText ?? Resrc.OK } });
        }

        public static void Finish(Window parent, string instruction, string text = null, string okText = null)
        {
            Information(parent, instruction, text, Resrc.Finish, okText);
        }

        public static void Error(Window parent, string pos, string details = null, Exception e = null)
        {
            Log.Error.Write(e);
            var options = new TaskDialogOptions
            {
                Title = Resrc.Error, MainInstruction = pos, Content = details, MainIcon = TaskDialogIcon.Error, Owner = parent,
                CustomButtons = new[] { Resrc.Close }
            };
            if (e != null)
            {
                options.CollapsedControlText = options.ExpandedControlText = Resrc.ErrorDetailsLabel;
                options.ExpandedInfo = e.Message;
            }
            TaskDialog.Show(options);
        }

        public static int Fatal(Exception e)
        {
            Log.Crash.Write(e);
            return TaskDialog.Show(new TaskDialogOptions { Title = Resrc.Error, MainInstruction = Resrc.Fatal, 
                AllowDialogCancellation = true, MainIcon = TaskDialogIcon.Error, CollapsedControlText = Resrc.ErrorDetailsLabel, 
                ExpandedControlText = Resrc.ErrorDetailsLabel, ExpandedInfo = e.Message, DefaultButtonIndex = 0, 
                CommandButtons = new[] { Resrc.FatalBreak, Resrc.FatalRestart, Resrc.FatalContinue }}).CommandButtonResult ?? 0;
        }

        internal static string Input(string title, string defaultValue = null, EnterType enterType = EnterType.String, 
                                     Func<string, bool> validCheck = null, IEnumerable list = null, string displayMemberPath = null, 
                                     AutoCompleteFilterMode filterMode = AutoCompleteFilterMode.Contains)
        {
            var dialog = new EnterDialog
            {
                Title = title, Accepted = false, Type = enterType, Check = validCheck, 
                EnterBox =
                {
                    Text = defaultValue, ItemsSource = list, FilterMode = filterMode, 
                    ItemTemplate = DataGridAutoCompleteColumn.GetItemTemplate(displayMemberPath)
                }, 
                BrowseButton = {Visibility = enterType == EnterType.Directory ? Visibility.Visible : Visibility.Collapsed}
            };
            dialog.ShowDialog();
            return dialog.Accepted ? dialog.EnterBox.Text : null;
        }

        public static bool YesNoQuestion(Window parent, string instruction, string text = null, string title = null, string yesText = null,
                                         string noText = null, bool yesDefault = true)
        {
            return TaskDialog.Show(new TaskDialogOptions { Title = title ?? Resrc.Ask, MainInstruction = instruction, Content = text, 
                Owner = parent, MainIcon = TaskDialogIcon.Information, DefaultButtonIndex = yesDefault ? 0 : 1, 
                CustomButtons = new[] { yesText ?? Resrc.Yes, noText ?? Resrc.No } }).CustomButtonResult == 0;
        }

        public static bool? YesNoCancelQuestion(Window parent, string instruction, string text = null, string title = null,
                                                string yesText = null, string noText = null, bool yesDefault = true)
        {
            switch (TaskDialog.Show(new TaskDialogOptions { Title = title ?? Resrc.Ask, MainInstruction = instruction, 
                AllowDialogCancellation = true, MainIcon = TaskDialogIcon.Information, DefaultButtonIndex = yesDefault ? 0 : 1, 
                CustomButtons = new[] { yesText ?? Resrc.Yes, noText ?? Resrc.No, Resrc.Cancel }, 
                Content = text, Owner = parent }).CustomButtonResult)
            {
                case 0: return true;
                case 1: return false;
                default: return null;
            }
        }

        public static bool OKCancelQuestion(Window parent, string instruction, string text = null, string title = null, 
                                            string okText = null)
        {
            return TaskDialog.Show(new TaskDialogOptions { Title = title ?? Resrc.Ask, MainInstruction = instruction, Content = text, 
                Owner = parent, MainIcon = TaskDialogIcon.Information, DefaultButtonIndex = 0, 
                CustomButtons = new[] { okText ?? Resrc.OK, Resrc.Cancel } }).CustomButtonResult == 0;
        }
    }
}
