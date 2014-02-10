using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows;
using System.Windows.Threading;

namespace Mygod.WorldOfGoo.Cursor
{
    public partial class App
    {
        private void OnStartup(object sender, StartupEventArgs e)
        {
            AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
        }

        private void OnUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
        {
            e.Handled = true;
            OnError(e.Exception);
        }

        private static void OnUnhandledException(object sender, UnhandledExceptionEventArgs e)
        {
            OnError(e.ExceptionObject as Exception);
        }

        private static void OnError(Exception e)
        {
            if (e == null || e is ThreadAbortException) return;
            var msg = e.GetMessage();
            File.WriteAllText("crash.log", msg);
            MessageBox.Show("Something really TERRIBLE happened! Here are the details: (you can see it later in crash.log)"
                            + Environment.NewLine + msg, "ERROR", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    public static class ExceptionHelper
    {
        public static string GetMessage(this Exception e)
        {
            var result = new StringBuilder();
            GetMessage(e, result);
            return result.ToString();
        }

        private static void GetMessage(Exception e, StringBuilder result)
        {
            while (e != null && !(e is AggregateException))
            {
                result.AppendFormat("({0}) {1}{2}{3}{2}", e.GetType(), e.Message, Environment.NewLine, e.StackTrace);
                e = e.InnerException;
            }
            var ae = e as AggregateException;
            if (ae != null) foreach (var ex in ae.InnerExceptions) GetMessage(ex, result);
        }
    }
}
