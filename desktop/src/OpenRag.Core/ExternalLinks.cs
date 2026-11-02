namespace OpenRag.Core;

/// <summary>The only web pages the app opens, in the default browser: its authors' profiles and its source code. The
/// page asks by URL; anything not on this list is ignored, so even a compromised page can't open other sites.</summary>
public static class ExternalLinks
{
    public static IReadOnlySet<string> Allowed { get; } = new HashSet<string>(StringComparer.Ordinal)
    {
        "https://github.com/Carthavate/open-rag-engine",
        "https://github.com/TWadi",
        "https://www.linkedin.com/in/wadi-touil-117472319/",
        "https://github.com/GhassenJamoussi99",
        "https://www.linkedin.com/in/ghassen-jamoussi/",
    };

    public static bool IsAllowed(string? url) => url is not null && Allowed.Contains(url);
}
