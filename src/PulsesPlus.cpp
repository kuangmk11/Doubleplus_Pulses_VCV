#include "plugin.hpp"

// Pulses Plus — a VCV Rack port of the hardware Turing Machine gate router.
//
// Eight pulse channels, each routed by a 3-position toggle to Bus A, off, or
// Bus B. Each bus continuously computes both the OR and the AND of whatever is
// routed to it; a per-bus mode toggle (OR / MUTE / AND) picks which one reaches
// the output.
//
// Input front end: VCV's Turing Machine (Stellare Modular) exposes its shift
// register to expanders over a private module bus, not as a patchable ribbon, so
// we reconstruct the eight bits ourselves. Feed the module the TM's stage-1 bit
// (BIT) and the same clock that drives the TM (CLOCK). Across each clock period we
// latch whether BIT pulsed, then shift that into our own 8-stage register; since
// stage k is stage 1 delayed by k-1 clocks, the local register mirrors the TM's
// BIT1..BIT8 (bit 8 included — the TM puts it on the bus but never uses it). The
// latch is what makes the Stellare port's hair-thin triggers usable: the register
// holds each bit for a full period, so the outputs are full-width gates.
//
// Faithful quirk from the hardware design doc: "AND of zero terms is vacuously
// true" — a bus in AND mode with nothing routed to it sits high. Kept as the
// default, with a context-menu switch to treat an empty bus as low instead.

// Routing toggle values (CKSSThreeHorizontal: value 0 = left throw, 2 = right)
static const int ROUTE_A = 0;    // left  → Bus A
static const int ROUTE_OFF = 1;  // centre → off
static const int ROUTE_B = 2;    // right → Bus B

static const int MODE_OR = 2;    // up
static const int MODE_MUTE = 1;  // centre
static const int MODE_AND = 0;   // down

static const float GATE_HIGH = 10.f;
static const float THRESH_HI = 1.0f;  // Schmitt-style thresholds on the inputs
static const float THRESH_LO = 0.2f;

struct PulsesPlus : Module {
	enum ParamId {
		ENUMS(ROUTE_PARAM, 8),
		MODE_A_PARAM,
		MODE_B_PARAM,
		PARAMS_LEN
	};
	enum InputId {
		CLOCK_INPUT,
		BIT_INPUT,
		INPUTS_LEN
	};
	enum OutputId {
		OUTA_OUTPUT,
		OUTB_OUTPUT,
		OUTPUTS_LEN
	};
	enum LightId {
		ENUMS(CH_LIGHT, 8),
		OUTA_LIGHT,
		OUTB_LIGHT,
		LIGHTS_LEN
	};

	bool reg[8] = {};   // local shift register: stage 0 = newest = BIT1
	bool bitSeen = false;   // BIT went high at least once since the last clock
	dsp::SchmittTrigger clockTrigger;   // rising-edge detect on CLOCK
	dsp::SchmittTrigger bitTrigger;     // level detect on BIT (hysteresis)
	bool andEmptyHigh = true;   // AND of zero routed channels is high (hardware behaviour)
	bool gateWithClock = true;  // pass outputs only while CLOCK is high (stock Pulses behaviour)

	PulsesPlus() {
		config(PARAMS_LEN, INPUTS_LEN, OUTPUTS_LEN, LIGHTS_LEN);
		for (int i = 0; i < 8; i++) {
			configSwitch(ROUTE_PARAM + i, 0.f, 2.f, ROUTE_OFF,
				string::f("Channel %d route", i + 1), {"Bus A", "Off", "Bus B"});
		}
		configSwitch(MODE_A_PARAM, 0.f, 2.f, MODE_OR, "Bus A mode", {"AND", "Mute", "OR"});
		configSwitch(MODE_B_PARAM, 0.f, 2.f, MODE_OR, "Bus B mode", {"AND", "Mute", "OR"});
		configInput(CLOCK_INPUT, "Clock (chain from the TM clock)");
		configInput(BIT_INPUT, "Bit (TM stage-1 / Pulses BIT1)");
		configOutput(OUTA_OUTPUT, "Bus A");
		configOutput(OUTB_OUTPUT, "Bus B");
	}

	void process(const ProcessArgs& args) override {
		// --- reconstruct the eight bits with a local shift register ----------
		// Latch any BIT activity across the whole clock period rather than
		// sampling the instant of the edge: VCV's Turing Machine emits a
		// hair-thin trigger per step, not the full-width ribbon level a hardware
		// TM presents, so an edge-instant sample would miss it. A pulse anywhere
		// in the period counts, and the register holds it until the next clock —
		// so the outputs come out as full-width gates.
		bitTrigger.process(inputs[BIT_INPUT].getVoltage(), THRESH_LO, THRESH_HI);
		if (bitTrigger.isHigh())
			bitSeen = true;
		if (clockTrigger.process(inputs[CLOCK_INPUT].getVoltage(), 0.1f, 1.0f)) {
			for (int i = 7; i > 0; i--)
				reg[i] = reg[i - 1];   // shift the pattern down
			reg[0] = bitSeen;          // did a pulse arrive since the last clock?
			bitSeen = false;           // rearm for the next period
		}
		bool p[8];
		for (int i = 0; i < 8; i++)
			p[i] = reg[i];

		// --- merge buses: OR and AND computed continuously for both ----------
		bool anyA = false, allA = true;
		bool anyB = false, allB = true;
		int cntA = 0, cntB = 0;
		for (int i = 0; i < 8; i++) {
			int route = (int) std::round(params[ROUTE_PARAM + i].getValue());
			if (route == ROUTE_A) {
				cntA++;
				anyA = anyA || p[i];
				allA = allA && p[i];
			}
			else if (route == ROUTE_B) {
				cntB++;
				anyB = anyB || p[i];
				allB = allB && p[i];
			}
		}
		bool aOr = anyA;
		bool bOr = anyB;
		bool aAnd = (cntA == 0) ? andEmptyHigh : allA;
		bool bAnd = (cntB == 0) ? andEmptyHigh : allB;

		// --- mode select -----------------------------------------------------
		int modeA = (int) std::round(params[MODE_A_PARAM].getValue());
		int modeB = (int) std::round(params[MODE_B_PARAM].getValue());
		bool outA = (modeA == MODE_OR) ? aOr : (modeA == MODE_AND) ? aAnd : false;  // else MUTE
		bool outB = (modeB == MODE_OR) ? bOr : (modeB == MODE_AND) ? bAnd : false;

		// --- clock-gate the outputs ------------------------------------------
		// Like the stock Pulses expander (bit AND clock): the jack passes the bus
		// result only while CLOCK is high, so the output width follows the clock
		// pulse fed in and every step re-fires — a bit that stays set across steps
		// still gives a clean falling+rising edge instead of one held gate.
		//
		// One exception mirrors the board: an AND bus with nothing routed to it
		// isn't driven by any clocked bit — it's just its pull-up — so it sits at
		// DC high and bypasses the gate rather than being chopped into a clock.
		bool aEmptyAndHigh = (modeA == MODE_AND) && (cntA == 0) && andEmptyHigh;
		bool bEmptyAndHigh = (modeB == MODE_AND) && (cntB == 0) && andEmptyHigh;
		bool clockHigh = clockTrigger.isHigh();
		if (gateWithClock) {
			outA = outA && (clockHigh || aEmptyAndHigh);
			outB = outB && (clockHigh || bEmptyAndHigh);
		}

		outputs[OUTA_OUTPUT].setVoltage(outA ? GATE_HIGH : 0.f);
		outputs[OUTB_OUTPUT].setVoltage(outB ? GATE_HIGH : 0.f);

		// --- LEDs: channels show the held bit; outputs show the (gated) jack -
		for (int i = 0; i < 8; i++)
			lights[CH_LIGHT + i].setBrightnessSmooth(p[i] ? 1.f : 0.f, args.sampleTime);
		lights[OUTA_LIGHT].setBrightnessSmooth(outA ? 1.f : 0.f, args.sampleTime);
		lights[OUTB_LIGHT].setBrightnessSmooth(outB ? 1.f : 0.f, args.sampleTime);
	}

	json_t* dataToJson() override {
		json_t* root = json_object();
		json_object_set_new(root, "andEmptyHigh", json_boolean(andEmptyHigh));
		json_object_set_new(root, "gateWithClock", json_boolean(gateWithClock));
		return root;
	}

	void dataFromJson(json_t* root) override {
		json_t* j = json_object_get(root, "andEmptyHigh");
		if (j) andEmptyHigh = json_boolean_value(j);
		json_t* g = json_object_get(root, "gateWithClock");
		if (g) gateWithClock = json_boolean_value(g);
	}
};

// Horizontal Befaco toggle: the stock BefacoSwitch art rotated 90° (frames baked
// by res-src/rotate_befaco.py) so the lever throws left = Bus A, right = Bus B.
struct BefacoSwitchHoriz : app::SvgSwitch {
	BefacoSwitchHoriz() {
		addFrame(Svg::load(asset::plugin(pluginInstance, "res/BefacoSwitchHoriz_0.svg")));
		addFrame(Svg::load(asset::plugin(pluginInstance, "res/BefacoSwitchHoriz_1.svg")));
		addFrame(Svg::load(asset::plugin(pluginInstance, "res/BefacoSwitchHoriz_2.svg")));
	}
};

// Layout in millimetres — MUST match res-src/gen_panel.py.
static const float W_MM = 8 * 5.08f;
static const float CX = W_MM / 2;
static const float COL_L = CX - 12.28f;   // 8.04 — left toggle column
static const float COL_R = CX + 12.28f;   // 32.60 — right toggle column
static const float CH_ROW0 = 16.5f;
static const float CH_PITCH = 7.2f;
static const float CH_LED_RISE = 2.5f;    // channel LED rides above its toggle row
static const float IN_Y = 78.0f;          // CLOCK / BIT input row
static const float BUS_LED_Y = 88.0f;
static const float BUS_SW_Y = 97.5f;
static const float OUT_Y = 109.0f;

struct PulsesPlusWidget : ModuleWidget {
	PulsesPlusWidget(PulsesPlus* module) {
		setModule(module);
		setPanel(createPanel(asset::plugin(pluginInstance, "res/PulsesPlus.svg")));

		addChild(createWidget<ScrewSilver>(Vec(RACK_GRID_WIDTH, 0)));
		addChild(createWidget<ScrewSilver>(Vec(box.size.x - 2 * RACK_GRID_WIDTH, 0)));
		addChild(createWidget<ScrewSilver>(Vec(RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
		addChild(createWidget<ScrewSilver>(Vec(box.size.x - 2 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));

		// channel routing toggles (horizontal Befaco, zig-zag columns: left = Bus
		// A, right = Bus B) + channel LEDs on the centre spine
		for (int i = 0; i < 8; i++) {
			float y = CH_ROW0 + i * CH_PITCH;
			float sx = (i % 2 == 0) ? COL_L : COL_R;
			addParam(createParamCentered<BefacoSwitchHoriz>(mm2px(Vec(sx, y)), module, PulsesPlus::ROUTE_PARAM + i));
			addChild(createLightCentered<MediumLight<YellowLight>>(mm2px(Vec(CX, y - CH_LED_RISE)), module, PulsesPlus::CH_LIGHT + i));
		}

		// CLOCK + BIT inputs (feed the local shift register)
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(CX - 6.5f, IN_Y)), module, PulsesPlus::CLOCK_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(CX + 6.5f, IN_Y)), module, PulsesPlus::BIT_INPUT));

		// bus mode toggles (vertical Befaco: OR up / MUTE centre / AND down)
		addParam(createParamCentered<BefacoSwitch>(mm2px(Vec(COL_L, BUS_SW_Y)), module, PulsesPlus::MODE_A_PARAM));
		addParam(createParamCentered<BefacoSwitch>(mm2px(Vec(COL_R, BUS_SW_Y)), module, PulsesPlus::MODE_B_PARAM));

		// bus output LEDs
		addChild(createLightCentered<MediumLight<GreenLight>>(mm2px(Vec(COL_L, BUS_LED_Y)), module, PulsesPlus::OUTA_LIGHT));
		addChild(createLightCentered<MediumLight<GreenLight>>(mm2px(Vec(COL_R, BUS_LED_Y)), module, PulsesPlus::OUTB_LIGHT));

		// bus outputs
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(COL_L, OUT_Y)), module, PulsesPlus::OUTA_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(COL_R, OUT_Y)), module, PulsesPlus::OUTB_OUTPUT));
	}

	void appendContextMenu(Menu* menu) override {
		PulsesPlus* module = getModule<PulsesPlus>();
		menu->addChild(new MenuSeparator);
		menu->addChild(createBoolPtrMenuItem("Gate outputs with clock", "", &module->gateWithClock));
		menu->addChild(createBoolPtrMenuItem("AND of empty bus is high", "", &module->andEmptyHigh));
	}
};

Model* modelPulsesPlus = createModel<PulsesPlus, PulsesPlusWidget>("PulsesPlus");
