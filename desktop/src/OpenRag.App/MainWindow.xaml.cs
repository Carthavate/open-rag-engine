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
    // Loopback only, so never through a system proxy (and no WPAD lookups when offline). Timeouts are per request.
    private readonly HttpClient _http = new(new SocketsHttpHandler { UseProxy = false }) { Timeout = Timeout.InfiniteTimeSpan };
    private readonly SemaphoreSlim _lifecycle = new(1, 1);
    private readonly Dictionary<string, CancellationTokenSource> _asks = [];
    private EngineHost? _engine;
    private EngineProxy? _proxy;
    private object _engineState = new { type = "engine", state = "starting" };
    private string _origin = $"https://{AppHost}";

    public MainWindow()
    {
        InitializeComponent();
        ApplyTheme();
        SourceInitialized += (_, _) => WindowFrame.RoundCorners(this);
        StateChanged += (_, _) => OnWindowStateChanged();
        SystemEvents.UserPreferenceChanged += OnUserPreferenceChanged;
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

    /// <summary>Checkout discovery runs `uv` from a source tree, so only developer (Debug) builds may use it.</summary>
#if DEBUG
    private const bool AllowCheckout = true;
#else
    private const bool AllowCheckout = false;
#endif

    /// <summary>Starts (or restarts) the engine. Serialised, so two clicks on "Try again" can't start two engines on the
    /// same data.</summary>
    private async Task StartEngineAsync(bool restart = false)
    {
        if (!await _lifecycle.WaitAsync(0))
        {
            return;
        }
        try
        {
            if (restart)
            {
                await StopEngineAsync();
            }
            await LaunchEngineAsync();
        }
        finally
        {
            _lifecycle.Release();
        }
    }

    private async Task LaunchEngineAsync()
    {
        SetEngineState("starting");
        var command = EngineLocator.Find(AppContext.BaseDirectory, Environment.GetEnvironmentVariable, AllowCheckout);
        if (command is null)
        {
            SetEngineState("failed", "Open RAG couldn't find its engine. Reinstalling the app should fix this.");
            return;
        }
        try
        {
            var engine = new EngineHost(command, command.ServeArguments(_paths.Data, Environment.ProcessId), _paths.EngineLog);
            engine.Started += process => _job?.Add(process);
            // Only the current engine may report a crash; a late exit from a replaced one is ignored.
            engine.Exited += code => Dispatcher.BeginInvoke(() =>
            {
                if (!ReferenceEquals(engine, _engine))
                {
                    return;
                }
                _proxy = null;
                SetEngineState("failed", $"The engine stopped unexpectedly (exit code {code}). Details are in {_paths.EngineLog}.");
            });
            _engine = engine;
            var connection = await engine.StartAsync(new Dictionary<string, string> { ["ORE_API_TOKEN"] = _token }, EngineStartTimeout);
            _proxy = new EngineProxy(_http, connection.BaseUrl, _token);
            SetEngineState("ready");
        }
        catch (EngineStartException e)
        {
            SetEngineState("failed", $"{e.Message}\n\nThe full log is in {_paths.EngineLog}.");
        }
        catch (Exception e)
        {
            // Anything else (no permission to create the log folder, a blocked program) must not leave "starting" forever.
            LogError(e);
            SetEngineState("failed", $"Open RAG couldn't start its engine: {e.Message}\n\nDetails are in {_paths.ErrorLog}.");
        }
    }

    private async Task StopEngineAsync()
    {
        _proxy = null;
        var engine = _engine;
        _engine = null;
        if (engine is not null)
        {
            await engine.DisposeAsync();
        }
    }

    private void LogError(Exception e)
    {
        try
        {
            Directory.CreateDirectory(_paths.Logs);
            File.AppendAllText(_paths.ErrorLog, $"{DateTime.Now:u} {e}\n\n");
        }
        catch (Exception logError) when (logError is IOException or UnauthorizedAccessException)
        {
            Debug.WriteLine($"Couldn't write the error log: {logError.Message}");
        }
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
        core.Settings.IsStatusBarEnabled = false;
        // The page's top bar is the title bar: `app-region: drag` areas move the window, double-click maximises.
        core.Settings.IsNonClientRegionSupportEnabled = true;
        core.Settings.IsZoomControlEnabled = false;
        core.Settings.AreBrowserAcceleratorKeysEnabled = dev;
        core.Settings.AreDefaultContextMenusEnabled = dev;
        core.Settings.AreDevToolsEnabled = dev || Debugger.IsAttached;
        core.Settings.AreHostObjectsAllowed = false;
        core.Settings.IsWebMessageEnabled = true;
        // The page gets no camera, microphone, location, clipboard reads or anything else it might ask for.
        core.PermissionRequested += (_, e) => e.State = CoreWebView2PermissionState.Deny;
        core.SetVirtualHostNameToFolderMapping(AppHost, WebRoot, CoreWebView2HostResourceAccessKind.DenyCors);

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
                    PostWindowState();
                    break;
                case "window":
                    OnWindowButton(message.GetProperty("action").GetString());
                    break;
                case "pickFolder":
                    PickFolder(message.GetProperty("id").GetString());
                    break;
                case "openSource":
                    await OpenSourceAsync(message.GetProperty("path").GetString(), reveal: false);
                    break;
                case "revealSource":
                    await OpenSourceAsync(message.GetProperty("path").GetString(), reveal: true);
                    break;
                case "restartEngine":
                    await StartEngineAsync(restart: true);
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
        // An async void handler must never throw: log it and tell the page, instead of a crash dialog.
        catch (Exception ex)
        {
            LogError(ex);
            Post(new { type = "notice", message = $"Something went wrong: {ex.Message}" });
        }
    }

    private void OnWindowButton(string? action)
    {
        switch (action)
        {
            case "minimize":
                WindowState = WindowState.Minimized;
                break;
            case "maximize":
                WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
                break;
            case "close":
                Close();
                break;
        }
    }

    private void OnWindowStateChanged()
    {
        Frame.Padding = WindowFrame.Padding(WindowState == WindowState.Maximized);
        PostWindowState();
    }

    private void PostWindowState() => Post(new { type = "windowState", maximized = WindowState == WindowState.Maximized });

    private void OnUserPreferenceChanged(object sender, UserPreferenceChangedEventArgs e)
    {
        if (e.Category == UserPreferenceCategory.General)
        {
            Dispatcher.Invoke(ApplyTheme);
        }
    }

    /// <summary>The frame and the first frame before the page paints use the Arena background for light or dark mode.</summary>
    private void ApplyTheme()
    {
        var color = WindowFrame.IsDarkMode() ? WindowFrame.Dark : WindowFrame.Light;
        Background = new System.Windows.Media.SolidColorBrush(color);
        Web.DefaultBackgroundColor = System.Drawing.Color.FromArgb(color.R, color.G, color.B);
    }

    private static string? Body(JsonElement message) =>
        message.TryGetProperty("body", out var body) && body.ValueKind != JsonValueKind.Null ? body.GetRawText() : null;

    private static readonly ProxyResponse NotReady = EngineProxy.Problem(503, "Engine unavailable", "The engine isn't running.");

    /// <summary>One API call from the page: forwarded with the token, answered with the status and raw JSON body.
    /// Whatever happens, the page gets an answer for its id, so it never waits forever.</summary>
    private async Task ForwardAsync(JsonElement message)
    {
        var id = message.GetProperty("id").GetString();
        ProxyResponse result;
        try
        {
            result = _proxy is not { } proxy
                ? NotReady
                : await proxy.SendAsync(message.GetProperty("method").GetString() ?? "", message.GetProperty("path").GetString() ?? "", Body(message));
        }
        catch (Exception e)
        {
            LogError(e);
            result = EngineProxy.Problem(500, "Internal error", e.Message);
        }
        Post(new { type = "apiResult", id, status = result.Status, body = result.Body });
    }

    /// <summary>A question: the engine's NDJSON lines go to the page one by one as they arrive, then an end marker.</summary>
    private async Task AskAsync(JsonElement message)
    {
        var id = message.GetProperty("id").GetString() ?? "";
        if (_proxy is not { } proxy)
        {
            Post(new { type = "askEnd", id, status = NotReady.Status, body = NotReady.Body });
            return;
        }
        using var cancel = new CancellationTokenSource();
        _asks[id] = cancel;
        try
        {
            var result = await proxy.StreamAsync("/ask", Body(message) ?? "{}", line =>
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
        catch (Exception e)
        {
            LogError(e);
            var failed = EngineProxy.Problem(500, "Internal error", e.Message);
            Post(new { type = "askEnd", id, status = failed.Status, body = failed.Body });
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

    /// <summary>Opens a cited document with its usual app, or shows it in Explorer. Only documents on a local drive that
    /// exist, by absolute path, are opened, so nothing the page sends can launch a program or reach another computer.
    /// The check touches the disk, so it runs off the UI thread.</summary>
    private async Task OpenSourceAsync(string? path, bool reveal)
    {
        if (!SourceFiles.IsLocalDocumentPath(path) || !await Task.Run(() => SourceFiles.CanOpen(path)))
        {
            Post(new { type = "notice", message = "That file isn't there anymore. Re-index the section to update it." });
            return;
        }
        var full = Path.GetFullPath(path!);
        try
        {
            if (reveal)
            {
                Process.Start(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "explorer.exe"), $"/select,\"{full}\"");
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
        SystemEvents.UserPreferenceChanged -= OnUserPreferenceChanged;
        foreach (var ask in _asks.Values)
        {
            ask.Cancel();
        }
        await StopEngineAsync();
        _http.Dispose();
        _job?.Dispose();
    }
}
