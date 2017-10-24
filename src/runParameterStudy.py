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
    os.chdir("/media/timo/linuxSimData/compMultiphaseCavitation_validation/Branches/master/kunz_ParameterStudy")
    var = linspace(100,150,6)
    template=SolutionDirectory(os.path.join("/media/timo/linuxSimData/compMultiphaseCavitation_validation/standardSolverCoarseTests_template", "step_coarse_kunz"))
    
    for vari in var:
        currentCaseName = "kunz_CcCv_{}".format(vari)
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