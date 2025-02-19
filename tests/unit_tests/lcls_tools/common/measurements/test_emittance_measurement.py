from unittest import TestCase
from unittest.mock import MagicMock, patch, Mock
from matplotlib import pyplot as plt
import numpy as np

from lcls_tools.common.devices.magnet import Magnet, MagnetMetadata
from lcls_tools.common.devices.reader import create_magnet
from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.frontend.plotting.emittance import plot_quad_scan_result
from lcls_tools.common.measurements.emittance_measurement import QuadScanEmittance
from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurement, ScreenBeamProfileMeasurementResult


class EmittanceMeasurementTest(TestCase):
    def setUp(self) -> None:
        self.options = [
            "TRIM",
            "PERTURB",
            "BCON_TO_BDES",
            "SAVE_BDES",
            "LOAD_BDES",
            "UNDO_BDES",
            "DAC_ZERO",
            "CALIB",
            "STDZ",
            "RESET",
            "TURN_OFF",
            "TURN_ON",
            "DEGAUSS",
        ]
        self.ctrl_options_patch = patch("epics.PV.get_ctrlvars", new_callable=Mock)
        self.mock_ctrl_options = self.ctrl_options_patch.start()
        self.mock_ctrl_options.return_value = {"enum_strs": tuple(self.options)}
        self.magnet_collection = create_magnet(area="GUNB")
        return super().setUp()

    def test_with_meme(self):
        # TODO: implement this test
        try:
            import meme  # noqa: F401
            # from lcls_tools.common.measurements.emittance_measurement import (
            #    QuadScanEmittance,
            # )  # noqa: F401
        except ImportError:
            import unittest

            raise unittest.SkipTest(
                "Meme package not installed. ",
                "Skipping all tests in test_emittance.py.",
            )

    def test_measure_with_mocked_beamsize_measurement(self):
        """
        Test to verify correct emittance calculation based on data generated from a
        basic cheetah simulation of a quad and drift element.

        The cheetah simulation data is generated by running the following script:
        >>> from cheetah import Segment, Quadrupole, Drift, ParameterBeam
        >>> initial_beam = ParameterBeam.from_twiss(
                beta_x=torch.tensor(5.0),
                alpha_x=torch.tensor(5.0),
                emittance_x=torch.tensor(1e-8),
                beta_y=torch.tensor(3.0),
                alpha_y=torch.tensor(3.0),
                emittance_y=torch.tensor(1e-7),
            )
        >>> beamline = Segment([
            Quadrupole(name=f"Q0", length=torch.tensor(0.1)),
            Drift(length=torch.tensor(1.0))
        ])
        >>> output_beam = beamline.track(initial_beam)

        """
        # define rmat and design twiss
        # design twiss set such that the 5th element of the quad scan is the design
        # setting
        rmat = np.array([[[1, 1.0], [0, 1]], [[1, 1.0], [0, 1]]])
        design_twiss = {
            "beta_x": 0.2452,
            "alpha_x": -0.1726,
            "beta_y": 0.5323,
            "alpha_y": -1.0615,
        }
        # Prepare mock data (generated by cheetah simulation)
        k = np.linspace(-10, 10, 10)
        x_data = (
            np.array(
                [
                    2.11004182e-04,
                    1.61777833e-04,
                    1.14536742e-04,
                    7.24512720e-05,
                    4.95130807e-05,
                    6.79336517e-05,
                    np.nan,
                    1.52933266e-04,
                    1.99458518e-04,
                    2.46393640e-04,
                ]
            )
            * 1e6
        )
        y_data = (
            np.array(
                [
                    6.22674183e-04,
                    np.nan,
                    np.nan,
                    3.07886046e-04,
                    2.30726553e-04,
                    2.01972667e-04,
                    2.41091911e-04,
                    3.25417204e-04,
                    4.29859007e-04,
                    5.43555594e-04,
                ]
            )
            * 1e6
        )

        # run test with and without design_twiss
        for design_twiss_ele in [None, design_twiss]:
            for n_shots in [1, 3]:
                mock_beamsize_measurements = []
                for i, val in enumerate(k):
                    result = MagicMock(ScreenBeamProfileMeasurementResult)
                    result.rms_sizes = np.array(
                        [float(x_data[i]), float(y_data[i])]
                    ).reshape(1, 2)

                    # extend result.rms_sizes to simulate multiple shots
                    result.rms_sizes = np.repeat(result.rms_sizes, n_shots, axis=0)
                    mock_beamsize_measurements += [result]

                # External list to return beam sizes
                external_list = iter(mock_beamsize_measurements)

                # Mock beamsize_measurement
                mock_beamsize_measurement = MagicMock(spec=ScreenBeamProfileMeasurement)
                mock_beamsize_measurement.device = MagicMock(spec=Screen)
                mock_beamsize_measurement.device.resolution = 1.0
                mock_beamsize_measurement.measure = MagicMock(
                    side_effect=lambda _: next(external_list)
                )

                # Mock magnet
                mock_magnet = MagicMock(spec=Magnet)
                mock_magnet.metadata = MagnetMetadata(
                    area="test", beam_path=["test"], sum_l_meters=None, l_eff=0.1
                )

                def mock_function(scan_settings, function):
                    for ele in scan_settings:
                        function()

                mock_magnet.scan = mock_function

                # Instantiate the QuadScanEmittance object
                quad_scan = QuadScanEmittance(
                    energy=1e9 * 299.792458 / 1e3,
                    scan_values=k,
                    magnet=mock_magnet,
                    beamsize_measurement=mock_beamsize_measurement,
                    n_measurement_shots=1,
                    rmat=rmat,
                    design_twiss=design_twiss_ele,
                    wait_time=1e-3,
                )

                # Call the measure method
                result = quad_scan.measure()

                # check outputs based on nans in the data
                assert np.equal(result.quadrupole_pv_values[0], np.concat((k[:6],k[7:]))).all()
                assert np.equal(result.quadrupole_pv_values[1], np.concat((k[:1],k[3:]))).all()

                assert np.allclose(result.rms_beamsizes[0]*1e6, x_data[~np.isnan(x_data)])
                assert np.allclose(result.rms_beamsizes[1]*1e6, y_data[~np.isnan(y_data)])

                # check resulting calculations against cheetah simulation ground truth
                assert np.allclose(
                    result.emittance,
                    np.array([1.0e-2, 1.0e-1]).reshape(2,1),
                )
                assert np.allclose(
                    result.beam_matrix,
                    np.array([[5.0e-2, -5.0e-2, 5.2e-2], [0.3, -0.3, 0.33333328]]),
                )

                if design_twiss_ele is None:
                    assert result.bmag is None
                else:
                    assert np.allclose(result.bmag[0][4], 1.0)

                    # test get_best_bmag method
                    for mode in ["x", "y", "geometric_mean"]:
                        best_bmag = result.get_best_bmag(mode)
                        if mode == "x":
                            assert np.allclose(best_bmag[0], 1.0)
                            assert np.allclose(best_bmag[1], k[4])
                        elif mode == "y":
                            assert np.allclose(best_bmag[0], 1.0)
                            assert np.allclose(best_bmag[1], k[4])
                        elif mode == "geometric_mean":
                            assert np.allclose(best_bmag[0], 1.0, rtol=1e-2)
                            assert np.allclose(best_bmag[1], k[4])

                # test visualization
                fig, ax = plot_quad_scan_result(result)
                assert isinstance(fig, plt.Figure)
                assert isinstance(ax, np.ndarray)
                # plt.show()