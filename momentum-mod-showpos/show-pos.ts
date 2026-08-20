import { PanelHandler } from 'util/module-helpers';
import { CustomizerPropertyType, registerHUDCustomizerComponent } from 'common/hud-customizer';
import { getTextShadowFast } from 'common/hud-customizer';


//Server 
const ServerPost = () => {
    const angles = MomentumPlayerAPI.GetAngles();
    const velocity = MomentumPlayerAPI.GetVelocity();
    const energy = MomentumPlayerAPI.GetEnergy();
    const strafeSync0 = MomentumPlayerAPI.GetStrafeSync(0);
    const strafeSync1 = MomentumPlayerAPI.GetStrafeSync(1);
    const moveType = MomentumMovementAPI.GetMoveType();
    const moveHud = MomentumMovementAPI.GetMoveHudData();
    const lastTick = MomentumMovementAPI.GetLastTickStats();
    const currentTime = MomentumMovementAPI.GetCurrentTime();
    const ducking = MomentumPlayerAPI.IsDucking();
    const sprinting = MomentumPlayerAPI.IsSprinting();
    const walking = MomentumPlayerAPI.IsWalking();
    const buttons = MomentumInputAPI.GetButtons();

    const data = {
        time: currentTime,
        angles: JSON.stringify(angles),
        velocity: JSON.stringify(velocity),
        energy: energy,
        strafeSync0: strafeSync0,
        strafeSync1: strafeSync1,
        moveType: moveType,
        moveHud: JSON.stringify(moveHud),
        lastTick: JSON.stringify(lastTick),
        ducking: ducking,
        sprinting: sprinting,
        walking: walking,

        buttons: JSON.stringify(buttons)
    };

    $.AsyncWebRequest('http://127.0.0.1:8080/test', {
        type: 'POST',
        data: data,
    }as any);
};


const requestLoop = () => {
    ServerPost();

    $.Schedule(0, requestLoop);
};



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
