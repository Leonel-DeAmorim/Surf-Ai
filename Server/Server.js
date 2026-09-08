//Use Node's HTTP module which provides functionality needed to create and run the server
const http = require("http");
//Use querystring module to parse data received in the HTTP request body
const querystring = require("querystring");

//File system module to read HTML, CSS and JavaScript files
const fs = require("fs");

//Store all connected clients so they can receive updates through SSE
let client=[];

//Store latest player data
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
            //Send latest game data to all connected clients if latestData exists
            if(latestData !== null){
            for (const clientRes of client){
                clientRes.write("data: "+ JSON.stringify(latestData) + "\n\n");
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
        //Set response headers required for SSE
        res.writeHead(200, {
        //Tell browser that the response will contain event stream
        "Content-Type": "text/event-stream",
        //Prevent browser from caching the event stream
        "Cache-Control": "no-cache",
        //Keep connection open so server can send future updates
        "Connection": "keep-alive"
        });
        //Add connected client to the list of clients receiving updates
        client.push(res);
        //Remove client when the connection is closed
        req.on("close", () => {
            client = client.filter(clientRes => clientRes !== res);
        });
        //Keep SSE connection open
        return; 
       
    }

    //Handle a GET request for the main dashboard page
    if(req.method === "GET" && req.url === '/'){
        //Read the Dashboard.html file from the server
        fs.readFile("Dashboard.html", (error,data) => { 
            //If the HTML file cannot be read then send a server error
            if(error){
                res.writeHead(500,{"content-type": "text/plain"})
                res.end("Server Error");
                return;
            }
            //If the file was read successfully then send it to browser
            else{
                res.writeHead(200, {'Content-Type': 'text/html'});
                res.end(data);
            }
        }
    );
    //Stop processing request
    return;
    }

    //Handle a GET request for the dashboard CSS file
    if(req.method === "GET" && req.url === '/Dashboard.css'){
        //Read the Dashboard.css file from the server
        fs.readFile("Dashboard.css", (error,data) =>{
            //If the CSS file cannot be read then send server error
          if(error){
                res.writeHead(500,{"content-type": "text/plain"})
                res.end("Server Error");
                return;
            }
            //If the file was read successfully then send it to browser
            else{
            res.writeHead(200, {'Content-Type': 'text/css'});
            res.end(data);        
            }
        });
        //Stop processing this request
        return;

    }
        //Handle a GET request for the dashboard JS file
        if(req.method === "GET" && req.url === '/Dashboard.js'){
        //Read the Dashboard.js file from the server
        fs.readFile("Dashboard.js", (error,data) =>{
          //If the Javascript file cannot be read then send a server error
          if(error){
                res.writeHead(500,{"content-type": "text/plain"})
                res.end("Server Error");
                return;
            }
            //If the file was read successfully then send it to browser
            else{
            res.writeHead(200, {'Content-Type': 'text/javascript'});
            res.end(data);        
            }
        })
        //Stop processing request
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
