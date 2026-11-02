using System.Net.Http.Headers;
using System.Text;
using System.Text.RegularExpressions;

namespace OpenRag.Core;

/// <summary>A response from the engine: the HTTP status and the raw JSON body (empty for 204).</summary>
public sealed record ProxyResponse(int Status, string Body);

/// <summary>Forwards the page's API calls to the engine, adding the token. The page never sees the token or talks to a
/// local port itself, and it can only reach the engine's own API paths with the usual methods.</summary>
public sealed partial class EngineProxy(HttpClient http, Uri baseUrl, string token)
{
    private static readonly HashSet<string> Methods = ["GET", "POST", "PATCH", "DELETE"];

    [GeneratedRegex(@"^/(health|library|ask|categories(/[a-f0-9]{1,64})?|sections(/[a-f0-9]{1,64}(/(folders|folders/remove|index|status|documents))?)?)$")]
    private static partial Regex ApiPath();

    public static bool IsAllowed(string? method, string? path) =>
        method is not null && Methods.Contains(method) && path is not null && ApiPath().IsMatch(path);

    public async Task<ProxyResponse> SendAsync(string method, string path, string? json, CancellationToken cancel = default)
    {
        if (!IsAllowed(method, path))
        {
            return Refused();
        }
        using var request = Request(method, path, json);
        try
        {
            using var response = await http.SendAsync(request, cancel);
            return new ProxyResponse((int)response.StatusCode, await response.Content.ReadAsStringAsync(cancel));
        }
        catch (HttpRequestException e)
        {
            return Unreachable(e);
        }
    }

    /// <summary>Posts to a streaming endpoint and hands over each NDJSON line as it arrives. Returns the status, plus
    /// the body when the engine refused the request before streaming.</summary>
    public async Task<ProxyResponse> StreamAsync(string path, string json, Func<string, Task> onLine, CancellationToken cancel = default)
    {
        if (!IsAllowed("POST", path))
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
        catch (HttpRequestException e)
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

    private static ProxyResponse Refused() =>
        new(400, """{"title":"Invalid request","status":400,"detail":"That request isn't part of the engine's API."}""");

    private static ProxyResponse Unreachable(HttpRequestException e) =>
        new(503, $$"""{"title":"Engine unavailable","status":503,"detail":"Can't reach the engine: {{Escape(e.Message)}}"}""");

    private static string Escape(string text) => text.Replace("\\", "\\\\").Replace("\"", "\\\"");
}
