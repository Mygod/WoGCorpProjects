using System;
using System.Collections;
using System.Windows;
using Microsoft.WindowsAPICodePack.Dialogs;
using Mygod.Windows.Controls;
using Mygod.WorldOfGoo.Modifier.IO;

namespace Mygod.WorldOfGoo.Modifier.UI.Dialogs
{
    public static class Dialog
    {
        public static void Information(Window parent, string instruction, string text = null, string title = null)
        {
            new TaskDialog
            {
                OwnerWindowHandle = parent.GetHwnd(), InstructionText = instruction, Text = text,
                Caption = title ?? Resrc.Information, Icon = TaskDialogStandardIcon.Information,
                StandardButtons = TaskDialogStandardButtons.Ok
            }.Show();
        }

        public static void Finish(Window parent, string instruction, string text = null)
        {
            Information(parent, instruction, text, Resrc.Finish);
        }

        public static void Error(Window parent, string pos, string details = null, Exception e = null,
                                 EventHandler<TaskDialogHyperlinkClickedEventArgs> linkClicked = null)
        {
            Log.Error.Write(e);
            var dialog = new TaskDialog
            {
                Caption = Resrc.Error, InstructionText = pos, Text = details, Icon = TaskDialogStandardIcon.Error,
                OwnerWindowHandle = parent.GetHwnd(), StandardButtons = TaskDialogStandardButtons.Close
            };
            if (e != null)
            {
                dialog.DetailsCollapsedLabel = dialog.DetailsExpandedLabel = Resrc.ErrorDetailsLabel;
                dialog.DetailsExpandedText = e.Message;
            }
            if (linkClicked != null)
            {
                dialog.HyperlinksEnabled = true;
                dialog.HyperlinkClick += linkClicked;
            }
            dialog.Show();
        }

        public static TaskDialogResult Fatal(Exception exc)
        {
            Log.Crash.Write(exc);
            TaskDialogCommandLink
                breakLink = new TaskDialogCommandLink("Break", Resrc.FatalBreak, Resrc.FatalBreakInstructions),
                restartLink = new TaskDialogCommandLink("Restart", Resrc.FatalRestart, Resrc.FatalRestartInstructions),
                continueLink = new TaskDialogCommandLink("Continue", Resrc.FatalContinue,
                                                         Resrc.FatalContinueInstructions);
            var dialog = new TaskDialog
            {
                Caption = Resrc.Error, InstructionText = Resrc.Fatal, Cancelable = true,
                Icon = TaskDialogStandardIcon.Error, DetailsExpandedText = exc.Message,
                DetailsCollapsedLabel = Resrc.ErrorDetailsLabel, DetailsExpandedLabel = Resrc.ErrorDetailsLabel,
                DefaultButtonId = breakLink.Id, Controls = { breakLink, restartLink, continueLink }
            };
            breakLink.Click += (sender, e) => dialog.Close(TaskDialogResult.Cancel);
            restartLink.Click += (sender, e) => dialog.Close(TaskDialogResult.Yes);
            continueLink.Click += (sender, e) => dialog.Close(TaskDialogResult.No);
            return dialog.Show();
        }

        internal static string Input(string title, string defaultValue = null, EnterType enterType = EnterType.String, 
                                     Func<string, bool> validCheck = null, IEnumerable list = null,
                                     string displayMemberPath = null, 
                                     AutoCompleteFilterMode filterMode = AutoCompleteFilterMode.Contains,
                                     int? min = null, int? max = null)
        {
            var dialog = new EnterDialog
            {
                Title = title, Accepted = false, Type = enterType, Check = validCheck, Value = defaultValue,
                EnterBox =
                {
                    ItemsSource = list, FilterMode = filterMode, 
                    ItemTemplate = DataGridAutoCompleteColumn.GetItemTemplate(displayMemberPath),
                    Visibility = enterType == EnterType.Int32 || enterType == EnterType.Double
                                    ? Visibility.Visible : Visibility.Collapsed
                },
                Int32Box =
                {
                    Visibility = enterType == EnterType.Int32 ? Visibility.Visible : Visibility.Collapsed,
                    Minimum = min, Maximum = max
                },
                DoubleBox = { Visibility = enterType == EnterType.Double ? Visibility.Visible : Visibility.Collapsed },
                BrowseButton =
                {
                    Visibility = enterType == EnterType.Directory ? Visibility.Visible : Visibility.Collapsed
                }
            };
            dialog.ShowDialog();
            return dialog.Accepted ? dialog.Value : null;
        }

        public static bool YesNoQuestion(Window parent, string instruction, string text = null, string title = null,
                                         string yesText = null, string noText = null, bool yesDefault = true)
        {
            TaskDialogButton yesButton = new TaskDialogButton("Yes", yesText ?? Resrc.Yes),
                             noButton = new TaskDialogButton("No", noText ?? Resrc.No);
            var dialog = new TaskDialog
            {
                Caption = title ?? Resrc.Ask, InstructionText = instruction, Text = text,
                OwnerWindowHandle = parent.GetHwnd(), Icon = TaskDialogStandardIcon.Information,
                DefaultButtonId = yesDefault ? yesButton.Id : noButton.Id, Controls = { yesButton, noButton }
            };
            yesButton.Click += (sender, e) => dialog.Close(TaskDialogResult.Yes);
            noButton.Click += (sender, e) => dialog.Close(TaskDialogResult.No);
            return dialog.Show() == TaskDialogResult.Yes;
        }

        public static bool? YesNoCancelQuestion(Window parent, string instruction, string text = null,
                                                string title = null, string yesText = null, string noText = null,
                                                bool yesDefault = true)
        {
            TaskDialogButton yesButton = new TaskDialogButton("Yes", yesText ?? Resrc.Yes),
                             noButton = new TaskDialogButton("No", noText ?? Resrc.No);
            var dialog = new TaskDialog
            {
                Caption = title ?? Resrc.Ask, InstructionText = instruction, Text = text, Cancelable = true,
                OwnerWindowHandle = parent.GetHwnd(), Icon = TaskDialogStandardIcon.Information,
                DefaultButtonId = yesDefault ? yesButton.Id : noButton.Id, Controls = { yesButton, noButton },
                StandardButtons = TaskDialogStandardButtons.Cancel
            };
            yesButton.Click += (sender, e) => dialog.Close(TaskDialogResult.Yes);
            noButton.Click += (sender, e) => dialog.Close(TaskDialogResult.No);
            switch (dialog.Show())
            {
                case TaskDialogResult.Yes: return true;
                case TaskDialogResult.No: return false;
                default: return null;
            }
        }

        public static bool OKCancelQuestion(Window parent, string instruction, string text = null, string title = null, 
                                            string okText = null)
        {
            var button = new TaskDialogButton("OK", okText ?? Resrc.OK);
            var dialog = new TaskDialog
            {
                Caption = title ?? Resrc.Ask, InstructionText = instruction, Text = text, Cancelable = true,
                OwnerWindowHandle = parent.GetHwnd(), Icon = TaskDialogStandardIcon.Information,
                DefaultButtonId = button.Id, Controls = { button }, StandardButtons = TaskDialogStandardButtons.Cancel
            };
            button.Click += (sender, e) => dialog.Close(TaskDialogResult.Ok);
            return dialog.Show() == TaskDialogResult.Ok;
        }
    }
}
