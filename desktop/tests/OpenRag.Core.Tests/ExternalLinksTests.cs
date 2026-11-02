using System.Text.RegularExpressions;
using OpenRag.Core;

namespace OpenRag.Core.Tests;

public class ExternalLinksTests
{
    [Theory]
    [InlineData("https://github.com/TWadi")]
    [InlineData("https://www.linkedin.com/in/ghassen-jamoussi/")]
    [InlineData("https://github.com/Carthavate/open-rag-engine")]
    public void Opens_the_credits_and_the_source(string url) => Assert.True(ExternalLinks.IsAllowed(url));

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("http://github.com/TWadi")]
    [InlineData("https://github.com/TWadi/../evil")]
    [InlineData("https://github.com/TWadi.evil.example")]
    [InlineData("https://GITHUB.com/TWadi")]
    [InlineData("file:///C:/Windows/System32/calc.exe")]
    [InlineData("javascript:alert(1)")]
    public void Refuses_anything_else(string? url) => Assert.False(ExternalLinks.IsAllowed(url));

    /// <summary>The Credits sheet (desktop/web/src/lib/credits.ts) must only show links the window will open.</summary>
    [Fact]
    public void Every_link_in_the_credits_sheet_opens()
    {
        var credits = File.ReadAllText(Path.Combine(DesktopFolder(), "web", "src", "lib", "credits.ts"));
        var links = Regex.Matches(credits, "\"(https://[^\"]+)\"").Select(m => m.Groups[1].Value).ToList();
        Assert.Equal(5, links.Count);
        Assert.All(links, link => Assert.True(ExternalLinks.IsAllowed(link), $"{link} isn't in ExternalLinks.Allowed"));
    }

    private static string DesktopFolder()
    {
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
        {
            if (File.Exists(Path.Combine(dir.FullName, "OpenRag.slnx")))
            {
                return dir.FullName;
            }
        }
        throw new DirectoryNotFoundException("desktop/OpenRag.slnx not found above the test output.");
    }
}
