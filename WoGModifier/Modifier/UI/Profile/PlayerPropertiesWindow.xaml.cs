using System;
using System.ComponentModel;
using System.Net;
using System.Windows;
using System.Xml;
using System.Xml.Linq;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    public partial class PlayerPropertiesWindow
    {
        public PlayerPropertiesWindow(ProfilePlayer p)
        {
            DataContext = player = p;
            InitializeComponent();
        }

        private readonly ProfilePlayer player;
        private static readonly Lazy<WebClient> Client = new Lazy<WebClient>();

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }
        
        private void GenerateOnlinePlayerKey(object sender, RoutedEventArgs e)
        {
            if (Dialog.YesNoQuestion(this, Resrc.GenerateOnlinePlayerKeyInstruction, Resrc.GenerateOnlinePlayerKeyText))
                return;
            try
            {
                // ReSharper disable PossibleNullReferenceException
                var s = Client.Value.DownloadString
                    ("https://worldofgoo.com/wogbuddy2.php?hwkey=93540be1cc0a8c61e6ea0f0f3a4b9d47&name=" +
                     Uri.EscapeUriString(player.PlayerName) + "&op=GetPlayerKey&version=1%2e40win");
                if (string.IsNullOrEmpty(s)) throw new WebException(Resrc.GenerateOnlinePlayerKeyEmptyResponse);
                XDocument document;
                try
                {
                    document = XDocument.Parse(s);
                }
                catch (XmlException)
                {
                    throw new WebException(Resrc.GenerateOnlinePlayerKeyInvalidResponse + s);
                }
                var response = document.Element("WogResponse");
                if (response.Attribute("result").Value.ToLower() != "ok")
                    throw new WebException(Resrc.GenerateOnlinePlayerKeyProcessFailed +
                                           response.Attribute("message").Value);
                player.OnlinePlayerKey = response.Element("playerkey").Value;
                player.OnlinePlayEnabled = true;
                // ReSharper restore PossibleNullReferenceException
            }
            catch (Exception exc)
            {
                Dialog.Error(this, Resrc.GenerateOnlinePlayerKeyFailed, e: exc);
            }
        }
    }
}
