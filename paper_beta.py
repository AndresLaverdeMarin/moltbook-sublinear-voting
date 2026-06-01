"""Beta-fitting code copied verbatim from the paper's repository, so every beta in
this analysis is computed with the authors' exact method.

Source: github.com/giordano-demarzo/moltbook-api-crawler
  - `bin_and_average`  -> repo/analysis_scripts/figure3_popularity.py
  - `fit_power_law`    -> repo/analysis_scripts/figure_style.py

The repo fits the upvotes-vs-size exponent (Figure 3a) by: log-binning size,
averaging the metric per bin (>=5 points/bin), then taking the log-log slope of the
bin means over bins >= 2 via np.polyfit. `fit_beta` below wraps those two functions
to reproduce that exact procedure for any (size, value) pair.
"""
import numpy as np


# ----- verbatim from repo/analysis_scripts/figure3_popularity.py -----
def bin_and_average(x_vals, y_vals, num_bins=30):
    """Bin x values logarithmically and compute average y per bin with 10-90% quantiles."""
    x_vals = np.array(x_vals)
    y_vals = np.array(y_vals)

    # Filter positive values
    mask = (x_vals > 0) & (y_vals >= 0)
    x_vals = x_vals[mask]
    y_vals = y_vals[mask]

    if len(x_vals) < 10:
        return np.array([]), np.array([]), np.array([]), np.array([])

    # Create logarithmic bins
    log_bins = np.logspace(np.log10(x_vals.min()), np.log10(x_vals.max()), num_bins)

    bin_centers = []
    bin_means = []
    bin_lo = []
    bin_hi = []

    for i in range(len(log_bins) - 1):
        mask = (x_vals >= log_bins[i]) & (x_vals < log_bins[i + 1])
        if mask.sum() >= 5:  # Require at least 5 points per bin
            bin_centers.append(np.sqrt(log_bins[i] * log_bins[i + 1]))
            bin_means.append(np.mean(y_vals[mask]))
            bin_lo.append(np.percentile(y_vals[mask], 10))
            bin_hi.append(np.percentile(y_vals[mask], 90))

    return np.array(bin_centers), np.array(bin_means), np.array(bin_lo), np.array(bin_hi)


# ----- verbatim from repo/analysis_scripts/figure_style.py -----
def fit_power_law(x, y, x_min=None, x_max=None):
    """Fit power law to data in log-log space. Returns (exponent, prefactor)."""
    mask = np.ones(len(x), dtype=bool)
    if x_min is not None:
        mask &= (x >= x_min)
    if x_max is not None:
        mask &= (x <= x_max)

    if mask.sum() < 3:
        return None, None

    log_x = np.log10(x[mask])
    log_y = np.log10(y[mask])
    coeffs = np.polyfit(log_x, log_y, 1)

    return coeffs[0], 10**coeffs[1]


# ----- wrapper reproducing the repo's Figure 3a beta procedure -----
def fit_beta(size, value, x_min=2, x_max=None, num_bins=30):
    """Beta of <value> vs <size> using the paper's method (Figure 3a).

    Log-bin size and average value per bin (`bin_and_average`, >=5 pts/bin), then fit
    the log-log slope of the bin means over bins in [x_min, x_max] (`fit_power_law`).
    Returns (beta, n_bins_fit); (nan, n) when there are too few points/bins to fit.
    """
    x_bins, y_means, _, _ = bin_and_average(np.asarray(size, float), np.asarray(value, float),
                                            num_bins=num_bins)
    if x_bins.size == 0:
        return np.nan, 0
    mask = np.ones(len(x_bins), dtype=bool)
    if x_min is not None:
        mask &= (x_bins >= x_min)
    if x_max is not None:
        mask &= (x_bins <= x_max)
    n = int(mask.sum())
    exp, _ = fit_power_law(x_bins, y_means, x_min=x_min, x_max=x_max)
    if exp is None:
        return np.nan, n
    return exp, n
