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
    # The varibale range of parameter alpha
    alpha = linspace(0.01,1.0,5)
    print(alpha)
    
    # The template case
    template=SolutionDirectory(os.path.join("/media/timo/sharedParti/cp501/parameterStudies/2DWedge_grid003_template_001"))
    
    for alphai in alpha:
        currentCaseName = "2DWedge_grid003_alpha{}".format(alphai)
        print(currentCaseName)
        currentCase = template.cloneCase(path.join(getcwd(), currentCaseName))
        
        
        propertiesFilepath = path.join(currentCase.name, "constant", "viscoelasticProperties")
        parsedPropertiesFile = ParsedParameterFile(propertiesFilepath)
           
        rheologyDict = parsedPropertiesFile["rheology"]
        print(rheologyDict)
        alpha_case = rheologyDict.get('alpha')
        alpha_case[2] = alphai
        print(alpha_case[2])
        parsedPropertiesFile.writeFile()