using System;
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

        private void Load(object sender, EventArgs e)
        {
            switch (Type)
            {
                case EnterType.Int32:
                    Int32Box.SelectAll();
                    Int32Box.Focus();
                    break;
                case EnterType.Double:
                    DoubleBox.SelectAll();
                    DoubleBox.Focus();
                    break;
                default:
                    EnterBox.SelectAll();
                    EnterBox.Focus();
                    break;
            }
        }

        private void Accept(object sender, RoutedEventArgs e)
        {
            CheckValid(sender, e);
            if (!ValidCheck) return;
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

        private void CheckValid(object sender, RoutedEventArgs e)
        {
            try
            {
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
