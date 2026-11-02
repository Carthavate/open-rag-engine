using OpenRag.Core;

namespace OpenRag.Core.Tests;

public sealed class TempDir : IDisposable
{
    public string Path { get; } = Directory.CreateTempSubdirectory("openrag-").FullName;

    public string Make(params string[] parts)
    {
        var path = System.IO.Path.Combine([Path, .. parts]);
        Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path)!);
        File.WriteAllText(path, "");
        return path;
    }

    public void Dispose()
    {
        try
        {
            Directory.Delete(Path, recursive: true);
        }
        catch (IOException)
        {
            // A test process may still hold a file for a moment; the temp folder is cleaned up eventually.
        }
    }
}

public class ReadyLineTests
{
    [Theory]
    [InlineData("ORE_READY port=62130", 62130)]
    [InlineData("  ORE_READY port=8 ", 8)]
    public void Parses_the_port(string line, int port) => Assert.Equal(port, ReadyLine.TryParsePort(line));

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("ORE_READY port=")]
    [InlineData("ORE_READY port=99999")]
    [InlineData("something ORE_READY port=80")]
    public void Ignores_anything_else(string? line) => Assert.Null(ReadyLine.TryParsePort(line));
}

public class TokenTests
{
    [Fact]
    public void Tokens_are_long_random_hex()
    {
        var a = Token.New();
        Assert.Equal(64, a.Length);
        Assert.Matches("^[0-9a-f]{64}$", a);
        Assert.NotEqual(a, Token.New());
    }
}

public class SourceFilesTests
{
    [Fact]
    public void Opens_only_existing_documents_by_absolute_path()
    {
        using var dir = new TempDir();
        var pdf = dir.Make("notes", "lecture.pdf");
        var exe = dir.Make("tool.exe");
        Assert.True(SourceFiles.CanOpen(pdf));
        Assert.True(SourceFiles.CanOpen(pdf.Replace('\\', '/')));
        Assert.False(SourceFiles.CanOpen(exe));
        Assert.False(SourceFiles.CanOpen(Path.Combine(dir.Path, "missing.md")));
        Assert.False(SourceFiles.CanOpen("notes/lecture.pdf"));
        Assert.False(SourceFiles.CanOpen(""));
    }

    [Theory]
    [InlineData(@"\\attacker\share\a.pdf")]
    [InlineData("//attacker/share/a.pdf")]
    [InlineData(@"\\server@80\DavWWWRoot\a.txt")]
    [InlineData(@"\\?\C:\docs\a.pdf")]
    [InlineData(@"\\.\C:\docs\a.pdf")]
    [InlineData(@"C:\tools\a.exe:hidden.txt")]
    [InlineData(@"C:relative.pdf")]
    public void Network_device_and_stream_paths_are_refused_without_touching_them(string path) =>
        Assert.False(SourceFiles.IsLocalDocumentPath(path));

    [Fact]
    public void Ordinary_local_paths_are_accepted() =>
        Assert.True(SourceFiles.IsLocalDocumentPath("C:/Courses/Physics/lecture 3.pdf"));
}

public class EngineLocatorTests
{
    private static Func<string, string?> Env(Dictionary<string, string>? values = null) =>
        name => values is not null && values.TryGetValue(name, out var v) ? v : null;

    [Fact]
    public void Prefers_the_bundled_engine_next_to_the_app()
    {
        using var dir = new TempDir();
        var python = dir.Make("engine", "python", "python.exe");
        var config = dir.Make("engine", "ore.toml");
        var command = EngineLocator.Find(dir.Path, Env())!;
        Assert.Equal(python, command.FileName);
        Assert.Equal(["-m", "open_rag_engine", "serve"], command.Arguments);
        Assert.Equal(config, command.ConfigPath);
    }

    [Fact]
    public void Finds_a_development_checkout_above_the_app()
    {
        using var dir = new TempDir();
        File.WriteAllText(dir.Make("pyproject.toml"), "[project]\nname = \"open-rag-engine\"\n");
        var appDir = Directory.CreateDirectory(Path.Combine(dir.Path, "desktop", "src", "bin")).FullName;
        var command = EngineLocator.Find(appDir, Env())!;
        Assert.Equal("uv", command.FileName);
        Assert.Equal(["run", "--project", dir.Path, "ore", "serve"], command.Arguments);
        Assert.Null(command.ConfigPath);
    }

    [Fact]
    public void An_environment_variable_points_at_a_checkout()
    {
        using var dir = new TempDir();
        File.WriteAllText(dir.Make("repo", "pyproject.toml"), "name = \"open-rag-engine\"");
        var repo = Path.Combine(dir.Path, "repo");
        var command = EngineLocator.Find(dir.Path, Env(new() { [EngineLocator.EngineDirVariable] = repo }))!;
        Assert.Contains(repo, command.Arguments);
    }

    [Fact]
    public void Release_builds_never_fall_back_to_a_checkout()
    {
        using var dir = new TempDir();
        File.WriteAllText(dir.Make("pyproject.toml"), "name = \"open-rag-engine\"");
        Assert.Null(EngineLocator.Find(dir.Path, Env(), allowCheckout: false));
    }

    [Fact]
    public void Returns_null_when_there_is_no_engine()
    {
        using var dir = new TempDir();
        File.WriteAllText(dir.Make("pyproject.toml"), "name = \"something-else\"");
        Assert.Null(EngineLocator.Find(dir.Path, Env()));
    }

    [Fact]
    public void Serve_arguments_add_data_dir_parent_and_config()
    {
        var command = new EngineCommand("python.exe", ["-m", "open_rag_engine", "serve"], "C:/app", "C:/app/ore.toml");
        var args = command.ServeArguments("C:/data", 42);
        Assert.Equal(["-m", "open_rag_engine", "serve", "--data-dir", "C:/data", "--parent-pid", "42", "--warm",
            "--config", "C:/app/ore.toml"], args);
    }
}

public class EngineHostTests
{
    private static EngineCommand Cmd(string script) => new("cmd.exe", ["/c", script], Environment.CurrentDirectory, null);

    [Fact]
    public async Task Start_returns_the_port_the_engine_announces()
    {
        using var dir = new TempDir();
        await using var host = new EngineHost(Cmd("echo starting & echo ORE_READY port=4321 & ping -n 20 127.0.0.1 >nul"),
            ["/c", "echo starting & echo ORE_READY port=4321 & ping -n 20 127.0.0.1 >nul"], Path.Combine(dir.Path, "engine.log"));
        var connection = await host.StartAsync(new Dictionary<string, string> { ["ORE_API_TOKEN"] = "x" }, TimeSpan.FromSeconds(20));
        Assert.Equal(new Uri("http://127.0.0.1:4321/"), connection.BaseUrl);
        Assert.Contains("starting", File.ReadAllText(Path.Combine(dir.Path, "engine.log")));
    }

    [Fact]
    public async Task A_deliberate_stop_is_not_reported_as_a_crash()
    {
        using var dir = new TempDir();
        var script = "echo ORE_READY port=4322 & ping -n 30 127.0.0.1 >nul";
        await using var host = new EngineHost(Cmd(script), ["/c", script], Path.Combine(dir.Path, "engine.log"));
        var crashes = 0;
        host.Exited += _ => crashes++;
        await host.StartAsync(new Dictionary<string, string>(), TimeSpan.FromSeconds(20));
        host.Stop();
        await Task.Delay(1500);
        Assert.Equal(0, crashes);
    }

    [Fact]
    public async Task A_start_that_times_out_stops_the_process()
    {
        using var dir = new TempDir();
        var script = "ping -n 30 127.0.0.1 >nul";
        await using var host = new EngineHost(Cmd(script), ["/c", script], Path.Combine(dir.Path, "engine.log"));
        System.Diagnostics.Process? started = null;
        host.Started += p => started = p;
        await Assert.ThrowsAsync<EngineStartException>(() => host.StartAsync(new Dictionary<string, string>(), TimeSpan.FromSeconds(1)));
        Assert.True(started!.WaitForExit(5000));
    }

    [Fact]
    public async Task A_crash_before_ready_reports_the_last_output()
    {
        using var dir = new TempDir();
        await using var host = new EngineHost(Cmd("echo no module named open_rag_engine 1>&2 & exit 3"),
            ["/c", "echo no module named open_rag_engine 1>&2 & exit 3"], Path.Combine(dir.Path, "engine.log"));
        var error = await Assert.ThrowsAsync<EngineStartException>(() =>
            host.StartAsync(new Dictionary<string, string>(), TimeSpan.FromSeconds(20)));
        Assert.Contains("no module named open_rag_engine", error.Message);
    }
}
