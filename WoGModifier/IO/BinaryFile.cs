using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.IO
{
    public static class BinaryFile
    {
        private static readonly byte[] ProfileKey =
        {
            0x0D, 0x06, 0x07, 0x07, 0x0C, 0x01, 0x08, 0x05, 0x06, 0x09, 0x09, 0x04,
            0x06, 0x0D, 0x03, 0x0F, 0x03, 0x06, 0x0E, 0x01, 0x0E, 0x02, 0x07, 0x0B
        };
        private static readonly AesManaged Aes = 
            new AesManaged { Key = ProfileKey, Mode = CipherMode.CBC, IV = new byte[16], Padding = PaddingMode.None };

        private static string Decrypt(byte[] data, bool isXml = true) 
        {
            data = Aes.CreateDecryptor().TransformFinalBlock(data, 0, data.Length);
            var result = Encoding.UTF8.GetString(data).TrimStart('\uFEFF');
            if (!isXml) return result.TrimEnd('\uFFFD', '\0');
            var first = true;
            do
            {
                if (!first) result = result.Substring(0, result.Length - 1);
                var r = result.LastIndexOf('>');
                if (r < 0) throw new ArgumentException(Resrc.DecryptDataError, "data");
                result = result.Substring(0, r + 1);
                first = false;
            } while (!char.IsLetter(result[result.Length - 2]) && !char.IsSymbol(result[result.Length - 2]) 
                  && !char.IsSeparator(result[result.Length - 2]) && result[result.Length - 2] != '/');
            return result;
        }

        private static byte[] Encrypt(string data)
        {
            var list = Encoding.UTF8.GetBytes(data.TrimStart('\uFEFF')).ToList();
            var add = 0;
            while ((list.LongCount() & 15) != 0)
            {
                add++;
                list.Add((byte)(add > 4 ? 0xFD : 0));
            }
            return Aes.CreateEncryptor().TransformFinalBlock(list.ToArray(), 0, list.Count());
        }

        public static string ReadAllText(string path, bool isXml = true)
        {
            return Decrypt(File.ReadAllBytes(path), isXml);
        }

        public static void WriteAllText(string path, string text)
        {
            File.WriteAllBytes(path, Encrypt(text));
        }

        private static readonly HashSet<string> OpenedPaths = new HashSet<string>();

        public static void Edit(string path, string editorPath, bool isXml = true, bool ignoreErrors = false)
        {
            var target = path;
            try
            {
                if (path.ToLowerInvariant().EndsWith(".bin", StringComparison.Ordinal))
                    target = path.Substring(0, path.Length - 4);
                if (isXml && !target.ToLowerInvariant().EndsWith(".xml", StringComparison.Ordinal)) target += ".xml";
                if (target == path) if (isXml) target += ".xml"; else target += ".txt";
                if (OpenedPaths.Contains(target)) return;
                OpenedPaths.Add(target);
                using (var writer = new StreamWriter(target)) writer.Write(ReadAllText(path, isXml));
                new Thread((() =>
                {
                    FileSystemWatcher watcher = null;
                    try
                    {
                        var editor = Process.Start(editorPath, target);
                        // ReSharper disable AssignNullToNotNullAttribute
                        watcher = new FileSystemWatcher(Path.GetDirectoryName(target), Path.GetFileName(target))
                            { EnableRaisingEvents = true };
                        // ReSharper restore AssignNullToNotNullAttribute
                        watcher.Changed += (sender, e) =>
                        {
                        retry:
                            try
                            {
                                using (var reader = new StreamReader(target)) WriteAllText(path, reader.ReadToEnd());
                            }
                            catch (IOException)
                            {
                                Trace.WriteLine(string.Format("Retry at Thread {0}",
                                                              Thread.CurrentThread.ManagedThreadId));
                                goto retry;
                            }
                        };
                        if (editor != null) editor.WaitForExit();
                    }
                    finally
                    {
                        if (watcher != null) watcher.Dispose();
                    retryDelete:
                        try
                        {
                            if (File.Exists(target)) File.Delete(target);
                        }
                        catch
                        {
                            goto retryDelete;
                        }
                        OpenedPaths.Remove(target);
                    }
                })).Start();
            }
            catch (Exception e)
            {
                if (!ignoreErrors) Dialog.Error(null, Resrc.ErrorOnBinaryFileEdit, e: e);
                File.Delete(target);
            }
        }
        public static void Edit(IGameBinFile file, string editorPath)
        {
            Edit(file.FilePath, editorPath, false);
        }
        public static void Edit(IGameBinXmlFile file, string editorPath)
        {
            Edit(file.FilePath, editorPath);
        }
    }
}
