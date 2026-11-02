using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace OpenRag.Core;

/// <summary>Where Open RAG keeps its own files: all under %LOCALAPPDATA%\OpenRag, never next to the user's documents.</summary>
public sealed record AppPaths(string Root)
{
    public static AppPaths Default { get; } =
        new(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "OpenRag"));

    public string Data => Path.Combine(Root, "data");
    public string WebView => Path.Combine(Root, "WebView2");
    public string Logs => Path.Combine(Root, "logs");
    public string EngineLog => Path.Combine(Logs, "engine.log");
    public string ErrorLog => Path.Combine(Logs, "errors.log");
}

/// <summary>A per-launch secret the engine requires on every request, so no other program on the machine can use it.</summary>
public static class Token
{
    public static string New() => Convert.ToHexString(RandomNumberGenerator.GetBytes(32)).ToLowerInvariant();
}

/// <summary>The engine prints <c>ORE_READY port=N</c> once it listens.</summary>
public static partial class ReadyLine
{
    [GeneratedRegex(@"^ORE_READY port=(\d{1,5})$")]
    private static partial Regex Pattern();

    public static int? TryParsePort(string? line)
    {
        var match = Pattern().Match(line?.Trim() ?? "");
        return match.Success && int.TryParse(match.Groups[1].Value, out var port) && port is > 0 and <= 65535 ? port : null;
    }
}

/// <summary>Which source files the app opens when a citation is clicked: documents only, by absolute path, that exist.</summary>
public static class SourceFiles
{
    private static readonly HashSet<string> Documents = new(StringComparer.OrdinalIgnoreCase) { ".pdf", ".md", ".markdown", ".txt" };

    public static bool CanOpen(string? path) =>
        !string.IsNullOrWhiteSpace(path)
        && Path.IsPathFullyQualified(path)
        && Documents.Contains(Path.GetExtension(path))
        && File.Exists(path);
}

/// <summary>How to start the engine: a program, its base arguments, where to run it, and an optional config file.</summary>
public sealed record EngineCommand(string FileName, IReadOnlyList<string> Arguments, string WorkingDirectory, string? ConfigPath)
{
    public IReadOnlyList<string> ServeArguments(string dataDirectory, int parentProcessId)
    {
        var args = new List<string>(Arguments) { "--data-dir", dataDirectory, "--parent-pid", parentProcessId.ToString(), "--warm" };
        if (ConfigPath is not null)
        {
            args.AddRange(["--config", ConfigPath]);
        }
        return args;
    }
}

public static class EngineLocator
{
    public const string EngineDirVariable = "OPENRAG_ENGINE_DIR";

    /// <summary>The installed layout (a bundled Python next to the app) wins; otherwise a development checkout of
    /// open-rag-engine, from <see cref="EngineDirVariable"/> or found above the app, run through uv.</summary>
    public static EngineCommand? Find(string appDirectory, Func<string, string?> environment)
    {
        var engine = Path.Combine(appDirectory, "engine");
        var python = Path.Combine(engine, "python", "python.exe");
        if (File.Exists(python))
        {
            var config = Path.Combine(engine, "ore.toml");
            return new EngineCommand(python, ["-m", "open_rag_engine", "serve"], engine, File.Exists(config) ? config : null);
        }
        var checkout = environment(EngineDirVariable) is { } dir && IsCheckout(dir) ? dir : FindCheckoutAbove(appDirectory);
        return checkout is null ? null : new EngineCommand("uv", ["run", "--project", checkout, "ore", "serve"], checkout, null);
    }

    private static string? FindCheckoutAbove(string start)
    {
        for (var dir = new DirectoryInfo(start); dir is not null; dir = dir.Parent)
        {
            if (IsCheckout(dir.FullName))
            {
                return dir.FullName;
            }
        }
        return null;
    }

    private static bool IsCheckout(string dir)
    {
        var pyproject = Path.Combine(dir, "pyproject.toml");
        return File.Exists(pyproject) && File.ReadAllText(pyproject).Contains("name = \"open-rag-engine\"", StringComparison.Ordinal);
    }
}

public sealed record EngineConnection(Uri BaseUrl);

public sealed class EngineStartException(string message) : Exception(message);

/// <summary>Runs the engine as a hidden child process, writes its output to a log, and reports the port it listens on.</summary>
public sealed class EngineHost(EngineCommand command, IReadOnlyList<string> arguments, string logPath) : IAsyncDisposable
{
    private const int TailLines = 12;
    private readonly Queue<string> _tail = new();
    private readonly Lock _log = new();
    private Process? _process;

    /// <summary>Raised when the engine exits after it was ready (a crash, or killed from outside).</summary>
    public event Action<int>? Exited;

    /// <summary>Lets the app put the process in its job object, so the engine dies with the app.</summary>
    public event Action<Process>? Started;

    public async Task<EngineConnection> StartAsync(IReadOnlyDictionary<string, string> environment, TimeSpan timeout,
        CancellationToken cancel = default)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(logPath)!);
        var info = new ProcessStartInfo(command.FileName)
        {
            WorkingDirectory = command.WorkingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardErrorEncoding = System.Text.Encoding.UTF8,
        };
        foreach (var argument in arguments)
        {
            info.ArgumentList.Add(argument);
        }
        info.Environment["PYTHONUTF8"] = "1";
        foreach (var (key, value) in environment)
        {
            info.Environment[key] = value;
        }

        var ready = new TaskCompletionSource<EngineConnection>(TaskCreationOptions.RunContinuationsAsynchronously);
        var process = new Process { StartInfo = info, EnableRaisingEvents = true };
        process.OutputDataReceived += (_, e) =>
        {
            Write(e.Data);
            if (ReadyLine.TryParsePort(e.Data) is { } port)
            {
                ready.TrySetResult(new EngineConnection(new Uri($"http://127.0.0.1:{port}/")));
            }
        };
        process.ErrorDataReceived += (_, e) => Write(e.Data);
        process.Exited += (_, _) =>
        {
            var code = SafeExitCode(process);
            if (!ready.TrySetException(new EngineStartException(FailureMessage(code))))
            {
                Exited?.Invoke(code);
            }
        };

        try
        {
            process.Start();
        }
        catch (System.ComponentModel.Win32Exception e)
        {
            throw new EngineStartException($"Couldn't start the engine ({command.FileName}): {e.Message}");
        }
        _process = process;
        Started?.Invoke(process);
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        using var timer = CancellationTokenSource.CreateLinkedTokenSource(cancel);
        timer.CancelAfter(timeout);
        try
        {
            return await ready.Task.WaitAsync(timer.Token);
        }
        catch (OperationCanceledException) when (!cancel.IsCancellationRequested)
        {
            throw new EngineStartException($"The engine didn't start within {timeout.TotalSeconds:0} seconds. {Tail()}");
        }
    }

    public void Stop()
    {
        try
        {
            if (_process is { HasExited: false } process)
            {
                process.Kill(entireProcessTree: true);
            }
        }
        catch (Exception e) when (e is InvalidOperationException or System.ComponentModel.Win32Exception)
        {
            // Already gone.
        }
    }

    public async ValueTask DisposeAsync()
    {
        Stop();
        if (_process is not null)
        {
            await _process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5)).ContinueWith(_ => { });
            _process.Dispose();
        }
    }

    private void Write(string? line)
    {
        if (line is null)
        {
            return;
        }
        lock (_log)
        {
            _tail.Enqueue(line);
            while (_tail.Count > TailLines)
            {
                _tail.Dequeue();
            }
            try
            {
                File.AppendAllText(logPath, $"{DateTime.Now:HH:mm:ss} {line}{Environment.NewLine}");
            }
            catch (IOException)
            {
                // The log is a convenience; a locked file must not stop the engine.
            }
        }
    }

    private string Tail()
    {
        lock (_log)
        {
            return _tail.Count == 0 ? "" : "Last output:\n" + string.Join("\n", _tail);
        }
    }

    private string FailureMessage(int code) => $"The engine stopped (exit code {code}) before it was ready. {Tail()}".Trim();

    private static int SafeExitCode(Process process)
    {
        try
        {
            return process.ExitCode;
        }
        catch (InvalidOperationException)
        {
            return -1;
        }
    }
}
