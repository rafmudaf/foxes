from abc import abstractmethod

from .point_data_model import PointDataModel, PointDataModelList
import foxes.variables as FV


class States(PointDataModel):
    """
    Abstract base class for states.

    States describe ambient meteorological data,
    typically wind speed, wind direction, turbulence
    intensity and air density.

    """

    @abstractmethod
    def size(self):
        """
        The total number of states.

        Returns
        -------
        int:
            The total number of states

        """
        pass

    def index(self):
        """
        The index list

        Returns
        -------
        indices : array_like
            The index labels of states, or None for default integers

        """
        pass

    @abstractmethod
    def weights(self, algo):
        """
        The statistical weights of all states.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        weights : numpy.ndarray
            The weights, shape: (n_states, n_turbines)

        """
        pass

    def model_input_data(self, algo):
        """
        The model input data, as needed for the
        calculation.

        This function is automatically called during
        initialization. It should specify all data
        that is either state or point dependent, or
        intended to be shared between chunks.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        idata : dict
            The dict has exactly two entries: `data_vars`,
            a dict with entries `name_str -> (dim_tuple, data_ndarray)`;
            and `coords`, a dict with entries `dim_name_str -> dim_array`

        """
        idata = {"coords": {}, "data_vars": {}}

        sinds = self.index()
        if sinds is not None:
            idata["coords"][FV.STATE] = sinds

        weights = self.weights(algo)
        if len(weights.shape) != 2:
            raise ValueError(
                f"States '{self.name}': Wrong weights dimension, expecing ({FV.STATE}, {FV.TURBINE}), got shape {weights.shape}"
            )
        if weights.shape[1] != algo.n_turbines:
            raise ValueError(
                f"States '{self.name}': Wrong size of second axis dimension '{FV.TURBINE}': Expecting {algo.n_turbines}, got {weights.shape[1]}"
            )
        idata["data_vars"][FV.WEIGHT] = ((FV.STATE, FV.TURBINE), weights)

        return idata

    def output_point_vars(self, algo):
        """
        The variables which are being modified by the model.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        output_vars : list of str
            The output variable names

        """
        return [FV.WS, FV.WD, FV.TI, FV.RHO]

    def __add__(self, s):
        if isinstance(s, list):
            return ExtendedStates(self, s)
        elif isinstance(s, ExtendedStates):
            if s.states is not self:
                raise ValueError(
                    f"Cannot add extended states, since not based on same states"
                )
            return ExtendedStates(self, s.pmodels.models[1:])
        else:
            return ExtendedStates(self, [s])


class ExtendedStates(States):
    """
    States extended by point data models.

    Parameters
    ----------
    states : foxes.core.States
        The base states to start from
    point_models : list of foxes.core.PointDataModel, optional
        The point models, executed after states

    Attributes
    ----------
    states : foxes.core.States
        The base states to start from
    pmodels : foxes.core.PointDataModelList
        The point models, including states as first model

    """

    def __init__(self, states, point_models=[]):
        super().__init__()
        self.states = states
        self.pmodels = PointDataModelList(models=[states] + point_models)

    def append(self, model):
        """
        Add a model to the list

        Parameters
        ----------
        model : foxes.core.PointDataModel
            The model to add

        """
        self.pmodels.append(model)

    def size(self):
        """
        The total number of states.

        Returns
        -------
        int:
            The total number of states

        """
        return self.states.size()

    def index(self):
        """
        The index list

        Returns
        -------
        indices : array_like
            The index labels of states, or None for default integers

        """
        return self.states.index()

    def weights(self, algo):
        """
        The statistical weights of all states.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        weights : numpy.ndarray
            The weights, shape: (n_states, n_turbines)

        """
        return self.states.weights(algo)

    def initialize(self, algo, verbosity=0):
        """
        Initializes the model.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        verbosity : int
            The verbosity level

        """
        if not self.pmodels.initialized:
            self.pmodels.initialize(algo, verbosity=verbosity)
        super().initialize(algo, verbosity=verbosity)

    def model_input_data(self, algo):
        """
        The model input data, as needed for the
        calculation.

        This function should specify all data
        that depend on the loop variable (e.g. state),
        or that are intended to be shared between chunks.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        idata : dict
            The dict has exactly two entries: `data_vars`,
            a dict with entries `name_str -> (dim_tuple, data_ndarray)`;
            and `coords`, a dict with entries `dim_name_str -> dim_array`

        """
        return self.pmodels.model_input_data(algo)

    def output_point_vars(self, algo):
        """
        The variables which are being modified by the model.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        output_vars : list of str
            The output variable names

        """
        return self.states.output_point_vars(algo)

    def calculate(self, algo, mdata, fdata, pdata):
        """ "
        The main model calculation.

        This function is executed on a single chunk of data,
        all computations should be based on numpy arrays.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        mdata : foxes.core.Data
            The model data
        fdata : foxes.core.Data
            The farm data
        pdata : foxes.core.Data
            The point data

        Returns
        -------
        results : dict
            The resulting data, keys: output variable str.
            Values: numpy.ndarray with shape (n_states, n_points)

        """
        return self.pmodels.calculate(algo, mdata, fdata, pdata)

    def finalize(self, algo, results, clear_mem=False, verbosity=0):
        """
        Finalizes the model.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        results : xarray.Dataset
            The calculation results
        clear_mem : bool
            Flag for deleting model data and
            resetting initialization flag
        verbosity : int
            The verbosity level

        """
        self.pmodels.finalize(algo, results, clear_mem, verbosity)
        super().finalize(algo, results, clear_mem, verbosity)

    def __add__(self, m):
        models = self.pmodels.models[1:]
        if isinstance(m, list):
            return ExtendedStates(self.states, models + m)
        elif isinstance(m, ExtendedStates):
            if m.states is not self.states:
                raise ValueError(
                    f"Cannot add extended states, since not based on same states"
                )
            return ExtendedStates(self.states, models + m.pmodels.models[1:])
        else:
            return ExtendedStates(self.states, models + [m])
