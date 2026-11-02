using System.Net;
using System.Text;
using OpenRag.Core;

namespace OpenRag.Core.Tests;

public class EngineProxyTests
{
    private sealed class FakeEngine(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
    {
        public List<HttpRequestMessage> Seen { get; } = [];
        public List<string?> Bodies { get; } = [];

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancel)
        {
            Seen.Add(request);
            Bodies.Add(request.Content is null ? null : await request.Content.ReadAsStringAsync(cancel));
            return respond(request);
        }
    }

    private static (EngineProxy, FakeEngine) Make(Func<HttpRequestMessage, HttpResponseMessage> respond)
    {
        var engine = new FakeEngine(respond);
        return (new EngineProxy(new HttpClient(engine), new Uri("http://127.0.0.1:5000/"), "secret"), engine);
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    [Theory]
    [InlineData("GET", "/library")]
    [InlineData("POST", "/categories")]
    [InlineData("PATCH", "/categories/abc123")]
    [InlineData("DELETE", "/sections/0f9e")]
    [InlineData("POST", "/sections/0f9e/folders/remove")]
    [InlineData("GET", "/sections/0f9e/documents")]
    [InlineData("POST", "/ask")]
    public void Allows_the_engine_api(string method, string path) => Assert.True(EngineProxy.IsAllowed(method, path));

    [Theory]
    [InlineData("GET", "/../secret")]
    [InlineData("GET", "http://evil.example/library")]
    [InlineData("GET", "//evil.example/library")]
    [InlineData("PUT", "/library")]
    [InlineData("GET", "/sections/ABC/status")]
    [InlineData("GET", "/library?x=1")]
    [InlineData(null, "/library")]
    [InlineData("GET", null)]
    public void Refuses_anything_else(string? method, string? path) => Assert.False(EngineProxy.IsAllowed(method, path));

    [Fact]
    public async Task Adds_the_token_and_returns_status_and_body()
    {
        var (proxy, engine) = Make(_ => Json(HttpStatusCode.Created, """{"id":"abc"}"""));
        var result = await proxy.SendAsync("POST", "/categories", """{"name":"Physics"}""");
        Assert.Equal(new ProxyResponse(201, """{"id":"abc"}"""), result);
        var sent = Assert.Single(engine.Seen);
        Assert.Equal("Bearer secret", sent.Headers.Authorization?.ToString());
        Assert.Equal(new Uri("http://127.0.0.1:5000/categories"), sent.RequestUri);
        Assert.Equal("""{"name":"Physics"}""", Assert.Single(engine.Bodies));
    }

    [Fact]
    public async Task Refused_paths_never_reach_the_engine()
    {
        var (proxy, engine) = Make(_ => Json(HttpStatusCode.OK, "{}"));
        var result = await proxy.SendAsync("GET", "/../etc", null);
        Assert.Equal(400, result.Status);
        Assert.Empty(engine.Seen);
    }

    [Fact]
    public async Task Streams_each_line_then_reports_success()
    {
        var (proxy, _) = Make(_ => Json(HttpStatusCode.OK, "{\"type\":\"token\",\"text\":\"Hi\"}\n\n{\"type\":\"done\"}\n"));
        var lines = new List<string>();
        var result = await proxy.StreamAsync("/ask", "{}", line =>
        {
            lines.Add(line);
            return Task.CompletedTask;
        });
        Assert.Equal(200, result.Status);
        Assert.Equal(["{\"type\":\"token\",\"text\":\"Hi\"}", "{\"type\":\"done\"}"], lines);
    }

    [Fact]
    public async Task A_refused_stream_returns_the_engines_explanation()
    {
        var (proxy, _) = Make(_ => Json(HttpStatusCode.Conflict, """{"detail":"Still indexing"}"""));
        var result = await proxy.StreamAsync("/ask", "{}", _ => Task.CompletedTask);
        Assert.Equal(new ProxyResponse(409, """{"detail":"Still indexing"}"""), result);
    }

    [Fact]
    public async Task An_unreachable_engine_is_a_503_problem()
    {
        var (proxy, _) = Make(_ => throw new HttpRequestException("connection refused"));
        var result = await proxy.SendAsync("GET", "/library", null);
        Assert.Equal(503, result.Status);
        Assert.Contains("connection refused", result.Body);
    }
}
