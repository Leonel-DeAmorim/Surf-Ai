//Use Node's HTTP module which provides functionality needed to create and run the server
const http = require("http");
//Use querystring module to parse data received in the HTTP request body
const querystring = require("querystring");


//Store latest player data
let latestData= null;
const HISTORY_WINDOW_MS = 2000;
const MAX_HISTORY_SAMPLES = 500;
const telemetryHistory = [];
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


function pruneHistory(now = Date.now()){
    const cutoff = now - HISTORY_WINDOW_MS;

    while(telemetryHistory.length > 0 && telemetryHistory[0].timestampMs < cutoff){
        telemetryHistory.shift();
    }
    while (telemetryHistory.length > MAX_HISTORY_SAMPLES){
        telemetryHistory.shift();
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
            historySamples: telemetryHistory.length

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
            historySamples: telemetryHistory.length
        });
    }

    //Send the latest player state to Python
    if (req.method === "GET" && req.url === "/latest"){
        return sendJSON( res, 200, latestData);
    }

if (req.method === "GET" && req.url.startsWith("/history")) {
    const url = new URL(req.url, "http://127.0.0.1:8080");

    const sinceParam = url.searchParams.get("since");
    const afterIdParam = url.searchParams.get("afterId");
    const limitParam = url.searchParams.get("limit");

    let since = sinceParam === null ? null : Number(sinceParam);
    let afterId = afterIdParam === null ? null : Number(afterIdParam);
    let limit = limitParam === null ? MAX_HISTORY_SAMPLES : Number(limitParam);

    if (since !== null && !Number.isFinite(since)) {
        return sendJSON(res, 400, { error: "Invalid since timestamp." });
    }

    if (afterId !== null &&
        (!Number.isSafeInteger(afterId) || afterId < 0)) {
        return sendJSON(res, 400, { error: "Invalid afterId." });
    }

    if (!Number.isSafeInteger(limit) || limit < 1) {
        return sendJSON(res, 400, { error: "Invalid limit." });
    }

    limit = Math.min(limit, MAX_HISTORY_SAMPLES);

    pruneHistory();

    let samples = telemetryHistory.filter(sample => {
        if (since !== null && sample.timestampMs <= since) return false;
        if (afterId !== null && sample.sampleId <= afterId) return false;

        return true;
    });

    samples = samples.slice(0, limit);

    return sendJSON(res, 200, {
        count: samples.length,
        samples: samples,
        oldestTimestampMs: telemetryHistory.length
            ? telemetryHistory[0].timestampMs
            : null,
        latestTimestampMs: latestData
            ? latestData.timestampMs
            : null,
        latestSampleId: latestData
            ? latestData.sampleId
            : null
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

            for (const data of batch) {
                const sample = {
                    ...data,
                    sampleId: nextSampleId++,
                    serverReceivedAtMs: serverReceivedAtMs,
                    transportDelayMs:
                        serverReceivedAtMs - data.timestampMs
                };

                if(latestData === null || sample.timestampMs >= latestData.timestampMs){
                    latestData = sample;
                }
                if (sample.timestampMs >= serverReceivedAtMs - HISTORY_WINDOW_MS){
                    telemetryHistory.push(sample);
                }
                stats.received++;
                stats.totalDelayMs += sample.transportDelayMs;
                stats.maxDelayMs = Math.max(
                    stats.maxDelayMs,
                    sample.transportDelayMs
                );

            }

            pruneHistory(serverReceivedAtMs);
            reportStats(serverReceivedAtMs);

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

if (req.method === "POST" && req.url === "/test") {

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

            const data = JSON.parse(rawPayload);

            if (
                data === null ||
                typeof data !== "object" ||
                Array.isArray(data) ||
                typeof data.timestampMs !== "number" ||
                !Number.isFinite(data.timestampMs)
            ) {
                return sendJSON(res, 400, {
                    error: "Invalid timestampMs."
                });
            }

            const serverReceivedAtMs = Date.now();

            const sample = {
                ...data,
                sampleId: nextSampleId++,
                serverReceivedAtMs: serverReceivedAtMs,
                transportDelayMs:
                    serverReceivedAtMs - data.timestampMs
            };

            if(latestData === null || sample.timestampMs >= latestData.timestampMs){
                    latestData = sample;
                }

             if (sample.timestampMs >= serverReceivedAtMs - HISTORY_WINDOW_MS){
                    telemetryHistory.push(sample);
                }

            pruneHistory(serverReceivedAtMs);

            stats.received++;
            stats.totalDelayMs += sample.transportDelayMs;
            stats.maxDelayMs = Math.max(
                stats.maxDelayMs,
                sample.transportDelayMs
            );

            reportStats(serverReceivedAtMs);

            return sendJSON(res, 200, {
                ok: true,
                sampleId: sample.sampleId
            });

        } catch (error) {
            console.error("Failed to process telemetry:", error.message);

            return sendJSON(res, 400, {
                error: "Invalid telemetry payload."
            });
        }
    });

    return;
}


    //Return a 404 Not Found response for requests that don't match the POST/test endpoint
    res.writeHead(404);
    res.end("Not found");
});
//Start the server on localhost at port 8080
server.listen(8080, "127.0.0.1", () => {
    //Confirm in the terminal that the server has started successfully
    console.log("Server listening on http://127.0.0.1:8080");
});
