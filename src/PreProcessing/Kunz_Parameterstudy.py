'''
Created on Sep 26, 2017

@author: timo
'''

from PyFoam.RunDictionary.SolutionDirectory     import SolutionDirectory
from PyFoam.RunDictionary.ParsedParameterFile   import ParsedParameterFile

from numpy import linspace
import os
from os import getcwd,path

if __name__ == '__main__':
    os.chdir("/media/timo/linuxSimData/Cavitation/compMultiphaseCavitation_validation/Branches/Features/AcousticCourantNo/RouseMcNown_bluntHead_2D_grid2/parameterStudy_remote")
    var = linspace(100,900,9)
    template=SolutionDirectory("/media/timo/linuxSimData/Cavitation/compMultiphaseCavitation_validation/Branches/Features/AcousticCourantNo/RouseMcNown_bluntHead_2D_grid2/RouseMcNown_bluntHead_2D_grid2_coarse_kunz_template")
    
    for vari in var:
        currentCaseName = "komegaSST_kunz_CcCv_{}".format(vari)
        print(currentCaseName)
        currentCase = template.cloneCase(path.join(getcwd(), currentCaseName))
        propertiesFilepath = path.join(currentCase.name, "constant", "thermophysicalProperties")
        parsedPropertiesFile = ParsedParameterFile(propertiesFilepath)
        
        cavParameterDict = parsedPropertiesFile["KunzCoeffs"]
        print(cavParameterDict)
        CcList = parsedPropertiesFile["KunzCoeffs"].get('Cc')
        CvList = parsedPropertiesFile["KunzCoeffs"].get('Cv')
        CcList[2] = vari
        CvList[2] = vari
        print(parsedPropertiesFile["KunzCoeffs"])
        parsedPropertiesFile.writeFile()