using System;
using System.IO;
using System.Windows;
using Microsoft.WindowsAPICodePack.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI.Dialogs
{
    public sealed partial class EnterDialog
    {
        public EnterDialog()
        {
            InitializeComponent();
        }

        public bool Accepted;
        public EnterType Type;
        public Func<string, bool> Check;

        public string Value
        {
            get
            {
                switch (Type)
                {
                    case EnterType.Int32:
                        return Int32Box.Text;
                    case EnterType.Double:
                        return DoubleBox.Text;
                    default:
                        return EnterBox.Text;
                }
            }
            set
            {
                switch (Type)
                {
                    case EnterType.Int32:
                        Int32Box.Text = value;
                        break;
                    case EnterType.Double:
                        DoubleBox.Text = value;
                        break;
                    default:
                        EnterBox.Text = value;
                        break;
                }
            }
        }

        private void Load(object sender, RoutedEventArgs e)
        {
            EnterBox.SelectAll();
            EnterBox.Focus();
        }

        private void Accept(object sender, RoutedEventArgs e)
        {
            CheckValid(sender, e);
            if (!IsValid()) return;
            Accepted = true;
            Close();
        }

        private void Cancel(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private bool ValidCheck
        {
            get
            {
                try
                {
                    return Check == null || Check(Value);
                }
                catch
                {
                    return false;
                }
            }
        }

        private bool IsValid()
        {
            if (Type == EnterType.Directory && !Directory.Exists(EnterBox.Text)) return false;
            return ValidCheck;
        }

        private void CheckValid(object sender, RoutedEventArgs e)
        {
            try
            {
                if (Type == EnterType.Directory) new DirectoryInfo(EnterBox.Text).GetAccessControl();
                if (!ValidCheck) throw new FormatException(Resrc.IncorrectInput);
                OKButton.IsEnabled = true;
                ErrorMessage.Text = null;
                ErrorMessage.Visibility = Visibility.Collapsed;
            }
            catch (Exception exc)
            {
                OKButton.IsEnabled = false;
                ErrorMessage.Text = exc.Message;
                ErrorMessage.Visibility = Visibility.Visible;
            }
        }

        private void Browse(object sender, RoutedEventArgs e)
        {
            if (Type != EnterType.Directory) return;
            var browser = new CommonOpenFileDialog { Title = Title, IsFolderPicker = true };
            if (browser.ShowDialog() == CommonFileDialogResult.Ok) EnterBox.Text = browser.FileName;
        }
    }

    public enum EnterType
    {
        Int32, Double, String, Directory
    }
}
