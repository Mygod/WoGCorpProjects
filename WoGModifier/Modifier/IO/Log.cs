using System;
using System.IO;
using Mygod.Windows;

namespace Mygod.WorldOfGoo.Modifier.IO
{
    class Log : IDisposable
    {
        private Log(string logFile, bool isMain = false)
        {
            fileName = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, logFile);
            writer = new StreamWriter(fileName, true) { AutoFlush = true };
            isCurrentMain = isMain;
            if (!isMain) return;
            writer.WriteLine("[{1}]\t{0} started to run. (Compiled at {2})",
                             CurrentApp.Title, DateTime.Now - Program.StartupTime.Elapsed, CurrentApp.CompilationTime);
            writer.WriteLine("\t\t\tProcess Path: " + CurrentApp.FileName);
            writer.WriteLine("\t\t\tOperating System: " + Environment.OSVersion);
        }

        public static void Initialize()
        {
            Error = new Log("error.log");
            Crash = new Log("crash.log");
            Performance = new Log("performance.log", true);
        }

        public void Dispose()
        {
            if (isCurrentMain) writer.WriteLine("[{1}]\t{0} has been run for {2}.", CurrentApp.Title, DateTime.Now,
                                                Program.StartupTime.Elapsed);
            writer.WriteLine();
            writer.Dispose();
        }

        private readonly string fileName;
        private StreamWriter writer;
        private readonly bool isCurrentMain;

        public void Write(Exception e)
        {
            if (e == null) return;
            writer.WriteLine("[{0}] An error has occurred. Details here:", DateTime.Now);
            writer.WriteLine(e.GetMessage());
            writer.WriteLine();
            writer.WriteLine();
        }
        public void Write(string operation, TimeSpan time)
        {
            writer.WriteLine("[{0}]\tOperation <{1}> finished. It took {2} seconds.", DateTime.Now, operation,
                             time.TotalSeconds);
        }
        public long Clear()
        {
            writer.Close();
            var result = new FileInfo(fileName).Length;
            writer = new StreamWriter(fileName) {AutoFlush = true};
            return result;
        }

        public static Log Error;
        public static Log Crash;
        public static Log Performance;
    }
}
