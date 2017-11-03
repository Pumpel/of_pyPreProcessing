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
    os.chdir("/media/timo/sharedParti/cp501/parameterStudies/grid003_parameterStudy_q_001")
    # The varibale range of parameter q
    q = linspace(0.01,1.0,5)
    print(q)
    
    # The template case
    template=SolutionDirectory(os.path.join("/media/timo/sharedParti/cp501/parameterStudies/2DWedge_grid003_template"))
    
    for qi in q:
        currentCaseName = "2DWedge_grid003_q{}".format(qi)
        print(currentCaseName)
        currentCase = template.cloneCase(path.join(getcwd(), currentCaseName))
        
        
        propertiesFilepath = path.join(currentCase.name, "constant", "viscoelasticProperties")
        parsedPropertiesFile = ParsedParameterFile(propertiesFilepath)
           
        rheologyDict = parsedPropertiesFile["rheology"]
        print(rheologyDict)
        q_case = rheologyDict.get('q')
        q_case[2] = qi
        print(q_case[2])
        parsedPropertiesFile.writeFile()