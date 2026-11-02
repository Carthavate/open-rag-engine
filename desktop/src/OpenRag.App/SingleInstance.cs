using System.Diagnostics;
using System.Runtime.InteropServices;

namespace OpenRag.App;

/// <summary>Keeps Open RAG to one window. A second copy would start a second engine over the same indexes,
/// so opening Open RAG again (a second click on the desktop icon) brings the running window forward instead.</summary>
internal static class SingleInstance
{
    private const string MutexName = @"Local\OpenRag.SingleInstance";
    private const int SwRestore = 9;

    // Held for the life of the process; Windows frees it when Open RAG exits, even after a crash.
    private static Mutex? _claim;

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hwnd);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr hwnd, int command);

    [DllImport("user32.dll")]
    private static extern bool IsIconic(IntPtr hwnd);

    /// <summary>True when no other Open RAG is running. Otherwise shows the running one and returns false.</summary>
    public static bool Claim()
    {
        _claim = new Mutex(initiallyOwned: true, MutexName, out var first);
        if (!first)
        {
            ShowRunningCopy();
        }
        return first;
    }

    private static void ShowRunningCopy()
    {
        using var current = Process.GetCurrentProcess();
        foreach (var other in Process.GetProcessesByName(current.ProcessName))
        {
            using (other)
            {
                var window = other.Id == current.Id ? IntPtr.Zero : other.MainWindowHandle;
                if (window == IntPtr.Zero)
                {
                    continue;
                }
                if (IsIconic(window))
                {
                    ShowWindow(window, SwRestore);
                }
                SetForegroundWindow(window);
                return;
            }
        }
    }
}
