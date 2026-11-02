using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows;
using Microsoft.Web.WebView2.Core;
using Microsoft.Win32;
using OpenRag.Core;

namespace OpenRag.App;

/// <summary>Hosts the React interface and runs the engine. The page reaches the engine only through this window: its API
/// calls arrive as messages and go out through <see cref="EngineProxy"/>, which adds the token. The page never sees the
/// token and never talks to a local port.</summary>
public partial class MainWindow : Window
{
    private const string AppHost = "app.ore";

    /// <summary>Debug builds only: set to the Vite dev server (http://localhost:5176) to work on the interface with live reload.</summary>
    private const string DevUrlVariable = "OPENRAG_DEV_URL";

    private static readonly TimeSpan EngineStartTimeout = TimeSpan.FromMinutes(3);
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private static readonly string WebRoot = Path.Combine(AppContext.BaseDirectory, "wwwroot");

    private readonly AppPaths _paths = AppPaths.Default;
    private readonly ChildProcessJob? _job = CreateJob();
    private readonly string _token = Token.New();
    private readonly string? _devUrl = DevServerUrl();
    private readonly HttpClient _http = new() { Timeout = Timeout.InfiniteTimeSpan };
    private readonly Dictionary<string, CancellationTokenSource> _asks = [];
    private EngineHost? _engine;
    private EngineProxy? _proxy;
    private object _engineState = new { type = "engine", state = "starting" };
    private string _origin = $"https://{AppHost}";

    public MainWindow()
    {
        InitializeComponent();
        Loaded += async (_, _) => await Task.WhenAll(StartWebViewAsync(), StartEngineAsync());
        Closing += async (_, _) => await ShutdownAsync();
    }

    private static ChildProcessJob? CreateJob()
    {
        try
        {
            return new ChildProcessJob();
        }
        catch (System.ComponentModel.Win32Exception e)
        {
            Debug.WriteLine($"No job object, so the engine could outlive a crash: {e.Message}");
            return null;
        }
    }

    /// <summary>The dev server is honoured only in Debug builds and only on this machine.</summary>
    private static string? DevServerUrl()
    {
#if DEBUG
        var url = Environment.GetEnvironmentVariable(DevUrlVariable);
        return url is not null && Uri.TryCreate(url, UriKind.Absolute, out var uri) && uri.IsLoopback ? url : null;
#else
        return null;
#endif
    }

    private bool IsOwnPage(string url) =>
        Uri.TryCreate(url, UriKind.Absolute, out var uri) && string.Equals(uri.GetLeftPart(UriPartial.Authority), _origin, StringComparison.OrdinalIgnoreCase);

    private async Task StartEngineAsync()
    {
        SetEngineState("starting");
        var command = EngineLocator.Find(AppContext.BaseDirectory, Environment.GetEnvironmentVariable);
        if (command is null)
        {
            SetEngineState("failed", "Open RAG couldn't find its engine. Reinstalling the app should fix this.");
            return;
        }
        var engine = new EngineHost(command, command.ServeArguments(_paths.Data, Environment.ProcessId), _paths.EngineLog);
        engine.Started += process => _job?.Add(process);
        engine.Exited += code => Dispatcher.Invoke(() =>
            SetEngineState("failed", $"The engine stopped unexpectedly (exit code {code}). Details are in {_paths.EngineLog}."));
        _engine = engine;
        try
        {
            var connection = await engine.StartAsync(new Dictionary<string, string> { ["ORE_API_TOKEN"] = _token }, EngineStartTimeout);
            _proxy = new EngineProxy(_http, connection.BaseUrl, _token);
            SetEngineState("ready");
        }
        catch (EngineStartException e)
        {
            SetEngineState("failed", $"{e.Message}\n\nThe full log is in {_paths.EngineLog}.");
        }
    }

    private async Task RestartEngineAsync()
    {
        _proxy = null;
        if (_engine is not null)
        {
            await _engine.DisposeAsync();
            _engine = null;
        }
        await StartEngineAsync();
    }

    private void SetEngineState(string state, string? message = null)
    {
        _engineState = new { type = "engine", state, message };
        Post(_engineState);
    }

    private void Post(object message)
    {
        if (Web.CoreWebView2 is { } core)
        {
            core.PostWebMessageAsJson(JsonSerializer.Serialize(message, Json));
        }
    }

    private async Task StartWebViewAsync()
    {
        if (_devUrl is null && !File.Exists(Path.Combine(WebRoot, "index.html")))
        {
            MessageBox.Show(this, $"The interface files are missing from {WebRoot}. Run \"npm run build\" in desktop/web, then build again.", "Open RAG");
            return;
        }
        try
        {
            var environment = await CoreWebView2Environment.CreateAsync(userDataFolder: _paths.WebView);
            await Web.EnsureCoreWebView2Async(environment);
        }
        catch (Exception e) when (e is WebView2RuntimeNotFoundException or COMException or InvalidOperationException)
        {
            MessageBox.Show(this, $"Open RAG needs the Microsoft Edge WebView2 Runtime, which comes with Windows 11.\n\n{e.Message}", "Open RAG");
            return;
        }

        var core = Web.CoreWebView2;
        var dev = _devUrl is not null;
        Web.DefaultBackgroundColor = System.Drawing.Color.FromArgb(0xEA, 0xF2, 0xFF);
        core.Settings.IsStatusBarEnabled = false;
        core.Settings.IsZoomControlEnabled = false;
        core.Settings.AreBrowserAcceleratorKeysEnabled = dev;
        core.Settings.AreDefaultContextMenusEnabled = dev;
        core.Settings.AreDevToolsEnabled = dev || Debugger.IsAttached;
        core.SetVirtualHostNameToFolderMapping(AppHost, WebRoot, CoreWebView2HostResourceAccessKind.Allow);

        // Only our own page may run here; anything else (a dropped file, a link) is refused.
        var start = dev ? _devUrl!.TrimEnd('/') + "/" : $"{_origin}/index.html";
        _origin = new Uri(start).GetLeftPart(UriPartial.Authority);
        core.NavigationStarting += (_, e) => e.Cancel = !IsOwnPage(e.Uri);
        core.NewWindowRequested += (_, e) => e.Handled = true;
        core.WebMessageReceived += OnWebMessage;
        core.ProcessFailed += (_, e) =>
        {
            if (e.ProcessFailedKind is CoreWebView2ProcessFailedKind.RenderProcessExited or CoreWebView2ProcessFailedKind.RenderProcessUnresponsive)
            {
                Web.CoreWebView2?.Reload();
            }
        };
        core.Navigate(start);
    }

    private async void OnWebMessage(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (!IsOwnPage(e.Source))
        {
            return;
        }
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson);
            var message = doc.RootElement;
            switch (message.GetProperty("type").GetString())
            {
                case "ready":
                    Post(_engineState);
                    break;
                case "pickFolder":
                    PickFolder(message.GetProperty("id").GetString());
                    break;
                case "openSource":
                    OpenSource(message.GetProperty("path").GetString(), reveal: false);
                    break;
                case "revealSource":
                    OpenSource(message.GetProperty("path").GetString(), reveal: true);
                    break;
                case "restartEngine":
                    await RestartEngineAsync();
                    break;
                case "api":
                    await ForwardAsync(message);
                    break;
                case "ask":
                    await AskAsync(message);
                    break;
                case "cancel":
                    if (_asks.TryGetValue(message.GetProperty("id").GetString() ?? "", out var ask))
                    {
                        ask.Cancel();
                    }
                    break;
            }
        }
        // An async void handler must not throw: tell the page instead of losing it.
        catch (Exception ex) when (ex is JsonException or KeyNotFoundException or InvalidOperationException)
        {
            Post(new { type = "notice", message = $"Something went wrong: {ex.Message}" });
        }
    }

    private static string? Body(JsonElement message) =>
        message.TryGetProperty("body", out var body) && body.ValueKind != JsonValueKind.Null ? body.GetRawText() : null;

    private const string NotReady = """{"title":"Engine unavailable","status":503,"detail":"The engine isn't running."}""";

    /// <summary>One API call from the page: forwarded with the token, answered with the status and raw JSON body.</summary>
    private async Task ForwardAsync(JsonElement message)
    {
        var id = message.GetProperty("id").GetString();
        var result = _proxy is null
            ? new ProxyResponse(503, NotReady)
            : await _proxy.SendAsync(message.GetProperty("method").GetString() ?? "", message.GetProperty("path").GetString() ?? "", Body(message));
        Post(new { type = "apiResult", id, status = result.Status, body = result.Body });
    }

    /// <summary>A question: the engine's NDJSON lines go to the page one by one as they arrive, then an end marker.</summary>
    private async Task AskAsync(JsonElement message)
    {
        var id = message.GetProperty("id").GetString() ?? "";
        if (_proxy is null)
        {
            Post(new { type = "askEnd", id, status = 503, body = NotReady });
            return;
        }
        using var cancel = new CancellationTokenSource();
        _asks[id] = cancel;
        try
        {
            var result = await _proxy.StreamAsync("/ask", Body(message) ?? "{}", line =>
            {
                Post(new { type = "askLine", id, line });
                return Task.CompletedTask;
            }, cancel.Token);
            Post(new { type = "askEnd", id, status = result.Status, body = result.Body });
        }
        catch (OperationCanceledException)
        {
            Post(new { type = "askEnd", id, status = 499, body = "" });
        }
        finally
        {
            _asks.Remove(id);
        }
    }

    private void PickFolder(string? id)
    {
        var dialog = new OpenFolderDialog { Title = "Choose a folder for this section" };
        var path = dialog.ShowDialog(this) == true ? dialog.FolderName : null;
        Post(new { type = "folderPicked", id, path });
    }

    /// <summary>Opens a cited document with its usual app, or shows it in Explorer. Only documents that exist, by absolute
    /// path, are opened, so nothing the page sends can launch a program.</summary>
    private void OpenSource(string? path, bool reveal)
    {
        if (!SourceFiles.CanOpen(path))
        {
            Post(new { type = "notice", message = "That file isn't there anymore. Re-index the section to update it." });
            return;
        }
        var full = Path.GetFullPath(path!);
        try
        {
            if (reveal)
            {
                Process.Start("explorer.exe", $"/select,\"{full}\"");
            }
            else
            {
                Process.Start(new ProcessStartInfo(full) { UseShellExecute = true });
            }
        }
        catch (System.ComponentModel.Win32Exception ex)
        {
            Post(new { type = "notice", message = $"Couldn't open {Path.GetFileName(full)}: {ex.Message}" });
        }
    }

    private async Task ShutdownAsync()
    {
        foreach (var ask in _asks.Values)
        {
            ask.Cancel();
        }
        if (_engine is not null)
        {
            await _engine.DisposeAsync();
        }
        _http.Dispose();
        _job?.Dispose();
    }
}
