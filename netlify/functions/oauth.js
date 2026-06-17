const https = require("https");

function exchangeCode(code, redirectUri, clientId, clientSecret) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      redirect_uri: redirectUri,
    });

    const req = https.request(
      {
        hostname: "github.com",
        path: "/login/oauth/access_token",
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "Content-Length": Buffer.byteLength(data),
        },
      },
      (res) => {
        let body = "";
        res.on("data", (chunk) => (body += chunk));
        res.on("end", () => {
          try {
            resolve(JSON.parse(body));
          } catch (e) {
            reject(new Error("Invalid JSON from GitHub"));
          }
        });
      }
    );
    req.on("error", reject);
    req.write(data);
    req.end();
  });
}

exports.handler = async (event) => {
  const CLIENT_ID = process.env.CMS_GITHUB_CLIENT_ID;
  const CLIENT_SECRET = process.env.CMS_GITHUB_CLIENT_SECRET;

  if (!CLIENT_ID || !CLIENT_SECRET) {
    return {
      statusCode: 500,
      body: "Missing CMS_GITHUB_CLIENT_ID or CMS_GITHUB_CLIENT_SECRET env vars",
    };
  }

  const proto = event.headers["x-forwarded-proto"] || "https";
  const host = event.headers["host"];
  const currentUrl = `${proto}://${host}${event.path}`;

  const code = (event.queryStringParameters || {}).code;

  if (!code) {
    const params = new URLSearchParams({
      client_id: CLIENT_ID,
      redirect_uri: currentUrl,
      scope: "repo,user",
    });

    return {
      statusCode: 302,
      headers: {
        Location: `https://github.com/login/oauth/authorize?${params.toString()}`,
      },
    };
  }

  try {
    const result = await exchangeCode(code, currentUrl, CLIENT_ID, CLIENT_SECRET);
    const token = result.access_token;

    if (!token) {
      const errMsg = (result.error_description || result.error || "No token").replace(/'/g, "\\'");
      return {
        statusCode: 200,
        headers: { "Content-Type": "text/html" },
        body: `<!DOCTYPE html><html><body><script>
window.opener.postMessage('authorization:github:success',{token:'${errMsg}'},'*');
window.close();
</script></body></html>`,
      };
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "text/html" },
      body: `<!DOCTYPE html><html><body><script>
window.opener.postMessage('authorization:github:success',{token:'${token}'},'*');
window.close();
</script></body></html>`,
    };
  } catch (err) {
    return { statusCode: 500, body: `OAuth error: ${err.message}` };
  }
};
