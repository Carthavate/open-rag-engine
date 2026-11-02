using System.IO;
using System.Windows;
using System.Windows.Threading;
using OpenRag.Core;

namespace OpenRag.App;

public partial class App : Application
{
    /// <summary>Opens the window, unless Open RAG is already running. Unexpected errors are written down and
    /// the window kept alive, instead of closing without a trace.</summary>
    protected override void OnStartup(StartupEventArgs e)
    {
        if (!SingleInstance.Claim())
        {
            Shutdown();
            return;
        }
        DispatcherUnhandledException += OnUnhandled;
        base.OnStartup(e);
        new MainWindow().Show();
    }

    private static void OnUnhandled(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        var log = AppPaths.Default.ErrorLog;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(log)!);
            File.AppendAllText(log, $"{DateTime.Now:u} {e.Exception}\n\n");
        }
        catch (Exception logError) when (logError is IOException or UnauthorizedAccessException)
        {
            // Nowhere to write it; the message box below still tells the user.
        }
        MessageBox.Show($"Something went wrong, but Open RAG kept running.\n\n{e.Exception.Message}\n\nDetails: {log}", "Open RAG");
        e.Handled = true;
    }
}
