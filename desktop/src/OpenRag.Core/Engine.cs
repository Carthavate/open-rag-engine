using System.Net;
using System.Net.Sockets;
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
    public string LlmLog => Path.Combine(Logs, "llm.log");
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

/// <summary>Which source files the app opens when a citation is clicked: documents only, on a local drive, by absolute
/// path, that exist. Network (UNC) and device paths are refused, so a request can never make Windows contact another
/// computer, and alternate data streams (file.exe:x.txt) are refused, so nothing but a document is ever opened.</summary>
public static class SourceFiles
{
    private static readonly HashSet<string> Documents = new(StringComparer.OrdinalIgnoreCase) { ".pdf", ".md", ".markdown", ".txt" };

    public static bool IsLocalDocumentPath(string? path) =>
        !string.IsNullOrWhiteSpace(path)
        && path.Length > 3
        && char.IsAsciiLetter(path[0])
        && path[1] == ':'
        && path[2] is '\\' or '/'
        && path.IndexOf(':', 2) < 0
        && Path.IsPathFullyQualified(path)
        && Documents.Contains(Path.GetExtension(path));

    public static bool CanOpen(string? path) => IsLocalDocumentPath(path) && File.Exists(path);
}

/// <summary>The language model an installed app brings along: llama.cpp's server and a GGUF model file.</summary>
public sealed record LlmBundle(string ServerPath, string ModelPath)
{
    public const string ModelAlias = "qwen3-4b-instruct";

    /// <summary>llama-server reads its key from here, so the key never shows on its command line.</summary>
    public const string ApiKeyVariable = "LLAMA_API_KEY";

    /// <summary>Loopback only, with its own key; the context matches the engine's default (8192 tokens).</summary>
    public IReadOnlyList<string> Arguments(int port) =>
        ["-m", ModelPath, "--host", "127.0.0.1", "--port", port.ToString(), "--ctx-size", "8192", "--jinja",
         "--alias", ModelAlias, "--no-webui"];

    public static int FreePort()
    {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        return port;
    }
}

/// <summary>How to start the engine: a program, its base arguments, where to run it, an optional config file, and the
/// bundled language model when there is one.</summary>
public sealed record EngineCommand(string FileName, IReadOnlyList<string> Arguments, string WorkingDirectory, string? ConfigPath,
    LlmBundle? Llm = null)
{
    /// <param name="llmUrl">The bundled language model's server, when the app runs one (an OpenAI-compatible /v1 URL).</param>
    public IReadOnlyList<string> ServeArguments(string dataDirectory, int parentProcessId, string? llmUrl = null)
    {
        var args = new List<string>(Arguments) { "--data-dir", dataDirectory, "--parent-pid", parentProcessId.ToString(), "--warm" };
        if (llmUrl is not null)
        {
            args.AddRange(["--llm-url", llmUrl]);
        }
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

    /// <summary>The installed layout (a bundled Python next to the app) wins. Only when <paramref name="allowCheckout"/> is
    /// set (Debug builds) may it fall back to a development checkout of open-rag-engine, from
    /// <see cref="EngineDirVariable"/> or found above the app, run through uv.</summary>
    public static EngineCommand? Find(string appDirectory, Func<string, string?> environment, bool allowCheckout = true)
    {
        var engine = Path.Combine(appDirectory, "engine");
        var python = Path.Combine(engine, "python", "python.exe");
        if (File.Exists(python))
        {
            var config = Path.Combine(engine, "ore.toml");
            var server = Path.Combine(engine, "llm", "llama-server.exe");
            var model = Path.Combine(engine, "llm", "model.gguf");
            var llm = File.Exists(server) && File.Exists(model) ? new LlmBundle(server, model) : null;
            return new EngineCommand(python, ["-m", "open_rag_engine", "serve"], engine, File.Exists(config) ? config : null, llm);
        }
        if (!allowCheckout)
        {
            return null;
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
