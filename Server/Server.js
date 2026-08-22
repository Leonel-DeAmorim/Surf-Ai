const http = require("http");
const querystring = require("querystring");

const server = http.createServer((req, res) => {

    if (req.method === "POST" && req.url === "/test") {
    
        let body = "";

        req.on("data", chunk => {
            body += chunk;
        });

        req.on("end", () => {
            
            try {

            const formData = querystring.parse(body);
            const data = JSON.parse(formData.payload);


                console.clear();

                console.log("--------- GAME DATA ----------");
                console.log(data);
                console.log("------------------------------");

                res.writeHead(200);
                res.end("OK");

            } catch (error) {

                console.error("Failed to parse data:", error);

                res.writeHead(400);
                res.end("Invalid data");
            }
        });

        return;
    }

    res.writeHead(404);
    res.end("Not found");
});

server.listen(8080, "127.0.0.1", () => {
    console.log("Server listening on http://127.0.0.1:8080");
});