import pandas as pd
from pathlib import Path
import inspect

import foxes
import foxes.variables as FV


class Tests:

    thisdir = Path(inspect.getfile(inspect.currentframe())).parent
    verbosity = 0

    def print(self, *args):
        if self.verbosity:
            print(*args)

    def test(self):

        c = 2000
        cfile = self.thisdir / "flappy" / "results.csv.gz"
        tfile = self.thisdir / "NREL-5MW-D126-H90.csv"
        sfile = self.thisdir / "states.csv.gz"
        lfile = self.thisdir / "test_farm.csv"

        ck = {FV.STATE: c}

        mbook = foxes.models.ModelBook()
        ttype = foxes.models.turbine_types.PCtFile(
            data_source=tfile, var_ws_ct=FV.REWS, var_ws_P=FV.REWS
        )
        mbook.turbine_types[ttype.name] = ttype

        states = foxes.input.states.StatesTable(
            data_source=sfile,
            output_vars=[FV.WS, FV.WD, FV.TI, FV.RHO],
            var2col={FV.WS: "ws", FV.WD: "wd", FV.TI: "ti"},
            fixed_vars={FV.RHO: 1.225},
        )

        farm = foxes.WindFarm()
        foxes.input.farm_layout.add_from_file(
            farm, lfile, turbine_models=[ttype.name], verbosity=0
        )

        algo = foxes.algorithms.Downwind(
            mbook,
            farm,
            states=states,
            rotor_model="centre",
            wake_models=["Jensen_linear_k007"],
            wake_frame="rotor_wd",
            partial_wakes_model="top_hat",
            chunks=ck,
            verbosity=0,
        )

        data = algo.calc_farm()

        df = data.to_dataframe()[
            [FV.AMB_WD, FV.WD, FV.AMB_REWS, FV.REWS, FV.AMB_P, FV.P]
        ]

        self.print()
        self.print("TRESULTS\n")
        self.print(df)

        self.print("\nReading file", cfile)
        fdata = pd.read_csv(cfile)
        self.print(fdata)

        self.print("\nVERIFYING\n")
        df[FV.WS] = df["REWS"]
        df[FV.AMB_WS] = df["AMB_REWS"]

        delta = df.reset_index() - fdata
        self.print(delta)
        self.print(delta.max())
        chk = delta[[FV.AMB_WS, FV.AMB_P, FV.WS, FV.P]].abs()
        self.print(chk.max())

        assert (chk[FV.WS] < 1e-5).all()
        assert (chk[FV.P] < 1e-3).all()
