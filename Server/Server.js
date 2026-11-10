//Use Node's HTTP module which provides functionality needed to create and run the server
const http = require("http");
//Use querystring module to parse data received in the HTTP request body
const querystring = require("querystring");
const WebSocket = require("ws");


let nextSampleId = 1;

let stats = {
    received: 0,
    totalDelayMs: 0 ,
    maxDelayMs: 0,
    lastReportsMs: Date.now()
};


function sendJSON(res, statusCode, data){
    res.writeHead(statusCode,{
        "Content-Type": "application/json",
        "Cache-Control": "no-store"
    });
    res.end(JSON.stringify(data));
}
function broadcastTelemetry(samples) {
    if (wss.clients.size === 0) return;

    const message = JSON.stringify({
        type: "telemetry",
        samples: samples
    });

    for (const client of wss.clients) {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message, error => {
                if (error) {
                    console.error("WebSocket send error:", error.message);
                }
            });
        }
    }
}

function reportStats(now){
    if(now - stats.lastReportsMs < 2000){
        return;
    }
    if(stats.received > 0 ){
        console.log({
            samplesReceived: stats.received,
            averageTransportDelayMs:
                Number((stats.totalDelayMs / stats.received).toFixed(2)),
            maxTransportDelayMs: stats.maxDelayMs,

        });
    }
    stats = {
        received : 0 ,
        totalDelayMs: 0 ,
        maxDelayMs: 0,
        lastReportsMs: now
    };
}

//Create the HTTP server and handle incoming requests
const server = http.createServer((req, res) => {

    //Server Health check endpoint
    if (req.method === "GET" && req.url === "/health") {
        return sendJSON(res, 200, {
            status: "online",
            timestampMs: Date.now(),
        });
    }
if (req.method === "POST" && req.url === "/batch") {
    let body = "";

    req.setEncoding("utf8");

    req.on("data", chunk => {
        body += chunk;
    });

    req.on("end", () => {
        try {
            const formData = querystring.parse(body);
            const batch = JSON.parse(formData.payload);

            if (
                !Array.isArray(batch) ||
                batch.length === 0 ||
                batch.length > 100
            ) {
                throw new Error("Invalid batch size.");
            }

            for (const data of batch) {
                if (
                    !data ||
                    typeof data !== "object" ||
                    Array.isArray(data) ||
                    typeof data.timestampMs !== "number" ||
                    !Number.isFinite(data.timestampMs)
                ) {
                    throw new Error("Invalid telemetry sample.");
                }
            }

            const serverReceivedAtMs = Date.now();

            const samples = batch.map(data => ({
                ...data,
                sampleId: nextSampleId++,
                serverReceivedAtMs,
                transportDelayMs: serverReceivedAtMs - data.timestampMs
            }));

            for (const sample of samples) {
                stats.received++;
                stats.totalDelayMs += sample.transportDelayMs;
                stats.maxDelayMs = Math.max(
                    stats.maxDelayMs,
                    sample.transportDelayMs
                );
            }

            reportStats(serverReceivedAtMs);
            broadcastTelemetry(samples);

            return sendJSON(res, 200, {
                ok: true,
                accepted: samples.length,
                latestSampleId: samples[samples.length - 1].sampleId
            });

        } catch (error) {
            console.error("[Server] Batch error:", error.message);

            return sendJSON(res, 400, {
                error: error.message
            });
        }
    });

    return;
    }

    return sendJSON(res, 404, {
        error: "Not found."
    });
});

const wss = new WebSocket.Server({ noServer: true });

// Handle WebSocket upgrade requests
server.on("upgrade", (req, socket, head) => {
    const pathname = new URL(
        req.url,
        "http://127.0.0.1:8080"
    ).pathname;

    if (pathname !== "/ws") {
        socket.destroy();
        return;
    }

    wss.handleUpgrade(req, socket, head, ws => {
        wss.emit("connection", ws, req);
    });
});

// Handle new Python connections
wss.on("connection", ws => {
    console.log("[WebSocket] Python client connected.");

    // Tell Python the latest sample ID so it can avoid old data
    ws.send(JSON.stringify({
        type: "connected",
        latestSampleId: nextSampleId - 1
    }));

    ws.on("close", () => {
        console.log("[WebSocket] Python client disconnected.");
    });

    ws.on("error", error => {
        console.error("[WebSocket] Error:", error.message);
    });
});
//Start the server on localhost at port 8080
server.listen(8080, "127.0.0.1", () => {
    //Confirm in the terminal that the server has started successfully
    console.log("Server listening on http://127.0.0.1:8080");
});