using System.Diagnostics;

namespace OpenRag.Core;

public sealed record EngineConnection(Uri BaseUrl);

public sealed class EngineStartException(string message) : Exception(message);

/// <summary>Runs a helper program (the engine, or the bundled language model server) as a hidden child process, writes
/// its output to a log, and tells when it is ready: either from a line it prints, or from a health check.</summary>
public sealed class ChildHost(EngineCommand command, IReadOnlyList<string> arguments, string logPath, string name = "engine")
    : IAsyncDisposable
{
    private const int TailLines = 12;
    private static readonly TimeSpan ProbeInterval = TimeSpan.FromMilliseconds(500);

    private readonly Queue<string> _tail = new();
    private readonly Lock _log = new();
    private readonly TaskCompletionSource<EngineConnection> _readyLine = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource<int> _exited = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private Process? _process;
    private volatile bool _stopping;
    private volatile bool _ready;

    /// <summary>Raised when the process exits after it was ready, unless we stopped it ourselves.</summary>
    public event Action<int>? Exited;

    /// <summary>Lets the app put the process in its job object, so it dies with the app.</summary>
    public event Action<Process>? Started;

    /// <summary>Starts the process and waits for its <c>ORE_READY port=N</c> line.</summary>
    public async Task<EngineConnection> StartAsync(IReadOnlyDictionary<string, string> environment, TimeSpan timeout,
        CancellationToken cancel = default)
    {
        Start(environment);
        return await WaitAsync(_readyLine.Task, timeout, cancel);
    }

    /// <summary>Starts the process and waits until <paramref name="probe"/> says it is ready (for example a health check).</summary>
    public async Task StartAsync(IReadOnlyDictionary<string, string> environment, Func<CancellationToken, Task<bool>> probe,
        TimeSpan timeout, CancellationToken cancel = default)
    {
        Start(environment);
        await WaitAsync(Probe(probe), timeout, cancel);
    }

    private async Task<bool> Probe(Func<CancellationToken, Task<bool>> probe)
    {
        using var stop = new CancellationTokenSource();
        _ = _exited.Task.ContinueWith(_ => stop.Cancel(), TaskScheduler.Default);
        while (!stop.IsCancellationRequested)
        {
            try
            {
                if (await probe(stop.Token))
                {
                    return true;
                }
                await Task.Delay(ProbeInterval, stop.Token);
            }
            catch (Exception e) when (e is OperationCanceledException or HttpRequestException)
            {
                // Not up yet, or it exited; WaitAsync reports which.
            }
        }
        return false;
    }

    /// <summary>Above this size the log moves to <c>.old</c> when the process next starts, so it can't grow forever.</summary>
    public const long MaxLogBytes = 5 * 1024 * 1024;

    private void Start(IReadOnlyDictionary<string, string> environment)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(logPath)!);
        RotateLog();
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

        var process = new Process { StartInfo = info, EnableRaisingEvents = true };
        process.OutputDataReceived += (_, e) =>
        {
            Write(e.Data);
            if (ReadyLine.TryParsePort(e.Data) is { } port)
            {
                _readyLine.TrySetResult(new EngineConnection(new Uri($"http://127.0.0.1:{port}/")));
            }
        };
        process.ErrorDataReceived += (_, e) => Write(e.Data);
        process.Exited += (_, _) =>
        {
            var code = SafeExitCode(process);
            _exited.TrySetResult(code);
            // Before it was ready, the waiting start reports the failure. A stop we asked for is not a crash.
            if (_ready && !_stopping)
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
            throw new EngineStartException($"Couldn't start the {name} ({command.FileName}): {e.Message}");
        }
        _process = process;
        Started?.Invoke(process);
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
    }

    private async Task<T> WaitAsync<T>(Task<T> ready, TimeSpan timeout, CancellationToken cancel)
    {
        using var timer = CancellationTokenSource.CreateLinkedTokenSource(cancel);
        timer.CancelAfter(timeout);
        try
        {
            var first = await Task.WhenAny(ready, _exited.Task).WaitAsync(timer.Token);
            if (first == ready && !_exited.Task.IsCompleted && (ready.Result is not bool ok || ok))
            {
                _ready = true;
                return ready.Result;
            }
            throw new EngineStartException(FailureMessage(await _exited.Task));
        }
        catch (OperationCanceledException) when (!cancel.IsCancellationRequested)
        {
            Stop();
            throw new EngineStartException($"The {name} didn't start within {timeout.TotalSeconds:0} seconds. {Tail()}");
        }
    }

    public void Stop()
    {
        _stopping = true;
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
                // The log is a convenience; a locked file must not stop the process.
            }
        }
    }

    private void RotateLog()
    {
        try
        {
            if (File.Exists(logPath) && new FileInfo(logPath).Length > MaxLogBytes)
            {
                File.Move(logPath, logPath + ".old", overwrite: true);
            }
        }
        catch (IOException)
        {
            // Rotation is housekeeping; the process starts either way.
        }
    }

    private string Tail()
    {
        lock (_log)
        {
            return _tail.Count == 0 ? "" : "Last output:\n" + string.Join("\n", _tail);
        }
    }

    private string FailureMessage(int code) => $"The {name} stopped (exit code {code}) before it was ready. {Tail()}".Trim();

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
