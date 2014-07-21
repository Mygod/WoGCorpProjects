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
                    return Check == null || Check(EnterBox.Text);
                }
                catch
                {
                    return false;
                }
            }
        }

        private bool IsValid()
        {
            switch (Type)
            {
                case EnterType.String:
                    return ValidCheck;
                case EnterType.Int32:
                    int i;
                    return int.TryParse(EnterBox.Text, out i) && ValidCheck;
                case EnterType.Double:
                    double j;
                    return double.TryParse(EnterBox.Text, out j) && ValidCheck;
                case EnterType.Directory:
                    return Directory.Exists(EnterBox.Text) && ValidCheck;
                default:
                    return false;
            }
        }

        private void CheckValid(object sender, RoutedEventArgs e)
        {
            try
            {
                // ReSharper disable ReturnValueOfPureMethodIsNotUsed
                if (Type == EnterType.Int32) int.Parse(EnterBox.Text);
                if (Type == EnterType.Double) double.Parse(EnterBox.Text);
                // ReSharper restore ReturnValueOfPureMethodIsNotUsed
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
