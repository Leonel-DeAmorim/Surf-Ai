import { PanelHandler } from 'util/module-helpers';
import { CustomizerPropertyType, registerHUDCustomizerComponent } from 'common/hud-customizer';
import { getTextShadowFast } from 'common/hud-customizer';

//Use Panorama API to enable cl_showpos 1 allowing us to read player's X,Y and Z coordinates from the HUD
 GameInterfaceAPI.ConsoleCommand('cl_showpos 1');


//Collect the current player state and send it to our local server 
const ServerPost = () => {

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
    //Get player's strafe synchronization data
    const strafeSync0 = MomentumPlayerAPI.GetStrafeSync(0);
    const strafeSync1 = MomentumPlayerAPI.GetStrafeSync(1);
    //Get player's movement type 
    const moveType = MomentumMovementAPI.GetMoveType();
    //Get movement related HUD information 
    const moveHud = MomentumMovementAPI.GetMoveHudData();
    //Get statistics from the player's previous movement tick 
    const lastTick = MomentumMovementAPI.GetLastTickStats();
    //Get current game time 
    const currentTime = MomentumMovementAPI.GetCurrentTime();
    //Check which movement states the player is in 
    const ducking = MomentumPlayerAPI.IsDucking();
    const sprinting = MomentumPlayerAPI.IsSprinting();
    const walking = MomentumPlayerAPI.IsWalking();
    //Get  player's input buttons 
    const buttons = MomentumInputAPI.GetButtons();

    //Combine all the collected player/game information into a single object
    //This object will be converted to JSON before being sent to the server
    const data = {
    time: currentTime,
    position: position,
    angles: angles,
    velocity: velocity,
    energy: energy,
    strafeSync0: strafeSync0,
    strafeSync1: strafeSync1,
    moveType: moveType,
    moveHud: moveHud,
    lastTick: lastTick,
    ducking: ducking,
    sprinting: sprinting,
    walking: walking,
    buttons: buttons
};
    //Send collected data to local server 
    //Data object is converted to JSON and sent as payload
    $.AsyncWebRequest('http://127.0.0.1:8080/test', {
    type: 'POST',
    data: {
        payload: JSON.stringify(data)
    }
} as any);
};

    //Create a loop that continuously sends updated player data to the server
    const requestLoop = () => {
    ServerPost();
    //Schedule this function to run at delay 0
    //This means we run it as the scheduling system allows which after testing appeared to be ~200 times a second or about every 5ms
    $.Schedule(0, requestLoop);
    };
    //Start data collection/sending loop
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
