//Use Node's HTTP module which provides functionality needed to create and run the server
const http = require("http");
//Use querystring module to parse data received in the HTTP request body
const querystring = require("querystring");

let client=[];
let latestData= null;

//Create the HTTP server and handle incoming requests
const server = http.createServer((req, res) => {

    //Only process POST requests sent to the /test endpoint
    if (req.method === "POST" && req.url === "/test") {
        
        //Initialize an empty string to store incoming request body
        let body = "";
        //Append each incoming chunk of data to the request body
        req.on("data", chunk => {
            body += chunk;
        });
        //Once all of the request data has been received we process it
        req.on("end", () => {
            
            try {
            //Parse the request body into an object
            const formData = querystring.parse(body);
            //Extract the JSON payload from the form data and parse it into a JavaScript object
            const data = JSON.parse(formData.payload);

                //Clear the console and print the received game data
                console.clear();

                console.log("--------- GAME DATA ----------");
                console.log(data);
                console.log("------------------------------");
                
            latestData=data;
            //Here we send data to client 
            if(latestData !== null){
            for (const res of client){
                res.write("data: "+ JSON.stringify(latestData) + "\n\n");
            }
        }
                //Send 200 OK response to indicate the data was received and processed successfully
                res.writeHead(200);
                res.end("OK");

            } catch (error) {
                //Log an error if the received data could not be parsed
                console.error("Failed to parse data:", error);
                //Return a 400 Bad Request response because received data was invalid
                res.writeHead(400);
                res.end("Invalid data");
            }
        });

        return;
    }


    //Create /event endpoint for SSE (Server-Sent Event)
    if (req.method === "GET" && req.url === "/event") {
        res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
        });

        client.push(res);

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