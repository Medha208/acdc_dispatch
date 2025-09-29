# save_dispatch_scenarios.py
import os
import argparse
import pickle
import numpy as np
import pandas as pd

def save_dispatch_scenarios(res, filename="gridcal_timeseries.xlsx", path="."):
    """
    Export GridCal TimeSeriesResults to an Excel file in a structured, multi-sheet layout.

    Sheets (when available):
      - Bus_Vmag, Bus_Vang, Bus_P, Bus_Q
      - Branch_Pf, Branch_Qf, Branch_Pt, Branch_Qt,
        Branch_Losses_P, Branch_Losses_Q, Branch_dV
      - HVDC_Pf, HVDC_Pt, HVDC_Losses
      - Convergence
      - Names (bus/branch/hvdc/area dictionaries)

    Args:
      res: GridCal TimeSeriesResults
      filename: output Excel filename
      path: directory to write the file into (created if missing)
    """
    # ---------- helpers ----------
    def _as2d(a):
        a = np.asarray(a)
        if a.ndim == 0: a = a.reshape(1, 1)
        elif a.ndim == 1: a = a.reshape(1, -1)
        return a

    def _safe_get(name):
        return getattr(res, name, None)

    def _names(attr_name, n, prefix):
        names = list(getattr(res, attr_name, []))
        if not names or len(names) < n:
            names = [f"{prefix}{i+1}" for i in range(n)]
        return names[:n]

   
   # ---- time axis ----
    T = None
    for key in ("voltage", "S", "Sf", "loading", "hvdc_Pf"):
        a = _safe_get(key)
        if a is not None:
            a = np.asarray(a)
            if a.ndim >= 1:
                T = a.shape[0]
                break

    # force time as 1..T
    t = np.arange(1, (T if T is not None else 1) + 1)

    # ---------- names ----------
    bus_names    = list(getattr(res, "bus_names", []))
    branch_names = list(getattr(res, "branch_names", []))
    hvdc_names   = list(getattr(res, "hvdc_names", []))
    area_names   = list(getattr(res, "area_names", []))

    # ---------- bus results ----------
    V    = _safe_get("voltage")    # complex (T, nb)
    Sbus = _safe_get("S")          # complex (T, nb) in your environment

    Vmag = Vang = Pbus = Qbus = None
    nb = 0

    if V is not None:
        V = _as2d(V)
        Vmag = np.abs(V)
        Vang = np.angle(V, deg=True)
        nb = Vmag.shape[1]
        bus_names = (bus_names[:nb] if bus_names else [f"Bus{i+1}" for i in range(nb)])

    if Sbus is not None:
        Sbus = _as2d(Sbus)
        nb_s = Sbus.shape[1]
        if nb == 0:
            nb = nb_s
            bus_names = (bus_names[:nb] if bus_names else [f"Bus{i+1}" for i in range(nb)])
        Pbus = Sbus.real
        Qbus = Sbus.imag

    # ---------- branch results ----------
    Sf      = _safe_get("Sf")        # complex (T, n_br)
    St      = _safe_get("St")
    losses  = _safe_get("losses")    # complex (T, n_br)
    Vbranch = _safe_get("Vbranch")   # optional

    Pf = Qf = Pt = Qt = Ploss = Qloss = dV = None
    nb_br = 0

    if Sf is not None:
        Sf = _as2d(Sf); Pf, Qf = Sf.real, Sf.imag; nb_br = Sf.shape[1]
    if St is not None:
        St = _as2d(St); Pt, Qt = St.real, St.imag; nb_br = max(nb_br, St.shape[1])
    if losses is not None:
        losses = _as2d(losses); Ploss, Qloss = losses.real, losses.imag; nb_br = max(nb_br, losses.shape[1])
    if Vbranch is not None:
        dV = _as2d(Vbranch); nb_br = max(nb_br, dV.shape[1])

    branch_names = _names("branch_names", nb_br, "Branch")

    # ---------- HVDC ----------
    hvdc_Pf     = _safe_get("hvdc_Pf")
    hvdc_Pt     = _safe_get("hvdc_Pt")
    hvdc_losses = _safe_get("hvdc_losses")
    nhv = 0
    if hvdc_Pf is not None:     hvdc_Pf = _as2d(hvdc_Pf);         nhv = max(nhv, hvdc_Pf.shape[1])
    if hvdc_Pt is not None:     hvdc_Pt = _as2d(hvdc_Pt);         nhv = max(nhv, hvdc_Pt.shape[1])
    if hvdc_losses is not None: hvdc_losses = _as2d(hvdc_losses); nhv = max(nhv, hvdc_losses.shape[1])
    hvdc_names = _names("hvdc_names", nhv, "HVDC")

    # ---------- convergence / errors ----------
    conv = getattr(res, "converged", None)
    err  = getattr(res, "error", None)

    # ---------- helper to make wide sheets ----------
    def _make_wide(arr, names):
        if arr is None: return None
        T_here = arr.shape[0]
        df = pd.DataFrame({"time": t[:T_here]})
        for i, nm in enumerate(names[:arr.shape[1]]):
            df[nm] = arr[:, i]
        return df

    # choose writer engine
    engine = None
    try:
        import openpyxl  # noqa
        engine = "openpyxl"
    except Exception:
        try:
            import xlsxwriter  # noqa
            engine = "xlsxwriter"
        except Exception:
            pass

    os.makedirs(path, exist_ok=True)
    out_path = os.path.join(path, filename)

    with pd.ExcelWriter(out_path, engine=engine) as xl:
        # Names
        meta = []
        for i, nm in enumerate(bus_names):      meta.append(("Bus",    i+1, nm))
        for i, nm in enumerate(branch_names):   meta.append(("Branch", i+1, nm))
        for i, nm in enumerate(hvdc_names):     meta.append(("HVDC",   i+1, nm))
        for i, nm in enumerate(area_names or []): meta.append(("Area", i+1, nm))
        if meta:
            pd.DataFrame(meta, columns=["Type", "Index", "Name"]).to_excel(xl, "Names", index=False)

        # Bus
        if Vmag is not None: _make_wide(Vmag, bus_names).to_excel(xl, "Bus_Vmag", index=False)
        if Vang is not None: _make_wide(Vang, bus_names).to_excel(xl, "Bus_Vang", index=False)
        if Pbus is not None: _make_wide(Pbus, bus_names).to_excel(xl, "Bus_P",    index=False)
        if Qbus is not None: _make_wide(Qbus, bus_names).to_excel(xl, "Bus_Q",    index=False)

        # Branch
        if Pf    is not None: _make_wide(Pf,    branch_names).to_excel(xl, "Branch_Pf", index=False)
        if Qf    is not None: _make_wide(Qf,    branch_names).to_excel(xl, "Branch_Qf", index=False)
        if Pt    is not None: _make_wide(Pt,    branch_names).to_excel(xl, "Branch_Pt", index=False)
        if Qt    is not None: _make_wide(Qt,    branch_names).to_excel(xl, "Branch_Qt", index=False)
        if Ploss is not None: _make_wide(Ploss, branch_names).to_excel(xl, "Branch_Losses_P", index=False)
        if Qloss is not None: _make_wide(Qloss, branch_names).to_excel(xl, "Branch_Losses_Q", index=False)
        if dV    is not None: _make_wide(dV,    branch_names).to_excel(xl, "Branch_dV",          index=False)

        # HVDC
        if hvdc_Pf     is not None: _make_wide(hvdc_Pf,     hvdc_names).to_excel(xl, "HVDC_Pf",     index=False)
        if hvdc_Pt     is not None: _make_wide(hvdc_Pt,     hvdc_names).to_excel(xl, "HVDC_Pt",     index=False)
        if hvdc_losses is not None: _make_wide(hvdc_losses, hvdc_names).to_excel(xl, "HVDC_Losses", index=False)

        # Convergence
        conv_df = pd.DataFrame({"time": t})
        if conv is not None:
            c = np.asarray(conv)
            conv_df["converged"] = (c[:len(t)] if c.ndim else np.repeat(bool(c), len(t)))
        if err is not None:
            conv_df["error"] = np.asarray(err)[:len(t)] if np.ndim(err) else str(err)
        conv_df.to_excel(xl, "Convergence", index=False)

    print(f"✅ Wrote {out_path}")

# --------------- CLI ----------------

def _load_results(pf_results_path):
    ext = os.path.splitext(pf_results_path)[1].lower()
    if ext in (".pkl", ".pickle"):
        with open(pf_results_path, "rb") as f:
            return pickle.load(f)
    raise ValueError("Only pickled results are supported by the CLI. "
                     "Save your TimeSeriesResults with: pickle.dump(res, open('res.pkl','wb'))")

def main():
    parser = argparse.ArgumentParser(
        prog="save_dispatch_scenarios",
        description="Export GridCal TimeSeriesResults to a structured Excel workbook."
    )
    parser.add_argument("--pf_results", required=True,
                        help="Path to pickled TimeSeriesResults (e.g., res.pkl).")
    parser.add_argument("--file_name", default="gridcal_timeseries.xlsx",
                        help="Output Excel filename.")
    parser.add_argument("--path", default=".",
                        help="Output directory (created if missing).")
    args = parser.parse_args()

    res = _load_results(args.pf_results)
    save_dispatch_scenario(res, filename=args.file_name, path=args.path)

if __name__ == "__main__":
    main()
