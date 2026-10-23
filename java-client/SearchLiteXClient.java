import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;

/** Dependency-free Java 21 REST client for the Python SearchLiteX engine. */
public class SearchLiteXClient {
    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("Usage: java SearchLiteXClient.java <search terms>");
            System.exit(2);
        }
        String query = String.join(" ", args);
        String api = System.getenv().getOrDefault("SEARCHLITEX_URL", "http://localhost:8000");
        String target = api + "/api/search?q=" + URLEncoder.encode(query, StandardCharsets.UTF_8);
        var request = HttpRequest.newBuilder(URI.create(target)).GET().build();
        var response = HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() != 200) {
            System.err.println("Search failed: HTTP " + response.statusCode());
            System.exit(1);
        }
        System.out.println(response.body());
    }
}
