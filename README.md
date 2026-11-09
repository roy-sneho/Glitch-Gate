# ⚡ Glitch Gate

### A clock-glitching learning game | ECE 576

## 🎮 Play the game

**[👉 Click here to play Glitch Gate](https://glitch-gate-ehx7hl9rawazegc8ta5awe.streamlit.app/)**

The game runs in your web browser. **No installation, Python setup, or hardware is required.** Open the link above to begin.

---

## Welcome to Glitch Gate!

Your goal is to explore how a precisely timed **clock glitch** can change the outcome of a password-checking program.

The simulated device expects a password, but you will deliberately submit one with **one incorrect character**. Normally, the program rejects it. Your challenge is to adjust the clock-glitch settings until the simulated device **accepts the incorrect password**.

This is an experiment, not a password-guessing game. You already know that the input is incorrect. The question is: **Can a timing fault change what the program does?**

### What you will learn

By the end of the game, you should be able to:

- Describe how an extra, early clock edge changes the time available for a digital operation.
- Explain the roles of **width**, **offset**, and **ext_offset** in a glitch attempt.
- Distinguish a normal execution from a modeled reset or an authentication bypass.
- Interpret a clock waveform, timing margin, and experimental search map.
- Explain why a timing violation does **not** guarantee a successful attack.

---

## 1. Get familiar with the screen

When you open the game, you will see several areas:

| Area | What it does |
| --- | --- |
| **Challenge setup** (sidebar) | Choose an intentionally incorrect password or start a new challenge. |
| **1. Inject a clock glitch** | Set the three glitch parameters and run an experiment. |
| **2. Observe the response** | See the result, timing measurements, and illustrative clock waveform. |
| **3. Parameter search map** | Compare your recorded attempts using two heatmaps. |
| **Target execution timeline** | Study the virtual program's operations without being given exact cycle numbers. |
| **Why these rules?** | Read the timing assumptions used by the simulator. |
| **4. Explain what happened** | Complete the conceptual questions, a prediction, and a short written explanation. |

The counters near the top show the number of glitch attempts, how many have succeeded, and the current target response.

## 2. Choose your password and establish a baseline

1. In the left sidebar, find **Intentionally wrong password** and choose one of the available inputs. Each choice differs from the expected password by exactly one character.
2. Click **Run baseline (no glitch)**.
3. Observe the target response. With no injected fault, the incorrect password should be rejected: **NORMAL**.

This baseline is your reference point. It shows what the simulated program does before you try changing its clock timing.

> **Tip:** You can change the password later. Doing so starts a fresh run, so record anything you want to keep first.

## 3. Understand the three glitch controls

All three controls start at zero. To create an active glitch, set a **nonzero width** and a **negative offset**, then choose a cycle to target.

| Control | Meaning | What to experiment with |
| --- | --- | --- |
| **width** | How long the extra clock pulse stays high, in model nanoseconds. | Try different pulse durations. A very short pulse may have no effect; a disruptive pulse may produce RESET. |
| **offset** | How early the inserted clock edge occurs relative to the normal rising edge, in model nanoseconds. | Move the early edge closer to or farther from the normal edge. Negative values indicate an earlier edge. |
| **ext_offset** | The virtual clock cycle in which the glitch is injected. | Move the injection to different parts of the password-checking operation. The selectable range is **0–20**. |

**Remember:** `offset` changes the *timing within a cycle*, while `ext_offset` changes *which cycle* is targeted. They are not interchangeable.

### Why does timing matter?

The model uses a nominal clock period **T** and an earlier edge at **T + offset**. It checks whether the operation has enough time to complete before that edge.

The displayed timing margin is:

```text
Timing margin = Available sampling interval − (Path delay + Setup time)
```

- A **positive margin** means the operation has sufficient time under the model's assumptions.
- A **negative margin** indicates an assumed setup-time violation.
- A negative margin **does not automatically mean SUCCESS**. The result also depends on the targeted operation and glitch conditions.

You do not need to calculate every margin by hand. The game displays the measurements after an experiment; use them to explain what happened.

## 4. Perform your first glitch experiment

1. Keep your intentionally wrong password selected.
2. Choose a pulse **width greater than zero**.
3. Choose a **negative offset**.
4. Set an **ext_offset** between 0 and 20.
5. Click **⚡ Inject Glitch**.
6. Read the result in **2. Observe the response**.
7. Change one or more parameters and try again.

**Attempts are unlimited.** Treat each attempt as an experiment rather than a guess. A useful strategy is to hold two settings constant while changing the third, so you can see what that variable affects.

### Understanding the three possible outcomes

| Result | Color | Interpretation |
| --- | --- | --- |
| **NORMAL** | 🔵 Blue | The incorrect password is rejected. The glitch may be ineffective, or the operation may still complete safely. |
| **RESET** | 🔴 Red | The simulated disturbance is too disruptive for the modeled execution to continue normally. |
| **SUCCESS** | 🟢 Green | The simulated program accepts the incorrect password because the fault model produces an authentication-bypass effect. |

Your task is to find **SUCCESS** and understand *why* your chosen settings led to it. Do not assume that making a glitch stronger always makes an attack better.

## 5. Read the waveform and timing feedback

After running an experiment, examine the clock plot:

- **Normal clock (blue):** The reference clock without the injected early pulse.
- **Glitched clock (orange):** The clock with your selected extra pulse.
- **Nominal edge:** The ordinary rising edge.
- **Early edge:** Where the extra edge is introduced by your offset setting.

You will also see these measurements:

| Measurement | Meaning |
| --- | --- |
| **Sampling interval** | Time available to the selected operation after moving the edge earlier. |
| **Delay + setup** | Time the operation needs according to the virtual timing model. |
| **Timing margin** | The difference between the available interval and the required time. |

Compare the measurements with the outcome. For example, ask yourself whether the extra edge came too early, whether the pulse was effective, and whether the targeted operation was relevant to authentication.

## 6. Use the parameter search maps

Open the **3. Parameter search map** tab after making some glitch attempts.

The heatmaps show **results you have actually tested**. Gray cells mean not tested. Other colors show the observed outcomes: **blue for NORMAL, red for RESET, and green for SUCCESS.**

### Heatmap A — Search the virtual clock cycles

This view compares:

- **Horizontal axis:** `ext_offset` (the cycle you target).
- **Vertical axis:** `offset` (how early the edge is placed).
- **Fixed parameter:** `width`, chosen using **Show attempts with this width**.

Use this map when you want to compare attempts across different virtual cycles. If you tested multiple widths, select the width you want to inspect; the map will show only experiments at that width.

### Heatmap B — Fine-tune around a tested cycle

This view compares:

- **Horizontal axis:** `offset`.
- **Vertical axis:** `width`.
- **Fixed parameter:** `ext_offset`, chosen using **Inspect one tested ext_offset**.

Use this map after you have decided which cycle to investigate more closely. Holding the cycle fixed lets you compare how pulse width and edge timing affect the result.

### Focus and attempt history

- Turn on **Focus heatmaps on explored / observed SUCCESS region** to zoom into the tested area or an observed successful neighborhood.
- Turn off **Focus** to view a wider parameter range.
- Open **Attempt history and CSV export** to review the actual settings and results behind the colored cells.
- Use **Download results (CSV)** if you want a record of your experiments.

**Important:** A colored cell reports an *observation*. It does not prove that adjacent, untested settings will behave the same way.

## 7. Explore the execution timeline

Open **Target execution timeline** to see a simplified sequence of operations performed by the virtual password-checking program.

The timeline shows **what kinds of operations occur**, but deliberately hides their precise cycle numbers. Use the `ext_offset` control and your observations to explore when the glitch is applied.

The **Why these rules?** tab explains the simplified model used for clock edges, timing violations, and possible outcomes. Consult it when you need to connect an experimental result to a timing concept.

## 8. Complete the learning assessment

Once you have explored the game, scroll to **4. Explain what happened**.

1. Answer the **four multiple-choice questions** about the fault model and glitch parameters.
2. Answer the **Prediction** question. The game selects one scenario for the challenge. Read the displayed width, offset, and target operation, then predict **NORMAL**, **RESET**, or **SUCCESS**.
3. Write a short explanation in **Explain your prediction using the waveform and timing rules**. Explain *why* you expect that outcome, not just which outcome you chose.
4. Click **Check learning answers** to submit.

After submission, the app shows the correct answers, whether your prediction matched the model's result, and an example explanation for your selected scenario. 


## 9. Start another challenge

Use **🔄 New challenge / new trigger alignment** in the sidebar if you want to try again.

A new challenge clears the previous attempt history and response, resets the three sliders to zero, and changes the simulated trigger alignment. 

---

## About this simulation

Glitch Gate is a **software-only educational model** inspired by the ChipWhisperer clock-glitching password-bypass exercise. The clock waveforms, timing values, and rules that convert timing violations into program effects are **illustrative assumptions**. They are **not measurements from a physical chip**, and SUCCESS in this game is not evidence that the same parameter values would work on real hardware.

The goal is to understand the relationship between **clock timing, instruction effects, and authentication behavior** in a controlled learning environment.

**Ready to try? [Play Glitch Gate in your browser](https://glitch-gate-ehx7hl9rawazegc8ta5awe.streamlit.app/).**

