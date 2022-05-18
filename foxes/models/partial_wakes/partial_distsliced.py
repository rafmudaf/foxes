import numpy as np

from foxes.core import PartialWakesModel
from foxes.models.wake_models.dist_sliced import DistSlicedWakeModel
from foxes.models.rotor_models.grid import GridRotor
from foxes.tools import wd2uv, uv2wd
import foxes.variables as FV
import foxes.constants as FC

class PartialDistSlicedWake(PartialWakesModel):

    def __init__(self, n=None, wake_models=None, wake_frame=None, rotor_model=None, **kwargs):
        super().__init__(wake_models, wake_frame)

        self.rotor_model = rotor_model
        self.grotor      = None if n is None else GridRotor(n=n, calc_vars=[], **kwargs)

    def initialize(self, algo):
        super().initialize(algo)

        if self.rotor_model is None:
            self.rotor_model = algo.rotor_model
        if not self.rotor_model.initialized:
            self.rotor_model.initialize(algo)
            
        for w in self.wake_models:
            if not isinstance(w, DistSlicedWakeModel):
                raise TypeError(f"Partial wakes '{self.name}': Cannot be applied to wake model '{w.name}', since not an DistSlicedWakeModel")

        if self.grotor is None:
            self.grotor = self.rotor_model
        else:
            self.grotor.name = f"{self.name}_grotor"
            self.grotor.initialize(algo)

        self.YZ = self.var("YZ")
        self.W  = self.var(FV.WEIGHT)

    def new_wake_deltas(self, algo, mdata, fdata):

        n_rpoints   = self.grotor.n_rotor_points()
        n_points    = fdata.n_turbines * n_rpoints
        wake_deltas = {}
        for w in self.wake_models:
            w.init_wake_deltas(algo, mdata, fdata, n_points, wake_deltas)

        return wake_deltas

    def contribute_to_wake_deltas(self, algo, mdata, fdata, 
                                    states_source_turbine, wake_deltas):

        # calc coordinates to rotor centres:
        wcoos = self.wake_frame.get_wake_coos(algo, mdata, fdata, states_source_turbine, 
                                                fdata[FV.TXYH])

        # get x coordinates:
        x = wcoos[:, :, 0]
        del wcoos

        # evaluate grid rotor:
        n_states   = fdata.n_states
        n_turbines = fdata.n_turbines
        n_rpoints  = self.grotor.n_rotor_points()
        n_points   = n_turbines * n_rpoints
        points     = self.grotor.get_rotor_points(algo, mdata, fdata).reshape(n_states, n_points, 3)
        wcoos      = self.wake_frame.get_wake_coos(algo, mdata, fdata, states_source_turbine, points)
        yz         = wcoos.reshape(n_states, n_turbines, n_rpoints, 3)[:, :, :, 1:3]
        del points, wcoos

        # evaluate wake models:
        for w in self.wake_models:

            wdeltas, sp_sel = w.calc_wakes_spsel_x_yz(algo, mdata, fdata, 
                                                        states_source_turbine, x, yz)
            
            wsps    = np.zeros((n_states, n_turbines, n_rpoints), dtype=bool)
            wsps[:] = sp_sel[:, :, None]
            wsps    = wsps.reshape(n_states, n_points)
            
            for v, wdel in wdeltas.items():

                d = np.zeros((n_states, n_turbines, n_rpoints), dtype=FC.DTYPE)
                d[sp_sel] = wdel
                d = d.reshape(n_states, n_points)[wsps]

                try:
                    superp = w.superp[v]
                except KeyError:
                    raise KeyError(f"Model '{self.name}': Missing wake superposition entry for variable '{v}' in wake model '{w.name}', found {sorted(list(w.superp.keys()))}")

                wake_deltas[v] = superp.calc_wakes_plus_wake(algo, mdata, fdata, states_source_turbine, 
                                                            wsps, v, wake_deltas[v], d)
                                                            
    def evaluate_results(self, algo, mdata, fdata, wake_deltas, states_turbine, update_amb_res=False):
        
        amb_res   = self.get_data(FV.AMB_RPOINT_RESULTS, mdata)
        rpoints   = self.get_data(FV.RPOINTS, mdata)
        rweights  = self.get_data(FV.RWEIGHTS, mdata)
        wweights  = self.grotor.rotor_point_weights()
        n_wpoints = self.grotor.n_rotor_points()
        n_states, n_turbines, n_rpoints, __ = rpoints.shape
        st_sel    = (np.arange(n_states), states_turbine)

        uv = None
        if FV.WS in amb_res and FV.WD in amb_res:
            wd = amb_res[FV.WD].reshape(n_states, n_turbines, n_rpoints)[st_sel]
            ws = amb_res[FV.WS].reshape(n_states, n_turbines, n_rpoints)[st_sel]
            uv = wd2uv(wd, ws, axis=-1)
            uv = np.einsum('spd,p->sd', uv, rweights)
            del ws, wd
        elif (FV.WS in amb_res and FV.WD not in amb_res) \
            or (FV.WS not in amb_res and FV.WD in amb_res):
            raise KeyError(f"Model '{self.name}': Missing one of the variables '{FV.WS}', '{FV.WD}' in ambient rotor results: {list(amb_res.keys())}")

        wres = {}
        for v, ares in amb_res.items():
            if v == FV.WS:
                wres[v] = np.linalg.norm(uv, axis=-1)
            elif v == FV.WD:
                wres[v] = uv2wd(uv, axis=-1)
            else:
                wres[v] = ares.reshape(n_states, n_turbines, n_rpoints)[st_sel]
                wres[v] = np.einsum('sp,p->s', wres[v], rweights)
            wres[v] = wres[v][:, None]
        del amb_res, uv

        wdel = {}
        for v, d in wake_deltas.items():
            wdel[v] = d.reshape(n_states, n_turbines, n_wpoints)[st_sel]
        for w in self.wake_models:
            w.finalize_wake_deltas(algo, mdata, fdata, wres, wdel)
        for v in wdel.keys():
            wdel[v] = np.einsum('sp,p->s', wdel[v], wweights)[:, None]

        for v in wres.keys():
            if v in wake_deltas:
                wres[v] += wdel[v]
                if update_amb_res:
                    mdata[FV.AMB_RPOINT_RESULTS][v][st_sel] = wres[v]
            wres[v] = wres[v][:, None]
        
        self.rotor_model.eval_rpoint_results(algo, mdata, fdata, wres, np.array([1.]), 
                                                states_turbine=states_turbine)

    def finalize(self, algo, clear_mem=False):
        self.grotor.finalize(algo, clear_mem=clear_mem)
        super().finalize(algo, clear_mem=clear_mem)
