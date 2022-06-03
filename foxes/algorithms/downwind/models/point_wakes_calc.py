import foxes.variables as FV
import foxes.constants as FC
from foxes.core import PointDataModel, PointDataModelList

class PointWakesCalculation(PointDataModel):

    def __init__(self, point_vars, emodels, emodels_cpars):
        super().__init__()
        self.pvars = point_vars
        self.emodels = emodels
        self.emodels_cpars = emodels_cpars

    def output_point_vars(self, algo):
        if self.pvars is None:
            self.pvars = algo.states.output_point_vars(algo)
        return self.pvars

    def calculate(self, algo, mdata, fdata, pdata):
        
        torder   = fdata[FV.ORDER].astype(FC.ITYPE)
        n_order  = torder.shape[1]
        points   = pdata[FV.POINTS]

        wdeltas = {}
        for w in algo.wake_models:
            w.init_wake_deltas(algo, mdata, fdata, pdata.n_points, wdeltas)

        for oi in range(n_order):

            o = torder[:, oi]
            wcoos = algo.wake_frame.get_wake_coos(algo, mdata, fdata, o, points)
            
            for w in algo.wake_models:
                w.contribute_to_wake_deltas(algo, mdata, fdata, o, wcoos, wdeltas)
        
        amb_res = {v: pdata[FV.var2amb[v]] for v in wdeltas}
        for w in algo.wake_models:
            w.finalize_wake_deltas(algo, mdata, fdata, amb_res, wdeltas)

        for v in self.pvars:
            if v in wdeltas:
                pdata[v] = amb_res[v] + wdeltas[v]
        
        self.emodels.calculate(algo, mdata, fdata, pdata, self.emodels_cpars)

        return {v: pdata[v] for v in self.output_point_vars(algo)}
