using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace OpenRag.Core;

/// <summary>A response from the engine: the HTTP status and the raw JSON body (empty for 204).</summary>
public sealed record ProxyResponse(int Status, string Body);

/// <summary>Forwards the page's API calls to the engine, adding the token. The page never sees the token or talks to a
/// local port itself, and it can only reach the engine's own API paths with the usual methods.</summary>
public sealed partial class EngineProxy(HttpClient http, Uri baseUrl, string token)
{
    /// <summary>Library calls are quick; one that takes this long means the engine is stuck.</summary>
    public static readonly TimeSpan RequestTimeout = TimeSpan.FromMinutes(2);

    private const string AskPath = "/ask";
    private static readonly HashSet<string> Methods = ["GET", "POST", "PATCH", "DELETE"];

    // \z, not $: $ would also accept a trailing newline.
    [GeneratedRegex(@"\A/(health|library|ask|categories(/[a-f0-9]{1,64})?|sections(/[a-f0-9]{1,64}(/(folders|folders/remove|index|status|documents))?)?)\z")]
    private static partial Regex ApiPath();

    public static bool IsAllowed(string? method, string? path) =>
        method is not null && Methods.Contains(method) && path is not null && ApiPath().IsMatch(path);

    /// <summary>One request and its whole reply. Questions go through <see cref="StreamAsync"/> instead.</summary>
    public async Task<ProxyResponse> SendAsync(string method, string path, string? json, CancellationToken cancel = default)
    {
        if (!IsAllowed(method, path) || path == AskPath)
        {
            return Refused();
        }
        using var request = Request(method, path, json);
        using var limit = CancellationTokenSource.CreateLinkedTokenSource(cancel);
        limit.CancelAfter(RequestTimeout);
        try
        {
            using var response = await http.SendAsync(request, limit.Token);
            return new ProxyResponse((int)response.StatusCode, await response.Content.ReadAsStringAsync(limit.Token));
        }
        catch (OperationCanceledException) when (!cancel.IsCancellationRequested)
        {
            return Problem(504, "Engine too slow", "The engine took too long to answer. Try again.");
        }
        catch (Exception e) when (e is HttpRequestException or IOException)
        {
            return Unreachable(e);
        }
    }

    /// <summary>Posts a question and hands over each NDJSON line as it arrives. Returns the status, plus the body when
    /// the engine refused the request before streaming. A connection lost midway becomes a 503, never an exception.</summary>
    public async Task<ProxyResponse> StreamAsync(string path, string json, Func<string, Task> onLine, CancellationToken cancel = default)
    {
        if (!IsAllowed("POST", path) || path != AskPath)
        {
            return Refused();
        }
        using var request = Request("POST", path, json);
        try
        {
            using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancel);
            if (!response.IsSuccessStatusCode)
            {
                return new ProxyResponse((int)response.StatusCode, await response.Content.ReadAsStringAsync(cancel));
            }
            using var reader = new StreamReader(await response.Content.ReadAsStreamAsync(cancel), Encoding.UTF8);
            while (await reader.ReadLineAsync(cancel) is { } line)
            {
                if (line.Length > 0)
                {
                    await onLine(line);
                }
            }
            return new ProxyResponse((int)response.StatusCode, "");
        }
        catch (Exception e) when (e is HttpRequestException or IOException)
        {
            return Unreachable(e);
        }
    }

    private HttpRequestMessage Request(string method, string path, string? json)
    {
        var request = new HttpRequestMessage(new HttpMethod(method), new Uri(baseUrl, path));
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        if (json is not null && method != "GET")
        {
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
        }
        return request;
    }

    /// <summary>An RFC 9457 problem body, serialised properly so any message text stays valid JSON.</summary>
    public static ProxyResponse Problem(int status, string title, string detail) =>
        new(status, JsonSerializer.Serialize(new { title, status, detail }));

    private static ProxyResponse Refused() => Problem(400, "Invalid request", "That request isn't part of the engine's API.");

    private static ProxyResponse Unreachable(Exception e) => Problem(503, "Engine unavailable", $"Can't reach the engine: {e.Message}");
}
