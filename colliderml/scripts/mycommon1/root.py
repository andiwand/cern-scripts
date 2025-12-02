import numpy as np


class TH1:
    def __init__(self, th1_tefficiency, xrange=None):
        try:
            th1 = th1_tefficiency.GetTotalHistogram()
        except:
            th1 = th1_tefficiency

        bins = list(range(1, th1.GetNbinsX() + 1))

        if xrange is not None:
            bins = [
                i
                for i in bins
                if th1.GetBinCenter(i) >= xrange[0] and th1.GetBinCenter(i) <= xrange[1]
            ]

        self.x = np.array([th1.GetBinCenter(i) for i in bins])

        self.x_lo = np.array([th1.GetBinLowEdge(i) for i in bins])
        self.x_width = np.array([th1.GetBinWidth(i) for i in bins])
        self.x_hi = np.add(self.x_lo, self.x_width)
        self.x_err_lo = np.subtract(self.x, self.x_lo)
        self.x_err_hi = np.subtract(self.x_hi, self.x)

        try:
            self.y = np.array([th1_tefficiency.GetEfficiency(i) for i in bins])
            self.y_err_lo = np.array(
                [th1_tefficiency.GetEfficiencyErrorLow(i) for i in bins]
            )
            self.y_err_hi = np.array(
                [th1_tefficiency.GetEfficiencyErrorUp(i) for i in bins]
            )

            self.mask = ~((self.y == 0) & (self.y_err_lo == 0) & (self.y_err_hi == 1))
            self.x = self.x[self.mask].copy()
            self.x_lo = self.x_lo[self.mask].copy()
            self.x_width = self.x_width[self.mask].copy()
            self.x_hi = self.x_hi[self.mask].copy()
            self.x_err_lo = self.x_err_lo[self.mask].copy()
            self.x_err_hi = self.x_err_hi[self.mask].copy()
            self.y = self.y[self.mask].copy()
            self.y_err_lo = self.y_err_lo[self.mask].copy()
            self.y_err_hi = self.y_err_hi[self.mask].copy()
        except Exception:
            self.y = np.array([th1_tefficiency.GetBinContent(i) for i in bins])
            self.y_err_lo = np.array([th1_tefficiency.GetBinError(i) for i in bins])
            self.y_err_hi = np.array([th1_tefficiency.GetBinError(i) for i in bins])

    def errorbar(self, ax, **errorbar_kwargs):
        ax.errorbar(
            self.x,
            self.y,
            yerr=(self.y_err_lo, self.y_err_hi),
            xerr=(self.x_err_lo, self.x_err_hi),
            **errorbar_kwargs,
        )
        return ax

    def step(self, ax, **step_kwargs):
        ax.step(self.x_hi, self.y, **step_kwargs)
        return ax

    def bar(self, ax, **bar_kwargs):
        ax.bar(self.x, height=self.y, yerr=(self.y_err_lo, self.y_err_hi), **bar_kwargs)
        return ax
