import numpy as np

from foxes.opt.core import FarmOptProblem
import foxes.variables as FV
import foxes.constants as FC
from foxes.models.wake_frames import YawedWakes

class TuningProblem(FarmOptProblem):
    """
    Tuning the parameters in Porte-Agel

    Parameters
    ----------
    name : str
        The problem's name
    algo : foxes.core.Algorithm
        The algorithm
    runner : foxes.core.Runner, optional
        The runner for running the algorithm
    sel_turbines : list of int, optional
        The turbines selected for optimization,
        or None for all
    calc_farm_args : dict
        Additional parameters for algo.calc_farm()
    kwargs : dict, optional
        Additional parameters for `FarmOptProblem`

    """

    def __init__(
        self,
        name,
        algo,
        vars_names,
        vars_init,
        vars_min=None,
        vars_max=None,
        runner=None,
        sel_turbines=None,
        calc_farm_args={},
        **kwargs,
    ):
        self.vars_names = vars_names
        self.vars_init = vars_init
        self.vars_min = vars_min
        self.vars_max = vars_max

        super().__init__(
            name,
            algo,
            runner,
            pre_rotor=True,
            sel_turbines=sel_turbines,
            calc_farm_args=calc_farm_args,
            **kwargs,
        )

    def var_names_float(self):
        """
        The names of float variables.

        Returns
        -------
        names : list of str
            The names of the float variables

        """
        return self.vars_names

    def initial_values_float(self):
        """
        The initial values of the float variables.

        Returns
        -------
        values : numpy.ndarray
            Initial float values, shape: (n_vars_float,)

        """
        return self.vars_init

    def min_values_float(self):
        """
        The minimal values of the float variables.

        Use -numpy.inf for unbounded.

        Returns
        -------
        values : numpy.ndarray
            Minimal float values, shape: (n_vars_float,)

        """
        return self.vars_min

    def max_values_float(self):
        """
        The maximal values of the float variables.

        Use numpy.inf for unbounded.

        Returns
        -------
        values : numpy.ndarray
            Maximal float values, shape: (n_vars_float,)

        """
        return self.vars_max
    
    def opt2farm_vars_individual(self, vars_int, vars_float):
        """
        Translates optimization variables to farm variables

        Parameters
        ----------
        vars_int : numpy.ndarray
            The integer optimization variable values,
            shape: (n_vars_int,)
        vars_float : numpy.ndarray
            The float optimization variable values,
            shape: (n_vars_float,)

        Returns
        -------
        farm_vars : dict
            The foxes farm variables. Key: var name,
            value: numpy.ndarray with values, shape:
            (n_states, n_sel_turbines)

        """
        farm_vars = {
            FV.PA_ALPHA: np.zeros((self.algo.n_states), dtype=FC.DTYPE),
            FV.PA_BETA: np.zeros((self.algo.n_states), dtype=FC.DTYPE),
        }
        farm_vars[FV.PA_ALPHA][:] = vars_float[0]
        farm_vars[FV.PA_BETA][:] = vars_float[1]
        return farm_vars


    def opt2farm_vars_population(self, vars_int, vars_float, n_states):
        """
        Translates optimization variables to farm variables

        Parameters
        ----------
        vars_int : numpy.ndarray
            The integer optimization variable values,
            shape: (n_pop, n_vars_int)
        vars_float : numpy.ndarray
            The float optimization variable values,
            shape: (n_pop, n_vars_float)
        n_states : int
            The number of original (non-pop) states

        Returns
        -------
        farm_vars : dict
            The foxes farm variables. Key: var name,
            value: numpy.ndarray with values, shape:
            (n_pop, n_states, n_sel_turbines)

        """
        pass
