# ⚡ Glitch Gate

**ECE 576 | Interactive Clock Glitching Challenge**| Estimated Time: 20-30 minutes

## 🎮 Play the Game

**[Click Here to Play Glitch Gate](https://glitch-gate-ehx7hl9rawazegc8ta5awe.streamlit.app/)**

## About the Game

Glitch Gate is an interactive, software-based hardware security challenge inspired by the ChipWhisperer clock-glitching exercises.

Your objective is to experiment with clock-glitch parameters and complete the authentication challenge. You will observe the simulated device's behavior, analyze your experiments, and answer questions about your findings.

## ⏱ Estimated Completion Time

**20–30 minutes**

## Setup Requirements

- A computer with a modern web browser
- An internet connection
- No installation or additional hardware required

## How to Play

### Step 1: Start the Challenge

Open the game using the link above. In the left sidebar, choose an intentionally incorrect password. You can also click **New challenge / new trigger alignment** to start a fresh challenge.

### Step 2: Run the Baseline

Click **Run baseline (no glitch)** to observe how the target normally responds before any fault injection.

### Step 3: Configure the Clock Glitch

Use the three sliders in the **Inject a clock glitch** section:

- **Width:** Adjusts the duration of the injected clock pulse.
- **Offset:** Adjusts the timing of the injected edge relative to the normal clock.
- **Ext_offset:** Selects the virtual clock cycle where the glitch is applied.

Click **Inject Glitch** to test the selected parameters.

### Step 4: Observe the Results

After each injection, check the **Observe the response** section.

The game reports one of three outcomes: **NORMAL**, **RESET**, or **SUCCESS**.

You can also examine the clock waveform and timing information associated with your experiment.

### Step 5: Explore the Parameter Search Map

Open **3. Parameter search map** to review your experiments.

The game provides two heatmaps:

- **Cycle Search:** Compare tested `ext_offset` and `offset` combinations while holding width constant.
- **Parameter Fine-Tuning:** Compare tested width and offset combinations at a selected `ext_offset`.

Untested combinations are shown in gray. You can use the focus option to zoom into previously explored regions.

You may continue experimenting as many times as needed.

### Step 6: Complete the Learning Assessment

Scroll to **4. Explain what happened**.

Answer the multiple-choice questions, make your prediction for the provided glitch settings, and write a brief explanation based on your observations.

Click **Check learning answers** to submit your responses and view the assessment feedback.

## Restarting the Game

You can select another incorrect password or click **New challenge / new trigger alignment** to begin a new experiment.

## Notes

- There is no limit on glitch attempts.
- No physical ChipWhisperer device is required.
- The game is a software-based educational simulation, not an experiment on actual hardware.

---

**ECE 576 — Hardware Security**

*Glitch Gate is intended for educational use.*

