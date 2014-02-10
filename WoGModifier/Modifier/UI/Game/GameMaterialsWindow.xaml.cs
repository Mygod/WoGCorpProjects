using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using Mygod.WorldOfGoo.IO;
using Mygod.WorldOfGoo.Modifier.UI.Dialogs;

namespace Mygod.WorldOfGoo.Modifier.UI
{
    internal partial class GameMaterialsWindow
    {
        public GameMaterialsWindow(Game g)
        {
            DataContext = game = g;
            InitializeComponent();
            MaterialGrid.ItemsSource = game.Properties.Materials;
        }

        private void BlockClosing(object sender, CancelEventArgs e)
        {
            if (Program.Closing) return;
            e.Cancel = true;
            Hide();
        }

        private readonly Game game;
        private IEnumerable<Material> SelectedMaterials { get { return MaterialGrid.SelectedItems.OfType<Material>(); } }

        private void MaterialSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = MaterialGrid.SelectedItem != null;
        }

        private void SingleMaterialSelected(object sender, CanExecuteRoutedEventArgs e)
        {
            e.CanExecute = MaterialGrid.SelectedItems.Count == 1;
        }

        private void SaveMaterials(object sender = null, ExecutedRoutedEventArgs e = null)
        {
            game.Properties.Materials.Save();
        }

        private void AddMaterial(object sender, ExecutedRoutedEventArgs e)
        {
            var id = Dialog.Input(Resrc.EnterIDTitle, validCheck: i => !game.Properties.Materials.Contains(i));
            if (id != null) game.Properties.Materials.Add(new Material(game.Properties.Materials, id));
        }

        private void CopyMaterial(object sender, ExecutedRoutedEventArgs e)
        {
            var material = SelectedMaterials.FirstOrDefault();
            if (material == null) return;
            var id = Dialog.Input(Resrc.EnterIDTitle, material.ID, validCheck: i => !game.Properties.Materials.Contains(i));
            if (id != null) game.Properties.Materials.Add(new Material(material, id));
        }

        private void RemoveMaterials(object sender, ExecutedRoutedEventArgs e)
        {
            foreach (var material in SelectedMaterials.ToList()) game.Properties.Materials.Remove(material);
        }

        private void EditMaterialsXml(object sender, RoutedEventArgs e)
        {
            BinaryFile.Edit(game.Properties.Materials, Settings.BinFileEditor);
        }

        private void TestMaterial(object sender, RoutedEventArgs e)
        {
            var material = SelectedMaterials.FirstOrDefault();
            if (material == null) return;
            SaveMaterials();
            Kernel.Execute(game, Features.MaterialTester.CreateAt(game.Res.Levels, sceneArgs: new object[] { material.ID }));
        }

        private void EditMaterialsFriction(object sender, ExecutedRoutedEventArgs e)
        {
            var str = Dialog.Input(Resrc.EnterNewValueTitle, SelectedMaterials.First().Friction.ToString(), EnterType.Double);
            if (str == null) return;
            var value = double.Parse(str);
            foreach (var material in SelectedMaterials) material.Friction = value;
        }

        private void EditMaterialsBounce(object sender, ExecutedRoutedEventArgs e)
        {
            var str = Dialog.Input(Resrc.EnterNewValueTitle, SelectedMaterials.First().Bounce.ToString(), EnterType.Double);
            if (str == null) return;
            var value = double.Parse(str);
            foreach (var material in SelectedMaterials) material.Bounce = value;
        }

        private void EditMaterialsMinimumBounceVelocity(object sender, ExecutedRoutedEventArgs e)
        {
            var str = Dialog.Input(Resrc.EnterNewValueTitle, SelectedMaterials.First().MinimumBounceVelocity.ToString(), EnterType.Double);
            if (str == null) return;
            var value = double.Parse(str);
            foreach (var material in SelectedMaterials) material.MinimumBounceVelocity = value;
        }

        private void EditMaterialsStickiness(object sender, ExecutedRoutedEventArgs e)
        {
            var str = Dialog.Input(Resrc.EnterNewValueTitle, SelectedMaterials.First().Stickiness.ToString(), EnterType.Double);
            if (str == null) return;
            var value = double.Parse(str);
            foreach (var material in SelectedMaterials) material.Stickiness = value;
        }
    }
}
