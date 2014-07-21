using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Security.Cryptography.X509Certificates;
using System.Security.Principal;
using System.Windows;
using Microsoft.Win32;

namespace Mygod.WorldOfGoo.Cursor.Installer
{
    static class Program
    {
        private static AssemblyName NowAssemblyName { get { return Assembly.GetEntryAssembly().GetName(); } }
        private static string Name { get { return NowAssemblyName.Name; } }
        private static string Version { get { return NowAssemblyName.Version.ToString(); } }
        private static string Title { get { return Name + " V" + Version; } }
        private static readonly string RegistryPath = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                                       RegistryKey = "EnableSecureUIAPaths",
                                       MainProgram = "World of Goo Cursor.exe", Dll = "MygodLibrary.dll", Pdb = ".pdb";

        private static Stream GetResourceStream(string path)
        {
            // ReSharper disable PossibleNullReferenceException
            return Application.GetResourceStream(new Uri('/' + path, UriKind.Relative)).Stream;
            // ReSharper restore PossibleNullReferenceException
        }
        private static byte[] ReadResourceBytes(string path)
        {
            try
            {
                var reader = new BinaryReader(GetResourceStream(path));
                return reader.ReadBytes((int)(reader.BaseStream.Length));
            }
            catch
            {
                return null;
            }
        }
        private static void ExtractResource(string path)
        {
            using (var stream = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read))
                GetResourceStream(path).CopyTo(stream);
        }

        private static void Main()
        {
            Console.Write(@"You're going to install {0}.
The following changes will be applied:
    1. Files will be extracted to current working directory.
    2. The annoying security setting will be disabled - User Account Control: Only elevate UIAccess applications that are installed in secure locations.
    3. Our awesome certificate will be installed to the Trusted Root Certificate Authority.
You can revert the changes by clicking Uninstall in the application.

Now press Enter to start install, or press any key else to abort.",
                          (Console.Title = Title).Replace(" Installer", string.Empty));
            var ch = Console.ReadKey().Key;
            Console.WriteLine();
            if (ch != ConsoleKey.Enter)
            {
                Console.WriteLine("Installation aborted.");
                return;
            }
            Console.WriteLine("Extracting files...");
            ExtractResource(MainProgram);
            ExtractResource(Path.GetFileNameWithoutExtension(MainProgram) + Pdb);
            ExtractResource(Dll);
            ExtractResource(Path.GetFileNameWithoutExtension(Dll) + Pdb);
            Console.WriteLine("Disabling the annoying security setting...");
            using (var key = Registry.LocalMachine.OpenSubKey(RegistryPath, true) ??
                             Registry.LocalMachine.CreateSubKey(RegistryPath))
            {
                var val = (int) key.GetValue(RegistryKey, -1);
                if (val != 0)
                {
                    key.SetValue(RegistryKey + "_WoGCursor", val);  // backup
                    key.SetValue(RegistryKey, 0);
                }
            }
            Console.WriteLine("Installing our awesome certificate...");
            if (new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator))
            {
                var store = new X509Store(StoreName.Root, StoreLocation.LocalMachine);
                store.Open(OpenFlags.ReadWrite);
                store.Add(new X509Certificate2(ReadResourceBytes("Mygod.cer")));
                store.Close();
            }
            Console.Write(@"Installation completed. You can delete the installer if you want. ;)
Press Enter to launch the application, press any key else to exit.");
            ch = Console.ReadKey().Key;
            Console.WriteLine();
            if (ch == ConsoleKey.Enter) Process.Start(MainProgram);
        }
    }
}
