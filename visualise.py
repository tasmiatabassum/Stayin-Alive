"""
visualise.py  —  Simulation & Modelling Presentation Figures
=============================================================
6-panel figure covering every stochastic model in the project.

  A  Gap Acceptance       real recorded data + log-normal MLE fit per character
  B  Poisson Arrivals     Exp(λ) PDFs showing how inter-arrival time shrinks
  C  Speed Distributions  truncated-normal KDE per lane (bimodal middle visible)
  D  Lane Activation      Bernoulli p_lane curves by round
  E  Vehicle Composition  weighted-categorical proportions by round
  F  NaSch Space-Time     CA simulation showing emergent phantom traffic jams

Run:  python visualise.py
Out:  simulation_figures.png  (300 dpi)
"""

import json, math, random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from scipy.stats import lognorm, expon, gaussian_kde

random.seed(42)
np.random.seed(42)

# ── Colour palette ───────────────────────────────────────────────────────
BG     = "#0f1117"
PANEL  = "#1a1d27"
GRID   = "#2a2d3a"
WHITE  = "#e8e8f0"
DIM    = "#6b6d80"

C_NEAR   = "#ff6b6b"
C_MID    = "#ffd93d"
C_FAR    = "#6bceff"
C_BADRUL = "#b9e901"
C_MRIT   = "#fc9ee8"

ROUND_PALETTE = ["#3a86ff", "#06d6a0", "#ffd93d", "#ff6b6b", "#c77dff"]

# ════════════════════════════════════════════════════════════════════════
#  Model helpers  (no pygame dependency)
# ════════════════════════════════════════════════════════════════════════

def truncnorm_samples(mean, std, lo, hi, n):
    out = []
    while len(out) < n:
        batch = np.random.normal(mean, std, n * 6)
        batch = batch[(batch >= lo) & (batch <= hi)]
        out.extend(batch.tolist())
    return np.array(out[:n])


def speed_batch(vtype, lane, rnd, n=600):
    base = {"car": (3.0, 6.0), "motorcycle": (5.0, 9.0),
            "bus": (2.0, 4.0), "truck": (2.0, 4.0)}
    lo, hi  = base[vtype]
    boost   = (rnd - 1) * 0.25
    new_hi  = hi + boost

    if lane == 3:
        mean = lo + (hi - lo) * 0.30 + boost * 0.60
        std  = 0.50 + (rnd - 1) * 0.03
        return truncnorm_samples(mean, std, lo, new_hi, n)

    if lane == 1:
        mean = lo + (hi - lo) * 0.75 + boost
        std  = 0.90 + (rnd - 1) * 0.06
        return truncnorm_samples(mean, std, lo, new_hi, n)

    # lane 2 — bimodal
    std  = 1.20 + (rnd - 1) * 0.07
    slow = truncnorm_samples(lo + (hi - lo)*0.25 + boost*0.70, std, lo, new_hi, n//2)
    fast = truncnorm_samples(lo + (hi - lo)*0.75 + boost,      std, lo, new_hi, n - n//2)
    arr  = np.concatenate([slow, fast])
    np.random.shuffle(arr)
    return arr


def lane_probs(r):
    return (min(0.90, 0.50 + r*0.05),
            min(0.80, 0.15 + r*0.08),
            min(0.75, 0.10 + r*0.07))


def vtype_weights_norm(r):
    raw = {"Car":        max(1.0, 8.0 - r*0.5),
           "Motorcycle": min(6.0, 0.5 + r*0.6),
           "Bus":        min(5.0, r*0.4),
           "Truck":      min(4.0, r*0.3)}
    tot = sum(raw.values())
    return {k: v/tot for k, v in raw.items()}


def spawn_freq(r):
    return max(15.0, 40.0 - r*3.0)


def run_nasch(cells=150, n_veh=38, v_max=5, p_slow=0.25, steps=100):
    pos = sorted(random.sample(range(cells), n_veh))
    vel = [v_max]*n_veh
    grid = np.zeros((steps, cells), dtype=np.int8)
    for t in range(steps):
        for p in pos:
            grid[t, p] = 1
        np_new, nv_new = pos[:], vel[:]
        for i in range(n_veh):
            nxt  = (i+1) % n_veh
            gap  = (pos[nxt] - pos[i] - 1) % cells
            nv_new[i] = min(vel[i]+1, v_max)
            nv_new[i] = min(nv_new[i], gap)
            if random.random() < p_slow:
                nv_new[i] = max(0, nv_new[i]-1)
            np_new[i] = (pos[i]+nv_new[i]) % cells
        pos, vel = np_new, nv_new
    return grid

# ════════════════════════════════════════════════════════════════════════
#  Load real gap data
# ════════════════════════════════════════════════════════════════════════

with open("gap_acceptance_log.json") as f:
    log_data = json.load(f)

real_gaps   = {}
ln_params   = {}

for session in log_data:
    char = session["character"]
    gaps = [e["time_gap_s"] for e in session["events"] if e["time_gap_s"] < 90]
    real_gaps[char] = gaps
    s = session["summary"]
    if s.get("lognormal_mu") and s.get("lognormal_sigma"):
        ln_params[char] = (s["lognormal_mu"], s["lognormal_sigma"])

# ════════════════════════════════════════════════════════════════════════
#  Figure layout
# ════════════════════════════════════════════════════════════════════════

fig = plt.figure(figsize=(20, 13), facecolor=BG)
fig.suptitle(
    "Stayin' Alive in Boardbazar  ·  Stochastic Traffic Simulation Models",
    color=WHITE, fontsize=16, fontweight="bold", y=0.985,
    fontfamily="monospace"
)

gs = gridspec.GridSpec(2, 3, figure=fig,
                       hspace=0.44, wspace=0.30,
                       left=0.06, right=0.97,
                       top=0.92,  bottom=0.07)

axes = [fig.add_subplot(gs[r, c]) for r in range(2) for c in range(3)]


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=WHITE, fontsize=11, fontweight="bold",
                 fontfamily="monospace", pad=8)
    ax.set_xlabel(xlabel, color=DIM, fontsize=8.5)
    ax.set_ylabel(ylabel, color=DIM, fontsize=8.5)
    ax.tick_params(colors=DIM, labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID)
    ax.grid(color=GRID, linewidth=0.5, linestyle="--", alpha=0.55)


# ── Panel A  Gap Acceptance + Log-Normal MLE ─────────────────────────────

ax = axes[0]
style(ax, "A   Gap Acceptance Model",
      "Time gap to nearest vehicle (s)", "Density")

x_pdf = np.linspace(0.01, 8.0, 300)
char_cfg = [("Badrul",   C_BADRUL, "o"), ("Mrittika", C_MRIT, "s")]
leg_handles = []

for char, col, marker in char_cfg:
    gaps = real_gaps.get(char, [])
    if not gaps:
        continue
    # Rug
    ax.plot(gaps, np.full(len(gaps), -0.04),
            marker="|", color=col, markersize=16,
            linewidth=1.8, alpha=0.9, clip_on=False)
    # Dots
    ax.scatter(gaps, np.zeros(len(gaps)), color=col,
               s=60, zorder=5, alpha=0.9, marker=marker)
    # Log-normal fit curve
    if char in ln_params:
        mu, sig = ln_params[char]
        pdf = lognorm.pdf(x_pdf, s=sig, scale=math.exp(mu))
        ax.plot(x_pdf, pdf, color=col, linewidth=2.2)
        leg_handles.append(Line2D([0],[0], color=col, lw=2.2,
            label=f"{char}  (μ={mu:.2f}, σ={sig:.2f})"))

# Literature baseline
lit = lognorm.pdf(x_pdf, s=0.50, scale=math.exp(1.2))
ax.plot(x_pdf, lit, color=DIM, lw=1.5, linestyle=":")
leg_handles.append(Line2D([0],[0], color=DIM, lw=1.5, linestyle=":",
    label="Literature baseline\n(Petzoldt 2014)"))

mean_b = sum(real_gaps["Badrul"]) / len(real_gaps["Badrul"])
ax.axvline(mean_b, color=C_BADRUL, lw=0.9, linestyle="--", alpha=0.55)
ax.text(mean_b+0.08, 0.52, f"x̄={mean_b:.2f}s", color=C_BADRUL, fontsize=7.5)

ax.set_xlim(0, 7.5);  ax.set_ylim(-0.10, 0.82)
ax.legend(handles=leg_handles, facecolor=PANEL, edgecolor=GRID,
          labelcolor=WHITE, fontsize=8, loc="upper right")


# ── Panel B  Poisson Arrivals ────────────────────────────────────────────

ax = axes[1]
style(ax, "B   Poisson Arrival Process  (Exponential inter-arrival)",
      "Frames until next vehicle", "Probability density")

x_fr = np.linspace(0, 110, 400)
for i, r in enumerate([1, 3, 5, 7, 9]):
    lam = 1.0 / spawn_freq(r)
    pdf = expon.pdf(x_fr, scale=spawn_freq(r))
    col = ROUND_PALETTE[i]
    ax.plot(x_fr, pdf, color=col, lw=2.0,
            label=f"Round {r}  E[T]={spawn_freq(r):.0f} fr")
    ax.fill_between(x_fr, pdf, alpha=0.07, color=col)

ax.set_xlim(0, 100);  ax.set_ylim(bottom=0)
ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=WHITE,
          fontsize=8, loc="upper right")


# ── Panel C  Lane-Dependent Speed KDE ───────────────────────────────────

ax = axes[2]
style(ax, "C   Lane-Dependent Speed Distributions  (Round 3)",
      "Speed (px / frame)", "Density")

x_spd = np.linspace(1.5, 10.5, 400)
lane_cfg = [(3, C_NEAR, "Near  (residential)"),
            (2, C_MID,  "Middle  (bimodal)"),
            (1, C_FAR,  "Far  (highway)")]

for lane, col, lbl in lane_cfg:
    samp = speed_batch("car", lane, rnd=3, n=900)
    kde  = gaussian_kde(samp, bw_method=0.22)
    pdf  = kde(x_spd)
    ax.plot(x_spd, pdf, color=col, lw=2.2, label=lbl)
    ax.fill_between(x_spd, pdf, alpha=0.10, color=col)

ax.annotate("bimodal peaks\n(slow trucks + fast motos)",
            xy=(3.6, 0.20), xytext=(5.8, 0.35),
            color=C_MID, fontsize=7.5, ha="center",
            arrowprops=dict(arrowstyle="->", color=C_MID, lw=1.0))

ax.set_xlim(1.5, 10);  ax.set_ylim(bottom=0)
ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=WHITE, fontsize=8)


# ── Panel D  Bernoulli Lane Activation ──────────────────────────────────

ax = axes[3]
style(ax, "D   Bernoulli Lane Activation  p_lane vs Round",
      "Round", "Activation probability")

rounds = np.arange(1, 13)
pn = [lane_probs(r)[0] for r in rounds]
pm = [lane_probs(r)[1] for r in rounds]
pf = [lane_probs(r)[2] for r in rounds]

for ydata, col, lbl, mk in [(pn, C_NEAR, "Near lane",   "o"),
                              (pm, C_MID,  "Middle lane", "s"),
                              (pf, C_FAR,  "Far lane",   "^")]:
    ax.plot(rounds, ydata, color=col, lw=2.2, marker=mk, ms=5, label=lbl)
    ax.fill_between(rounds, ydata, alpha=0.08, color=col)

ax.axhline(0.5, color=WHITE, lw=0.8, linestyle=":", alpha=0.35)
ax.text(12.15, 0.51, "p=0.5", color=DIM, fontsize=7.5, va="bottom")
ax.set_xlim(1, 12);  ax.set_ylim(0, 1.0);  ax.set_xticks(rounds)
ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=WHITE, fontsize=8)


# ── Panel E  Vehicle Type Composition ───────────────────────────────────

ax = axes[4]
style(ax, "E   Vehicle Composition  (Weighted Categorical)",
      "Round", "Proportion of traffic")

rounds_e = list(range(1, 13))
vtypes   = ["Car", "Motorcycle", "Bus", "Truck"]
v_cols   = ["#3a86ff", "#ff6b6b", "#ffd93d", "#c77dff"]

bottom = np.zeros(len(rounds_e))
for vt, col in zip(vtypes, v_cols):
    vals = np.array([vtype_weights_norm(r)[vt] for r in rounds_e])
    ax.bar(rounds_e, vals, bottom=bottom, color=col,
           alpha=0.85, label=vt, width=0.72)
    for i, (b, v) in enumerate(zip(bottom, vals)):
        if v > 0.09:
            ax.text(rounds_e[i], b + v/2, f"{v:.0%}",
                    ha="center", va="center",
                    fontsize=6.5, color="black", fontweight="bold")
    bottom += vals

ax.set_xlim(0.3, 12.7);  ax.set_ylim(0, 1.0)
ax.set_xticks(rounds_e)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=WHITE,
          fontsize=8, loc="upper right", ncol=2)


# ── Panel F  NaSch Space-Time Diagram ───────────────────────────────────

ax = axes[5]
style(ax, "F   Nagel-Schreckenberg CA  —  Phantom Traffic Jams",
      "Road position (cells)", "Time step")

nasch = run_nasch()
ax.imshow(nasch, cmap="inferno", aspect="auto",
          interpolation="nearest", origin="upper",
          extent=[0, 150, 100, 0])

# Mark a phantom jam
col_sum  = nasch.sum(axis=0)
jam_x    = int(np.argmax(np.convolve(col_sum, np.ones(5), 'same')))
ax.annotate("phantom jam\n(spontaneous, no obstacle)",
            xy=(jam_x, 55), xytext=(min(jam_x+28, 130), 22),
            color=WHITE, fontsize=8, ha="center",
            arrowprops=dict(arrowstyle="->", color=WHITE, lw=1.0))

ax.text(2, 97, f"p_slow=0.25  ·  {38} vehicles  ·  v_max=5  ·  periodic boundary",
        color=DIM, fontsize=7)

ax.set_ylabel("← earlier      Time step      later →", color=DIM, fontsize=8)


# ════════════════════════════════════════════════════════════════════════
#  Save
# ════════════════════════════════════════════════════════════════════════

out = "simulation_figures.png"
fig.savefig(out, dpi=300, bbox_inches="tight", facecolor=BG)
print(f"Saved → {out}")
plt.close(fig)