using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using Microsoft.Win32;

namespace OpenRag.App;

/// <summary>The frame around the page: rounded corners on Windows 11, and the Arena background in light or dark mode,
/// so the thin resize border and the first frame before the page loads match the interface.</summary>
internal static class WindowFrame
{
    private const int DwmwaWindowCornerPreference = 33;
    private const int DwmwcpRound = 2;

    public static readonly Color Light = Color.FromRgb(0xEA, 0xF2, 0xFF);
    public static readonly Color Dark = Color.FromRgb(0x12, 0x14, 0x29);

    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attribute, ref int value, int size);

    /// <summary>Call from SourceInitialized. Windows 10 ignores it and keeps square corners.</summary>
    public static void RoundCorners(Window window)
    {
        var preference = DwmwcpRound;
        DwmSetWindowAttribute(new WindowInteropHelper(window).Handle, DwmwaWindowCornerPreference, ref preference, sizeof(int));
    }

    /// <summary>Follows the Windows "app mode" setting, like the page does through prefers-color-scheme.</summary>
    public static bool IsDarkMode()
    {
        using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize");
        return key?.GetValue("AppsUseLightTheme") is int light && light == 0;
    }

    /// <summary>Maximised borderless windows overhang the screen by the resize border, so pad them back in.
    /// Restored windows keep a few pixels of frame to grab for resizing.</summary>
    public static Thickness Padding(bool maximized)
    {
        if (!maximized)
        {
            return new Thickness(4);
        }
        var border = SystemParameters.WindowResizeBorderThickness;
        return new Thickness(border.Left + 4, border.Top + 4, border.Right + 4, border.Bottom + 4);
    }
}
