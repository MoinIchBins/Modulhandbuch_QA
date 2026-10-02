# Base search method

The canonical run uses the explicit coarse grids in `artifacts/experiments/base/configs/coarse.json` and adaptive local refinement in `fine.json`. Fine brackets come from neighboring coarse values, with 201 points per interval, edge extension clipped to configured bounds, retention of the coarse winner, and deduplication. The old quantile-based range note is preserved with the historical first run. See the root README for the complete stage order.
