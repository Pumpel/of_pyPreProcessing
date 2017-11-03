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
    # The working directory
    os.chdir("")
    # The varibale range of parameter lambdaOb
    lambdaOb = linspace(0.1,0.2,5)
    print(lambdaOb)
    
    # The template case
    template=SolutionDirectory(os.path.join(""))
    
    for lambdaObi in lambdaOb:
        currentCaseName = "2DWedge_grid003_lambdaOb{}".format(lambdaObi)
        print(currentCaseName)
        currentCase = template.cloneCase(path.join(getcwd(), currentCaseName))
        
        
        propertiesFilepath = path.join(currentCase.name, "constant", "viscoelasticProperties")
        parsedPropertiesFile = ParsedParameterFile(propertiesFilepath)
           
        rheologyDict = parsedPropertiesFile["rheology"]
        print(rheologyDict)
        lambdaOb_case = rheologyDict.get('lambdaOb')
        lambdaOb_case[2] = lambdaObi
        print(lambdaOb_case[2])
        parsedPropertiesFile.writeFile()