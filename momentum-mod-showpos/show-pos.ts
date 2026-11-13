import { PanelHandler } from 'util/module-helpers';
import { CustomizerPropertyType, registerHUDCustomizerComponent } from 'common/hud-customizer';
import { getTextShadowFast } from 'common/hud-customizer';

//Use Panorama API to enable cl_showpos 1 allowing us to read player's X,Y and Z coordinates from the HUD
 GameInterfaceAPI.ConsoleCommand('cl_showpos 1');
const COLLECTION_INTERVAL_SECONDS = 0;

const BATCH_SIZE = 5;
const MAX_QUEUE_SIZE = 50;
const MAX_BATCH_WAIT_MS = 5;

const MAX_CONCURRENT_REQUESTS = 15;
let activeRequests = 0;

let telemetryQueue = [];

let windowSamples = 0;
let windowDropped = 0;
let windowSent = 0;
let windowStartMs = Date.now();

//Collect the current player state and send it to our local server 
const ServerPost = () => {
    const collectionTimestampMs = Date.now();

//Store the player's current position 
//Set to null because the position may not be available in some states such as during map selection
//If a valid position is found it will be stored here
let position = null;

//Get the current UI context panel and its child panels 
const cp = $.GetContextPanel();
const children = cp.Children();

//Look for panel containing the cl_showpos position display
if (children.length > 0) {
    const showPosPanel = children[0];
    const labels = showPosPanel.Children();

    //Through testing the first label contains the player position we want (labels[0])
    //The second label contains the view angle (labels[1])
    if (labels.length > 0) {
        const posLabel = labels[0] as Label;

        //We make sure the label exists and contains position value
        if (posLabel && posLabel.text.startsWith('Pos:')) {
            //Remove "Pos:" and split the remaining position string into individual values
            //Each value is then converted from a string into a number
            //Example "Pos: 100 200 300" will then become [100, 200, 300]
            const values = posLabel.text
                .replace('Pos:', '')
                .trim()
                .split(/\s+/)
                .map(Number);

            //Accept the position if we receive exactly 3 valid numbers, then assign the values at each index to X, Y, and Z
            if (values.length === 3 && values.every(Number.isFinite)) {
                position = {
                    x: values[0],
                    y: values[1],
                    z: values[2]
                };
            }
        }
    }
}


    //Get player's current view angles
    const angles = MomentumPlayerAPI.GetAngles();
    //Get player's velocity 
    const velocity = MomentumPlayerAPI.GetVelocity();
    //Get player's movement energy 
    const energy = MomentumPlayerAPI.GetEnergy();
    //Get movement wishVel 
    const wishVel = MomentumMovementAPI.GetMoveHudData().wishVel;
    //Get Momentum Timer
    const timer = MomentumTimerAPI.GetObservedTimerStatus();

    const runTimer = timer.runTime;
    //Get Majornum
    const majorNum = timer.majorNum;
    //Get Minor num
    const minorNum =timer.minorNum;
    //Get seg countgame
    const segmentsCount = timer.segmentsCount;
    //Get check count
    const segmentCheckpointsCount  = timer.segmentCheckpointsCount;
    //Get statistics from the player's previous movement tick 
    const lastTick = MomentumMovementAPI.GetLastTickStats();
    //Get current game time 
    const gameTime = MomentumMovementAPI.GetCurrentTime();
    //Check which movement states the player is in 
    const ducking = MomentumPlayerAPI.IsDucking();
    //Get  player's input buttons 
    const physicalButtons = MomentumInputAPI.GetButtons().physicalButtons;
    //Get player movement type
    const moveType = MomentumMovementAPI.GetMoveType();
    //Get Tick interval
    const tickInterval = MomentumMovementAPI.GetTickInterval();
    //Get map name
    const mapName = MapCacheAPI.GetMapName();
    const speed = Math.sqrt(velocity.x * velocity.x + velocity.y * velocity.y + velocity.z * velocity.z);

    //Combine all the collected player/game information into a single object
    //This object will be converted to JSON before being sent to the server
    const data = {
    timestampMs: collectionTimestampMs,
    runTime: runTimer,
    position: position,
    angles: angles,
    velocity: velocity,
    speed: speed,
    energy: energy,
    wishVel: wishVel,
    gameTime: gameTime,
    majorNum: majorNum,
    minorNum: minorNum,
    segmentsCount: segmentsCount,
    segmentCheckpointsCount: segmentCheckpointsCount,
    lastTick: lastTick,
    ducking: ducking,
    moveType: moveType,
    tickInterval: tickInterval,
    mapName: mapName,
    physicalButtons: physicalButtons
};


if (telemetryQueue.length >= MAX_QUEUE_SIZE) {
    telemetryQueue.shift();
    windowDropped++;
}

telemetryQueue.push({
    data: data,
    queuedAtMs: Date.now()
});
windowSamples++;

};
    //Create a loop that continuously sends updated player data to the server


const sendBatch = () => {
    while (
        activeRequests < MAX_CONCURRENT_REQUESTS &&
        telemetryQueue.length > 0
    ) {
        const oldestQueuedAtMs = telemetryQueue[0].queuedAtMs;

        const batchExpired =
            Date.now() - oldestQueuedAtMs >= MAX_BATCH_WAIT_MS;

        if (
            telemetryQueue.length < BATCH_SIZE &&
            !batchExpired
        ) {
            return;
        }

        const queuedBatch = telemetryQueue.splice(0, BATCH_SIZE);
        const batch = queuedBatch.map(item => item.data);

        activeRequests++;

        $.AsyncWebRequest('http://127.0.0.1:8080/batch', {
            type: 'POST',
            data: {
                payload: JSON.stringify(batch)
            },
            success: () => {
                activeRequests--;
                windowSent += batch.length;
                sendBatch();
            },
            error: () => {
                activeRequests--;
                windowDropped += batch.length;
                sendBatch();
            }
        } as any);
    }
};

 const requestLoop = () => {

    ServerPost();

    sendBatch();

    const now = Date.now();

    if (now - windowStartMs >= 2000) {

        const elapsedSeconds = (now - windowStartMs) / 1000;

        $.Msg(
            `[Telemetry] Collection: ${(windowSamples / elapsedSeconds).toFixed(1)} Hz | ` +
            `Sent: ${windowSent} | ` +
            `Dropped: ${windowDropped} | ` +
            `Queue: ${telemetryQueue.length}` +
            `Active Requests: ${activeRequests}`
        );

        windowSamples = 0;
        windowSent = 0;
        windowDropped = 0;
        windowStartMs = now;
    }

    $.Schedule(COLLECTION_INTERVAL_SECONDS, requestLoop);
};
// Start collection
requestLoop();
    

@PanelHandler()
class HudShowPosHandler {
	constructor() {
		registerHUDCustomizerComponent($.GetContextPanel(), {
			name: $.Localize('#Customizer_Show_Pos_Name'),
			resizeX: true,
			resizeY: false,
			dynamicStyles: {
				fontStyling: {
					name: $.Localize('#Customizer_FontStyling'),
					type: CustomizerPropertyType.NONE,
					expandable: true,
					children: [{ styleID: 'font' }, { styleID: 'fontSize' }, { styleID: 'fontColor' }]
				},
				font: {
					name: $.Localize('#Customizer_Font'),
					type: CustomizerPropertyType.FONT_PICKER,
					targetPanel: '.showpos-entry__label',
					styleProperty: 'fontFamily',
					valueFn: (value) => `"${value}"`
				},
				fontSize: {
					name: $.Localize('#Customizer_FontSize'),
					type: CustomizerPropertyType.NUMBER_ENTRY,
					targetPanel: '.showpos-entry__label',
					styleProperty: 'fontSize',
					valueFn: (value) => `${value}px`
				},
				fontColor: {
					name: $.Localize('#Customizer_FontColor'),
					type: CustomizerPropertyType.COLOR_PICKER,
					targetPanel: '.showpos-entry__label',
					styleProperty: 'color',
					callbackFunc: (panel, value) =>
						(panel.style.textShadowFast = getTextShadowFast(value as rgbaColor, 0.9))
				},
				backgroundColor: {
					name: $.Localize('#Customizer_BackgroundColor'),
					type: CustomizerPropertyType.COLOR_PICKER,
					targetPanel: '.showpos-entry',
					styleProperty: 'backgroundColor'
				},
				alignText: {
					name: $.Localize('#Customizer_AlignText'),
					type: CustomizerPropertyType.DROPDOWN,
					options: [
						{ label: 'Left', value: 'left' },
						{ label: 'Center', value: 'center' },
						{ label: 'Right', value: 'right' }
					],
					targetPanel: ['.showpos-entry', '.showpos-entry__label'],
					styleProperty: 'horizontalAlign'
				}
			}
		});
	}
}
