from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock

import numpy as np

from lcls_tools.common.devices.magnet import Magnet, MagnetMetadata
from lcls_tools.common.devices.reader import create_magnet
from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurement
try:
    import meme
    from lcls_tools.common.measurements.emittance_measurement import QuadScanEmittance
except ImportError as e:
    raise unittest.SkipTest(
        "Meme package not installed. ",
        "Skipping all tests in test_emittance.py."
    )


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

    def test_measure_with_mocked_beamsize_measurement(self):
        """
        Test to verify correct emittance calculation based on data generated from a
        basic cheetah simulation of a quad and drift element
        """

        # Prepare mock data (generated by cheetah simulation)
        k = np.linspace(-10, 10, 10)
        x_data = np.array(
            [2.11004182e-04, 1.61777833e-04, 1.14536742e-04, 7.24512720e-05,
             4.95130807e-05, 6.79336517e-05, 1.07842716e-04, 1.52933266e-04,
             1.99458518e-04, 2.46393640e-04
             ]) * 1e6
        y_data = np.array(
            [6.22674183e-04, 5.12518862e-04, 4.05981787e-04, 3.07886046e-04,
             2.30726553e-04, 2.01972667e-04, 2.41091911e-04, 3.25417204e-04,
             4.29859007e-04, 5.43555594e-04
             ]) * 1e6

        mock_beamsize_measurements = []
        for i, val in enumerate(k):
            results = MagicMock()
            results.rms_size = [float(x_data[i]), float(y_data[i])]
            mock_beamsize_measurements += [{"fit_results": [results]}]

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
            area="test",
            beam_path=["test"],
            sum_l_meters=None,
            l_eff=0.1
        )

        def mock_function(scan_settings, function):
            for ele in scan_settings:
                function()

        mock_magnet.scan = mock_function

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

        # Instantiate the QuadScanEmittance object
        quad_scan = QuadScanEmittance(
            energy=1e9 * 299.792458 / 1e3,
            scan_values=k,
            magnet=mock_magnet,
            beamsize_measurement=mock_beamsize_measurement,
            n_measurement_shots=1,
            rmat=rmat,
            design_twiss=design_twiss,
            wait_time=1e-3,
        )

        # Call the measure method
        results = quad_scan.measure()

        # Assertions
        assert "x_rms" in results
        assert "y_rms" in results
        assert len(results["x_rms"]) == len(quad_scan.scan_values)
        assert len(results["y_rms"]) == len(quad_scan.scan_values)

        # check resulting calculations against cheetah simulation ground truth
        assert np.allclose(
            results["emittance"],
            np.array([1.0e-2, 1.0e-1]).reshape(2, 1),
        )
        assert np.allclose(results["beam_matrix"], np.array(
            [[5.0e-2, -5.0e-2, 5.2e-2],
             [0.3, -0.3, 0.33333328]]
        ))
        assert np.allclose(results["BMAG"][:, 4], 1.0)
