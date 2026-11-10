//Use Node's HTTP module which provides functionality needed to create and run the server
const http = require("http");
//Use querystring module to parse data received in the HTTP request body
const querystring = require("querystring");
const WebSocket = require("ws");

//Store latest player data
let latestData= null;
let nextSampleId = 1;



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

    req.on("data", chunk => {
        body += chunk;
    });

    req.on("end", () => {
        try {
            const formData = querystring.parse(body);
            const rawPayload = formData.payload;

            if (typeof rawPayload !== "string") {
                return sendJSON(res, 400, {
                    error: "Missing or invalid payload."
                });
            }

            const batch = JSON.parse(rawPayload);

            if (
                !Array.isArray(batch) ||
                batch.length === 0 ||
                batch.length > 100
            ) {
                return sendJSON(res, 400, {
                    error: "Batch must contain between 1 and 100 samples."
                });
            }

            // Validate the entire batch before storing anything.
            for (const data of batch) {
                if (
                    data === null ||
                    typeof data !== "object" ||
                    Array.isArray(data) ||
                    typeof data.timestampMs !== "number" ||
                    !Number.isFinite(data.timestampMs)
                ) {
                    return sendJSON(res, 400, {
                        error: "Invalid telemetry sample in batch."
                    });
                }
            }

            const serverReceivedAtMs = Date.now();
            const acceptedSamples = [];
            for (const data of batch) {
                const sample = {
                    ...data,
                    sampleId: nextSampleId++,
                    serverReceivedAtMs: serverReceivedAtMs,
                    transportDelayMs:
                        serverReceivedAtMs - data.timestampMs
                };
                acceptedSamples.push(sample);
                if(latestData === null || sample.timestampMs >= latestData.timestampMs){
                    latestData = sample;
                }
            }

            broadcastTelemetry(acceptedSamples);
            return sendJSON(res, 200, {
                ok: true,
                accepted: batch.length,
                latestSampleId: latestData.sampleId
            });

        } catch (error) {
            console.error("Failed to process telemetry batch:", error.message);

            return sendJSON(res, 400, {
                error: "Invalid telemetry batch."
            });
        }
    });

    return;
}
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
// Create WebSocket server using the existing HTTP server
