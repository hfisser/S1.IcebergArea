import numpy as np
from S1IcebergArea.s1_preprocessing.S1Prep import S1Prep


class Preprocessing:
    def __init__(self) -> None:
        pass

    def preprocess_s1(self, dir_safe):
        """
        Preprocesses Sentinel-1 EW GRDM data. Calibration, geocoding, noise removal (HV channel).
        :param: dir_safe str the directory of the .SAFE folder. Ends on .SAFE.
        :param: dir_out str the directory where the preprocessed Sentinel-1 data shall be written to.
        """        
        s1_prep = S1Prep(dir_safe)
        file_preprocessed = s1_prep.preprocess_s1(3996, 40, True, True, in_decibels=True)  # remove thermal and texture noise, return data in decibels
        s1_prep.cleanup()  # delete tmp files
        return file_preprocessed

    @staticmethod
    def decibels_to_linear(a):
        return np.power(10, np.divide(a, 10))

    @staticmethod
    def linear_to_decibels(a):
        return 10 * np.log10(np.absolute(a))
