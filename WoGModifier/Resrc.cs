using System;
using System.Reflection;
using Mygod.WorldOfGoo.Modifier;

namespace Mygod.WorldOfGoo
{
    static class Resrc
    {
        private static string GetString(object key)
        {
            try
            {
                return (Program.App.TryFindResource(key) ?? String.Empty).ToString()
                    .Replace("%N", "\n").Replace("%T", "\t").Replace("%%", "%");
            }
            catch (NullReferenceException) { return null; }
        }

        private static AssemblyName NowAssemblyName { get { return Assembly.GetCallingAssembly().GetName(); } }
        public static string ProgramName { get { return GetString("ProgramName"); } }
        public static string Title
            { get { return ProgramName + " V" + NowAssemblyName.Version + GetString("Version"); } }

        public static string Ask { get { return GetString("Ask"); } }
        public static string Backup { get { return GetString("Backup"); } }
        public static string Byte { get { return GetString("Byte"); } }
        public static string Continue { get { return GetString("Continue"); } }
        public static string DefaultText { get { return GetString("DefaultText"); } }
        public static string Delete { get { return GetString("Delete"); } }
        public static string Details { get { return GetString("Details"); } }
        public static string Error { get { return GetString("Error"); } }
        public static string Failed { get { return GetString("Failed"); } }
        public static string Finish { get { return GetString("Finish"); } }
        public static string GooBall { get { return GetString("GooBall"); } }
        public static string Information { get { return GetString("Information"); } }
        public static string Level { get { return GetString("Level"); } }
        public static string PlayerSharp { get { return GetString("PlayerSharp"); } }
        public static string Properties { get { return GetString("Properties"); } }
        public static string Reselect { get { return GetString("Reselect"); } }
        public static string Restore { get { return GetString("Restore"); } }
        public static string UnknownLanguage { get { return GetString("UnknownLanguage"); } }

        public static string FatalBreak { get { return GetString("FatalBreak"); } }
        public static string FatalBreakInstructions { get { return GetString("FatalBreakInstructions"); } }
        public static string FatalContinue { get { return GetString("FatalContinue"); } }
        public static string FatalContinueInstructions { get { return GetString("FatalContinueInstructions"); } }
        public static string FatalRestart { get { return GetString("FatalRestart"); } }
        public static string FatalRestartInstructions { get { return GetString("FatalRestartInstructions"); } }
        public static string No { get { return GetString("No"); } }
        public static string OK { get { return GetString("OK"); } }
        public static string Overwrite { get { return GetString("Overwrite"); } }
        public static string RestoreButton { get { return GetString("RestoreButton"); } }
        public static string Yes { get { return GetString("Yes"); } }

        public static string AboutDetails { get { return GetString("AboutDetails"); } }
        public static string BackupSameVolume { get { return GetString("BackupSameVolume"); } }
        public static string BackupSameVolumeDetails { get { return GetString("BackupSameVolumeDetails"); } }
        public static string BackupSuccessfully { get { return GetString("BackupSuccessfully"); } }
        public static string BatchProcessCancelConfirm { get { return GetString("BatchProcessCancelConfirm"); } }
        public static string BatchProcessCancelConfirmDetails
            { get { return GetString("BatchProcessCancelConfirmDetails"); } }
        public static string BatchProcessError { get { return GetString("BatchProcessError"); } }
        public static string BatchProcessFinish { get { return GetString("BatchProcessFinish"); } }
        public static string BatchProcessFinishInstruction
            { get { return GetString("BatchProcessFinishInstruction"); } }
        public static string BatchProcessFinishText { get { return GetString("BatchProcessFinishText"); } }
        public static string BatchProcessLog { get { return GetString("BatchProcessLog"); } }
        public static string BatchProcessSuccessfully { get { return GetString("BatchProcessSuccessfully"); } }
        public static string BatchProcessWarning { get { return GetString("BatchProcessWarning"); } }
        public static string CopyBackupsConfirm { get { return GetString("CopyBackupsConfirm"); } }
        public static string CopyFailed { get { return GetString("CopyFailed"); } }
        public static string DecryptDataError { get { return GetString("DecryptDataError"); } }
        public static string DefaultModifiedXml { get { return GetString("DefaultModifiedXml"); } }
        public static string DeleteBackupConfirm { get { return GetString("DeleteBackupConfirm"); } }
        public static string DeleteBackupInstruction { get { return GetString("DeleteBackupInstruction"); } }
        public static string DeleteBackupSuccessfully { get { return GetString("RestoreBackupSuccessfully"); } }
        public static string DeleteBackupText { get { return GetString("DeleteBackupText"); } }
        public static string DeleteConfirm { get { return GetString("DeleteConfirm"); } }
        public static string DeleteConfirmDetails { get { return GetString("DeleteConfirmDetails"); } }
        public static string DragFile { get { return GetString("DragFile"); } }
        public static string EditBackupsDirectorySuccessfully
            { get { return GetString("EditBackupsDirectorySuccessfully"); } }
        public static string EnterSkipEndOfLevelSequenceInstruction
            { get { return GetString("EnterSkipEndOfLevelSequenceInstruction"); } }
        public static string ErrorDetailsLabel { get { return GetString("ErrorDetailsLabel"); } }
        public static string FailedLoadingGame { get { return GetString("FailedLoadingGame"); } }
        public static string FailedLoadingProfile { get { return GetString("FailedLoadingProfile"); } }
        public static string Fatal { get { return GetString("Fatal"); } }
        public static string FeaturesParseError { get { return GetString("FeaturesParseError"); } }
        public static string FeaturesParseErrorDetails { get { return GetString("FeaturesParseErrorDetails"); } }
        public static string GameAlreadyRunning { get { return GetString("GameAlreadyRunning"); } }
        public static string GarbageCleanupDone { get { return GetString("GarbageCleanupDone"); } }
        public static string GarbageCleanupDetails { get { return GetString("GarbageCleanupDetails"); } }
        public static string GenerateOnlinePlayerKeyEmptyResponse
            { get { return GetString("GenerateOnlinePlayerKeyEmptyResponse"); } }
        public static string GenerateOnlinePlayerKeyFailed
            { get { return GetString("GenerateOnlinePlayerKeyFailed"); } }
        public static string GenerateOnlinePlayerKeyInstruction
            { get { return GetString("GenerateOnlinePlayerKeyInstruction"); } }
        public static string GenerateOnlinePlayerKeyInvalidResponse
            { get { return GetString("GenerateOnlinePlayerKeyInvalidResponse"); } }
        public static string GenerateOnlinePlayerKeyProcessFailed
            { get { return GetString("GenerateOnlinePlayerKeyProcessFailed"); } }
        public static string GenerateOnlinePlayerKeyText { get { return GetString("GenerateOnlinePlayerKeyText"); } }
        public static string IncorrectInput { get { return GetString("IncorrectInput"); } }
        public static string NoModifiedRecordFound { get { return GetString("NoModifiedRecordFound"); } }
        public static string OpenBinFileFilter { get { return GetString("OpenBinFileFilter"); } }
        public static string OpenBinFileTitle { get { return GetString("OpenBinFileTitle"); } }
        public static string OpenFileFilter { get { return GetString("OpenFileFilter"); } }
        public static string OpenFileTitle { get { return GetString("OpenFileTitle"); } }
        public static string OpenProgramTitle { get { return GetString("OpenProgramTitle"); } }
        public static string OpenProgramFilter { get { return GetString("OpenProgramFilter"); } }
        public static string OverwriteConfirm { get { return GetString("OverwriteConfirm"); } }
        public static string OverwriteBackupInstruction { get { return GetString("OverwriteBackupInstruction"); } }
        public static string OverwriteBackupText { get { return GetString("OverwriteBackupText"); } }
        public static string OverwritePlayerInstruction { get { return GetString("OverwritePlayerInstruction"); } }
        public static string OverwritePlayerText { get { return GetString("OverwritePlayerText"); } }
        public static string PastePlayerError { get { return GetString("PastePlayerError"); } }
        public static string PasteToInstruction { get { return GetString("PasteToInstruction"); } }
        public static string PlayMusicError { get { return GetString("PlayMusicError"); } }
        public static string PlayerLevelsTotal { get { return GetString("PlayerLevelsTotal"); } }
        public static string ProfileLoadBoth { get { return GetString("ProfileLoadBoth"); } }
        public static string ProfileNewVersion { get { return GetString("ProfileNewVersion"); } }
        public static string ProfileNotSavedInstruction { get { return GetString("ProfileNotSavedInstruction"); } }
        public static string ProfileNotSavedText { get { return GetString("ProfileNotSavedText"); } }
        public static string ProfileOldVersion { get { return GetString("ProfileOldVersion"); } }
        public static string RemainingTime { get { return GetString("RemainingTime"); } }
        public static string RenameSuccessfully { get { return GetString("RenameSuccessfully"); } }
        public static string RestoreBackupConfirm { get { return GetString("RestoreBackupConfirm"); } }
        public static string RestoreBackupInstruction { get { return GetString("RestoreBackupInstruction"); } }
        public static string RestoreBackupSuccessfully { get { return GetString("RestoreBackupSuccessfully"); } }
        public static string RestoreBackupText { get { return GetString("RestoreBackupText"); } }
        public static string SaveProfileFilter { get { return GetString("SaveProfileFilter"); } }
        public static string SaveProfileTitle { get { return GetString("SaveProfileTitle"); } }
        public static string SearchProfileFailed { get { return GetString("SearchProfileFailed"); } }
        public static string SearchProfileFinished { get { return GetString("SearchProfileFinished"); } }
        public static string SearchProfileText { get { return GetString("SearchProfileText"); } }
        public static string TestSelectedGooBalls { get { return GetString("TestSelectedGooBalls"); } }
        public static string UsedTime { get { return GetString("UsedTime"); } }
        public static string WelcomeUseTitle { get { return GetString("WelcomeUseTitle"); } }
        public static string WelcomeUse { get { return GetString("WelcomeUse"); } }
        public static string WoGCorpBallDetails { get { return GetString("WoGCorpBallDetails"); } }
        public static string XslTransformFailed { get { return GetString("XslTransformFailed"); } }

        public static string BatchProcessDetails { get { return GetString("BatchProcessDetails"); } }
        public static string EditDetails { get { return GetString("EditDetails"); } }
        public static string EnterSkipEndOfLevelSequenceText
            { get { return GetString("EnterSkipEndOfLevelSequenceText"); } }
        public static string ErrorDetails { get { return GetString("ErrorDetails"); } }
        public static string ErrorStart { get { return GetString("ErrorStart"); } }
        public static string FeatureEditDetails { get { return GetString("FeatureEditDetails"); } }
        public static string ProcessingDetails { get { return GetString("ProcessingDetails"); } }
        public static string PropertiesConfigFile { get { return GetString("PropertiesConfigFile"); } }
        public static string WarningDetails { get { return GetString("WarningDetails"); } }
        public static string WarningStart { get { return GetString("WarningStart"); } }

        public static string JumpListCategory { get { return GetString("JumpListCategory"); } }
        public static string JumpListSelectBinFiles { get { return GetString("JumpListSelectBinFiles"); } }
        public static string JumpListTechSupport { get { return GetString("JumpListTechSupport"); } }

        public static string ExceptionFeaturesXmlVersionIncorrect
            { get { return GetString("ExceptionFeaturesXmlVersionIncorrect"); } }
        public static string ExceptionXmlElementDoesNotExist
            { get { return GetString("ExceptionXmlElementDoesNotExist"); } }
        public static string ExceptionXmlAttributeDoesNotExist
            { get { return GetString("ExceptionXmlAttributeDoesNotExist"); } }
        public static string ExceptionXmlElementCannotRecognize
            { get { return GetString("ExceptionXmlElementCannotRecognize"); } }

        public static string ErrorOnBinaryFileEdit { get { return GetString("ErrorOnBinaryFileEdit"); } }
        public static string ErrorGooBallsTesterPositiveIntegerRequired
            { get { return GetString("ErrorGooBallsTesterPositiveIntegerRequired"); } }
        public static string ErrorGooBallsTesterNotExist { get { return GetString("ErrorGooBallsTesterNotExist"); } }
        public static string WarningGooBallsTesterCountGreaterThan1000
            { get { return GetString("WarningGooBallsTesterCountGreaterThan1000"); } }
        public static string WarningGooBallsTesterCountGreaterThan20000
            { get { return GetString("WarningGooBallsTesterCountGreaterThan20000"); } }
        public static string ErrorGooBallsTesterCountGreaterThan500000
            { get { return GetString("ErrorGooBallsTesterCountGreaterThan500000"); } }

        public static string EnterBackupsDirectoryTitle { get { return GetString("EnterBackupsDirectoryTitle"); } }
        public static string EnterBackupNameTitle { get { return GetString("EnterBackupNameTitle"); } }
        public static string EnterIslandToCopyNumber { get { return GetString("EnterIslandToCopyNumber"); } }
        public static string EnterIDTitle { get { return GetString("EnterIDTitle"); } }
        public static string EnterNewValueTitle { get { return GetString("EnterNewValueTitle"); } }

        public static string GiveUp { get { return GetString("GiveUp"); } }
        public static string Save { get { return GetString("Save"); } }
    }
}
